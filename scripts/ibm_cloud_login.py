"""Save your IBM Cloud API key (and Orchestrate instance URL) into .env.

Checks that the key works, shows which IBM Cloud user and account it belongs
to, and confirms the key can reach the workshop's Orchestrate instance.
Safe to re-run: it updates the existing values and leaves the rest of .env alone.

Usage:
    uv run python scripts/ibm_cloud_login.py                      # looks for ~/Downloads/apikey.json, else asks
    uv run python scripts/ibm_cloud_login.py path/to/apikey.json
    uv run python scripts/ibm_cloud_login.py --instance crn:v1:bluemix:public:watsonx-orchestrate:<region>:a/<account>:<guid>::
"""

import argparse
import base64
import getpass
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

import requests
from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"
ENV_EXAMPLE = REPO_ROOT / ".env-example"
DEFAULT_KEY_FILE = Path.home() / "Downloads" / "apikey.json"  # IBM Cloud's default download name
IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"
# The shared workshop EHR. Every attendee uses it; each gets a private copy of the
# patients, keyed by EHR_TENANT below.
SHARED_EHR_URL = os.environ.get("SHARED_EHR_URL", "https://workshop-ehr.2g7six4hbjvx.us-south.codeengine.appdomain.cloud")


def read_api_key(key_file: Path | None) -> str:
    """Get the API key from a downloaded apikey.json, or ask for it."""
    if key_file is None and DEFAULT_KEY_FILE.exists():
        answer = input(f"Use the API key in {DEFAULT_KEY_FILE}? [Y/n] ").strip().lower()
        if answer in ("", "y", "yes"):
            key_file = DEFAULT_KEY_FILE

    if key_file is not None:
        try:
            return json.loads(key_file.read_text())["apikey"].strip()
        except (OSError, ValueError, KeyError) as e:
            sys.exit(f"Couldn't read an API key from {key_file}: {e}")

    # getpass keeps the key off the screen and out of terminal scrollback.
    key = getpass.getpass("Paste your IBM Cloud API key (input is hidden): ").strip()
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


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("key_file", nargs="?", type=Path, help="path to the apikey.json you downloaded")
    parser.add_argument("--instance", help="Orchestrate instance CRN, or its API endpoint URL")
    args = parser.parse_args()

    if not ENV_FILE.exists():
        shutil.copy(ENV_EXAMPLE, ENV_FILE)
        print("Created .env from .env-example")
    current = dotenv_values(ENV_FILE)

    api_key = read_api_key(args.key_file)
    token = get_iam_token(api_key)
    claims = token_claims(token)
    print(f"✓ API key works: {describe_token(claims)}")

    instance = args.instance
    if not instance:
        # Ignore the .env-example placeholder; only offer a real saved value as the default.
        existing = current.get("WXO_INSTANCE_URL") or ""
        existing = "" if "<" in existing else existing
        print(
            "\nNext, the workshop's watsonx Orchestrate instance. In cloud.ibm.com: Resource list ->\n"
            "AI / Machine Learning -> the Orchestrate instance -> copy its CRN from the details panel."
        )
        prompt = "Paste the instance CRN (or its API endpoint URL)"
        prompt += f" [Enter keeps {existing}]: " if existing else ": "
        instance = input(prompt).strip() or existing
    instance_url = resolve_instance_url(instance) if instance else ""

    text = ENV_FILE.read_text()
    text = set_env_value(text, "WXO_API_KEY", api_key)
    text = set_env_value(text, "WXO_NAME_PREFIX", name_prefix(claims))
    text = set_env_value(text, "EHR_TENANT", tenant_id(api_key))
    if SHARED_EHR_URL:
        text = set_env_value(text, "EHR_API_URL", SHARED_EHR_URL)
    if instance_url:
        text = set_env_value(text, "WXO_INSTANCE_URL", instance_url)
    ENV_FILE.write_text(text)
    os.chmod(ENV_FILE, 0o600)  # the key is a password; keep it readable only by you
    print(f"✓ Saved WXO_API_KEY{' and WXO_INSTANCE_URL' if instance_url else ''} to {ENV_FILE}")
    print(f"✓ Your agent and tools will be named with the prefix {name_prefix(claims)!r}")

    if not instance_url:
        print("! No Orchestrate instance URL set. Re-run the script once you have its CRN.")
        return
    error = check_instance(instance_url, token)
    if error:
        sys.exit(f"✗ Saved, but couldn't reach the Orchestrate instance: {error}")
    print("✓ Orchestrate instance is reachable with this key")


if __name__ == "__main__":
    main()
