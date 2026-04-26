"""
FastAPI backend for the EHR inbox system.

Serves patient data from the JSON files in data/patients/.
Run with: uvicorn app.api:app --reload
"""

from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.store import load_patients, save_reply

app = FastAPI(title="Lakeview Family Medicine EHR", version="0.1.0")


# --- Request models ---


class ReplyRequest(BaseModel):
    body: str
    sender_name: str = "Dr. Sarah Kim, MD"


# --- Helpers ---


def get_patient_or_404(patient_id: str):
    """Load a single patient by ID, or raise 404."""
    patients = load_patients()
    if patient_id not in patients:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patients[patient_id]


# --- Endpoints ---


@app.get("/patients")
def list_patients():
    """List all patients with basic demographic and condition info."""
    patients = load_patients()
    return [
        {
            "id": p.id,
            "name": p.name,
            "birthDate": p.birth_date,
            "conditions": [c.display for c in p.active_conditions],
        }
        for p in patients.values()
    ]


@app.get("/patients/{patient_id}")
def get_patient(patient_id: str):
    """Get a full patient record as a structured object."""
    patient = get_patient_or_404(patient_id)
    return _serialize_patient(patient)


@app.get("/patients/{patient_id}/messages")
def get_messages(patient_id: str):
    """Get all messages for a patient, newest first."""
    patient = get_patient_or_404(patient_id)
    messages = sorted(patient.messages, key=lambda m: m.date, reverse=True)
    return [_serialize_message(m) for m in messages]


@app.get("/patients/{patient_id}/concerns")
def get_concerns(patient_id: str):
    """Get the current concerns for a patient.
    Returns empty list until the agent populates it."""
    # TODO: this will be populated by the agent in later steps
    return []


@app.get("/inbox")
def get_inbox():
    """Get all messages needing a provider response, newest first."""
    patients = load_patients()
    backlog = []
    for patient in patients.values():
        for msg in patient.messages:
            if msg.needs_response():
                backlog.append({
                    "patient_id": patient.id,
                    "patient_name": patient.name,
                    "message_id": msg.id,
                    "date": msg.date,
                    "category": msg.category,
                    "subject": msg.subject,
                    "body": msg.body,
                })
    return sorted(backlog, key=lambda m: m["date"], reverse=True)


@app.post("/patients/{patient_id}/messages/{message_id}/reply")
def reply_to_message(patient_id: str, message_id: str, reply: ReplyRequest):
    """Add a provider reply to a patient message."""
    patient = get_patient_or_404(patient_id)

    # Verify the message exists
    if not any(m.id == message_id for m in patient.messages):
        raise HTTPException(status_code=404, detail="Message not found")

    save_reply(
        patient_id=patient_id,
        message_id=message_id,
        sender_name=reply.sender_name,
        body=reply.body,
        date=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    return {"status": "ok"}


# --- Serialization helpers ---
# These convert model objects to dicts for the JSON API responses.


def _serialize_patient(patient):
    """Serialize a Patient to a dict matching the API contract."""
    return {
        "id": patient.id,
        "name": patient.name,
        "demographics": {
            "name": {"given": patient.given_name, "family": patient.family_name},
            "birthDate": patient.birth_date,
            "preferredLanguage": patient.language,
        },
        "conditions": [
            {"display": c.display, "status": c.status, "notes": c.notes}
            for c in patient.conditions
        ],
        "allergies": [
            {"substance": a.substance, "reaction": a.reaction}
            for a in patient.allergies
        ],
        "medications": [
            {"display": m.display, "dosage": m.dosage, "frequency": m.frequency,
             "prescriber": m.prescriber, "status": m.status}
            for m in patient.medications
        ],
        "labs": [
            {
                "date": lab.date,
                "orderedBy": lab.ordered_by,
                "panels": [
                    {
                        "name": panel.name,
                        "results": [
                            {"test": r.test, "value": r.value, "unit": r.unit,
                             "interpretation": r.interpretation}
                            for r in panel.results
                        ],
                    }
                    for panel in lab.panels
                ],
            }
            for lab in patient.labs
        ],
        "encounters": [
            {
                "date": enc.date,
                "reasonForVisit": enc.reason,
                "notes": {
                    "subjective": enc.notes.subjective,
                    "objective": enc.notes.objective,
                    "assessment": enc.notes.assessment,
                    "plan": enc.notes.plan,
                },
            }
            for enc in patient.encounters
        ],
        "messages": [_serialize_message(m) for m in patient.messages],
        "socialHistory": patient.social_history,
    }


def _serialize_message(msg):
    """Serialize a Message to a dict."""
    return {
        "id": msg.id,
        "date": msg.date,
        "sender": {"name": msg.sender.name, "role": msg.sender.role},
        "category": msg.category,
        "subject": msg.subject,
        "body": msg.body,
        "thread": [
            {
                "date": t.date,
                "sender": {"name": t.sender.name, "role": t.sender.role},
                "body": t.body,
            }
            for t in msg.thread
        ],
    }
