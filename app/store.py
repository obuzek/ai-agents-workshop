"""
Data store: loads and saves patient records from JSON files.

This is the only module that knows about the JSON format. Everything else
works with the Pydantic models in models.py.
"""

import json
import re
from pathlib import Path

from app.models import Patient

DATA_DIR = Path(__file__).parent.parent / "data" / "patients"


# --- JSON -> Model parsing ---


def _parse_patient(data: dict) -> Patient:
    """Parse a raw JSON dict into a Patient model.

    Pydantic handles nested model construction, alias resolution, and
    validation automatically via model_validate().
    """
    return Patient.model_validate(data)


# --- Public API ---


PATIENT_ID_RE = re.compile(r"^patient-\d{3}$")


def _validate_patient_id(patient_id: str):
    """Validate that a patient ID matches the expected format."""
    if not PATIENT_ID_RE.match(patient_id):
        raise ValueError(f"Invalid patient ID: {patient_id}")


def _patient_filepath(patient_id: str) -> Path:
    """Return the JSON file path for a patient ID."""
    _validate_patient_id(patient_id)
    return DATA_DIR / (patient_id.replace("-", "_") + ".json")


def load_patients() -> dict[str, Patient]:
    """Load all patient records from disk, keyed by patient ID."""
    patients = {}
    for filepath in sorted(DATA_DIR.glob("*.json")):
        with open(filepath) as f:
            patient = _parse_patient(json.load(f))
            patients[patient.id] = patient
    return patients


def load_patient(patient_id: str) -> Patient:
    """Load a single patient record by ID."""
    filepath = _patient_filepath(patient_id)
    with open(filepath) as f:
        return _parse_patient(json.load(f))


def save_reply(patient_id: str, message_id: str, sender_name: str, body: str, date: str):
    """Append a reply to a message in the JSON file on disk.
    This writes directly to JSON since we need to preserve the full file structure."""
    filepath = _patient_filepath(patient_id)

    with open(filepath) as f:
        data = json.load(f)

    for msg in data.get("messages", []):
        if msg["id"] == message_id:
            if "thread" not in msg:
                msg["thread"] = []
            msg["thread"].append({
                "date": date,
                "sender": {"name": sender_name, "role": "provider"},
                "body": body,
            })
            break

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
