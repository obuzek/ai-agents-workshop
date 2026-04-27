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
from fastapi import FastAPI, HTTPException

from app.llm import check_llm_config
from lab1.agent.models import Concern
from lab1.agent.store import get_concerns, load_store, resolve_concern

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    check_llm_config()
    logger.info(
        "\n"
        "╔══════════════════════════════════════════════════════════╗\n"
        "║  Lab 1 Agent — The Naive Agent                          ║\n"
        "║  Runs the ReAct agent and stores concerns as JSON        ║\n"
        "║  http://localhost:8001/docs                              ║\n"
        "╚══════════════════════════════════════════════════════════╝"
    )
    yield


app = FastAPI(title="Lab 1 Agent API", version="0.1.0", lifespan=lifespan)

_run_lock = threading.Lock()
_run_error: str | None = None


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
        "error": _run_error,
    }


@app.post("/patients/{patient_id}/run")
def trigger_run(patient_id: str):
    """Run the agent for a single patient in a background thread."""
    if _run_lock.locked():
        return {"status": "already_running"}

    def _background_run():
        global _run_error
        from lab1.agent.run import run_single
        with _run_lock:
            _run_error = None
            try:
                run_single(patient_id)
            except Exception as e:
                _run_error = str(e)

    thread = threading.Thread(target=_background_run, daemon=True)
    thread.start()
    return {"status": "started", "patient_id": patient_id}


@app.post("/patients/{patient_id}/concerns/{concern_id}/resolve")
def mark_resolved(patient_id: str, concern_id: str):
    """Mark a concern as resolved."""
    if not resolve_concern(patient_id, concern_id):
        raise HTTPException(status_code=404, detail="Concern not found")
    return {"status": "resolved"}
