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
  - Optional WXO_NAME_PREFIX in .env (e.g. "student0_"). Agent, tool, and
    connection names are global to an Orchestrate instance, so attendees
    sharing one instance each deploy under their own prefix.

Usage:
    uv run python -m lab1.agent.deploy
"""

import json
import logging
import os
import re
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
NAME_PREFIX = os.environ.get("WXO_NAME_PREFIX", "")


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
    spec["name"] = NAME_PREFIX + spec["name"]
    spec["tools"] = [NAME_PREFIX + t for t in spec["tools"]]
    return spec


def render_tools_source() -> str:
    """tools.py with NAME_PREFIX applied to each tool name and the connection app_id.

    tools.py itself stays prefix-free so it reads cleanly; the prefix is baked
    into the uploaded copy because tools run inside Orchestrate, where our .env
    doesn't exist.
    """
    source = (AGENT_DIR / "tools.py").read_text()
    if not NAME_PREFIX:
        return source
    source, n_app = re.subn(r'^EHR_APP_ID = "lakeview_ehr"$', f'EHR_APP_ID = "{NAME_PREFIX}lakeview_ehr"',
                            source, flags=re.MULTILINE)
    source, n_tools = re.subn(r"^@tool\((.*)\)\ndef (\w+)\(",
                              lambda m: f'@tool(name="{NAME_PREFIX}{m[2]}", {m[1]})\ndef {m[2]}(',
                              source, flags=re.MULTILINE)
    if n_app != 1 or n_tools == 0:
        sys.exit("Couldn't apply WXO_NAME_PREFIX to tools.py; its EHR_APP_ID or @tool lines changed shape.")
    return source


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

    app_id = NAME_PREFIX + EHR_APP_ID
    if NAME_PREFIX:
        logger.info("Deploying with name prefix %r", NAME_PREFIX)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # 1. Connection: tools read the EHR URL from here instead of hardcoding it.
        connection = yaml.safe_load((AGENT_DIR / "connection.yaml").read_text())
        connection["app_id"] = app_id
        (tmp / "connection.yaml").write_text(yaml.safe_dump(connection, sort_keys=False))
        orchestrate("connections", "import", "-f", str(tmp / "connection.yaml"))
        for env in ("draft", "live"):
            orchestrate("connections", "set-credentials", "-a", app_id, "--env", env, "-e", f"base_url={ehr_api_url}")

        # 2. Tools. Orchestrate packages tools.py and runs it in its own sandbox.
        #    Newly imported tools take a few minutes to become callable.
        (tmp / "tools.py").write_text(render_tools_source())
        orchestrate("tools", "import", "-k", "python", "-f", str(tmp / "tools.py"),
                    "-r", str(REQUIREMENTS), "-a", app_id)

        # 3. Agent.
        (tmp / "agent.yaml").write_text(yaml.safe_dump(render_agent_spec(), sort_keys=False, allow_unicode=True))
        orchestrate("agents", "import", "-f", str(tmp / "agent.yaml"))

    logger.info("Deployed. New tools can take a few minutes before the agent can call them.")


if __name__ == "__main__":
    main()
