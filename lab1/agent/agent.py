"""
The naive agent — a ReAct tool-calling loop running on IBM watsonx Orchestrate.

The agent receives a patient ID and a goal. It decides which tools to call,
in what order, and how to interpret the results. When it has gathered enough
information, it returns structured concerns.

Unlike a LangGraph agent, the loop does not run in this process. The agent
(agent.yaml) and its tools (tools.py) are deployed to Orchestrate with
deploy.py; Orchestrate runs the ReAct cycle (observe, reason, act) on its
side. This module is just a client: it sends one message over the REST API,
waits for the run to finish, and validates the answer.
"""

import logging
import os
import sys
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from pydantic import ValidationError

from lab1.agent.models import PatientConcerns

load_dotenv()
logger = logging.getLogger(__name__)

# Where the agent lives. WXO_INSTANCE_URL is the "API endpoint" shown under
# Settings -> API details in the Orchestrate UI. WXO_API_KEY is an IBM Cloud
# API key for a user with access to that instance.
WXO_INSTANCE_URL = os.environ.get("WXO_INSTANCE_URL", "").rstrip("/")
WXO_API_KEY = os.environ.get("WXO_API_KEY", "")
WXO_AGENT_NAME = os.environ.get("WXO_AGENT_NAME") or os.environ.get("WXO_NAME_PREFIX", "") + "lakeview_inbox_agent"

IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"
RUN_TIMEOUT = 300  # seconds to wait for one agent run
POLL_INTERVAL = 2  # seconds between run status checks
FINAL_STATUSES = {"completed", "failed", "cancelled", "expired", "requires_input"}

# Orchestrate's react_core agents do not support constrained decoding the way
# LangGraph's response_format does, so the model can return malformed JSON.
# When that happens we tell it what was wrong and ask once more.
MAX_FORMAT_RETRIES = 1


def check_orchestrate_config():
    """Verify the Orchestrate connection settings exist. Call at agent startup."""
    missing = [name for name in ("WXO_INSTANCE_URL", "WXO_API_KEY") if not os.environ.get(name)]
    if missing:
        logger.error(
            "Missing %s in .env. See .env-example (watsonx Orchestrate section).",
            ", ".join(missing),
        )
        sys.exit(1)


class _OrchestrateClient:
    """Minimal client for the Orchestrate runs API, authenticated via IBM Cloud IAM."""

    def __init__(self):
        self._token = ""
        self._token_expires = 0.0
        self._agent_id = ""

    def _headers(self) -> dict:
        # IAM tokens last an hour; refresh a minute early.
        if time.time() > self._token_expires - 60:
            resp = requests.post(
                IAM_TOKEN_URL,
                data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": WXO_API_KEY},
                timeout=30,
            )
            resp.raise_for_status()
            body = resp.json()
            self._token = body["access_token"]
            self._token_expires = body["expiration"]
        return {"Authorization": f"Bearer {self._token}"}

    def _get_agent_id(self) -> str:
        if not self._agent_id:
            resp = requests.get(f"{WXO_INSTANCE_URL}/v1/orchestrate/agents", headers=self._headers(), timeout=30)
            resp.raise_for_status()
            matches = [a["id"] for a in resp.json() if a["name"] == WXO_AGENT_NAME]
            if not matches:
                raise RuntimeError(
                    f"Agent '{WXO_AGENT_NAME}' not found on Orchestrate. "
                    "Deploy it first: uv run python -m lab1.agent.deploy"
                )
            self._agent_id = matches[0]
        return self._agent_id

    def run(self, message: str, thread_id: str | None = None) -> tuple[str, str]:
        """Send one message to the agent and wait for its reply.

        Returns (reply_text, thread_id). Pass thread_id back in to continue
        the same conversation.
        """
        payload = {"agent_id": self._get_agent_id(), "message": {"role": "user", "content": message}}
        if thread_id:
            payload["thread_id"] = thread_id
        resp = requests.post(f"{WXO_INSTANCE_URL}/v1/orchestrate/runs", headers=self._headers(), json=payload, timeout=30)
        resp.raise_for_status()
        run = resp.json()

        # Runs are asynchronous: poll until Orchestrate finishes the ReAct loop.
        deadline = time.time() + RUN_TIMEOUT
        while True:
            resp = requests.get(
                f"{WXO_INSTANCE_URL}/v1/orchestrate/runs/{run['run_id']}", headers=self._headers(), timeout=30
            )
            resp.raise_for_status()
            status = resp.json()
            if status.get("status") in FINAL_STATUSES:
                break
            if time.time() > deadline:
                raise TimeoutError(f"Orchestrate run {run['run_id']} did not finish in {RUN_TIMEOUT}s")
            time.sleep(POLL_INTERVAL)

        if status["status"] != "completed":
            raise RuntimeError(f"Orchestrate run {status['status']}: {status.get('last_error')}")

        reply = status["result"]["data"]["message"]
        _log_tool_calls(reply)
        text = "".join(part.get("text", "") for part in reply["content"] if part.get("response_type") == "text")
        return text, run["thread_id"]


def _log_tool_calls(reply: dict):
    """Log which tools the agent chose, from the run's step history."""
    for step in reply.get("step_history") or []:
        for detail in step.get("step_details", []):
            for call in detail.get("tool_calls", []) if detail.get("type") == "tool_calls" else []:
                logger.info("  tool call: %s(%s)", call["name"], call.get("args", {}))


def _strip_code_fence(text: str) -> str:
    """Remove a ```json ... ``` wrapper if the model added one despite instructions."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    return text.strip()


_client = _OrchestrateClient()


def process_patient(patient_id: str) -> PatientConcerns:
    """Run the agent loop for a single patient. Returns structured concerns."""

    # This is the only message we send — the agent takes it from here,
    # calling tools as needed until it has enough info to respond.
    user_message = (
        f"Please review patient {patient_id}. "
        "Start by looking at their messages and record, then investigate "
        "any concerns you find. When done, output your findings."
    )

    logger.info("[%s] Starting agent run on Orchestrate", patient_id)
    text, thread_id = _client.run(user_message)

    # The agent's instructions ask for JSON matching PatientConcerns. Validate
    # it here; if it's malformed, show the model the error and ask again.
    for attempt in range(MAX_FORMAT_RETRIES + 1):
        try:
            structured = PatientConcerns.model_validate_json(_strip_code_fence(text))
            break
        except ValidationError as e:
            if attempt == MAX_FORMAT_RETRIES:
                raise
            logger.warning("[%s] Reply was not valid PatientConcerns JSON; asking again", patient_id)
            text, thread_id = _client.run(
                "Your reply was not valid JSON for the required schema. Error:\n"
                f"{e}\n"
                "Reply again with ONLY the corrected JSON object.",
                thread_id=thread_id,
            )

    # Patch in the patient_id and timestamps — the LLM sometimes gets
    # these wrong or leaves them empty, so we normalize here.
    now = datetime.now(timezone.utc).isoformat()
    for concern in structured.concerns:
        concern.patient_id = patient_id
        if not concern.last_updated:
            concern.last_updated = now

    if not structured.patient_id:
        structured.patient_id = patient_id

    logger.info("[%s] Agent found %d concerns", patient_id, len(structured.concerns))
    return structured
