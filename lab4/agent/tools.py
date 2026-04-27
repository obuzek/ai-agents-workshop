"""
Agent tools — keyword-based search tools for patient data.

Lab 4 replaces the naive "dump everything" tools from Labs 1–2 with
focused search tools. The agent must specify *what* it's looking for,
which forces it to reason about relevance and reduces token waste / PHI
exposure in traces.

Each tool hits a dedicated search endpoint on the main API.

SECURITY (new in Lab 4):
Tools are created per-patient via `create_tools()`. All patient-specific
tools enforce an access check: the agent can only query data for the
patient it was authorized to review. `list_patients` and `get_inbox`
are unscoped — the agent can see the clinic directory and inbox.
"""

import logging

import requests
from langchain_core.tools import tool

from lab4.agent import API_URL

logger = logging.getLogger(__name__)


def _check_access(patient_id: str, authorized_id: str) -> str | None:
    """Return an error message if access is denied, or None if allowed."""
    if patient_id != authorized_id:
        msg = (
            f"Access denied: you are only authorized to access patient "
            f"{authorized_id}. You cannot access patient {patient_id}."
        )
        logger.warning("Tool access denied: requested %s, authorized %s",
                        patient_id, authorized_id)
        return msg
    return None


def create_tools(authorized_patient_id: str) -> list:
    """Create a tool list scoped to a specific patient.

    Unscoped tools (list_patients, get_inbox) are available to all agents.
    Patient-specific tools check that the requested patient_id matches
    the authorized_patient_id before making any API call.
    """

    # --- Unscoped tools ---

    @tool
    def list_patients() -> list[dict]:
        """Get a summary of all patients: IDs, names, birth dates, active conditions."""
        resp = requests.get(f"{API_URL}/patients")
        resp.raise_for_status()
        return resp.json()

    @tool
    def get_inbox() -> list[dict]:
        """Get all messages across ALL patients that still need a provider response. Returns patient name, message subject, date, and category."""
        resp = requests.get(f"{API_URL}/inbox")
        resp.raise_for_status()
        return resp.json()

    # --- Scoped tools ---

    @tool
    def get_demographics(patient_id: str) -> dict | str:
        """Get a patient's demographics: name, birth date, contact info, insurance."""
        denied = _check_access(patient_id, authorized_patient_id)
        if denied:
            return denied
        resp = requests.get(f"{API_URL}/patients/{patient_id}/demographics")
        resp.raise_for_status()
        return resp.json()

    @tool
    def get_messages(patient_id: str) -> list[dict] | str:
        """Get all portal messages for a patient, newest first. Includes message body, sender, category, subject, and full thread."""
        denied = _check_access(patient_id, authorized_patient_id)
        if denied:
            return denied
        resp = requests.get(f"{API_URL}/patients/{patient_id}/messages")
        resp.raise_for_status()
        return resp.json()

    @tool
    def search_conditions(patient_id: str, keyword: str) -> list[dict] | str:
        """Search a patient's conditions by keyword (e.g., 'diabetes', 'hypertension').

        Returns matching conditions with status, onset date, and notes.
        """
        denied = _check_access(patient_id, authorized_patient_id)
        if denied:
            return denied
        resp = requests.get(f"{API_URL}/patients/{patient_id}/conditions", params={"q": keyword})
        resp.raise_for_status()
        return resp.json()

    @tool
    def search_medications(patient_id: str, keyword: str) -> list[dict] | str:
        """Search a patient's medications by keyword (e.g., 'metformin', 'statin').

        Returns matching medications with dosage, frequency, status, and prescriber.
        """
        denied = _check_access(patient_id, authorized_patient_id)
        if denied:
            return denied
        resp = requests.get(f"{API_URL}/patients/{patient_id}/medications", params={"q": keyword})
        resp.raise_for_status()
        return resp.json()

    @tool
    def search_labs(patient_id: str, test_name: str) -> list[dict] | str:
        """Search for lab results by test name (e.g., 'potassium', 'eGFR', 'hemoglobin').

        Returns matching results sorted newest first with date, value, unit, and interpretation.
        Useful for tracking trends over time.
        """
        denied = _check_access(patient_id, authorized_patient_id)
        if denied:
            return denied
        resp = requests.get(f"{API_URL}/patients/{patient_id}/labs", params={"test": test_name})
        resp.raise_for_status()
        return resp.json()

    @tool
    def search_encounters(patient_id: str, keyword: str) -> list[dict] | str:
        """Search a patient's encounters by keyword (e.g., 'follow-up', 'annual', 'urgent').

        Returns matching encounters with date, type, provider, reason, and notes.
        """
        denied = _check_access(patient_id, authorized_patient_id)
        if denied:
            return denied
        resp = requests.get(f"{API_URL}/patients/{patient_id}/encounters", params={"q": keyword})
        resp.raise_for_status()
        return resp.json()

    return [
        list_patients, get_demographics, get_messages,
        search_conditions, search_medications, search_labs, search_encounters,
        get_inbox,
    ]
