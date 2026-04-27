"""
Agent API — serves concerns from the agent's store.

This is the agent's side of the contract. The main API proxies
/patients/{id}/concerns here. Each lab can reimplement this API
however it wants, as long as it serves the same Concern schema.

Run with: uv run uvicorn lab4.agent.api:app --port 8001
"""

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from lab4.agent.models import Concern
from lab4.agent.store import (
    get_concerns,
    resolve_concern,
    share_concern,
    get_providers,
    get_provider_patients,
    get_shared_by,
    using_postgres,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    store = "Postgres (RLS enabled)" if using_postgres() else "JSON fallback (no RLS)"
    logger.info(
        "\n"
        "╔══════════════════════════════════════════════════════════╗\n"
        "║  Lab 4 Agent — Securing Agent Data                      ║\n"
        "║  Scoped tools, concern stability, provider isolation     ║\n"
        "║  Store: %-48s ║\n"
        "║  http://localhost:8001/docs                              ║\n"
        "╚══════════════════════════════════════════════════════════╝",
        store,
    )
    yield


app = FastAPI(title="Lab 4 Agent API", version="0.1.0", lifespan=lifespan)

_run_lock = threading.Lock()
_run_error: str | None = None

# Module-level state: active provider (same pattern as masking/grounding toggles)
_active_provider: str = "dr_kim"


class ShareRequest(BaseModel):
    shared_with: str


# ============================================================
# Provider management
# ============================================================


@app.get("/providers")
def list_providers():
    """Get all providers."""
    return get_providers()


@app.get("/role")
def get_role():
    """Get the currently active provider."""
    return {"provider_id": _active_provider}


@app.post("/role")
def set_role(provider_id: str):
    """Set the active provider. Validates the provider exists (Postgres only)."""
    global _active_provider
    if using_postgres():
        providers = get_providers()
        provider_ids = [p["id"] for p in providers]
        if provider_id not in provider_ids:
            raise HTTPException(status_code=404, detail="Provider not found")
    _active_provider = provider_id
    return {"provider_id": _active_provider}


@app.get("/role/patients")
def role_patients():
    """Get the patient IDs the active provider is authorized for."""
    return {
        "provider_id": _active_provider,
        "patient_ids": get_provider_patients(_active_provider),
    }


# ============================================================
# Concern endpoints
# ============================================================


@app.get("/patients/{patient_id}/concerns", response_model=list[Concern])
def patient_concerns(patient_id: str):
    """Get concerns for a patient from the agent store."""
    return get_concerns(patient_id, _active_provider)


@app.post("/patients/{patient_id}/concerns/{concern_id}/resolve")
def mark_resolved(patient_id: str, concern_id: str):
    """Mark a concern as resolved."""
    if not resolve_concern(patient_id, concern_id, _active_provider):
        raise HTTPException(status_code=404, detail="Concern not found")
    return {"status": "resolved"}


@app.post("/patients/{patient_id}/concerns/{concern_id}/share")
def share(patient_id: str, concern_id: str, body: ShareRequest):
    """Share a concern with another provider. Requires Postgres."""
    if not using_postgres():
        raise HTTPException(
            status_code=501,
            detail="Sharing requires Postgres (DATABASE_URL not set)",
        )
    share_concern(concern_id, body.shared_with, _active_provider)
    return {"status": "shared"}


@app.get("/patients/{patient_id}/concerns/{concern_id}/shared-by")
def shared_by(patient_id: str, concern_id: str):
    """If this concern was shared with the active provider, return who shared it."""
    return {"shared_by": get_shared_by(concern_id, _active_provider)}


# ============================================================
# Agent run
# ============================================================


@app.get("/status")
def agent_status():
    """Check when the agent last ran and whether it's currently running."""
    return {
        "provider_id": _active_provider,
        "running": _run_lock.locked(),
        "error": _run_error,
    }


@app.post("/patients/{patient_id}/run")
def trigger_run(patient_id: str):
    """Run the agent for a single patient in a background thread."""
    # Capture provider at trigger time (not at execution time)
    provider_id = _active_provider

    # Acquire non-blocking to avoid TOCTOU race — if two requests arrive
    # simultaneously, only the one that gets the lock proceeds.
    if not _run_lock.acquire(blocking=False):
        return {"status": "already_running"}

    def _background_run():
        global _run_error
        from lab4.agent.run import run_single

        try:
            _run_error = None
            run_single(patient_id, provider_id)
        except Exception as e:
            _run_error = str(e)
        finally:
            _run_lock.release()

    thread = threading.Thread(target=_background_run, daemon=True)
    thread.start()
    return {"status": "started", "patient_id": patient_id}


# ============================================================
# Masking toggle
# ============================================================
# Lets participants compare masked vs. unmasked traces without restarting.


@app.get("/masking")
def get_masking():
    """Check whether PII masking is currently enabled."""
    from lab4.agent.observability.masking import masking_enabled

    return {"enabled": masking_enabled}


@app.post("/masking/toggle")
def toggle_masking():
    """Toggle PII masking on/off. Takes effect on the next agent run."""
    import lab4.agent.observability.masking as m

    m.masking_enabled = not m.masking_enabled
    return {"enabled": m.masking_enabled}


# ============================================================
# Grounding mode toggle
# ============================================================
# Lets participants compare LLM-as-judge vs. Granite Guardian grounding.


@app.get("/grounding")
def get_grounding():
    """Check which grounding mode is active: 'llm' or 'guardian'."""
    from lab4.agent.grounding import grounding_mode

    return {"mode": grounding_mode}


@app.post("/grounding/toggle")
def toggle_grounding():
    """Toggle grounding mode between LLM-as-judge and Granite Guardian."""
    import lab4.agent.grounding as g

    g.grounding_mode = "llm" if g.grounding_mode == "guardian" else "guardian"
    return {"mode": g.grounding_mode}
