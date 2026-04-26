"""
The naive agent — a ReAct tool-calling loop powered by LangGraph.

The agent receives a patient ID and a goal. It decides which tools to call,
in what order, and how to interpret the results. When it has gathered enough
information, it returns structured concerns.

This is the core of Lab 1: a real agent loop where the LLM drives the
investigation. LangGraph manages the ReAct cycle (observe, reason, act)
and structured output ensures we get valid JSON every time.
"""

import logging
import os
from datetime import datetime, timezone

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from lab1.agent.tools import ALL_TOOLS
from lab1.agent.models import PatientConcerns

logger = logging.getLogger(__name__)

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

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
    """Build the LangGraph ReAct agent."""
    llm = ChatOpenAI(model=MODEL)
    return create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        prompt=SYSTEM_PROMPT,
        response_format=PatientConcerns,
    )


# Module-level agent instance (reused across calls)
_agent = _build_agent()


def process_patient(patient_id: str) -> PatientConcerns:
    """Run the agent loop for a single patient. Returns structured concerns."""

    user_message = (
        f"Please review patient {patient_id}. "
        "Start by looking at their messages and record, then investigate "
        "any concerns you find. When done, output your findings."
    )

    logger.info("[%s] Starting agent run", patient_id)
    result = _agent.invoke(
        {"messages": [{"role": "user", "content": user_message}]},
    )

    # LangGraph returns the structured response directly
    structured = result["structured_response"]

    # Ensure patient_id is set correctly and timestamps are filled in
    now = datetime.now(timezone.utc).isoformat()
    for concern in structured.concerns:
        concern.patient_id = patient_id
        if not concern.last_updated:
            concern.last_updated = now

    if not structured.patient_id:
        structured.patient_id = patient_id

    logger.info("[%s] Agent found %d concerns", patient_id, len(structured.concerns))
    return structured
