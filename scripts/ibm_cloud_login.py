"""Save your IBM Cloud API key (and Orchestrate instance URL) into .env.

Checks that the key works, shows which IBM Cloud user and account it belongs
to, and confirms the key can reach the workshop's Orchestrate instance.
Safe to re-run: it updates the existing values and leaves the rest of .env alone.

Usage:
    uv run python scripts/ibm_cloud_login.py                      # looks for ~/Downloads/apikey.json, else asks
    uv run python scripts/ibm_cloud_login.py path/to/apikey.json
    uv run python scripts/ibm_cloud_login.py --instance-url https://api.<region>.watson-orchestrate.cloud.ibm.com/instances/<id>
"""

import argparse
import base64
import getpass
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


def describe_token(token: str) -> str:
    """Who the token belongs to, from the (unverified) JWT payload — for display only."""
    payload = token.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    who = claims.get("email") or claims.get("name") or claims.get("sub", "unknown user")
    account = claims.get("account", {}).get("bss", "unknown account")
    return f"{who} (account {account})"


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
    parser.add_argument("--instance-url", help="Orchestrate API endpoint (Settings -> API details)")
    args = parser.parse_args()

    if not ENV_FILE.exists():
        shutil.copy(ENV_EXAMPLE, ENV_FILE)
        print("Created .env from .env-example")
    current = dotenv_values(ENV_FILE)

    api_key = read_api_key(args.key_file)
    token = get_iam_token(api_key)
    print(f"✓ API key works: {describe_token(token)}")

    instance_url = args.instance_url
    if not instance_url:
        existing = current.get("WXO_INSTANCE_URL") or ""
        prompt = "Orchestrate instance URL"
        prompt += f" [{existing}]: " if existing else " (from your instructor; Enter to skip): "
        instance_url = input(prompt).strip() or existing
    instance_url = instance_url.rstrip("/")

    text = ENV_FILE.read_text()
    text = set_env_value(text, "WXO_API_KEY", api_key)
    if instance_url:
        text = set_env_value(text, "WXO_INSTANCE_URL", instance_url)
    ENV_FILE.write_text(text)
    os.chmod(ENV_FILE, 0o600)  # the key is a password; keep it readable only by you
    print(f"✓ Saved WXO_API_KEY{' and WXO_INSTANCE_URL' if instance_url else ''} to {ENV_FILE}")

    if not instance_url:
        print("! No Orchestrate instance URL set. Re-run with --instance-url once you have it.")
        return
    error = check_instance(instance_url, token)
    if error:
        sys.exit(f"✗ Saved, but couldn't reach the Orchestrate instance: {error}")
    print("✓ Orchestrate instance is reachable with this key")


if __name__ == "__main__":
    main()
