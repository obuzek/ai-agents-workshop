"""
Grounding check — verify that the agent's output is real, not hallucinated.

Three steps:
  1. Claim extraction: an LLM reads the concern (summary, action, evidence)
     and extracts every specific medical claim that needs verification.
  2. Grounding: each extracted claim is checked against the tool output.
     Two implementations behind a runtime toggle:
       a. LLM-as-judge: the configured LLM evaluates groundedness.
       b. Granite Guardian: a purpose-built IBM model via Ollama.
  3. Results are returned to the caller (the evaluate node) for the critic.

The toggle follows the same pattern as Lab 2's PII masking toggle:
a module-level flag flipped by the agent API at runtime.
"""

import json
import logging
import os

from app.llm import get_chat_model
from langfuse import observe
from langfuse.langchain import CallbackHandler
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# --- Runtime toggle ---
# "llm" = LLM-as-judge, "guardian" = Granite Guardian via Ollama
grounding_mode: str = "llm"

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
GUARDIAN_MODEL = os.environ.get("GUARDIAN_MODEL", "ibm/granite3.2-guardian:3b")


# --- Structured output ---


class ExtractedClaims(BaseModel):
    """Medical claims extracted from a concern for grounding verification."""
    claims: list[str]


class ClaimVerdict(BaseModel):
    """Grounding verdict for a single claim."""
    claim: str
    supported: bool
    reason: str


class ClaimVerdicts(BaseModel):
    """Wrapper for structured output — list of grounding verdicts."""
    verdicts: list[ClaimVerdict]


class GroundingResult(BaseModel):
    """Grounding results for one concern."""
    concern_title: str
    claims: list[str]
    verdicts: list[ClaimVerdict]
    all_supported: bool


# --- Claim extraction ---


_EXTRACT_PROMPT = """\
You are a medical claim extractor. Given a concern from a clinical inbox
assistant, extract every specific medical claim that can be verified against
source data.

A claim is a self-contained factual assertion about the patient — a diagnosis,
a lab value, a medication, a date, a symptom, a message content. Each claim
must be understandable on its own without looking anything up.

RULES:
- Do NOT include internal IDs (message IDs, encounter IDs, patient IDs).
  Replace them with the actual content they refer to.
- Do NOT include vague descriptions like "recent message about X" or
  "previous encounters."
- Each claim must contain the specific fact being asserted.

Good claims:
- "Patient's HbA1c is 8.2%"
- "Patient was prescribed metformin 500mg"
- "Patient reported blurry vision in a portal message dated 2026-04-15"
- "TSH trending up from 3.1 to 4.8 over 6 months"
- "Patient expressed anxiety about pending MRI results on 2026-04-24"

Bad claims (do not extract):
- "Recent lab results"
- "Messages from August"
- "Patient awaiting MRI results: msg-002-003"
- "See encounter enc-005"

CONCERN:
Title: {title}
Summary: {summary}
Action: {action}
Evidence: {evidence}
"""


@observe(name="Claim Extraction")
def _extract_claims(title: str, summary: str, action: str, evidence: list[str]) -> list[str]:
    """Extract specific, verifiable medical claims from a concern."""
    llm = get_chat_model(max_retries=3).with_structured_output(ExtractedClaims)
    handler = CallbackHandler()
    result = llm.invoke(
        _EXTRACT_PROMPT.format(
            title=title,
            summary=summary,
            action=action or "(none)",
            evidence="\n".join(f"- {e}" for e in evidence) if evidence else "(none)",
        ),
        config={"callbacks": [handler]},
    )
    return result.claims


# --- LLM-as-judge implementation ---


_JUDGE_PROMPT = """\
You are a grounding evaluator. Given source data from tool calls and a list of
medical claims from an agent, determine whether each claim is supported by the
source data.

For each claim, output:
- supported: true if the claim matches the source data (values, dates, names)
- supported: false if the claim contains information not in the source data
- reason: brief explanation

SOURCE DATA (tool call results):
{context}

CLAIMS TO VERIFY:
{claims}
"""


@observe(name="Grounding: LLM-as-Judge")
def _check_llm_judge(claims: list[str], context: str) -> list[ClaimVerdict]:
    """Use the configured LLM to evaluate groundedness."""
    llm = get_chat_model(max_retries=3).with_structured_output(ClaimVerdicts)
    handler = CallbackHandler()
    result = llm.invoke(
        _JUDGE_PROMPT.format(context=context, claims=json.dumps(claims)),
        config={"callbacks": [handler]},
    )
    return result.verdicts


# --- Granite Guardian implementation ---


@observe(name="Grounding: Granite Guardian")
def _check_guardian(claims: list[str], context: str) -> list[ClaimVerdict]:
    """Use Granite Guardian via Ollama for groundedness detection.

    Uses the canonical Granite Guardian message format:
    - system: "groundedness" (selects the groundedness risk detector)
    - user: "Context: ...\n\nClaim: ..." (the claim to verify)

    Guardian outputs Yes (risk detected = hallucination) or No (grounded).
    """
    import ollama

    client = ollama.Client(host=OLLAMA_BASE_URL)
    verdicts = []

    for claim in claims:
        response = client.chat(
            model=GUARDIAN_MODEL,
            messages=[
                {"role": "system", "content": "groundedness"},
                {
                    "role": "user",
                    "content": f"Context: {context}\n\nClaim: {claim}",
                },
            ],
            options={"temperature": 0.0},
        )
        text = response["message"]["content"]
        # Guardian outputs "Yes" (risk = hallucination) or "No" (grounded).
        # Strip any <think> reasoning tags if present.
        answer = text.split("</think>")[-1].strip().lower()
        is_hallucinated = "yes" in answer
        verdicts.append(ClaimVerdict(
            claim=claim,
            supported=not is_hallucinated,
            reason=text.strip(),
        ))

    return verdicts


# --- Public API ---


@observe(name="Grounding Check")
def check_grounding(concern, tool_context: str) -> GroundingResult:
    """Extract medical claims from a concern and verify them against tool output.

    Step 1: An LLM extracts specific, verifiable claims from the concern's
    summary, action, and evidence fields.
    Step 2: Each claim is checked against the tool output using the active
    grounding mode (LLM-as-judge or Granite Guardian).

    On failure (rate limits, timeouts), assumes grounded and lets the
    original output stand — better to surface an unverified concern
    than to crash the entire run.
    """
    try:
        claims = _extract_claims(
            concern.title, concern.summary, concern.action, concern.evidence
        )
    except Exception:
        logger.warning("Claim extraction failed for '%s', skipping grounding", concern.title, exc_info=True)
        return GroundingResult(
            concern_title=concern.title, claims=[], verdicts=[], all_supported=True
        )

    if not claims:
        return GroundingResult(
            concern_title=concern.title, claims=[], verdicts=[], all_supported=True
        )

    try:
        if grounding_mode == "guardian":
            verdicts = _check_guardian(claims, tool_context)
        else:
            verdicts = _check_llm_judge(claims, tool_context)
    except Exception:
        logger.warning("Grounding check failed for '%s', assuming grounded", concern.title, exc_info=True)
        verdicts = [
            ClaimVerdict(claim=c, supported=True, reason="grounding check unavailable")
            for c in claims
        ]

    return GroundingResult(
        concern_title=concern.title,
        claims=claims,
        verdicts=verdicts,
        all_supported=all(v.supported for v in verdicts),
    )
