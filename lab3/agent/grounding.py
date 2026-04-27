"""
Grounding check — verify that the agent's evidence is real, not hallucinated.

Two implementations behind a runtime toggle:
  1. LLM-as-judge: the same OpenAI model evaluates whether each concern's
     evidence is supported by the tool output. Convenient but circular —
     the LLM is checking its own work.
  2. Granite Guardian: a purpose-built IBM model for groundedness detection,
     served locally via Ollama. A separate model avoids self-evaluation bias.

The toggle follows the same pattern as Lab 2's PII masking toggle:
a module-level flag flipped by the agent API at runtime.
"""

import json
import logging
import os

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# --- Runtime toggle ---
# "llm" = LLM-as-judge, "guardian" = Granite Guardian via Ollama
grounding_mode: str = "guardian"

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
GUARDIAN_MODEL = os.environ.get("GUARDIAN_MODEL", "ibm/granite3.2-guardian")


# --- Structured output for grounding verdicts ---


class EvidenceVerdict(BaseModel):
    """Grounding verdict for a single piece of evidence."""
    evidence: str
    supported: bool
    reason: str


class GroundingResult(BaseModel):
    """Grounding results for one concern."""
    concern_title: str
    verdicts: list[EvidenceVerdict]
    all_supported: bool


# --- LLM-as-judge implementation ---


_JUDGE_PROMPT = """\
You are a grounding evaluator. Given source data from tool calls and a list of
evidence claims from an agent, determine whether each claim is supported by the
source data.

For each evidence string, output:
- supported: true if the claim matches the source data (values, dates, names)
- supported: false if the claim contains information not in the source data
- reason: brief explanation

SOURCE DATA:
{context}

EVIDENCE CLAIMS:
{evidence}
"""


def _check_llm_judge(evidence: list[str], context: str) -> list[EvidenceVerdict]:
    """Use the same OpenAI model to evaluate groundedness."""
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")
    llm = ChatOpenAI(model=model).with_structured_output(
        type("EvidenceVerdicts", (BaseModel,), {
            "__annotations__": {"verdicts": list[EvidenceVerdict]},
        })
    )
    result = llm.invoke(_JUDGE_PROMPT.format(
        context=context,
        evidence=json.dumps(evidence),
    ))
    return result.verdicts


# --- Granite Guardian implementation ---


def _check_guardian(evidence: list[str], context: str) -> list[EvidenceVerdict]:
    """Use Granite Guardian via Ollama for groundedness detection."""
    import ollama

    client = ollama.Client(host=OLLAMA_BASE_URL)
    verdicts = []

    for claim in evidence:
        response = client.chat(
            model=GUARDIAN_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Check if the following claim is supported by the context.\n\n"
                        f"Context: {context}\n\n"
                        f"Claim: {claim}"
                    ),
                },
            ],
            options={"temperature": 0.0},
        )
        text = response["message"]["content"]
        # Granite Guardian outputs Yes (risk = hallucination) or No (grounded)
        is_hallucinated = "yes" in text.lower().split("</think>")[-1].lower()
        verdicts.append(EvidenceVerdict(
            evidence=claim,
            supported=not is_hallucinated,
            reason=text.strip(),
        ))

    return verdicts


# --- Public API ---


def check_grounding(concern_title: str, evidence: list[str], context: str) -> GroundingResult:
    """Check whether evidence claims are grounded in source data.

    Uses the current grounding_mode to select the implementation.
    """
    if not evidence:
        return GroundingResult(concern_title=concern_title, verdicts=[], all_supported=True)

    if grounding_mode == "guardian":
        verdicts = _check_guardian(evidence, context)
    else:
        verdicts = _check_llm_judge(evidence, context)

    return GroundingResult(
        concern_title=concern_title,
        verdicts=verdicts,
        all_supported=all(v.supported for v in verdicts),
    )
