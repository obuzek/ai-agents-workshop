"""
Data models for the EHR system.

These dataclasses define the internal representation of patient records.
The JSON files in data/patients/ are one way to populate them — the models
themselves are independent of the storage format.
"""

from dataclasses import dataclass, field


@dataclass
class Sender:
    name: str
    role: str  # "patient" or "provider"


@dataclass
class ThreadEntry:
    date: str
    sender: Sender
    body: str


@dataclass
class Message:
    id: str
    date: str
    sender: Sender
    category: str
    subject: str
    body: str
    thread: list[ThreadEntry] = field(default_factory=list)

    def needs_response(self) -> bool:
        """True if the most recent message in this thread is from the patient."""
        if not self.thread:
            return True
        return self.thread[-1].sender.role != "provider"


@dataclass
class Condition:
    display: str
    status: str
    onset_date: str
    notes: str = ""


@dataclass
class Allergy:
    substance: str
    reaction: str


@dataclass
class Medication:
    display: str
    dosage: str
    frequency: str
    prescriber: str
    status: str


@dataclass
class LabResult:
    test: str
    value: object  # str or numeric
    unit: str
    interpretation: str = ""


@dataclass
class LabPanel:
    name: str
    results: list[LabResult] = field(default_factory=list)


@dataclass
class Lab:
    date: str
    ordered_by: str
    panels: list[LabPanel] = field(default_factory=list)


@dataclass
class SOAPNotes:
    subjective: str = ""
    objective: str = ""
    assessment: str = ""
    plan: str = ""


@dataclass
class Encounter:
    date: str
    reason: str
    notes: SOAPNotes = field(default_factory=SOAPNotes)


@dataclass
class Patient:
    id: str
    given_name: str
    family_name: str
    birth_date: str
    language: str
    conditions: list[Condition] = field(default_factory=list)
    allergies: list[Allergy] = field(default_factory=list)
    medications: list[Medication] = field(default_factory=list)
    labs: list[Lab] = field(default_factory=list)
    encounters: list[Encounter] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)
    social_history: str = ""

    @property
    def name(self) -> str:
        return f"{self.given_name} {self.family_name}"

    @property
    def active_conditions(self) -> list[Condition]:
        return [c for c in self.conditions if c.status == "active"]

    @property
    def active_medications(self) -> list[Medication]:
        return [m for m in self.medications if m.status == "active"]

    def new_message_count(self) -> int:
        return sum(1 for m in self.messages if m.needs_response())
