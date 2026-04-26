"""
Agent entrypoint — run the concern-extraction loop.

Processes all patients, writes concerns to the store, then polls for changes.
When a pass produces no new or changed concerns, the agent announces DONE.

Usage:
    python -m lab1.agent.run
"""

import time
from datetime import datetime, timezone

from lab1.agent.agent import process_patient
from lab1.agent.store import load_store, save_store
from lab1.agent.tools import list_patients
from lab1.agent.models import ConcernsStore

POLL_INTERVAL = 30  # seconds between passes


def run_single(patient_id: str):
    """Run the agent for a single patient and save to the store."""
    print(f"\n--- Processing {patient_id} ---")
    result = process_patient(patient_id)

    store = load_store()
    store.patients[patient_id] = result
    store.last_run = datetime.now(timezone.utc).isoformat()
    save_store(store)

    n = len(result.concerns)
    print(f"  -> {n} concern{'s' if n != 1 else ''} identified (saved)")


def run_pass() -> ConcernsStore:
    """Run the agent once for every patient. Saves incrementally after each patient."""
    patients = list_patients()
    store = load_store()

    for p in patients:
        patient_id = p["id"]
        print(f"\n--- Processing {p['name']} ({patient_id}) ---")

        result = process_patient(patient_id)
        store.patients[patient_id] = result
        store.last_run = datetime.now(timezone.utc).isoformat()
        save_store(store)

        n = len(result.concerns)
        print(f"  -> {n} concern{'s' if n != 1 else ''} identified (saved)")

    return store


def stores_match(a: ConcernsStore, b: ConcernsStore) -> bool:
    """Check if two stores have the same concerns (ignoring timestamps)."""
    if set(a.patients.keys()) != set(b.patients.keys()):
        return False
    for pid in a.patients:
        a_titles = sorted(c.title for c in a.patients[pid].concerns)
        b_titles = sorted(c.title for c in b.patients[pid].concerns)
        if a_titles != b_titles:
            return False
    return True


def main():
    print("=== Lab 1: Naive Agent ===")
    print("Starting concern extraction loop...\n")

    previous = load_store()

    while True:
        new_store = run_pass()
        save_store(new_store)

        total = sum(len(pc.concerns) for pc in new_store.patients.values())
        print(f"\n--- Pass complete: {total} total concerns across {len(new_store.patients)} patients ---")

        if stores_match(previous, new_store):
            print("\nDONE — no new concerns found. Agent is up to date.")
            break

        previous = new_store
        print(f"\nConcerns changed. Polling again in {POLL_INTERVAL}s...")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
