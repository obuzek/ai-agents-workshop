"""Unit tests for the instructor-only --dev-* flags of scripts/ibm_cloud_login.py (no network)."""

import json

import pytest

from scripts import ibm_cloud_login as login

INSTANCE = "https://api.ca-tor.watson-orchestrate.cloud.ibm.com/instances/test-guid"


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Point the script at a temp .env and stub out every network/CLI call."""
    env_file, example = tmp_path / ".env", tmp_path / ".env-example"
    example.write_text("# WXO_NAME_PREFIX=student0_\n")
    key_file = tmp_path / "apikey.json"
    key_file.write_text(json.dumps({"apikey": "fake-key"}))
    monkeypatch.setattr(login, "ENV_FILE", env_file)
    monkeypatch.setattr(login, "ENV_EXAMPLE", example)
    monkeypatch.setattr(login, "get_iam_token", lambda key: "token")
    monkeypatch.setattr(login, "token_claims", lambda token: {"email": "Jane.Doe@example.com"})
    monkeypatch.setattr(login, "check_instance", lambda url, token: None)
    cli_calls = []
    monkeypatch.setattr(login, "setup_orchestrate_cli", lambda url, key: cli_calls.append(url))
    monkeypatch.setattr(login, "choose_instance", lambda token: pytest.fail("discovery should be skipped"))
    return env_file, key_file, cli_calls


def values(env_file):
    return dict(line.split("=", 1) for line in env_file.read_text().splitlines() if "=" in line and not line.startswith("#"))


def test_default_behaviour_unchanged(env):
    env_file, key_file, cli_calls = env
    login.main([str(key_file), "--instance", INSTANCE])
    v = values(env_file)
    assert v["WXO_NAME_PREFIX"] == "jane_doe_"
    assert v["EHR_TENANT"] == login.tenant_id("fake-key")
    assert v["WXO_INSTANCE_URL"] == INSTANCE
    assert cli_calls == [INSTANCE]


def test_dev_flags_override_prefix_tenant_and_skip_cli(env):
    env_file, key_file, cli_calls = env
    login.main([str(key_file), "--instance", INSTANCE, "--dev-prefix", "devA_", "--dev-tenant", "e2e-devA",
                "--dev-skip-cli"])
    v = values(env_file)
    assert v["WXO_NAME_PREFIX"] == "devA_"
    assert v["EHR_TENANT"] == "e2e-devA"
    assert cli_calls == []


def test_one_key_two_students_get_distinct_tenants(env):
    env_file, key_file, _ = env
    login.main([str(key_file), "--instance", INSTANCE, "--dev-tenant", "e2e-devA", "--dev-skip-cli"])
    a = values(env_file)["EHR_TENANT"]
    login.main([str(key_file), "--instance", INSTANCE, "--dev-tenant", "e2e-devB", "--dev-skip-cli"])
    assert values(env_file)["EHR_TENANT"] != a
    assert env_file.read_text().count("EHR_TENANT=") == 1  # re-run updates in place


@pytest.mark.parametrize("flag,value", [("--dev-prefix", "dev-A"), ("--dev-tenant", ""), ("--dev-tenant", "a/b")])
def test_bad_dev_values_rejected_before_any_call(env, flag, value):
    _, key_file, _ = env
    with pytest.raises(SystemExit):
        login.main([str(key_file), "--instance", INSTANCE, flag, value])
