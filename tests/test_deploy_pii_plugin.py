"""
Tests for deploy.py's --pii-plugin rendering: the prefixed plug-in source and
the plugins block in the agent spec. Nothing here calls the orchestrate CLI.

deploy.py reads WXO_NAME_PREFIX at import time, so each test sets the env var
and reloads the module.
"""

import importlib

import pytest

import lab1.agent.deploy


@pytest.fixture
def deploy(monkeypatch):
    def load(prefix: str):
        monkeypatch.setenv("WXO_NAME_PREFIX", prefix)
        # load_dotenv() doesn't override variables that are already set.
        return importlib.reload(lab1.agent.deploy)

    yield load
    monkeypatch.undo()
    importlib.reload(lab1.agent.deploy)


def test_plugin_source_gets_prefixed_name(deploy):
    module = deploy("student0_")
    source = module.render_pii_plugin_source()
    assert '@tool(name="student0_mask_pii_output", description=' in source
    assert source.count("\n@tool(") == 1
    compile(source, "pii_output_plugin.py", "exec")


def test_plugin_source_unchanged_without_prefix(deploy):
    module = deploy("")
    assert module.render_pii_plugin_source() == module.PII_PLUGIN.read_text()


def test_agent_spec_with_plugin(deploy):
    module = deploy("student0_")
    spec = module.render_agent_spec(pii_plugin=True)
    assert spec["plugins"] == {"agent_post_invoke": [{"plugin_name": "student0_mask_pii_output"}]}
    assert spec["name"] == "student0_lakeview_inbox_agent"


def test_agent_spec_without_plugin(deploy):
    module = deploy("student0_")
    assert "plugins" not in module.render_agent_spec()
    assert "plugins" not in module.render_agent_spec(pii_plugin=False)


@pytest.mark.parametrize("argv, expected", [([], False), (["--pii-plugin"], True)])
def test_parse_args(deploy, argv, expected):
    assert deploy("").parse_args(argv).pii_plugin is expected
