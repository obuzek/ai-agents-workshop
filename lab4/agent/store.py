"""
Naive agent store — a flat JSON file.

This is intentionally unsophisticated: one file, no history, no audit trail.
The agent overwrites it on every run. Later labs will improve this.
"""

import json
import os
from pathlib import Path

from lab4.agent.models import Concern, ConcernsStore, PatientConcerns

STORE_PATH = Path(os.environ.get("AGENT_STORE", "data/agent_output.json"))


def load_store() -> ConcernsStore:
    """Load the current store from disk. Returns empty store if file doesn't exist."""
    if not STORE_PATH.exists():
        return ConcernsStore()
    with open(STORE_PATH) as f:
        return ConcernsStore.model_validate(json.load(f))


def save_store(store: ConcernsStore):
    """Write the store to disk, overwriting any previous version."""
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w") as f:
        json.dump(store.model_dump(), f, indent=2)


def get_concerns(patient_id: str) -> list[Concern]:
    """Get concerns for a single patient."""
    store = load_store()
    patient_concerns = store.patients.get(patient_id)
    if patient_concerns is None:
        return []
    return patient_concerns.concerns


def resolve_concern(patient_id: str, concern_id: str) -> bool:
    """Mark a concern as resolved. Returns True if found and updated."""
    store = load_store()
    patient_concerns = store.patients.get(patient_id)
    if patient_concerns is None:
        return False
    for c in patient_concerns.concerns:
        if c.id == concern_id:
            c.status = "resolved"
            save_store(store)
            return True
    return False
