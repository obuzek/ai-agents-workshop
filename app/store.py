"""
Data store: loads and saves patient records from JSON files.

This is the only module that knows about the JSON format. Everything else
works with the dataclasses in models.py.
"""

import json
import re
from pathlib import Path

from app.models import (
    Patient, Condition, Allergy, Medication,
    Lab, LabPanel, LabResult,
    Encounter, SOAPNotes,
    Message, ThreadEntry, Sender,
)

DATA_DIR = Path(__file__).parent.parent / "data" / "patients"


# --- JSON -> Model parsing ---


def _parse_sender(data: dict) -> Sender:
    return Sender(name=data["name"], role=data["role"])


def _parse_thread_entry(data: dict) -> ThreadEntry:
    return ThreadEntry(
        date=data["date"],
        sender=_parse_sender(data["sender"]),
        body=data["body"],
    )


def _parse_message(data: dict) -> Message:
    return Message(
        id=data["id"],
        date=data["date"],
        sender=_parse_sender(data["sender"]),
        category=data["category"],
        subject=data["subject"],
        body=data["body"],
        thread=[_parse_thread_entry(t) for t in data.get("thread", [])],
    )


def _parse_condition(data: dict) -> Condition:
    return Condition(
        display=data["code"]["display"],
        status=data["status"],
        onset_date=data.get("onsetDate", ""),
        notes=data.get("notes", ""),
    )


def _parse_allergy(data: dict) -> Allergy:
    return Allergy(substance=data["substance"], reaction=data["reaction"])


def _parse_medication(data: dict) -> Medication:
    return Medication(
        display=data["code"]["display"],
        dosage=data["dosage"],
        frequency=data["frequency"],
        prescriber=data["prescriber"],
        status=data["status"],
    )


def _parse_lab_result(data: dict) -> LabResult:
    return LabResult(
        test=data["test"],
        value=data["value"],
        unit=data.get("unit", ""),
        interpretation=data.get("interpretation", ""),
    )


def _parse_lab(data: dict) -> Lab:
    return Lab(
        date=data["date"],
        ordered_by=data["orderedBy"],
        panels=[
            LabPanel(
                name=p["name"],
                results=[_parse_lab_result(r) for r in p.get("results", [])],
            )
            for p in data.get("panels", [])
        ],
    )


def _parse_encounter(data: dict) -> Encounter:
    notes_data = data.get("notes", {})
    return Encounter(
        date=data["date"],
        reason=data.get("reasonForVisit", "Visit"),
        notes=SOAPNotes(
            subjective=notes_data.get("subjective", ""),
            objective=notes_data.get("objective", ""),
            assessment=notes_data.get("assessment", ""),
            plan=notes_data.get("plan", ""),
        ),
    )


def _parse_patient(data: dict) -> Patient:
    demo = data["demographics"]
    social = data.get("socialHistory", {})
    return Patient(
        id=data["id"],
        given_name=demo["name"]["given"],
        family_name=demo["name"]["family"],
        birth_date=demo["birthDate"],
        language=demo.get("preferredLanguage", "English"),
        conditions=[_parse_condition(c) for c in data.get("conditions", [])],
        allergies=[_parse_allergy(a) for a in data.get("allergies", [])],
        medications=[_parse_medication(m) for m in data.get("medications", [])],
        labs=[_parse_lab(l) for l in data.get("labs", [])],
        encounters=[_parse_encounter(e) for e in data.get("encounters", [])],
        messages=[_parse_message(m) for m in data.get("messages", [])],
        social_history=social.get("notes", ""),
    )


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
