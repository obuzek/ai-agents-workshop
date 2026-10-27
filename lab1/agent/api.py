"""
Agent API — serves concerns from the agent's store.

This is the agent's side of the contract. The main API proxies
/patients/{id}/concerns here. Each lab can reimplement this API
however it wants, as long as it serves the same Concern schema.

Run with: uv run uvicorn lab1.agent.api:app --port 8001
"""

import logging
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import requests
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from lab1.agent.agent import check_orchestrate_config
from lab1.agent.models import Concern
from lab1.agent.store import get_concerns, load_store, resolve_concern

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@asynccontextmanager
async def lifespan(app):
    check_orchestrate_config()
    logger.info(
        "\n"
        "╔══════════════════════════════════════════════════════════╗\n"
        "║  Lab 1 Agent — The Naive Agent                           ║\n"
        "║  ReAct agent on watsonx Orchestrate; concerns as JSON    ║\n"
        "║  http://localhost:8001/docs                              ║\n"
        "╚══════════════════════════════════════════════════════════╝"
    )
    yield


app = FastAPI(title="Lab 1 Agent API", version="0.1.0", lifespan=lifespan)

_run_lock = threading.Lock()
_run_error: str | None = None
_running_patient: str | None = None
# The last run's outcome per patient, so the UI can say what happened to *this* patient.
_runs: dict[str, dict] = {}


def friendly_error(e: Exception) -> str:
    """Turn a failed run into one sentence a student can act on."""
    text = str(e)
    lowered = text.lower()
    status = getattr(getattr(e, "response", None), "status_code", None)
    if "iam.cloud.ibm.com" in text or (status in (400, 401) and "identity/token" in text):
        return ("IBM Cloud rejected your API key (it may have expired). Create a new key, then run: "
                "uv run python scripts/ibm_cloud_login.py")
    if "not found on orchestrate" in lowered:
        return "Your agent isn't deployed yet. Run: uv run python -m lab1.agent.deploy"
    if "configuring" in lowered:
        return "Your tools are still being set up on Orchestrate. Wait a minute and click Run Agent again."
    if isinstance(e, TimeoutError):
        return "The agent took longer than 5 minutes. Click Run Agent again; if it keeps happening, ask the instructor."
    if isinstance(e, ValidationError):
        return "The agent's answer didn't match the concern format, even after one retry. Click Run Agent again."
    if status == 429:
        return "The model is busy right now. Wait a few seconds and click Run Agent again."
    if status in (401, 403):
        return "Orchestrate refused your API key. Run: uv run python scripts/check_setup.py"
    if isinstance(e, requests.RequestException):
        return "Couldn't reach watsonx Orchestrate or the workshop EHR. Check your connection and click Run Agent again."
    return f"The agent run failed ({type(e).__name__}). Run: uv run python scripts/check_setup.py"


@app.get("/patients/{patient_id}/concerns", response_model=list[Concern])
def patient_concerns(patient_id: str):
    """Get concerns for a patient from the agent store."""
    return get_concerns(patient_id)


@app.get("/status")
def agent_status():
    """Check when the agent last ran and whether it's currently running."""
    store = load_store()
    total = sum(len(pc.concerns) for pc in store.patients.values())
    return {
        "last_run": store.last_run,
        "patient_count": len(store.patients),
        "total_concerns": total,
        "running": _run_lock.locked(),
        "running_patient": _running_patient,
        "error": _run_error,
        "patients": _runs,
    }


@app.post("/patients/{patient_id}/run")
def trigger_run(patient_id: str):
    """Run the agent for a single patient in a background thread."""
    # Take the lock here, not in the thread, so two quick clicks can't both start a run.
    if not _run_lock.acquire(blocking=False):
        return {"status": "already_running"}

    def _background_run():
        global _run_error, _running_patient
        from lab1.agent.run import run_single
        _run_error, _running_patient = None, patient_id
        try:
            run_single(patient_id)
            _runs[patient_id] = {"finished": _now(), "concerns": len(get_concerns(patient_id)), "error": None}
        except Exception as e:
            logger.exception("Agent run for %s failed", patient_id)
            _run_error = friendly_error(e)
            _runs[patient_id] = {"finished": _now(), "concerns": None, "error": _run_error}
        finally:
            _running_patient = None
            _run_lock.release()

    thread = threading.Thread(target=_background_run, daemon=True)
    thread.start()
    return {"status": "started", "patient_id": patient_id}


@app.post("/patients/{patient_id}/concerns/{concern_id}/resolve")
def mark_resolved(patient_id: str, concern_id: str):
    """Mark a concern as resolved."""
    if not resolve_concern(patient_id, concern_id):
        raise HTTPException(status_code=404, detail="Concern not found")
    return {"status": "resolved"}
