# Reference: Manual Tool-Calling Agent (No Framework)

This is a reference implementation of a ReAct agent using the OpenAI API directly,
without LangGraph or any agent framework. The workshop uses LangGraph, but this
shows what's happening under the hood.

## The Agent Loop

The core loop: send messages to the LLM, check if it wants to call tools,
execute them, feed results back, repeat until it responds with text.

```python
"""
The naive agent — a ReAct tool-calling loop using the OpenAI API directly.

The agent receives a patient ID and a goal. It decides which tools to call,
in what order, and how to interpret the results. When it has gathered enough
information, it returns structured concerns.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from openai import OpenAI, RateLimitError

logger = logging.getLogger(__name__)

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
        except RateLimitError:
            if attempt == MAX_RETRIES - 1:
                raise
            wait = 2 ** attempt
            logger.warning("Rate limited, retrying in %ds...", wait)
            time.sleep(wait)
    raise RuntimeError("Unreachable")


SYSTEM_PROMPT = """\
You are a clinical inbox assistant. Review the patient's record and surface
actionable concerns for the doctor.

When done investigating, respond with JSON matching the PatientConcerns schema.
"""


def process_patient(patient_id: str):
    """Run the agent loop for a single patient."""

    # TOOLS and TOOL_FUNCTIONS are defined separately — see below
    from tools import TOOLS, TOOL_FUNCTIONS

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Please review patient {patient_id}."},
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
        if raw.startswith("```"):
            lines = raw.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw = "\n".join(lines)

        return json.loads(raw)

    raise RuntimeError(f"Hit max turns ({MAX_TURNS}) without finishing")
```

## Tool Definitions

With the raw OpenAI API, you define tools twice: once as a Python function,
and once as a JSON schema the LLM can read. LangGraph's `@tool` decorator
eliminates this duplication.

```python
# The function
def search_labs(patient_id: str, test_name: str) -> list[dict]:
    """Search for all results of a specific lab test across all dates."""
    record = get_patient_record(patient_id)
    matches = []
    for lab in record.get("labs", []):
        for panel in lab.get("panels", []):
            for result in panel.get("results", []):
                if test_name.lower() in result["test"].lower():
                    matches.append({
                        "date": lab["date"],
                        "test": result["test"],
                        "value": result["value"],
                        "unit": result.get("unit", ""),
                        "interpretation": result.get("interpretation", ""),
                    })
    return sorted(matches, key=lambda r: r["date"], reverse=True)


# The schema (you have to write this by hand)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_labs",
            "description": "Search for all results of a specific lab test across all dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "string",
                        "description": "The patient ID, e.g. 'patient-001'",
                    },
                    "test_name": {
                        "type": "string",
                        "description": "Lab test name (case-insensitive partial match)",
                    },
                },
                "required": ["patient_id", "test_name"],
            },
        },
    },
]

# The dispatch table (you have to maintain this too)
TOOL_FUNCTIONS = {
    "search_labs": search_labs,
}
```

## What LangGraph Gives You

The workshop uses LangGraph instead of this manual approach. Key differences:

| Manual approach | LangGraph |
|---|---|
| Hand-write JSON schemas for every tool | `@tool` decorator generates them from docstrings + type hints |
| Build your own loop: check `finish_reason`, dispatch tools, append messages | `create_react_agent` handles the full ReAct loop |
| Parse JSON output yourself (strip code fences, `json.loads`, construct models) | Structured output via `with_structured_output(PydanticModel)` |
| Manual retry logic for rate limits | Configurable retry policies |
| No visibility into what happened | Built-in tracing with LangSmith |
