"""
Agent tools — functions the LLM can call to explore patient data.

Each tool is a plain function that hits the main API over HTTP.
LangGraph reads the @tool decorator, docstring, and type hints to
generate the schema the LLM sees. The agent chooses which tools to
call and when.

This is intentionally naive: the agent has unrestricted access to all
patient data. No access controls, no scoping. That's the point —
later labs will fix this.
"""

import requests

# The @tool decorator does three things:
#   1. Registers the function as a LangChain tool
#   2. Generates a JSON schema from the type hints + docstring
#   3. Makes the function callable by the LLM via tool-calling
# Compare this to the manual approach (see docs/content/reference/manual-agent.md)
# where you'd write both the function AND a separate JSON schema by hand.
from langchain_core.tools import tool

# Tools call the main EHR API to fetch patient data.
# The agent API and main API are separate services — tools bridge the gap.
from lab2.agent import API_URL


# --- Tools the LLM can call ---
# The docstring becomes the tool description the LLM sees.
# Good docstrings = better tool selection by the model.


@tool
def list_patients() -> list[dict]:
    """Get a summary of all patients: IDs, names, birth dates, active conditions."""
    resp = requests.get(f"{API_URL}/patients")
    resp.raise_for_status()
    return resp.json()


@tool
def get_patient_record(patient_id: str) -> dict:
    """Get a patient's full record: demographics, conditions, allergies, medications, lab results, encounter history, messages, and social history."""
    resp = requests.get(f"{API_URL}/patients/{patient_id}")
    resp.raise_for_status()
    return resp.json()


@tool
def get_messages(patient_id: str) -> list[dict]:
    """Get all portal messages for a patient, newest first. Includes message body, sender, category, subject, and full thread."""
    resp = requests.get(f"{API_URL}/patients/{patient_id}/messages")
    resp.raise_for_status()
    return resp.json()


@tool
def search_labs(patient_id: str, test_name: str) -> list[dict]:
    """Search for all results of a specific lab test across all dates.

    Useful for tracking trends (e.g., 'potassium', 'eGFR', 'hemoglobin').
    Returns results sorted newest first with date, value, unit, and interpretation.
    """
    # Naive implementation: fetch the entire record and filter client-side.
    # A real system would have a dedicated search endpoint or query the DB.
    # This is fine for now — later labs can optimize.
    resp = requests.get(f"{API_URL}/patients/{patient_id}")
    resp.raise_for_status()
    record = resp.json()

    # Walk through every lab panel and collect matching results
    matches = []
    for lab in record.get("labs", []):
        for panel in lab.get("panels", []):
            for result in panel.get("results", []):
                if test_name.lower() in result["test"].lower():
                    matches.append({
                        "date": lab["date"],
                        "panel": panel["name"],
                        "test": result["test"],
                        "value": result["value"],
                        "unit": result.get("unit", ""),
                        "interpretation": result.get("interpretation", ""),
                    })
    return sorted(matches, key=lambda r: r["date"], reverse=True)


@tool
def get_inbox() -> list[dict]:
    """Get all messages across ALL patients that still need a provider response. Returns patient name, message subject, date, and category."""
    resp = requests.get(f"{API_URL}/inbox")
    resp.raise_for_status()
    return resp.json()


# ALL_TOOLS is what we pass to create_react_agent(). LangGraph inspects each
# tool's schema and makes them available to the LLM as callable functions.
ALL_TOOLS = [list_patients, get_patient_record, get_messages, search_labs, get_inbox]
