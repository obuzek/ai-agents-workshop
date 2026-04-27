"""
The observable agent — Lab 1's ReAct loop, now with Langfuse tracing.

This is the same agent from Lab 1 with one key addition: every call to the
agent is traced via Langfuse. LLM calls, tool calls, token usage, latency,
and cost are all captured automatically — but PII is filtered out before
any data leaves the process.

What changed from Lab 1:
- Added `create_langfuse_handler()` to create a pre-configured callback handler
- Pass the handler via `config={"callbacks": [...]}` to `_agent.invoke()`
- Tag each trace with the patient_id for filtering in the Langfuse UI

That's it. Three lines of integration code. The Langfuse CallbackHandler
hooks into LangChain's callback system to capture everything LangGraph does
inside the ReAct loop — no manual instrumentation of individual steps needed.
"""

import logging
from datetime import datetime, timezone

from app.llm import get_chat_model
from langgraph.prebuilt import create_react_agent

from lab2.agent.tools import ALL_TOOLS
from lab2.agent.models import PatientConcerns
from lab2.agent.observability import create_langfuse_handler

logger = logging.getLogger(__name__)

# System prompt is identical to Lab 1 — we're adding observability,
# not changing agent behavior.
SYSTEM_PROMPT = """\
You are a clinical inbox assistant for a primary care practice. You review a
patient's record and portal messages, then surface actionable concerns for the
doctor. Think of yourself as a resident pre-rounding: your job is to organize
what the attending needs to see, not to make decisions.

A "concern" is anything that needs the doctor's attention:
- A patient message that hasn't been answered
- An abnormal or trending lab value
- A medication issue (expiring refill, reported side effect)
- An overdue follow-up or screening
- A symptom the patient reports
- An administrative request (scheduling, referral, records)

HOW TO INVESTIGATE:
Use the available tools to explore the patient's record. You decide what to
look at and in what order. Check labs, encounters, medications — whatever is
relevant to the concerns you find. Gather evidence before concluding.

OUTPUT RULES:
- "summary" must be ONE sentence. State the clinical fact, not a paragraph.
  Good: "TSH trending up from 3.1 to 4.8 over 6 months with new resting HR increase."
  Bad: "The patient has been experiencing a gradual increase in TSH levels..."
- "action" must say what the DOCTOR needs to do. Be specific.
  Good: "Reply to portal message — patient is requesting levothyroxine trial"
  Good: "Review TSH trend and correlate with HR increase at next visit"
  Bad: "Monitor" or "Follow up"
- "evidence" should be specific values and dates, not descriptions.
  Good: "TSH 4.8 mIU/L (2026-04-01), up from 3.1 (2025-06-18)"
  Bad: "Patient has elevated TSH"
- "related" MUST include the specific message_ids, lab_dates, conditions, and
  encounter_dates that are relevant. These become links in the UI.
- Only surface information that is IN the record. Do not infer diagnoses.
- Do not draft replies or make clinical recommendations.
"""


def _build_agent():
    """Build the LangGraph ReAct agent (identical to Lab 1)."""
    llm = get_chat_model()
    return create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        prompt=SYSTEM_PROMPT,
        response_format=PatientConcerns,
    )


_agent = _build_agent()

# --- NEW IN LAB 2 ---
# Create a Langfuse callback handler with PII masking enabled.
# This handler captures every LLM call, tool call, and their inputs/outputs.
# The mask function redacts patient names, DOBs, phone numbers, emails, and
# other PHI before any data is sent to the Langfuse server.
_langfuse_handler = create_langfuse_handler()


def process_patient(patient_id: str) -> PatientConcerns:
    """Run the agent loop for a single patient. Returns structured concerns.

    Identical to Lab 1, except the agent's execution is now traced via Langfuse.
    Open http://localhost:3000 to see the trace after this completes.
    """
    user_message = (
        f"Please review patient {patient_id}. "
        "Start by looking at their messages and record, then investigate "
        "any concerns you find. When done, output your findings."
    )

    logger.info("[%s] Starting agent run", patient_id)

    # --- NEW IN LAB 2 ---
    # Pass the Langfuse handler via config. LangGraph propagates it to every
    # LLM call and tool call in the ReAct loop. We also tag the trace with
    # the patient_id so we can filter by patient in the Langfuse UI.
    result = _agent.invoke(
        {"messages": [{"role": "user", "content": user_message}]},
        config={
            "callbacks": [_langfuse_handler],
            "metadata": {
                "langfuse_session_id": f"patient-review-{patient_id}",
                "langfuse_tags": ["lab2", patient_id],
            },
        },
    )

    structured = result["structured_response"]

    now = datetime.now(timezone.utc).isoformat()
    for concern in structured.concerns:
        concern.patient_id = patient_id
        if not concern.last_updated:
            concern.last_updated = now

    if not structured.patient_id:
        structured.patient_id = patient_id

    logger.info("[%s] Agent found %d concerns", patient_id, len(structured.concerns))
    return structured
