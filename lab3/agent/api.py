"""
Agent API — serves concerns from the agent's store.

This is the agent's side of the contract. The main API proxies
/patients/{id}/concerns here. Each lab can reimplement this API
however it wants, as long as it serves the same Concern schema.

Run with: uv run uvicorn lab3.agent.api:app --port 8001
"""

import threading
from fastapi import FastAPI, HTTPException

from lab3.agent.models import Concern
from lab3.agent.store import get_concerns, load_store, resolve_concern

app = FastAPI(title="Lab 3 Agent API", version="0.1.0")

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
    # Acquire non-blocking to avoid TOCTOU race — if two requests arrive
    # simultaneously, only the one that gets the lock proceeds.
    if not _run_lock.acquire(blocking=False):
        return {"status": "already_running"}

    def _background_run():
        global _run_error
        from lab3.agent.run import run_single
        try:
            _run_error = None
            run_single(patient_id)
        except Exception as e:
            _run_error = str(e)
        finally:
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


# --- Masking toggle ---
# Lets participants compare masked vs. unmasked traces without restarting.

@app.get("/masking")
def get_masking():
    """Check whether PII masking is currently enabled."""
    from lab3.agent.observability.masking import masking_enabled
    return {"enabled": masking_enabled}


@app.post("/masking/toggle")
def toggle_masking():
    """Toggle PII masking on/off. Takes effect on the next agent run."""
    import lab3.agent.observability.masking as m
    m.masking_enabled = not m.masking_enabled
    return {"enabled": m.masking_enabled}


# --- Grounding mode toggle ---
# Lets participants compare LLM-as-judge vs. Granite Guardian grounding.

@app.get("/grounding")
def get_grounding():
    """Check which grounding mode is active: 'llm' or 'guardian'."""
    from lab3.agent.grounding import grounding_mode
    return {"mode": grounding_mode}


@app.post("/grounding/toggle")
def toggle_grounding():
    """Toggle grounding mode between LLM-as-judge and Granite Guardian."""
    import lab3.agent.grounding as g
    g.grounding_mode = "llm" if g.grounding_mode == "guardian" else "guardian"
    return {"mode": g.grounding_mode}
