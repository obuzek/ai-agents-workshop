"""
Agent post-invoke plug-in: mask contact details and identifiers in the agent's final answer.

watsonx Orchestrate runs this after the agent finishes and before the answer is
returned to the caller. It is one of three PII layers in the IBM edition:

  1. Input   — the built-in "PII Filter" control at agent_pre_invoke masks PII
               the *user* types. It never sees tool output.
  2. Output  — this plug-in masks identifiers in the *answer*. It runs after the
               LLM has already read the full record, so the model's context and
               Orchestrate's traces still hold the raw values.
  3. Source  — returning only the fields the agent needs from the tool is the
               one layer that keeps PHI out of the model, the traces, and the answer.

Why a plug-in and not the PII Filter control for the output? On this platform the
control's agent_post_invoke and tool_post_invoke hooks don't execute — the trace
shows only an agent_pre_invoke control step. Plug-ins at agent_post_invoke do run;
you can see this one as its own "mask_pii_output" span in the trace.

This file is uploaded to Orchestrate as-is, so it must be self-contained: no
imports from the rest of the repo.

Deploy it with the agent (from the repo root, with your Orchestrate env active):
    uv run python -m lab1.agent.deploy --pii-plugin
That imports this file (named with your WXO_NAME_PREFIX, if set) and adds to the
agent YAML:
    plugins:
      agent_post_invoke:
      - plugin_name: mask_pii_output
Keep the @tool(...) decorator on one line: deploy.py adds the prefixed name to it.
"""

import re

from ibm_watsonx_orchestrate.agent_builder.tools import tool
from ibm_watsonx_orchestrate.agent_builder.tools.types import (
    AgentPostInvokePayload,
    AgentPostInvokeResult,
    Message,
    PluginContext,
    PythonToolKind,
    TextContent,
)

# Regexes, like the platform's own PII Filter: they catch structured identifiers
# but not names or street addresses. That gap is the point of layer 3.
PATTERNS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    (re.compile(r"\(?\b\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b"), "[PHONE]"),
    # Insurance member IDs like 1EG4-TE5-MK72 (Medicare Beneficiary Identifier shape).
    (re.compile(r"\b[0-9A-Z]{4}-[0-9A-Z]{3}-[0-9A-Z]{4}\b"), "[MEMBER_ID]"),
    # Dates of birth only when labelled, so lab and visit dates — which the
    # doctor needs as evidence — survive.
    (re.compile(r"(?i)(birth(?:\s*date)?|DOB)(\W{0,4})\d{4}-\d{2}-\d{2}"), r"\1\2[DOB]"),
]


def mask(text: str) -> str:
    """Replace each identifier pattern with a placeholder."""
    for pattern, replacement in PATTERNS:
        text = pattern.sub(replacement, text)
    return text


@tool(description="Masks contact details and identifiers in the agent's answer", kind=PythonToolKind.AGENTPOSTINVOKE)
def mask_pii_output(plugin_context: PluginContext, agent_post_invoke_payload: AgentPostInvokePayload) -> AgentPostInvokeResult:
    result = AgentPostInvokeResult(continue_processing=True, modified_payload=agent_post_invoke_payload)
    if not agent_post_invoke_payload or not agent_post_invoke_payload.messages:
        return result

    payload = agent_post_invoke_payload.copy(deep=True)
    for i, message in enumerate(payload.messages):
        text = getattr(message.content, "text", None)
        if text:
            payload.messages[i] = Message(role=message.role, content=TextContent(type="text", text=mask(text)))
    result.modified_payload = payload
    return result
