"""
Data store: loads and saves patient records.

This is the only module that knows where patient data lives. Everything else
works with the Pydantic models in models.py. It runs in one of three modes:

  local   (default) — read and write the JSON files in data/patients/.
  server  (EHR_MODE=server) — the shared workshop EHR. Each tenant gets a
          private in-memory copy of the synthetic patients, created on first
          use. The tenant comes from the X-Tenant request header (see api.py).
  remote  (EHR_API_URL and EHR_TENANT set) — a student's local EHR API that
          forwards patient data to the shared workshop EHR, so the local UI and
          the agent's cloud tools see the same records.

Tenancy here only keeps attendees' data apart; it isn't access control.
"""

import copy
import json
import os
import re
import threading
import time
from contextvars import ContextVar
from pathlib import Path

import requests
from dotenv import load_dotenv

from app.models import Patient

# The UI starts this API in-process without loading .env, so load it here:
# remote mode is switched on by EHR_API_URL / EHR_TENANT in the student's .env.
load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data" / "patients"

EHR_MODE = os.environ.get("EHR_MODE", "local")
REMOTE_URL = os.environ.get("EHR_API_URL", "").rstrip("/") if EHR_MODE != "server" else ""
REMOTE_TENANT = os.environ.get("EHR_TENANT", "") if EHR_MODE != "server" else ""
if REMOTE_URL and REMOTE_TENANT:
    EHR_MODE = "remote"

TENANT_HEADER = "X-Tenant"
MAX_TENANTS = 200  # a workshop has ~35 seats; this just bounds memory

# Set per request by api.py in server mode.
current_tenant: ContextVar[str | None] = ContextVar("current_tenant", default=None)


# --- JSON -> Model parsing ---


def _parse_patient(data: dict) -> Patient:
    """Parse a raw JSON dict into a Patient model.

    Pydantic handles nested model construction, alias resolution, and
    validation automatically via model_validate().
    """
    return Patient.model_validate(data)


# --- Patient IDs ---


PATIENT_ID_RE = re.compile(r"^patient-\d{3}$")


def _validate_patient_id(patient_id: str):
    """Validate that a patient ID matches the expected format."""
    if not PATIENT_ID_RE.match(patient_id):
        raise ValueError(f"Invalid patient ID: {patient_id}")


def _patient_filepath(patient_id: str) -> Path:
    """Return the JSON file path for a patient ID."""
    _validate_patient_id(patient_id)
    return DATA_DIR / (patient_id.replace("-", "_") + ".json")


def _append_reply(data: dict, message_id: str, sender_name: str, body: str, date: str):
    """Append a provider reply to a message thread in a raw patient dict."""
    for msg in data.get("messages", []):
        if msg["id"] == message_id:
            msg.setdefault("thread", []).append({
                "date": date,
                "sender": {"name": sender_name, "role": "provider"},
                "body": body,
            })
            break


# --- server mode: per-tenant in-memory copies ---


_tenant_data: dict[str, dict[str, dict]] = {}
_tenant_lock = threading.RLock()  # re-entrant: save_reply holds it while fetching records
_pristine: dict[str, dict] | None = None


class TooManyTenants(RuntimeError):
    pass


def _tenant_records() -> dict[str, dict]:
    """Raw patient dicts for the current request's tenant, creating them on first use."""
    global _pristine
    tenant = current_tenant.get()
    if not tenant:
        raise RuntimeError("No tenant set for this request")
    with _tenant_lock:
        if tenant not in _tenant_data:
            if len(_tenant_data) >= MAX_TENANTS:
                raise TooManyTenants(f"Tenant limit ({MAX_TENANTS}) reached")
            if _pristine is None:
                _pristine = {}
                for filepath in sorted(DATA_DIR.glob("*.json")):
                    data = json.loads(filepath.read_text())
                    _pristine[data["id"]] = data
            _tenant_data[tenant] = copy.deepcopy(_pristine)
        return _tenant_data[tenant]


# --- remote mode: forward to the shared EHR ---


# One UI redraw asks the local API for the patient list several times, and each
# answer is a ~500 KB download of every record. Reuse it briefly; a reply clears it.
REMOTE_CACHE_SECONDS = 5
_remote_records: tuple[float, list[dict]] | None = None


def _remote(method: str, path: str, **kwargs):
    resp = requests.request(method, f"{REMOTE_URL}{path}", headers={TENANT_HEADER: REMOTE_TENANT},
                            timeout=30, **kwargs)
    if resp.status_code == 404:
        raise FileNotFoundError(path)
    resp.raise_for_status()
    return resp.json()


# --- Public API ---


def load_raw_patients() -> list[dict]:
    """All patient records as raw dicts (what GET /records returns)."""
    if EHR_MODE == "server":
        return list(_tenant_records().values())
    if EHR_MODE == "remote":
        global _remote_records
        if _remote_records is None or time.monotonic() - _remote_records[0] > REMOTE_CACHE_SECONDS:
            _remote_records = (time.monotonic(), _remote("GET", "/records"))
        return _remote_records[1]
    return [json.loads(p.read_text()) for p in sorted(DATA_DIR.glob("*.json"))]


def load_patients() -> dict[str, Patient]:
    """Load all patient records, keyed by patient ID."""
    patients = [_parse_patient(data) for data in load_raw_patients()]
    return {p.id: p for p in sorted(patients, key=lambda p: p.id)}


def load_patient(patient_id: str) -> Patient:
    """Load a single patient record by ID."""
    _validate_patient_id(patient_id)
    if EHR_MODE == "server":
        records = _tenant_records()
        if patient_id not in records:
            raise FileNotFoundError(patient_id)
        return _parse_patient(records[patient_id])
    if EHR_MODE == "remote":
        # Served from the briefly cached full records (one cloud call per redraw, not one per read).
        for data in load_raw_patients():
            if data["id"] == patient_id:
                return _parse_patient(data)
        raise FileNotFoundError(patient_id)
    with open(_patient_filepath(patient_id)) as f:
        return _parse_patient(json.load(f))


def save_reply(patient_id: str, message_id: str, sender_name: str, body: str, date: str):
    """Append a provider reply to a message."""
    _validate_patient_id(patient_id)
    if EHR_MODE == "server":
        with _tenant_lock:
            _append_reply(_tenant_records()[patient_id], message_id, sender_name, body, date)
        return
    if EHR_MODE == "remote":
        global _remote_records
        _remote("POST", f"/patients/{patient_id}/messages/{message_id}/reply",
                json={"sender_name": sender_name, "body": body})
        _remote_records = None
        return

    # Local: write straight to the JSON file to preserve its full structure.
    filepath = _patient_filepath(patient_id)
    with open(filepath) as f:
        data = json.load(f)
    _append_reply(data, message_id, sender_name, body, date)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
