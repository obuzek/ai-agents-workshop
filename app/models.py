"""
Data models for the EHR system.

These Pydantic models define the internal representation of patient records
and serve as the FastAPI response schema. The JSON files in data/patients/
are the source of truth for the schema — these models match that structure.

Fields containing PII/PHI are annotated:
  - sensitivity="pii" — personally identifiable information (names, contact info)
  - sensitivity="phi" — protected health information (clinical data identifiers)

The observability masking layer reads these annotations to redact sensitive
data before it reaches the trace store.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class _AliasModel(BaseModel):
    """Base for models that use camelCase aliases but accept snake_case too."""
    model_config = {"populate_by_name": True}


# --- Helpers ---

def _pii(**kwargs):
    """Field containing personally identifiable information (names, contact info, addresses)."""
    return Field(json_schema_extra={"sensitivity": "pii"}, **kwargs)


def _phi(**kwargs):
    """Field containing protected health information (clinical data tied to a patient)."""
    return Field(json_schema_extra={"sensitivity": "phi"}, **kwargs)


# --- Coding (shared by conditions, medications, labs) ---


class Coding(BaseModel):
    system: str = ""
    code: str = ""
    display: str = ""


# --- Message models ---


class Sender(BaseModel):
    name: str = _pii()
    role: str  # "patient" or "provider"


class ThreadEntry(BaseModel):
    date: str
    sender: Sender
    body: str


class Message(BaseModel):
    id: str
    date: str
    sender: Sender
    recipient: Sender | None = None
    category: str = ""
    priority: str = ""
    subject: str = ""
    body: str = ""
    thread: list[ThreadEntry] = []

    def needs_response(self) -> bool:
        """True if the most recent message in this thread is from the patient."""
        if not self.thread:
            return True
        return self.thread[-1].sender.role != "provider"


# --- Clinical models ---


class Condition(_AliasModel):
    code: Coding = Coding()
    status: str = ""
    onset_date: str = Field(default="", alias="onsetDate")
    notes: str = ""

    @property
    def display(self) -> str:
        return self.code.display


class Allergy(BaseModel):
    substance: str = ""
    category: str = ""
    reaction: str = ""
    criticality: str = ""
    status: str = ""


class Medication(_AliasModel):
    code: Coding = Coding()
    dosage: str = ""
    frequency: str = ""
    route: str = ""
    status: str = ""
    prescribed_date: str = Field(default="", alias="prescribedDate")
    prescriber: str = ""

    @property
    def display(self) -> str:
        return self.code.display


class LabResult(_AliasModel):
    test: str = ""
    code: Coding | None = None
    value: str | int | float = ""
    unit: str = ""
    reference_range: dict[str, Any] | None = Field(default=None, alias="referenceRange")
    interpretation: str = ""


class LabPanel(BaseModel):
    name: str = ""
    code: Coding | None = None
    results: list[LabResult] = []


class Lab(_AliasModel):
    id: str = ""
    date: str = ""
    status: str = ""
    ordered_by: str = Field(default="", alias="orderedBy")
    panels: list[LabPanel] = []


class Immunization(_AliasModel):
    code: Coding = Coding()
    date: str = ""
    site: str = ""
    lot_number: str = Field(default="", alias="lotNumber")
    provider: str = ""


class SOAPNotes(BaseModel):
    subjective: str = ""
    objective: str = ""
    assessment: str = ""
    plan: str = ""


class Vitals(BaseModel):
    """Flexible vitals container — stores whatever the JSON provides."""
    model_config = {"extra": "allow"}


class Encounter(_AliasModel):
    id: str = ""
    date: str = ""
    type: str = ""
    provider: str = ""
    reason_for_visit: str = Field(default="", alias="reasonForVisit")
    vitals: Vitals | None = None
    notes: SOAPNotes = SOAPNotes()
    lab_orders: list[str] = Field(default=[], alias="labOrders")

    @property
    def reason(self) -> str:
        return self.reason_for_visit


# --- Demographics & Address ---


class Name(BaseModel):
    given: str = _pii()
    family: str = _pii()


class Address(_AliasModel):
    line: str = _pii(default="")
    city: str = _pii(default="")
    state: str = _pii(default="")
    postal_code: str = _pii(default="", alias="postalCode")


class EmergencyContact(BaseModel):
    name: str = _pii()
    relationship: str = ""
    phone: str = _pii(default="")


class Insurance(_AliasModel):
    type: str = ""
    plan_name: str = Field(default="", alias="planName")
    member_id: str = _phi(default="", alias="memberId")


class Demographics(_AliasModel):
    name: Name
    birth_date: str = _phi(default="", alias="birthDate")
    gender: str = ""
    phone: str = _pii(default="")
    email: str = _pii(default="")
    address: Address = Address()
    emergency_contact: EmergencyContact = Field(
        default=EmergencyContact(name="", phone=""), alias="emergencyContact"
    )
    insurance: Insurance = Insurance()
    preferred_language: str = Field(default="English", alias="preferredLanguage")


class SocialHistory(BaseModel):
    smoking: str = ""
    alcohol: str = ""
    exercise: str = ""
    notes: str = ""


class FamilyHistoryEntry(BaseModel):
    relationship: str = ""
    condition: str = ""
    deceased: bool | None = None


# --- Patient (top-level) ---


class Patient(_AliasModel):
    resource_type: str = Field(default="Patient", alias="resourceType")
    id: str
    demographics: Demographics = Demographics(name=Name(given="", family=""))
    social_history: SocialHistory = Field(default=SocialHistory(), alias="socialHistory")
    family_history: list[FamilyHistoryEntry] = Field(default=[], alias="familyHistory")
    conditions: list[Condition] = []
    allergies: list[Allergy] = []
    medications: list[Medication] = []
    labs: list[Lab] = []
    immunizations: list[Immunization] = []
    encounters: list[Encounter] = []
    messages: list[Message] = []

    @property
    def name(self) -> str:
        return f"{self.demographics.name.given} {self.demographics.name.family}"

    @property
    def given_name(self) -> str:
        return self.demographics.name.given

    @property
    def family_name(self) -> str:
        return self.demographics.name.family

    @property
    def birth_date(self) -> str:
        return self.demographics.birth_date

    @property
    def language(self) -> str:
        return self.demographics.preferred_language

    @property
    def active_conditions(self) -> list[Condition]:
        return [c for c in self.conditions if c.status == "active"]

    @property
    def active_medications(self) -> list[Medication]:
        return [m for m in self.medications if m.status == "active"]


# --- Concern models (shared contract between main API and agent API) ---

ConcernType = Literal["medication", "lab_result", "symptom", "follow_up", "administrative"]
Urgency = Literal["routine", "soon", "urgent"]
ConcernStatus = Literal["unresolved", "monitoring", "resolved"]


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
    summary: str
    action: str = ""
    concern_type: ConcernType
    urgency: Urgency
    status: ConcernStatus
    onset: str
    last_updated: str
    evidence: list[str]
    related: RelatedData = RelatedData()
