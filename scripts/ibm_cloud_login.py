"""Connect the workshop to IBM Cloud: save your API key and Orchestrate details into .env.

Asks you to paste your IBM Cloud API key, checks it, shows which user and
account it belongs to, finds the workshop's watsonx Orchestrate instance on its
own, and sets up the `orchestrate` CLI. Safe to re-run: it updates the existing
values and leaves the rest of .env alone.

Usage:
    uv run python scripts/ibm_cloud_login.py                  # paste your key when asked
    uv run python scripts/ibm_cloud_login.py path/to/apikey.json
    uv run python scripts/ibm_cloud_login.py --instance <CRN or URL>   # only if it can't find the instance

Instructors testing without a workshop seat can simulate a fresh student with
the --dev-* flags (see --help); students never need them.
"""

import argparse
import base64
import getpass
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"
ENV_EXAMPLE = REPO_ROOT / ".env-example"
IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"
# The shared workshop EHR. Every attendee uses it; each gets a private copy of the
# patients, keyed by EHR_TENANT below.
SHARED_EHR_URL = os.environ.get("SHARED_EHR_URL", "https://workshop-ehr.2g7six4hbjvx.us-south.codeengine.appdomain.cloud")


def read_api_key(key_file: Path | None) -> str:
    """Get the API key: from a key file if one was passed, otherwise pasted at a hidden prompt."""
    if key_file is not None:
        try:
            return json.loads(key_file.read_text())["apikey"].strip()
        except (OSError, ValueError, KeyError) as e:
            sys.exit(f"Couldn't read an API key from {key_file}: {e}")

    # getpass keeps the key off the screen and out of terminal scrollback.
    key = getpass.getpass("Paste your IBM Cloud API key (it won't show as you paste), then press Enter: ").strip()
    if not key:
        sys.exit("No API key entered.")
    return key


def get_iam_token(api_key: str) -> str:
    """Exchange the API key for an IAM access token. Exits with a clear message if the key is rejected."""
    resp = requests.post(
        IAM_TOKEN_URL,
        data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": api_key},
        timeout=30,
    )
    if resp.status_code in (400, 401):
        sys.exit("IBM Cloud rejected that API key. Check that you copied the whole key, or create a new one.")
    resp.raise_for_status()
    return resp.json()["access_token"]


def token_claims(token: str) -> dict:
    """The (unverified) JWT payload — only used to show and name things, never to authorize."""
    payload = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


def describe_token(claims: dict) -> str:
    who = claims.get("email") or claims.get("name") or claims.get("sub", "unknown user")
    account = claims.get("account", {}).get("bss", "unknown account")
    return f"{who} (account {account})"


def name_prefix(claims: dict) -> str:
    """A per-user prefix like "student0_" for Orchestrate agent/tool names.

    Names are global to an Orchestrate instance, so attendees sharing one each
    deploy under their own prefix (see lab1/agent/deploy.py).
    """
    user = (claims.get("email") or claims.get("name") or claims.get("sub", "user")).split("@")[0]
    return re.sub(r"[^a-z0-9]+", "_", user.lower()).strip("_") + "_"


def resolve_instance_url(value: str) -> str:
    """Turn what the user pasted (an instance CRN or the API endpoint URL) into the API endpoint URL.

    The endpoint is https://api.<region>.watson-orchestrate.cloud.ibm.com/instances/<guid>, and an
    instance CRN is crn:v1:bluemix:public:<service>:<region>:a/<account>:<guid>::, so the CRN has
    everything needed.
    """
    value = value.strip()
    if value.startswith("https://"):
        return value.rstrip("/")
    if value.startswith("crn:"):
        parts = value.split(":")
        if len(parts) >= 8 and parts[5] and parts[7]:
            region, guid = parts[5], parts[7]
            return f"https://api.{region}.watson-orchestrate.cloud.ibm.com/instances/{guid}"
        sys.exit("That doesn't look like a complete CRN. Copy it again from the Orchestrate instance's details.")
    sys.exit("Paste either the instance's CRN (starts with crn:) or its API endpoint URL (starts with https://).")


RESOURCE_CONTROLLER = "https://resource-controller.cloud.ibm.com/v2/resource_instances"


def find_orchestrate_instances(token: str) -> list[dict]:
    """The watsonx Orchestrate instances this key can see: [{"name", "url"}]."""
    found, url = [], f"{RESOURCE_CONTROLLER}?type=service_instance&limit=100"
    while url:
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        resp.raise_for_status()
        body = resp.json()
        for inst in body.get("resources", []):
            if ":watsonx-orchestrate:" in inst.get("crn", "") and inst.get("state") == "active":
                found.append({"name": inst["name"], "url": resolve_instance_url(inst["crn"])})
        nxt = body.get("next_url")
        url = f"https://resource-controller.cloud.ibm.com{nxt}" if nxt else None
    return found


def choose_instance(token: str) -> str:
    """Pick the Orchestrate instance automatically; ask only if there's more than one."""
    try:
        instances = find_orchestrate_instances(token)
    except requests.RequestException:
        instances = []
    if len(instances) == 1:
        print(f"✓ Found your watsonx Orchestrate instance: {instances[0]['name']}")
        return instances[0]["url"]
    if instances:
        print("This key can see more than one watsonx Orchestrate instance:")
        for i, inst in enumerate(instances, 1):
            print(f"  {i}. {inst['name']}")
        while True:
            choice = input(f"Which one is the workshop's? [1-{len(instances)}]: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(instances):
                return instances[int(choice) - 1]["url"]
    # No instance visible means the key belongs to an account without the workshop's
    # Orchestrate instance (usually: created while signed in with your own IBMid).
    print("✗ This API key can't see the workshop's watsonx Orchestrate instance.\n"
          "  It was probably created in a different IBM Cloud account (for example, signed in with your own IBMid).\n"
          "  Log in with your workshop seat through the access link on the IBM Cloud login page,\n"
          "  create a new API key there, and run this again: uv run python scripts/ibm_cloud_login.py")
    return ""


def check_instance(instance_url: str, token: str) -> str | None:
    """Read-only call to the Orchestrate instance. Returns an error message, or None if it worked."""
    try:
        resp = requests.get(
            f"{instance_url}/v1/orchestrate/agents",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
    except requests.RequestException as e:
        return f"couldn't connect ({e.__class__.__name__})"
    if resp.status_code in (401, 403):
        return f"HTTP {resp.status_code}: this key's user doesn't have access to that instance"
    if resp.status_code == 404:
        return "HTTP 404: check the URL — it should end in /instances/<instance-id>"
    if not resp.ok:
        return f"HTTP {resp.status_code}"
    return None


def tenant_id(api_key: str) -> str:
    """Your tenant on the shared EHR: a one-way fingerprint of your API key.

    Unique to you and stable across re-runs, and the EHR never sees the key itself.
    """
    return hashlib.sha256(api_key.encode()).hexdigest()[:24]


ORCHESTRATE_ENV = "workshop"


def setup_orchestrate_cli(instance_url: str, api_key: str) -> str | None:
    """Add and activate an `orchestrate` CLI environment for this instance (used by deploy.py).

    Returns an error message, or None on success. The key goes in on stdin so it
    never appears in the process list.
    """
    if not shutil.which("orchestrate"):
        return "the Orchestrate CLI isn't installed. Run: uv tool install ibm-watsonx-orchestrate"
    # Re-running asks "update the environment?"; answer yes so the URL stays current.
    add = subprocess.run(["orchestrate", "env", "add", "-n", ORCHESTRATE_ENV, "-u", instance_url, "-t", "ibm_iam"],
                         input="y\n", capture_output=True, text=True, timeout=60)
    if add.returncode != 0:
        return f"`orchestrate env add` failed: {(add.stderr or add.stdout).strip()[-200:]}"
    activate = subprocess.run(["orchestrate", "env", "activate", ORCHESTRATE_ENV],
                              input=api_key + "\n", capture_output=True, text=True, timeout=120)
    if activate.returncode != 0 or "now active" not in (activate.stdout + activate.stderr):
        return f"`orchestrate env activate` failed: {(activate.stderr or activate.stdout).strip()[-200:]}"
    return None


def set_env_value(text: str, key: str, value: str) -> str:
    """Set KEY=value in .env text, uncommenting `# KEY=...` if that's all there is. Appends if absent."""
    pattern = re.compile(rf"^[ \t]*(?:#[ \t]*)?{re.escape(key)}=.*$", re.MULTILINE)
    # Prefer an active line over a commented-out one, so we don't leave a stale duplicate.
    active = re.search(rf"^[ \t]*{re.escape(key)}=.*$", text, re.MULTILINE)
    match = active or pattern.search(text)
    line = f"{key}={value}"
    if match:
        return text[: match.start()] + line + text[match.end() :]
    return text.rstrip("\n") + f"\n{line}\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("key_file", nargs="?", type=Path, help="optional: an apikey.json file instead of pasting the key")
    parser.add_argument("--instance", help="optional: Orchestrate instance CRN or URL (found automatically otherwise)")
    dev = parser.add_argument_group(
        "instructor/testing only — students: ignore these",
        "Simulate a fresh student without a workshop seat key (e.g. tests/e2e/two_students.py).",
    )
    dev.add_argument("--dev-prefix", metavar="PREFIX",
                     help="use this WXO_NAME_PREFIX (e.g. devA_) instead of one derived from the key's user")
    dev.add_argument("--dev-tenant", metavar="TENANT",
                     help="use this EHR_TENANT instead of the key's fingerprint, so one key can act as several students")
    dev.add_argument("--dev-skip-cli", action="store_true",
                     help="don't add or activate an `orchestrate` CLI environment")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None):
    args = parse_args(argv)
    if args.dev_prefix is not None and not re.fullmatch(r"[A-Za-z0-9_]*", args.dev_prefix):
        sys.exit("--dev-prefix may only contain letters, digits and underscores.")
    if args.dev_tenant is not None and not re.fullmatch(r"[A-Za-z0-9_-]+", args.dev_tenant):
        sys.exit("--dev-tenant must be non-empty letters, digits, '-' or '_'.")

    if not ENV_FILE.exists():
        shutil.copy(ENV_EXAMPLE, ENV_FILE)
        print("Created .env from .env-example")

    api_key = read_api_key(args.key_file)
    token = get_iam_token(api_key)
    claims = token_claims(token)
    print(f"✓ API key works: {describe_token(claims)}")

    instance_url = resolve_instance_url(args.instance) if args.instance else choose_instance(token)

    prefix = args.dev_prefix if args.dev_prefix is not None else name_prefix(claims)
    tenant = args.dev_tenant if args.dev_tenant is not None else tenant_id(api_key)

    text = ENV_FILE.read_text()
    text = set_env_value(text, "WXO_API_KEY", api_key)
    text = set_env_value(text, "WXO_NAME_PREFIX", prefix)
    text = set_env_value(text, "EHR_TENANT", tenant)
    if SHARED_EHR_URL:
        text = set_env_value(text, "EHR_API_URL", SHARED_EHR_URL)
    if instance_url:
        text = set_env_value(text, "WXO_INSTANCE_URL", instance_url)
    ENV_FILE.write_text(text)
    os.chmod(ENV_FILE, 0o600)  # the key is a password; keep it readable only by you
    print(f"✓ Saved WXO_API_KEY{' and WXO_INSTANCE_URL' if instance_url else ''} to {ENV_FILE}")
    print(f"✓ Your agent and tools will be named with the prefix {prefix!r}")

    if not instance_url:
        sys.exit(1)
    error = check_instance(instance_url, token)
    if error:
        sys.exit(f"✗ Saved, but couldn't reach the Orchestrate instance: {error}")
    print("✓ Orchestrate instance is reachable with this key")

    if args.dev_skip_cli:
        print("- Skipped the Orchestrate CLI setup (--dev-skip-cli)")
        return
    error = setup_orchestrate_cli(instance_url, api_key)
    if error:
        sys.exit(f"✗ Couldn't set up the Orchestrate CLI: {error}")
    print(f"✓ Orchestrate CLI environment '{ORCHESTRATE_ENV}' is active (deploy with: uv run python -m lab1.agent.deploy)")


if __name__ == "__main__":
    main()
