"""
Tests for the Orchestrate post-invoke PII plug-in's masking rules.

The plug-in runs inside watsonx Orchestrate, so the ADK isn't installed in the
project environment. These tests stub the ADK imports and exercise mask() only.
"""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

PLUGIN = Path(__file__).parent.parent / "lab2" / "orchestrate" / "pii_output_plugin.py"


@pytest.fixture(scope="module")
def plugin():
    stubs = {
        "ibm_watsonx_orchestrate": types.ModuleType("ibm_watsonx_orchestrate"),
        "ibm_watsonx_orchestrate.agent_builder": types.ModuleType("ibm_watsonx_orchestrate.agent_builder"),
        "ibm_watsonx_orchestrate.agent_builder.tools": types.ModuleType("ibm_watsonx_orchestrate.agent_builder.tools"),
        "ibm_watsonx_orchestrate.agent_builder.tools.types": types.ModuleType("ibm_watsonx_orchestrate.agent_builder.tools.types"),
    }
    stubs["ibm_watsonx_orchestrate.agent_builder.tools"].tool = lambda **_: (lambda f: f)
    for name in ("AgentPostInvokePayload", "AgentPostInvokeResult", "Message", "PluginContext", "PythonToolKind", "TextContent"):
        setattr(stubs["ibm_watsonx_orchestrate.agent_builder.tools.types"], name, types.SimpleNamespace(AGENTPOSTINVOKE="agent_post_invoke"))

    saved = {name: sys.modules.get(name) for name in stubs}
    sys.modules.update(stubs)
    try:
        spec = importlib.util.spec_from_file_location("pii_output_plugin", PLUGIN)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module
    finally:
        for name, original in saved.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def test_masks_identifiers(plugin):
    text = ("Phone: 847-555-0143 | Email: pat.kowalski@gmail.com | "
            "Date of Birth: 1953-11-14 | Insurance Member ID: 1EG4-TE5-MK72")
    assert plugin.mask(text) == (
        "Phone: [PHONE] | Email: [EMAIL] | Date of Birth: [DOB] | Insurance Member ID: [MEMBER_ID]"
    )


@pytest.mark.parametrize("dob", ["DOB: 1953-11-14", "birthDate 1953-11-14", "Birth date - 1953-11-14"])
def test_masks_labelled_birth_dates(plugin, dob):
    assert "1953-11-14" not in plugin.mask(dob)


def test_keeps_clinical_dates(plugin):
    text = "TSH 4.8 mIU/L on 2026-04-01; follow-up visit 2026-05-12"
    assert plugin.mask(text) == text


def test_names_and_addresses_pass_through(plugin):
    # Documented limitation: regexes don't catch names or street addresses.
    text = "Patricia Kowalski, 482 Birch Lane, Evanston, IL 60201"
    assert plugin.mask(text) == text
