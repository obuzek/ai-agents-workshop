"""Tests for scripts/check_setup.py: output parsing, .env handling, and exit codes. No network."""

import pytest

from scripts import check_setup
from scripts.check_setup import Result


def test_parse_adk_version():
    assert check_setup.parse_adk_version("ADK Version: 2.19.1\nLangflow Version: 1.11.2\n") == "2.19.1"
    assert check_setup.parse_adk_version("Traceback (most recent call last):\n") is None


def test_parse_active_env():
    listing = (
        " ai-workshop-test   https://api.ca-tor.watson-orches…           \n"
        " \x1b[1mworkshop\x1b[0m           https://api.us-south.watson-orch…  (active) \n"
        " local              http://localhost:4321                       \n"
    )
    assert check_setup.parse_active_env(listing) == "workshop"
    assert check_setup.parse_active_env(" local  http://localhost:4321\n") is None


def test_env_file_missing(tmp_path):
    env_file = tmp_path / ".env"
    result = check_setup.check_env_file(check_setup.read_env(env_file), env_file)
    assert not result.ok
    assert "ibm_cloud_login.py" in result.hint


def test_env_file_placeholders_count_as_missing(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "WXO_API_KEY=your-ibm-cloud-api-key-here\n"
        "WXO_INSTANCE_URL=https://api.<region>.watson-orchestrate.cloud.ibm.com/instances/<instance-id>\n"
        "WXO_NAME_PREFIX=student0_\nEHR_TENANT=abc\nEHR_API_URL=https://ehr.example\n"
    )
    result = check_setup.check_env_file(check_setup.read_env(env_file), env_file)
    assert not result.ok
    assert result.detail == "missing WXO_API_KEY, WXO_INSTANCE_URL"


def test_env_file_complete_does_not_print_secret(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "WXO_API_KEY=supersecret\nWXO_INSTANCE_URL=https://api.x/instances/1\n"
        "WXO_NAME_PREFIX=student0_\nEHR_TENANT=abc\nEHR_API_URL=https://ehr.example\n"
    )
    result = check_setup.check_env_file(check_setup.read_env(env_file), env_file)
    assert result.ok
    assert "supersecret" not in result.detail


def test_cloud_checks_without_key_fail_cleanly():
    key_result, token = check_setup.get_iam_token({})
    assert not key_result.ok and token is None
    assert not check_setup.check_orchestrate_instance({"WXO_INSTANCE_URL": "https://x"}, None).ok
    assert not check_setup.check_ehr({})[0].ok


@pytest.mark.parametrize("results, code", [
    ([Result("a", True), Result("b", True)], 0),
    ([Result("a", True), Result("b", False, "broke", "do this")], 1),
])
def test_report_exit_code(results, code, capsys):
    assert check_setup.report(results) == code
    out = capsys.readouterr().out
    if code:
        assert "✗ b: broke" in out and "Fix: do this" in out
    else:
        assert "All checks passed." in out


def test_offline_runs_only_local_checks(monkeypatch):
    monkeypatch.setattr(check_setup, "check_python_env", lambda: Result("python", True))
    monkeypatch.setattr(check_setup, "check_orchestrate_cli", lambda: Result("cli", True))
    monkeypatch.setattr(check_setup, "read_env", lambda: pytest.fail("offline mode must not read .env"))
    assert [r.name for r in check_setup.run_checks(offline=True)] == ["python", "cli"]
