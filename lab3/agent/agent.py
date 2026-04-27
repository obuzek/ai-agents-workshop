"""
The improved agent — a primary agent + critic loop with grounding checks.

What changed from Lab 2:
- Focused search tools instead of get_patient_record (see tools.py)
- Grounding check verifies evidence against tool output (see grounding.py)
- Critic evaluates on-task behavior and grounding (see critic.py)
- All three run in a loop: agent → grounding → critic → revise → repeat

The loop continues until the critic approves or MAX_REVISIONS is reached.
The full back-and-forth is visible in Langfuse traces.
"""

import json
import logging
import os
from datetime import datetime, timezone

from langchain_openai import ChatOpenAI
from langfuse import observe
from langfuse.langchain import CallbackHandler
from langgraph.prebuilt import create_react_agent

from lab3.agent.tools import ALL_TOOLS
from lab3.agent.models import PatientConcerns
from lab3.agent.observability import create_langfuse_handler
from lab3.agent.grounding import check_grounding, GroundingResult
from lab3.agent.critic import evaluate as critic_evaluate

logger = logging.getLogger(__name__)

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
MAX_REVISIONS = int(os.environ.get("MAX_REVISIONS", "2"))

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
    """Build the LangGraph ReAct agent with focused search tools."""
    llm = ChatOpenAI(model=MODEL)
    return create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        prompt=SYSTEM_PROMPT,
        response_format=PatientConcerns,
    )


_agent = _build_agent()

# Initialize Langfuse with PII masking on import (side effect sets up the singleton).
_langfuse_handler = create_langfuse_handler()


def _extract_tool_context(messages: list) -> str:
    """Extract tool call results from the agent's message history.

    This becomes the source-of-truth context for grounding checks —
    did the agent's evidence actually come from these tool outputs?
    """
    chunks = []
    for msg in messages:
        if hasattr(msg, "type") and msg.type == "tool":
            chunks.append(str(msg.content))
    return "\n---\n".join(chunks)


@observe(name="Primary Agent")
def _run_primary_agent(patient_id: str, revision_feedback: str = "") -> tuple[PatientConcerns, str]:
    """Run the primary agent, optionally with revision feedback from the critic."""
    user_message = (
        f"Please review patient {patient_id}. "
        "Start by looking at their messages and record, then investigate "
        "any concerns you find. When done, output your findings."
    )
    if revision_feedback:
        user_message += (
            "\n\nREVISION REQUESTED — a reviewer found issues with your "
            "previous output. Fix them:\n" + revision_feedback
        )

    # CallbackHandler() auto-nests under the current @observe span.
    handler = CallbackHandler()
    result = _agent.invoke(
        {"messages": [{"role": "user", "content": user_message}]},
        config={
            "callbacks": [handler],
            "metadata": {
                "langfuse_session_id": f"patient-review-{patient_id}",
                "langfuse_tags": ["lab3", patient_id],
            },
        },
    )

    structured = result["structured_response"]
    context = _extract_tool_context(result["messages"])
    return structured, context


@observe(name="Patient Review")
def process_patient(patient_id: str) -> PatientConcerns:
    """Run the agent loop: primary agent → grounding → critic → revise.

    The loop continues until the critic approves or MAX_REVISIONS is reached.
    """
    logger.info("[%s] Starting agent run", patient_id)

    structured, context = _run_primary_agent(patient_id)

    for revision in range(MAX_REVISIONS):
        # Grounding: check each concern's evidence against tool output
        grounding_results: list[GroundingResult] = []
        for concern in structured.concerns:
            result = check_grounding(concern.title, concern.evidence, context)
            grounding_results.append(result)

        # Critic: evaluate on-task behavior + grounding
        concerns_json = json.dumps(
            [c.model_dump() for c in structured.concerns], indent=2
        )
        critic_result = critic_evaluate(concerns_json, grounding_results)

        if critic_result.approved:
            logger.info("[%s] Critic approved after %d revision(s)", patient_id, revision)
            break

        # Build revision feedback and re-run
        logger.info("[%s] Critic requested revision %d: %s", patient_id, revision + 1, critic_result.summary)
        feedback_parts = [critic_result.summary]
        for fb in critic_result.concern_feedback:
            if fb.revision_needed:
                feedback_parts.append(f"- {fb.concern_title}: {fb.feedback}")
        structured, context = _run_primary_agent(
            patient_id, revision_feedback="\n".join(feedback_parts)
        )
    else:
        logger.warning("[%s] Max revisions reached, using last output", patient_id)

    # Normalize patient_id and timestamps
    now = datetime.now(timezone.utc).isoformat()
    for concern in structured.concerns:
        concern.patient_id = patient_id
        if not concern.last_updated:
            concern.last_updated = now
    if not structured.patient_id:
        structured.patient_id = patient_id

    logger.info("[%s] Final: %d concerns", patient_id, len(structured.concerns))
    return structured
