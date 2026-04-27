"""
Shared models — the contract between the main API and the agent API.

Any service that serves or consumes concerns must use these models.
The main API proxies to the agent API; both sides agree on this schema.
"""

from pydantic import BaseModel

from app.models import (
    Concern, ConcernType, ConcernStatus, Urgency, RelatedData, _pii,
)


class PatientConcerns(BaseModel):
    """All concerns for one patient."""
    patient_id: str
    patient_name: str = _pii()
    concerns: list[Concern] = []


class ConcernsStore(BaseModel):
    """The full agent output — all patients' concerns. Written as a flat JSON file."""
    patients: dict[str, PatientConcerns] = {}
    last_run: str = ""
