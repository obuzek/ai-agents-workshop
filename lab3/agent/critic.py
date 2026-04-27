"""
Critic — evaluates whether the agent stayed on task.

The critic receives the primary agent's concerns plus grounding results
and checks two things:
  1. Is each concern on-task? (Surfacing actionable items for the doctor,
     not making diagnoses or drafting replies.)
  2. Are the grounding results acceptable? (Incorporates verdicts from
     the grounding check module.)

Returns structured feedback that the primary agent uses to revise its output.
This is a single LLM call with structured output — not a tool-calling agent.
"""

import logging
import os

from langchain_openai import ChatOpenAI
from langfuse import observe
from langfuse.langchain import CallbackHandler
from pydantic import BaseModel

from lab3.agent.grounding import GroundingResult

logger = logging.getLogger(__name__)


# --- Structured output ---


class ConcernFeedback(BaseModel):
    """Feedback for a single concern."""
    concern_title: str
    on_task: bool
    grounded: bool
    revision_needed: bool
    feedback: str


class CriticResult(BaseModel):
    """The critic's evaluation of all concerns."""
    concern_feedback: list[ConcernFeedback]
    approved: bool
    summary: str


# --- Critic prompt ---


_CRITIC_PROMPT = """\
You are a quality reviewer for a clinical inbox assistant. The assistant reviews
patient records and surfaces concerns for the doctor. Your job is to evaluate
whether each concern meets the quality bar.

For each concern, check:
1. ON-TASK: Is this surfacing an actionable item for the doctor? Flag concerns
   that make diagnoses, draft replies, give clinical recommendations, or go
   beyond what's in the record.
2. GROUNDED: The grounding check results are provided. If evidence was flagged
   as unsupported, the concern needs revision.
3. EVIDENCE QUALITY: Are the evidence strings specific (values, dates, names)
   rather than vague descriptions?

Set approved=true ONLY if every concern passes all checks.

CONCERNS:
{concerns}

GROUNDING RESULTS:
{grounding}
"""


@observe(name="Critic Evaluation")
def evaluate(concerns_json: str, grounding_results: list[GroundingResult]) -> CriticResult:
    """Run the critic on the primary agent's output.

    On failure (rate limits, timeouts), approves the output as-is —
    better to surface unreviewed concerns than to crash the run.
    """
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")
    llm = ChatOpenAI(model=model, max_retries=3).with_structured_output(CriticResult)

    grounding_json = "\n".join(r.model_dump_json() for r in grounding_results)

    try:
        handler = CallbackHandler()
        return llm.invoke(
            _CRITIC_PROMPT.format(
                concerns=concerns_json,
                grounding=grounding_json or "(no grounding results)",
            ),
            config={"callbacks": [handler]},
        )
    except Exception:
        logger.warning("Critic evaluation failed, auto-approving", exc_info=True)
        return CriticResult(
            concern_feedback=[],
            approved=True,
            summary="Critic unavailable — output accepted without review.",
        )
