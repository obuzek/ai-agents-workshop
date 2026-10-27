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
import logging
import os
import re
import threading
import time
from contextvars import ContextVar
from pathlib import Path

import requests
from dotenv import load_dotenv

from app.models import Patient

logger = logging.getLogger(__name__)

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


# --- server mode: per-tenant copies, kept in memory and saved to Object Storage ---
#
# Each tenant's records live in memory for speed. If COS_BUCKET is set, every write
# also saves the tenant's records to IBM Cloud Object Storage at
# tenants/<tenant>/records.json, and the first request after a restart loads them
# back, so a restart of the shared EHR doesn't wipe anyone's work.


_tenant_data: dict[str, dict[str, dict]] = {}
_tenant_lock = threading.RLock()  # re-entrant: save_reply holds it while fetching records
_pristine: dict[str, dict] | None = None


class TooManyTenants(RuntimeError):
    pass


class StorageUnavailable(RuntimeError):
    """Saved records exist (or might) but couldn't be read; never fall back to fresh data then."""


class _ObjectStorage:
    """Minimal IBM Cloud Object Storage client: GET/PUT JSON objects with an IAM API key."""

    def __init__(self, bucket: str, endpoint: str, api_key: str):
        self.bucket, self.endpoint, self.api_key = bucket, endpoint.rstrip("/"), api_key
        self._token, self._expires = "", 0.0
        self._token_lock = threading.Lock()

    def _headers(self) -> dict:
        with self._token_lock:
            if time.time() > self._expires - 300:
                resp = requests.post("https://iam.cloud.ibm.com/identity/token", timeout=30, data={
                    "grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": self.api_key})
                resp.raise_for_status()
                self._token, self._expires = resp.json()["access_token"], resp.json()["expiration"]
            return {"Authorization": f"Bearer {self._token}"}

    def _url(self, key: str) -> str:
        return f"{self.endpoint}/{self.bucket}/{key}"

    def get(self, key: str) -> dict | None:
        """The stored JSON, or None if there's no such object yet."""
        resp = requests.get(self._url(key), headers=self._headers(), timeout=30)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def put(self, key: str, data: dict):
        resp = requests.put(self._url(key), headers={**self._headers(), "Content-Type": "application/json"},
                            data=json.dumps(data), timeout=30)
        resp.raise_for_status()


_storage = (
    _ObjectStorage(os.environ["COS_BUCKET"],
                   os.environ.get("COS_ENDPOINT", "https://s3.us-south.cloud-object-storage.appdomain.cloud"),
                   os.environ.get("COS_APIKEY", ""))
    if EHR_MODE == "server" and os.environ.get("COS_BUCKET") else None
)


def _storage_key(tenant: str) -> str:
    return f"tenants/{tenant}/records.json"


def _pristine_records() -> dict[str, dict]:
    global _pristine
    if _pristine is None:
        _pristine = {}
        for filepath in sorted(DATA_DIR.glob("*.json")):
            data = json.loads(filepath.read_text())
            _pristine[data["id"]] = data
    return _pristine


def _tenant_records() -> dict[str, dict]:
    """Raw patient dicts for the current request's tenant, loading or creating them on first use."""
    tenant = current_tenant.get()
    if not tenant:
        raise RuntimeError("No tenant set for this request")
    with _tenant_lock:
        if tenant in _tenant_data:
            return _tenant_data[tenant]
        if len(_tenant_data) >= MAX_TENANTS:
            raise TooManyTenants(f"Tenant limit ({MAX_TENANTS}) reached")

    # Load outside the lock so one slow storage call doesn't hold up other tenants.
    saved = None
    if _storage is not None:
        try:
            saved = _storage.get(_storage_key(tenant))
        except Exception as e:
            logger.error("Couldn't load saved records for tenant %s: %s", tenant, e)
            raise StorageUnavailable("Saved records are temporarily unavailable; try again shortly") from e

    with _tenant_lock:
        # Another request for the same tenant may have loaded it meanwhile; keep the first copy.
        return _tenant_data.setdefault(tenant, saved if saved is not None else copy.deepcopy(_pristine_records()))


def _save_tenant(tenant: str):
    """Persist a tenant's records. A failed save is logged; the data stays in memory."""
    if _storage is None:
        return
    with _tenant_lock:
        snapshot = copy.deepcopy(_tenant_data[tenant])
    try:
        _storage.put(_storage_key(tenant), snapshot)
    except Exception as e:
        logger.error("Couldn't save records for tenant %s (kept in memory): %s", tenant, e)


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
        records = _tenant_records()
        with _tenant_lock:
            _append_reply(records[patient_id], message_id, sender_name, body, date)
        _save_tenant(current_tenant.get())
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
