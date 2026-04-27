"""
The improved agent — a primary agent + critic loop with grounding checks.

What changed from Lab 2:
- Focused search tools instead of get_patient_record (see tools.py)
- Grounding check verifies evidence against tool output (see grounding.py)
- Critic evaluates on-task behavior and grounding (see critic.py)
- All three are nodes in a LangGraph StateGraph that loops until approved

The graph: primary_agent → grounding → critic →(revise?)→ primary_agent
The full back-and-forth is visible in Langfuse traces.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Annotated, TypedDict

from langchain_openai import ChatOpenAI
from langfuse import observe
from langfuse.langchain import CallbackHandler
from langgraph.graph import StateGraph, START, END
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


# --- State schema ---


class ReviewState(TypedDict):
    """State that flows through the review graph.

    Each node receives the full state and returns a partial dict of updates.
    LangGraph merges the updates into the state before the next node runs.
    """
    patient_id: str                  # Which patient we're reviewing
    concerns: PatientConcerns | None # The primary agent's structured output
    tool_context: str                # Raw tool call results (grounding source-of-truth)
    revision_feedback: str           # Critic feedback for the next revision pass
    revision_count: int              # How many revision loops we've completed
    approved: bool                   # Whether the critic approved the output


# --- Graph nodes ---


_react_agent = create_react_agent(
    model=ChatOpenAI(model=MODEL, max_retries=3),
    tools=ALL_TOOLS,
    prompt=SYSTEM_PROMPT,
    response_format=PatientConcerns,
)

# Initialize Langfuse with PII masking on import (side effect sets up the singleton).
_langfuse_handler = create_langfuse_handler()


def _extract_tool_context(messages: list) -> str:
    """Extract tool call results from the ReAct agent's LangGraph message history.

    Filters for ToolMessage objects (the raw data each tool returned) and
    joins them. This becomes the source-of-truth for grounding checks —
    did the agent's evidence actually come from these tool outputs?
    """
    chunks = []
    for msg in messages:
        if hasattr(msg, "type") and msg.type == "tool":
            chunks.append(str(msg.content))
    return "\n---\n".join(chunks)


@observe(name="Primary Agent")
def primary_agent_node(state: ReviewState) -> dict:
    """Run the ReAct agent to generate or revise concerns.

    On the first pass, the agent investigates the patient record from scratch.
    On revision passes, the critic's feedback is appended to the prompt so
    the agent knows what to fix. Returns updated concerns and the raw tool
    output that the grounding check will verify against.
    """
    user_message = (
        f"Please review patient {state['patient_id']}. "
        "Start by looking at their messages and record, then investigate "
        "any concerns you find. When done, output your findings."
    )
    if state["revision_feedback"]:
        user_message += (
            "\n\nREVISION REQUESTED — a reviewer found issues with your "
            "previous output. Fix them:\n" + state["revision_feedback"]
        )

    handler = CallbackHandler()
    result = _react_agent.invoke(
        {"messages": [{"role": "user", "content": user_message}]},
        config={
            "callbacks": [handler],
            "metadata": {
                "langfuse_session_id": f"patient-review-{state['patient_id']}",
                "langfuse_tags": ["lab3", state["patient_id"]],
            },
        },
    )

    return {
        "concerns": result["structured_response"],
        "tool_context": _extract_tool_context(result["messages"]),
    }


def grounding_node(state: ReviewState) -> dict:
    """Run grounding checks and the critic in sequence.

    First, an LLM extracts specific medical claims from each concern
    (summary, action, evidence). Then each claim is verified against
    the raw tool output. Finally the critic evaluates whether concerns
    are on-task and grounded. If approved, sets approved=True.
    Otherwise, builds revision feedback for the next pass.
    """
    grounding_results: list[GroundingResult] = []
    for concern in state["concerns"].concerns:
        result = check_grounding(concern, state["tool_context"])
        grounding_results.append(result)

    concerns_json = json.dumps(
        [c.model_dump() for c in state["concerns"].concerns], indent=2
    )
    critic_result = critic_evaluate(concerns_json, grounding_results)

    if critic_result.approved:
        logger.info("[%s] Critic approved on revision %d",
                    state["patient_id"], state["revision_count"])
        return {"approved": True}

    # Build revision feedback for the next primary agent pass
    logger.info("[%s] Critic requested revision %d: %s",
                state["patient_id"], state["revision_count"] + 1,
                critic_result.summary)
    feedback_parts = [critic_result.summary]
    for fb in critic_result.concern_feedback:
        if fb.revision_needed:
            feedback_parts.append(f"- {fb.concern_title}: {fb.feedback}")

    return {
        "approved": False,
        "revision_feedback": "\n".join(feedback_parts),
        "revision_count": state["revision_count"] + 1,
    }


def should_revise(state: ReviewState) -> str:
    """Conditional edge: route back to the primary agent or finish.

    Returns "done" if the critic approved or we've hit MAX_REVISIONS.
    Returns "revise" to send the agent through another pass with feedback.
    """
    if state["approved"]:
        return "done"
    if state["revision_count"] >= MAX_REVISIONS:
        logger.warning("[%s] Max revisions reached, using last output", state["patient_id"])
        return "done"
    return "revise"


# --- Build the graph ---


def _build_review_graph():
    """Build the review graph: primary_agent → evaluate → (revise or done)."""
    graph = StateGraph(ReviewState)

    graph.add_node("primary_agent", primary_agent_node)
    graph.add_edge(START, "primary_agent")

    graph.add_node("evaluate", grounding_node)
    graph.add_edge("primary_agent", "evaluate")

    graph.add_conditional_edges("evaluate", should_revise, {
        "revise": "primary_agent",
        "done": END,
    })

    return graph.compile()


_review_graph = _build_review_graph()


# --- Public API ---


@observe(name="Patient Review")
def process_patient(patient_id: str) -> PatientConcerns:
    """Entry point: run the full review graph for a patient.

    Invokes the compiled graph with initial state, then normalizes the
    output (fills in patient_id, timestamps) before returning.
    """
    logger.info("[%s] Starting agent run", patient_id)

    result = _review_graph.invoke({
        "patient_id": patient_id,
        "concerns": None,
        "tool_context": "",
        "revision_feedback": "",
        "revision_count": 0,
        "approved": False,
    })

    structured = result["concerns"]

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
