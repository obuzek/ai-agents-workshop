"""
Deploy the Lab 1 agent to IBM watsonx Orchestrate.

Imports three things into the active Orchestrate environment:
  1. connection.yaml — a key-value connection holding the EHR API URL
  2. tools.py        — the @tool functions the agent can call
  3. agent.yaml      — the agent, with the JSON output format appended

Prerequisites:
  - The `orchestrate` CLI (ADK), with an environment added and activated:
        orchestrate env add -n workshop -u <WXO_INSTANCE_URL> -t ibm_iam
        orchestrate env activate workshop --api-key <WXO_API_KEY>
  - EHR_API_URL in .env: a public URL for the EHR API (see deploy/ehr-api/).
    Tools run in the cloud, so they can't reach localhost.

Usage:
    uv run python -m lab1.agent.deploy
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from dotenv import load_dotenv

from lab1.agent.models import PatientConcerns

load_dotenv()
logger = logging.getLogger(__name__)

AGENT_DIR = Path(__file__).parent
REQUIREMENTS = AGENT_DIR / "requirements-orchestrate.txt"
EHR_APP_ID = "lakeview_ehr"  # must match EHR_APP_ID in tools.py


def output_schema() -> dict:
    """JSON Schema for PatientConcerns, with $refs inlined so the LLM sees one flat schema."""
    schema = PatientConcerns.model_json_schema(by_alias=True)
    defs = schema.pop("$defs", {})

    def inline(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return inline(defs[node["$ref"].split("/")[-1]])
            # Drop "title" annotations (strings), but keep a *property* named "title" (a dict).
            return {k: inline(v) for k, v in node.items() if not (k == "title" and isinstance(v, str))}
        if isinstance(node, list):
            return [inline(x) for x in node]
        return node

    return inline(schema)


def render_agent_spec() -> dict:
    """Load agent.yaml and append the output format to its instructions.

    LangGraph enforced this format with constrained decoding (response_format).
    Orchestrate's react_core agents don't support that, so we ask for it in the
    prompt and validate the reply in agent.py.
    """
    spec = yaml.safe_load((AGENT_DIR / "agent.yaml").read_text())
    spec["instructions"] += (
        "\nFINAL ANSWER FORMAT:\n"
        "When you have finished investigating, reply with ONLY a JSON object (no prose, "
        "no markdown, no code fences) that validates against this JSON Schema:\n"
        + json.dumps(output_schema(), separators=(",", ":"))
        + "\n"
    )
    return spec


def orchestrate(*args: str):
    """Run an `orchestrate` CLI command, exiting on failure."""
    logger.info("$ orchestrate %s", " ".join(args))
    result = subprocess.run(["orchestrate", *args])
    if result.returncode != 0:
        sys.exit(result.returncode)


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    ehr_api_url = os.environ.get("EHR_API_URL", "")
    if not ehr_api_url.startswith("https://"):
        logger.error("Set EHR_API_URL in .env to the public https:// URL of the EHR API.")
        sys.exit(1)

    # 1. Connection: tools read the EHR URL from here instead of hardcoding it.
    orchestrate("connections", "import", "-f", str(AGENT_DIR / "connection.yaml"))
    for env in ("draft", "live"):
        orchestrate("connections", "set-credentials", "-a", EHR_APP_ID, "--env", env, "-e", f"base_url={ehr_api_url}")

    # 2. Tools. Orchestrate packages tools.py and runs it in its own sandbox.
    #    Newly imported tools take a few minutes to become callable.
    orchestrate("tools", "import", "-k", "python", "-f", str(AGENT_DIR / "tools.py"),
                "-r", str(REQUIREMENTS), "-a", EHR_APP_ID)

    # 3. Agent.
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(render_agent_spec(), f, sort_keys=False, allow_unicode=True)
    try:
        orchestrate("agents", "import", "-f", f.name)
    finally:
        os.unlink(f.name)

    logger.info("Deployed. New tools can take a few minutes before the agent can call them.")


if __name__ == "__main__":
    main()
