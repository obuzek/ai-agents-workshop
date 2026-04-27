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

# ChatOpenAI is LangChain's wrapper around the OpenAI chat API.
# It reads OPENAI_API_KEY from the environment automatically.
from langchain_openai import ChatOpenAI

# create_react_agent builds a full ReAct agent graph:
#   1. Send messages to the LLM
#   2. If the LLM returns tool calls → execute them, append results, go to 1
#   3. If the LLM returns text → done
# This replaces ~100 lines of manual loop code.
from langgraph.prebuilt import create_react_agent

from lab1.agent.tools import ALL_TOOLS
from lab1.agent.models import PatientConcerns

logger = logging.getLogger(__name__)

# Which model to use — override with OPENAI_MODEL env var
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

# The system prompt defines the agent's persona and output expectations.
# This is the single most important piece of the agent — it controls what
# the LLM investigates, how it reasons, and what format it returns.
# Getting this right is an iterative process (and a big part of the workshop).
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
    """Build the LangGraph ReAct agent.

    This wires together three things:
    - The LLM (what does the thinking)
    - The tools (what the LLM can do)
    - The response format (what shape the final answer must be)
    """
    llm = ChatOpenAI(model=MODEL)
    return create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        # The system prompt is injected at the start of every conversation
        prompt=SYSTEM_PROMPT,
        # response_format tells LangGraph to use OpenAI's structured output
        # mode. After the agent finishes calling tools, LangGraph makes one
        # final LLM call with constrained decoding so the output is guaranteed
        # to be valid JSON matching our Pydantic model. No parsing needed.
        response_format=PatientConcerns,
    )


# Build the agent once at import time and reuse it across calls.
# The agent is stateless — all state lives in the messages we pass in.
_agent = _build_agent()


def process_patient(patient_id: str) -> PatientConcerns:
    """Run the agent loop for a single patient. Returns structured concerns."""

    # This is the only message we send — the agent takes it from here,
    # calling tools as needed until it has enough info to respond.
    user_message = (
        f"Please review patient {patient_id}. "
        "Start by looking at their messages and record, then investigate "
        "any concerns you find. When done, output your findings."
    )

    logger.info("[%s] Starting agent run", patient_id)

    # invoke() runs the full ReAct loop to completion:
    #   user message → LLM → tool calls → tool results → LLM → ... → structured output
    # The result dict contains "messages" (full conversation) and
    # "structured_response" (the parsed PatientConcerns object).
    result = _agent.invoke(
        {"messages": [{"role": "user", "content": user_message}]},
    )

    # The structured response is already a PatientConcerns instance —
    # no JSON parsing, no code fence stripping, no manual field mapping.
    structured = result["structured_response"]

    # Patch in the patient_id and timestamps — the LLM sometimes gets
    # these wrong or leaves them empty, so we normalize here.
    now = datetime.now(timezone.utc).isoformat()
    for concern in structured.concerns:
        concern.patient_id = patient_id
        if not concern.last_updated:
            concern.last_updated = now

    if not structured.patient_id:
        structured.patient_id = patient_id

    logger.info("[%s] Agent found %d concerns", patient_id, len(structured.concerns))
    return structured
