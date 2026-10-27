"""Check that your workshop setup works. Read-only: it changes nothing.

Prints ✓ or ✗ for each part of the setup, with a fix for anything that fails,
and exits non-zero if something failed. The installer runs it for you at the end.

Usage:
    uv run python scripts/check_setup.py             # everything
    uv run python scripts/check_setup.py --offline   # only what's on this machine (no API key needed)
"""

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))  # run as a script, so `app` and `scripts` aren't importable otherwise

import requests  # noqa: E402
from dotenv import dotenv_values  # noqa: E402

from scripts.ibm_cloud_login import IAM_TOKEN_URL, ORCHESTRATE_ENV, check_instance  # noqa: E402

ENV_FILE = REPO_ROOT / ".env"
REQUIRED_ENV = ["WXO_API_KEY", "WXO_INSTANCE_URL", "WXO_NAME_PREFIX", "EHR_TENANT", "EHR_API_URL"]
TENANT_HEADER = "X-Tenant"  # same as app.store.TENANT_HEADER
LOGIN_HINT = "uv run python scripts/ibm_cloud_login.py"
NEW_KEY_HINT = "create a new API key in IBM Cloud (step 3 of the prerequisites), then run: uv run python scripts/ibm_cloud_login.py"


@dataclass
class Result:
    name: str
    ok: bool
    detail: str = ""
    hint: str = ""


def check_python_env() -> Result:
    name = "Python environment"
    try:
        import app.store  # noqa: F401  (pulls in the workshop's main dependencies)
    except Exception as e:  # any import failure means the environment is broken
        return Result(name, False, f"can't import the workshop code ({e.__class__.__name__}: {e})",
                      "cd ~/ai-agents-workshop && uv sync")
    return Result(name, True, f"Python {sys.version.split()[0]}, workshop packages installed")


def parse_adk_version(output: str) -> str | None:
    match = re.search(r"ADK Version:\s*(\S+)", output)
    return match.group(1) if match else None


def check_orchestrate_cli() -> Result:
    name = "Orchestrate CLI"
    path = shutil.which("orchestrate")
    if not path:
        return Result(name, False, "`orchestrate` isn't on your PATH",
                      "source $HOME/.local/bin/env (or open a new terminal). If it's still missing, run the installer again.")
    try:
        # `orchestrate --version` can exit non-zero even when it works, so judge it by its output.
        run = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        return Result(name, False, f"`orchestrate --version` didn't run ({e.__class__.__name__})",
                      "uv tool install --reinstall ibm-watsonx-orchestrate")
    version = parse_adk_version(run.stdout + run.stderr)
    if not version:
        return Result(name, False, "`orchestrate --version` didn't print a version",
                      "uv tool install --reinstall ibm-watsonx-orchestrate")
    return Result(name, True, f"ADK {version}")


def read_env(env_file: Path = ENV_FILE) -> dict[str, str]:
    """The non-empty, non-placeholder values in .env."""
    if not env_file.exists():
        return {}
    values = dotenv_values(env_file)
    return {k: v.strip() for k, v in values.items()
            if v and v.strip() and "your-" not in v and "<" not in v}


def check_env_file(env: dict[str, str], env_file: Path = ENV_FILE) -> Result:
    name = ".env settings"
    if not env_file.exists():
        return Result(name, False, f"{env_file} doesn't exist", LOGIN_HINT)
    missing = [k for k in REQUIRED_ENV if k not in env]
    if missing:
        return Result(name, False, f"missing {', '.join(missing)}", LOGIN_HINT)
    return Result(name, True, f"{', '.join(REQUIRED_ENV)} are set")


def get_iam_token(env: dict[str, str]) -> tuple[Result, str | None]:
    name = "IBM Cloud API key"
    key = env.get("WXO_API_KEY")
    if not key:
        return Result(name, False, "no WXO_API_KEY in .env", LOGIN_HINT), None
    try:
        resp = requests.post(IAM_TOKEN_URL, timeout=30,
                             data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": key})
    except requests.RequestException as e:
        return Result(name, False, f"couldn't reach IBM Cloud ({e.__class__.__name__})",
                      "check your internet connection, then run this again."), None
    if resp.status_code in (400, 401):
        return Result(name, False, "IBM Cloud rejected the key in .env (it may have expired or been deleted)",
                      NEW_KEY_HINT), None
    if not resp.ok:
        return Result(name, False, f"IBM Cloud returned HTTP {resp.status_code}", "wait a minute and run this again."), None
    return Result(name, True, "IBM Cloud accepts it"), resp.json()["access_token"]


def check_orchestrate_instance(env: dict[str, str], token: str | None) -> Result:
    name = "Orchestrate instance"
    url = env.get("WXO_INSTANCE_URL")
    if not url:
        return Result(name, False, "no WXO_INSTANCE_URL in .env", LOGIN_HINT)
    if not token:
        return Result(name, False, "not checked: needs a working API key (see above)", NEW_KEY_HINT)
    error = check_instance(url, token)
    if error:
        return Result(name, False, error, LOGIN_HINT)
    return Result(name, True, "reachable with your key")


def parse_active_env(output: str) -> str | None:
    """The name of the environment marked (active) in `orchestrate env list` output."""
    for line in re.sub(r"\x1b\[[0-9;]*m", "", output).splitlines():
        if "(active)" in line and line.split():
            return line.split()[0]
    return None


def check_active_env() -> Result:
    name = "Orchestrate CLI environment"
    path = shutil.which("orchestrate")
    if not path:
        return Result(name, False, "not checked: `orchestrate` isn't on your PATH (see above)",
                      "source $HOME/.local/bin/env, then run this again.")
    try:
        run = subprocess.run([path, "env", "list"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return Result(name, False, f"`orchestrate env list` didn't run ({e.__class__.__name__})", LOGIN_HINT)
    active = parse_active_env(run.stdout)
    if active != ORCHESTRATE_ENV:
        found = f"'{active}' is active" if active else "no environment is active"
        return Result(name, False, f"{found}, not '{ORCHESTRATE_ENV}'", LOGIN_HINT)
    return Result(name, True, f"'{ORCHESTRATE_ENV}' is active")


def check_ehr(env: dict[str, str]) -> list[Result]:
    name = "Shared workshop EHR"
    ask = "tell your instructor that the shared EHR isn't answering."
    url = env.get("EHR_API_URL", "").rstrip("/")
    tenant = env.get("EHR_TENANT")
    if not url or not tenant:
        return [Result(name, False, "no EHR_API_URL or EHR_TENANT in .env", LOGIN_HINT)]
    try:
        health = requests.get(f"{url}/health", timeout=30)
    except requests.RequestException as e:
        return [Result(name, False, f"couldn't connect to {url} ({e.__class__.__name__})", ask)]
    if not health.ok:
        return [Result(name, False, f"/health returned HTTP {health.status_code}", ask)]
    try:
        patients = requests.get(f"{url}/patients", headers={TENANT_HEADER: tenant}, timeout=60)
    except requests.RequestException as e:
        return [Result(name, False, f"/patients didn't answer ({e.__class__.__name__})", ask)]
    if not patients.ok:
        return [Result(name, False, f"/patients returned HTTP {patients.status_code}", ask)]
    return [Result(name, True, f"your copy has {len(patients.json())} patients")]


def run_checks(offline: bool) -> list[Result]:
    results = [check_python_env(), check_orchestrate_cli()]
    if offline:
        return results
    env = read_env()
    results.append(check_env_file(env))
    key_result, token = get_iam_token(env)
    results += [key_result, check_orchestrate_instance(env, token), check_active_env(), *check_ehr(env)]
    return results


def report(results: list[Result]) -> int:
    for r in results:
        print(f"{'✓' if r.ok else '✗'} {r.name}: {r.detail}")
        if not r.ok and r.hint:
            print(f"    Fix: {r.hint}")
    failed = sum(not r.ok for r in results)
    print()
    print("All checks passed." if not failed else f"{failed} check{'s' if failed > 1 else ''} failed. Fix them, then run this again.")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--offline", "--no-cloud", action="store_true",
                        help="only check this machine (Python packages, Orchestrate CLI); skip .env and IBM Cloud")
    args = parser.parse_args(argv)
    return report(run_checks(args.offline))


if __name__ == "__main__":
    sys.exit(main())
