"""
The naive agent — a ReAct tool-calling loop.

The agent receives a patient ID and a goal. It decides which tools to call,
in what order, and how to interpret the results. When it has gathered enough
information, it returns structured concerns.

This is the core of Lab 1: a real agent loop where the LLM drives the
investigation. The structured output is only for the final result — the
reasoning and tool selection are entirely up to the model.
"""

import json
import os
import time
from datetime import datetime, timezone
from openai import OpenAI, RateLimitError

from lab1.agent.tools import TOOLS, TOOL_FUNCTIONS
from lab1.agent.models import Concern, PatientConcerns, RelatedData

client = OpenAI()  # reads OPENAI_API_KEY, OPENAI_BASE_URL from env
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
MAX_TURNS = 20  # safety limit on tool-calling rounds
MAX_RETRIES = 5  # retries on rate limit


def _llm_call(messages, tools):
    """Call the LLM with retry + exponential backoff on rate limits."""
    for attempt in range(MAX_RETRIES):
        try:
            return client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=tools,
            )
        except RateLimitError as e:
            if attempt == MAX_RETRIES - 1:
                raise
            wait = 2 ** attempt
            print(f"  Rate limited, retrying in {wait}s...")
            time.sleep(wait)
    raise RuntimeError("Unreachable")

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

When you are done investigating, respond with ONLY this JSON (no other text):

{
  "patient_id": "patient-001",
  "patient_name": "First Last",
  "concerns": [
    {
      "id": "concern-001-001",
      "patient_id": "patient-001",
      "title": "Brief title (5 words max)",
      "summary": "One sentence: the clinical fact and why it matters.",
      "action": "Specific action the doctor should take",
      "concern_type": "medication|lab_result|symptom|follow_up|administrative",
      "urgency": "routine|soon|urgent",
      "status": "unresolved|monitoring|resolved",
      "onset": "YYYY-MM-DD",
      "last_updated": "<current ISO timestamp>",
      "evidence": ["TSH 4.8 mIU/L (2026-04-01)", "Previous TSH 3.1 (2025-06-18)"],
      "related": {
        "message_ids": ["msg-001-001"],
        "lab_dates": ["2025-01-09"],
        "conditions": ["Essential hypertension"],
        "encounter_dates": ["2025-04-02"]
      }
    }
  ]
}
"""


def process_patient(patient_id: str) -> PatientConcerns:
    """Run the agent loop for a single patient. Returns structured concerns."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": (
            f"Please review patient {patient_id}. "
            "Start by looking at their messages and record, then investigate "
            "any concerns you find. When done, output your findings as JSON."
        )},
    ]

    for turn in range(MAX_TURNS):
        response = _llm_call(messages, TOOLS)

        choice = response.choices[0]

        # If the model wants to call tools, execute them and feed results back
        if choice.finish_reason == "tool_calls":
            messages.append(choice.message.model_dump())

            for tool_call in choice.message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)

                print(f"  [{patient_id}] tool: {fn_name}({fn_args})")

                fn = TOOL_FUNCTIONS.get(fn_name)
                if fn is None:
                    result = {"error": f"Unknown tool: {fn_name}"}
                else:
                    try:
                        result = fn(**fn_args)
                    except Exception as e:
                        result = {"error": str(e)}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, default=str),
                })

            continue

        # Model is done — parse the final JSON response
        raw = choice.message.content.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            raw = "\n".join(lines)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"  [{patient_id}] WARNING: Could not parse agent output: {e}")
            print(f"  Raw output: {raw[:200]}...")
            return PatientConcerns(patient_id=patient_id, patient_name="Unknown")

        now = datetime.now(timezone.utc).isoformat()
        concerns = []
        for c in data.get("concerns", []):
            related = c.get("related", {})
            concerns.append(Concern(
                id=c.get("id", ""),
                patient_id=patient_id,
                title=c.get("title", ""),
                summary=c.get("summary", ""),
                action=c.get("action", ""),
                concern_type=c.get("concern_type", ""),
                urgency=c.get("urgency", "routine"),
                status=c.get("status", "monitoring"),
                onset=c.get("onset", ""),
                last_updated=c.get("last_updated", now),
                evidence=c.get("evidence", []),
                related=RelatedData(
                    message_ids=related.get("message_ids", []),
                    lab_dates=related.get("lab_dates", []),
                    conditions=related.get("conditions", []),
                    encounter_dates=related.get("encounter_dates", []),
                ),
            ))

        return PatientConcerns(
            patient_id=patient_id,
            patient_name=data.get("patient_name", "Unknown"),
            concerns=concerns,
        )

    # Safety: hit max turns without finishing
    print(f"  [{patient_id}] WARNING: Hit max turns ({MAX_TURNS}) without finishing")
    return PatientConcerns(patient_id=patient_id, patient_name="Unknown")
