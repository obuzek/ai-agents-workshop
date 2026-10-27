"""
Deploy the Lab 1 agent to IBM watsonx Orchestrate.

Imports three things into the active Orchestrate environment:
  1. connection.yaml — a key-value connection holding the EHR API URL and your tenant
  2. tools.py        — the @tool functions the agent can call
  3. agent.yaml      — the agent, with the JSON output format appended

With --pii-plugin (Lab 2), it also imports lab2/orchestrate/pii_output_plugin.py
and attaches it to the agent as an agent_post_invoke plug-in that masks contact
details and identifiers in the answer. Deploying again without the flag
detaches it.

Prerequisites:
  - The `orchestrate` CLI (ADK), with an environment added and activated:
        orchestrate env add -n workshop -u <WXO_INSTANCE_URL> -t ibm_iam
        orchestrate env activate workshop --api-key <WXO_API_KEY>
  - EHR_API_URL and EHR_TENANT in .env (scripts/install.sh writes both): the
    public URL of the shared EHR API and the ID of your copy of the patients.
    Tools run in the cloud, so they can't reach localhost.
  - Optional WXO_NAME_PREFIX in .env (e.g. "student0_"). Agent, tool, and
    connection names are global to an Orchestrate instance, so attendees
    sharing one instance each deploy under their own prefix.

Usage:
    uv run python -m lab1.agent.deploy                 # Lab 1
    uv run python -m lab1.agent.deploy --pii-plugin    # Lab 2: mask PII in answers
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

from lab1.agent.models import PatientConcerns

load_dotenv()
logger = logging.getLogger(__name__)

AGENT_DIR = Path(__file__).parent
REQUIREMENTS = AGENT_DIR / "requirements-orchestrate.txt"
PII_PLUGIN = AGENT_DIR.parent.parent / "lab2" / "orchestrate" / "pii_output_plugin.py"
PII_PLUGIN_NAME = "mask_pii_output"  # the plug-in's function name in PII_PLUGIN
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


def render_agent_spec(pii_plugin: bool = False) -> dict:
    """Load agent.yaml and append the output format to its instructions.

    Orchestrate's react_core agents don't support constrained decoding, so we
    ask for the format in the prompt and validate the reply in agent.py.

    With pii_plugin, the PII output plug-in is attached at agent_post_invoke.
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
    if pii_plugin:
        spec["plugins"] = {"agent_post_invoke": [{"plugin_name": NAME_PREFIX + PII_PLUGIN_NAME}]}
    return spec


def prefix_tool_names(source: str) -> tuple[str, int]:
    """Add name="<NAME_PREFIX><function>" to each one-line @tool(...) decorator."""
    return re.subn(r"^@tool\((.*)\)\ndef (\w+)\(",
                   lambda m: f'@tool(name="{NAME_PREFIX}{m[2]}", {m[1]})\ndef {m[2]}(',
                   source, flags=re.MULTILINE)


def render_tools_source() -> str:
    """tools.py with NAME_PREFIX applied to each tool name and the connection app_id.

    tools.py itself stays prefix-free so it reads cleanly; the prefix is baked
    into the uploaded copy because tools run inside Orchestrate, where our .env
    doesn't exist.
    """
    source = (AGENT_DIR / "tools.py").read_text()
    if not NAME_PREFIX:
        return source
    n_decorators = len(re.findall(r"^@tool\b", source, flags=re.MULTILINE))
    source, n_app = re.subn(rf'^EHR_APP_ID = "{EHR_APP_ID}"$', f'EHR_APP_ID = "{NAME_PREFIX}{EHR_APP_ID}"',
                            source, flags=re.MULTILINE)
    source, n_tools = prefix_tool_names(source)
    if n_app != 1 or n_tools == 0 or n_tools != n_decorators:
        sys.exit("Couldn't apply WXO_NAME_PREFIX to tools.py; its EHR_APP_ID or @tool lines changed shape.")
    return source


def render_pii_plugin_source() -> str:
    """pii_output_plugin.py with NAME_PREFIX applied to the plug-in's name."""
    source = PII_PLUGIN.read_text()
    if not NAME_PREFIX:
        return source
    source, n = prefix_tool_names(source)
    if n != 1:
        sys.exit("Couldn't apply WXO_NAME_PREFIX to pii_output_plugin.py; its @tool line changed shape.")
    return source


def orchestrate(*args: str):
    """Run an `orchestrate` CLI command, exiting on failure."""
    logger.info("$ orchestrate %s", " ".join(args))
    result = subprocess.run(["orchestrate", *args])
    if result.returncode != 0:
        sys.exit(result.returncode)


MODEL_CONNECTION = "workshop_llm_proxy"  # shared by every attendee on the instance


def model_registered(model: str) -> bool:
    """Whether this Orchestrate instance already has the model (full names need --raw)."""
    out = subprocess.run(["orchestrate", "models", "list", "--raw"], capture_output=True, text=True)
    return any(line.strip().lstrip("-◆ ").rstrip(":").strip() == model for line in out.stdout.splitlines())


def ensure_workshop_model(model: str, ehr_api_url: str):
    """Register the agent's model on the Orchestrate instance if no one has yet.

    The workshop model runs through the shared EHR's model proxy. The first
    attendee to deploy registers it; everyone after reuses it.
    """
    if not model.startswith("virtual-model/") or model_registered(model):
        return
    logger.info("Registering the workshop model %s on this Orchestrate instance", model)
    try:
        resp = requests.get(f"{ehr_api_url.rstrip('/')}/workshop/model-access", timeout=30)
        resp.raise_for_status()
        access = resp.json()
    except (requests.RequestException, ValueError):
        sys.exit(f"{model} isn't registered on this Orchestrate instance, and the workshop backend didn't "
                 "provide its settings. Ask the instructor.")

    # The connection holds the proxy token. Several attendees may get here at once,
    # so "already exists" from these commands is fine.
    for args in (["connections", "add", "-a", MODEL_CONNECTION],
                 *(["connections", "configure", "-a", MODEL_CONNECTION, "--env", env, "--kind", "key_value", "--type", "team"]
                   for env in ("draft", "live"))):
        subprocess.run(["orchestrate", *args], capture_output=True, text=True)
    for env in ("draft", "live"):
        orchestrate("connections", "set-credentials", "-a", MODEL_CONNECTION, "--env", env,
                    "-e", f"api_key={access['api_key']}")
    subprocess.run(["orchestrate", "models", "add", "--name", access["model"], "--app-id", MODEL_CONNECTION,
                    "--provider-config", json.dumps({"custom_host": access["custom_host"]})],
                   capture_output=True, text=True)
    if not model_registered(model):
        sys.exit(f"Couldn't register {model} on this Orchestrate instance. Run the deploy again; "
                 "if it fails twice, ask the instructor.")
    logger.info("Registered %s", model)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy the Lab 1 agent to watsonx Orchestrate.")
    parser.add_argument("--pii-plugin", action="store_true",
                        help="also deploy the Lab 2 PII output plug-in and attach it to the agent")
    return parser.parse_args(argv)


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    ehr_api_url = os.environ.get("EHR_API_URL", "")
    tenant = os.environ.get("EHR_TENANT", "")
    if not ehr_api_url.startswith("https://") or not tenant:
        logger.error("Set EHR_API_URL (the public https:// URL of the EHR API) and EHR_TENANT in .env. "
                     "scripts/install.sh writes both.")
        sys.exit(1)

    app_id = NAME_PREFIX + EHR_APP_ID
    if NAME_PREFIX:
        logger.info("Deploying with name prefix %r", NAME_PREFIX)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # 1. Connection: tools read the EHR URL and tenant from here instead of hardcoding them.
        connection = yaml.safe_load((AGENT_DIR / "connection.yaml").read_text())
        connection["app_id"] = app_id
        (tmp / "connection.yaml").write_text(yaml.safe_dump(connection, sort_keys=False))
        orchestrate("connections", "import", "-f", str(tmp / "connection.yaml"))
        for env in ("draft", "live"):
            orchestrate("connections", "set-credentials", "-a", app_id, "--env", env,
                        "-e", f"base_url={ehr_api_url}", "-e", f"tenant={tenant}")

        # 2. Tools. Orchestrate packages tools.py and runs it in its own sandbox.
        #    Newly imported tools take a few minutes to become callable.
        (tmp / "tools.py").write_text(render_tools_source())
        orchestrate("tools", "import", "-k", "python", "-f", str(tmp / "tools.py"),
                    "-r", str(REQUIREMENTS), "-a", app_id)

        # 3. Optional PII plug-in. It must exist before the agent that references it.
        if args.pii_plugin:
            (tmp / "pii_output_plugin.py").write_text(render_pii_plugin_source())
            orchestrate("tools", "import", "-k", "python", "-f", str(tmp / "pii_output_plugin.py"))

        # 4. Agent. Without --pii-plugin the spec has no plugins, which detaches any earlier one.
        spec = render_agent_spec(pii_plugin=args.pii_plugin)
        ensure_workshop_model(spec["llm"], ehr_api_url)
        (tmp / "agent.yaml").write_text(yaml.safe_dump(spec, sort_keys=False, allow_unicode=True))
        orchestrate("agents", "import", "-f", str(tmp / "agent.yaml"))

    logger.info("Deployed. New tools can take a few minutes before the agent can call them.")


if __name__ == "__main__":
    main()
