"""
Agent tools — functions the LLM can call to explore patient data.

Each tool is a plain function decorated with @tool from the IBM watsonx
Orchestrate ADK. The ADK reads the decorator, docstring, and type hints
to generate the schema the LLM sees. The agent chooses which tools to
call and when.

These tools run inside watsonx Orchestrate, not on your laptop. This file
is uploaded as-is, so it must be self-contained: no imports from the rest
of the repo.

This is intentionally naive: the agent has unrestricted access to all
patient data. No access controls, no scoping. That's the point —
later labs will fix this.
"""

import requests

# The @tool decorator from the Orchestrate ADK does three things:
#   1. Registers the function as a callable tool
#   2. Generates a JSON schema from the type hints + docstring
#   3. Makes the tool importable via `orchestrate tools import -k python`
#
# expected_credentials=EHR_CREDENTIALS tells Orchestrate the tool needs the
# EHR connection, so connections.key_value() can read it at run time.
from ibm_watsonx_orchestrate.agent_builder.tools import tool
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType, ExpectedCredentials
from ibm_watsonx_orchestrate.run import connections

# Tools call the EHR API to fetch patient data. Orchestrate can't reach
# localhost, so the tools call the shared workshop EHR. Its URL and your
# tenant ID (which copy of the patients is yours) live in an Orchestrate
# key-value connection rather than in this code. deploy.py creates it.
EHR_APP_ID = "lakeview_ehr"
EHR_CREDENTIALS = [ExpectedCredentials(app_id=EHR_APP_ID, type=ConnectionType.KEY_VALUE)]


def _get(path: str):
    """GET from the EHR API, using the URL and tenant stored in the Orchestrate connection."""
    conn = connections.key_value(EHR_APP_ID)
    return requests.get(f"{conn['base_url'].rstrip('/')}{path}",
                        headers={"X-Tenant": conn.get("tenant", "")}, timeout=30)


# --- Tools the LLM can call ---
# The docstring becomes the tool description the LLM sees.
# Good docstrings = better tool selection by the model.


@tool(expected_credentials=EHR_CREDENTIALS)
def list_patients() -> list[dict]:
    """Get a summary of all patients: IDs, names, birth dates, active conditions."""
    resp = _get("/patients")
    resp.raise_for_status()
    return resp.json()


@tool(expected_credentials=EHR_CREDENTIALS)
def get_patient_record(patient_id: str) -> dict:
    """Get a patient's full record: demographics, conditions, allergies, medications, lab results, encounter history, messages, and social history."""
    resp = _get(f"/patients/{patient_id}")
    resp.raise_for_status()
    return resp.json()


@tool(expected_credentials=EHR_CREDENTIALS)
def get_messages(patient_id: str) -> list[dict]:
    """Get all portal messages for a patient, newest first. Includes message body, sender, category, subject, and full thread."""
    resp = _get(f"/patients/{patient_id}/messages")
    resp.raise_for_status()
    return resp.json()


@tool(expected_credentials=EHR_CREDENTIALS)
def search_labs(patient_id: str, test_name: str) -> list[dict]:
    """Search for all results of a specific lab test across all dates.

    Useful for tracking trends (e.g., 'potassium', 'eGFR', 'hemoglobin').
    Returns results sorted newest first with date, value, unit, and interpretation.
    """
    # Naive implementation: fetch the entire record and filter client-side.
    # A real system would have a dedicated search endpoint or query the DB.
    # This is fine for Lab 1 — later labs can optimize.
    resp = _get(f"/patients/{patient_id}")
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


@tool(expected_credentials=EHR_CREDENTIALS)
def get_inbox() -> list[dict]:
    """Get all messages across ALL patients that still need a provider response. Returns patient name, message subject, date, and category."""
    resp = _get("/inbox")
    resp.raise_for_status()
    return resp.json()
