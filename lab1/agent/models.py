"""
Shared models — the contract between the main API and the agent API.

Any service that serves or consumes concerns must use these models.
The main API proxies to the agent API; both sides agree on this schema.
"""

from pydantic import BaseModel


# --- The contract: what a "concern" looks like to the UI ---


class RelatedData(BaseModel):
    """Pointers back into the patient record that support a concern."""
    message_ids: list[str] = []
    lab_dates: list[str] = []
    conditions: list[str] = []
    encounter_dates: list[str] = []


class Concern(BaseModel):
    """A single concern identified by the agent."""
    id: str
    patient_id: str
    title: str
    summary: str            # one sentence: what's going on and why it matters
    action: str = ""        # what the doctor should do: "Reply to message", "Review labs", etc.
    concern_type: str       # medication, lab_result, symptom, follow_up, administrative
    urgency: str            # routine, soon, urgent
    status: str             # unresolved, monitoring, resolved
    onset: str              # when the concern was first identified or reported
    last_updated: str       # ISO timestamp of last agent update
    evidence: list[str]     # key data points supporting this concern
    related: RelatedData = RelatedData()


class PatientConcerns(BaseModel):
    """All concerns for one patient."""
    patient_id: str
    patient_name: str
    concerns: list[Concern] = []


class ConcernsStore(BaseModel):
    """The full agent output — all patients' concerns. Written as a flat JSON file."""
    patients: dict[str, PatientConcerns] = {}
    last_run: str = ""
