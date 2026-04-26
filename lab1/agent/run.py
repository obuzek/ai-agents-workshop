"""
Agent entrypoint — run the concern-extraction loop.

Processes all patients, writes concerns to the store, then polls for changes.
When a pass produces no new or changed concerns, the agent announces DONE.

Usage:
    uv run python -m lab1.agent.run
"""

import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

from lab1.agent.agent import process_patient
from lab1.agent.store import load_store, save_store
from lab1.agent.tools import list_patients
from lab1.agent.models import ConcernsStore

POLL_INTERVAL = 30  # seconds between passes


def run_single(patient_id: str):
    """Run the agent for a single patient and save to the store."""
    logger.info("Processing %s", patient_id)
    result = process_patient(patient_id)

    store = load_store()
    store.patients[patient_id] = result
    store.last_run = datetime.now(timezone.utc).isoformat()
    save_store(store)

    n = len(result.concerns)
    logger.info("  -> %d concern%s identified (saved)", n, "s" if n != 1 else "")


def run_pass() -> ConcernsStore:
    """Run the agent once for every patient. Saves incrementally after each patient."""
    patients = list_patients()
    store = load_store()

    for p in patients:
        patient_id = p["id"]
        logger.info("Processing %s (%s)", p["name"], patient_id)

        result = process_patient(patient_id)
        store.patients[patient_id] = result
        store.last_run = datetime.now(timezone.utc).isoformat()
        save_store(store)

        n = len(result.concerns)
        logger.info("  -> %d concern%s identified (saved)", n, "s" if n != 1 else "")

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
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logger.info("=== Lab 1: Naive Agent ===")
    logger.info("Starting concern extraction loop...")

    previous = load_store()

    while True:
        new_store = run_pass()
        save_store(new_store)

        total = sum(len(pc.concerns) for pc in new_store.patients.values())
        logger.info("Pass complete: %d total concerns across %d patients", total, len(new_store.patients))

        if stores_match(previous, new_store):
            logger.info("DONE — no new concerns found. Agent is up to date.")
            break

        previous = new_store
        logger.info("Concerns changed. Polling again in %ds...", POLL_INTERVAL)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
