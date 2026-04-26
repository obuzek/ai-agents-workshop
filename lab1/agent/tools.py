"""
Agent tools — functions the LLM can call to explore patient data.

Each tool is a plain function that hits the main API over HTTP.
The TOOLS list provides OpenAI-format tool definitions so the LLM
knows what's available. The agent chooses which tools to call and when.

This is intentionally naive: the agent has unrestricted access to all
patient data. No access controls, no scoping. That's the point —
later labs will fix this.
"""

import os
import requests

API_URL = os.environ.get("API_URL", "http://localhost:8000")


# --- Tool implementations ---


def list_patients() -> list[dict]:
    """Get a summary of all patients in the practice."""
    resp = requests.get(f"{API_URL}/patients")
    resp.raise_for_status()
    return resp.json()


def get_patient_record(patient_id: str) -> dict:
    """Get the full patient record: demographics, conditions, meds, labs, encounters, messages."""
    resp = requests.get(f"{API_URL}/patients/{patient_id}")
    resp.raise_for_status()
    return resp.json()


def get_messages(patient_id: str) -> list[dict]:
    """Get all messages for a patient, newest first."""
    resp = requests.get(f"{API_URL}/patients/{patient_id}/messages")
    resp.raise_for_status()
    return resp.json()


def search_labs(patient_id: str, test_name: str) -> list[dict]:
    """Search for all results of a specific lab test across all panels and dates.

    Returns matching results sorted newest first with date, value, unit, and interpretation.
    """
    record = get_patient_record(patient_id)
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


def get_inbox() -> list[dict]:
    """Get all messages across all patients that need a provider response."""
    resp = requests.get(f"{API_URL}/inbox")
    resp.raise_for_status()
    return resp.json()


# --- Tool definitions for the LLM ---
# OpenAI function-calling format. The agent sees these and decides what to call.

TOOL_FUNCTIONS = {
    "list_patients": list_patients,
    "get_patient_record": get_patient_record,
    "get_messages": get_messages,
    "search_labs": search_labs,
    "get_inbox": get_inbox,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_patients",
            "description": "Get a summary of all patients: IDs, names, birth dates, active conditions.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_patient_record",
            "description": (
                "Get a patient's full record: demographics, conditions, allergies, "
                "medications, lab results, encounter history, messages, and social history."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "string",
                        "description": "The patient ID, e.g. 'patient-001'",
                    },
                },
                "required": ["patient_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_messages",
            "description": (
                "Get all portal messages for a patient, newest first. "
                "Includes message body, sender, category, subject, and full thread."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "string",
                        "description": "The patient ID, e.g. 'patient-001'",
                    },
                },
                "required": ["patient_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_labs",
            "description": (
                "Search for all results of a specific lab test across all dates. "
                "Useful for tracking trends (e.g., 'potassium', 'eGFR', 'hemoglobin'). "
                "Returns results sorted newest first with date, value, unit, and interpretation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "string",
                        "description": "The patient ID, e.g. 'patient-001'",
                    },
                    "test_name": {
                        "type": "string",
                        "description": "Lab test name to search for (case-insensitive partial match), e.g. 'potassium', 'hemoglobin', 'eGFR'",
                    },
                },
                "required": ["patient_id", "test_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_inbox",
            "description": (
                "Get all messages across ALL patients that still need a provider response. "
                "Returns patient name, message subject, date, and category."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]
