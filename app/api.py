"""
FastAPI backend for the EHR inbox system.

Serves patient data from the JSON files in data/patients/.
Run with: uv run uvicorn app.api:app --reload
"""

import os
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests as http_client

from app.store import load_patient, load_patients, save_reply

app = FastAPI(title="Lakeview Family Medicine EHR", version="0.1.0")

AGENT_API_URL = os.environ.get("AGENT_API_URL", "http://localhost:8001")


# --- Request models ---


class ReplyRequest(BaseModel):
    body: str
    sender_name: str = "Dr. Sarah Kim, MD"


# --- Helpers ---


def get_patient_or_404(patient_id: str):
    """Load a single patient by ID, or raise 404."""
    try:
        return load_patient(patient_id)
    except (ValueError, FileNotFoundError):
        raise HTTPException(status_code=404, detail="Patient not found")


def _agent_request(method: str, path: str, *, fallback=None, json_body=None):
    """Make a request to the agent API. Returns fallback on failure, or raises 503."""
    try:
        kwargs = {"timeout": 5}
        if json_body is not None:
            kwargs["json"] = json_body
        resp = getattr(http_client, method)(f"{AGENT_API_URL}{path}", **kwargs)
        resp.raise_for_status()
        return resp.json()
    except http_client.RequestException:
        if fallback is not None:
            return fallback
        raise HTTPException(status_code=503, detail="Agent API unavailable")


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
    return patient.model_dump(by_alias=True)


@app.get("/patients/{patient_id}/messages")
def get_messages(patient_id: str):
    """Get all messages for a patient, newest first."""
    patient = get_patient_or_404(patient_id)
    messages = sorted(patient.messages, key=lambda m: m.date, reverse=True)
    return [m.model_dump(by_alias=True) for m in messages]


# --- Search endpoints (Lab 3) ---
# These let agent tools request specific slices of a patient record
# instead of fetching the entire thing.


def _contains(obj, keyword: str) -> bool:
    """Recursively check if keyword appears in any string value of a Pydantic model or dict."""
    if isinstance(obj, str):
        return keyword in obj.lower()
    if isinstance(obj, BaseModel):
        return any(_contains(getattr(obj, f), keyword) for f in obj.model_fields)
    if isinstance(obj, dict):
        return any(_contains(v, keyword) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return any(_contains(item, keyword) for item in obj)
    return False


@app.get("/patients/{patient_id}/demographics")
def get_demographics(patient_id: str):
    """Get just the demographics for a patient."""
    patient = get_patient_or_404(patient_id)
    return patient.demographics.model_dump(by_alias=True)


@app.get("/patients/{patient_id}/conditions")
def search_conditions(patient_id: str, q: str = ""):
    """Search conditions by keyword. Returns all if no query given."""
    patient = get_patient_or_404(patient_id)
    return [
        c.model_dump(by_alias=True) for c in patient.conditions
        if not q or _contains(c, q.lower())
    ]


@app.get("/patients/{patient_id}/medications")
def search_medications(patient_id: str, q: str = ""):
    """Search medications by keyword. Returns all if no query given."""
    patient = get_patient_or_404(patient_id)
    return [
        m.model_dump(by_alias=True) for m in patient.medications
        if not q or _contains(m, q.lower())
    ]


@app.get("/patients/{patient_id}/labs")
def search_labs(patient_id: str, test: str = ""):
    """Search lab results by test name. Returns matching results with dates."""
    patient = get_patient_or_404(patient_id)
    test_lower = test.lower()
    matches = []
    for lab in patient.labs:
        for panel in lab.panels:
            for result in panel.results:
                if not test or test_lower in result.test.lower():
                    matches.append({
                        "date": lab.date,
                        "panel": panel.name,
                        "test": result.test,
                        "value": result.value,
                        "unit": result.unit,
                        "interpretation": result.interpretation,
                    })
    return sorted(matches, key=lambda r: r["date"], reverse=True)


@app.get("/patients/{patient_id}/encounters")
def search_encounters(patient_id: str, q: str = ""):
    """Search encounters by keyword. Returns all if no query given."""
    patient = get_patient_or_404(patient_id)
    return [
        e.model_dump(by_alias=True) for e in patient.encounters
        if not q or _contains(e, q.lower())
    ]


# --- Agent proxy endpoints ---


@app.get("/patients/{patient_id}/concerns")
def get_concerns(patient_id: str):
    """Get the current concerns for a patient.

    Proxies to the agent API. Returns empty list if the agent API
    is unavailable — the UI degrades gracefully without the agent.
    """
    get_patient_or_404(patient_id)
    return _agent_request("get", f"/patients/{patient_id}/concerns", fallback=[])


@app.post("/patients/{patient_id}/run")
def trigger_agent(patient_id: str):
    """Trigger the agent for a single patient. Proxies to the agent API."""
    get_patient_or_404(patient_id)
    return _agent_request("post", f"/patients/{patient_id}/run")


@app.post("/patients/{patient_id}/concerns/{concern_id}/resolve")
def resolve_concern(patient_id: str, concern_id: str):
    """Mark a concern as resolved. Proxies to the agent API."""
    get_patient_or_404(patient_id)
    return _agent_request("post", f"/patients/{patient_id}/concerns/{concern_id}/resolve")


@app.get("/agent/status")
def agent_status():
    """Get the agent's current status. Proxies to the agent API."""
    return _agent_request("get", "/status",
                          fallback={"running": False, "last_run": "", "error": "Agent API unavailable"})


# --- Lab 4: role and sharing proxy endpoints ---


@app.get("/providers")
def list_providers():
    return _agent_request("get", "/providers", fallback=[])


@app.get("/role")
def get_role():
    return _agent_request("get", "/role", fallback={"provider_id": None})


@app.post("/role")
def set_role(provider_id: str):
    return _agent_request("post", f"/role?provider_id={provider_id}")


@app.get("/role/patients")
def get_role_patients():
    return _agent_request("get", "/role/patients", fallback={"provider_id": None, "patient_ids": []})


@app.post("/patients/{patient_id}/concerns/{concern_id}/share")
def share_concern(patient_id: str, concern_id: str, shared_with: str):
    return _agent_request("post", f"/patients/{patient_id}/concerns/{concern_id}/share", json_body={"shared_with": shared_with})


@app.get("/patients/{patient_id}/concerns/{concern_id}/shared-by")
def concern_shared_by(patient_id: str, concern_id: str):
    return _agent_request("get", f"/patients/{patient_id}/concerns/{concern_id}/shared-by", fallback={"shared_by": None})


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
