"""
Agent entrypoint — run the concern-extraction loop.

Processes all patients, writes concerns to the store via upsert.
Each run loads existing concerns for stability, then saves the new
output back.

Usage:
    uv run python -m lab4.agent.run
"""

import logging

import requests

from lab4.agent import API_URL
from lab4.agent.agent import process_patient
from lab4.agent.store import get_concerns, save_concerns

logger = logging.getLogger(__name__)


def run_single(patient_id: str, provider_id: str = "dr_kim"):
    """Run the agent for a single patient, preserving existing concerns."""
    logger.info("Processing %s", patient_id)

    existing = get_concerns(patient_id, provider_id)
    result = process_patient(patient_id, existing_concerns=existing)

    save_concerns(patient_id, provider_id, result.concerns)

    n = len(result.concerns)
    logger.info("  -> %d concern%s identified (saved)", n, "s" if n != 1 else "")


def run_pass(provider_id: str = "dr_kim"):
    """Run the agent once for every patient."""
    resp = requests.get(f"{API_URL}/patients")
    resp.raise_for_status()
    patients = resp.json()

    for p in patients:
        run_single(p["id"], provider_id)


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logger.info("=== Lab 4: Securing Agent Data ===")
    logger.info("Starting concern extraction...")

    run_pass()
    logger.info("DONE — all patients processed.")


if __name__ == "__main__":
    main()
