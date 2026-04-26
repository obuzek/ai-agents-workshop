"""
Streamlit UI for the EHR inbox system.

Start the backend and UI in two terminals:
    uvicorn app.api:app --reload --port 8000
    streamlit run app/ui.py --server.port 8501

Set API_URL to point the UI at a different backend (default: http://localhost:8000).
"""

import os

import streamlit as st
import requests

from app.models import (
    Patient, Message, Condition, Allergy, Medication,
    Lab, LabPanel, LabResult, Encounter, SOAPNotes, Sender, ThreadEntry,
)

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Lakeview Family Medicine", layout="wide")


# ======================
# Data layer
# ======================
# The UI fetches JSON from the API and converts it to model objects.
# All rendering works with models, never raw dicts.


@st.cache_data(ttl=10)
def _fetch(endpoint: str):
    """Fetch JSON from the API."""
    resp = requests.get(f"{API_URL}{endpoint}")
    resp.raise_for_status()
    return resp.json()


def _post(endpoint: str, payload: dict):
    """Post JSON to the API and clear the cache so the UI refreshes."""
    resp = requests.post(f"{API_URL}{endpoint}", json=payload)
    resp.raise_for_status()
    st.cache_data.clear()


def _parse_sender(data: dict) -> Sender:
    return Sender(name=data["name"], role=data["role"])


def _parse_message(data: dict) -> Message:
    return Message(
        id=data["id"],
        date=data["date"],
        sender=_parse_sender(data["sender"]),
        category=data["category"],
        subject=data["subject"],
        body=data["body"],
        thread=[
            ThreadEntry(date=t["date"], sender=_parse_sender(t["sender"]), body=t["body"])
            for t in data.get("thread", [])
        ],
    )


def _parse_patient(data: dict) -> Patient:
    demo = data["demographics"]
    social = data.get("socialHistory", "")
    if isinstance(social, dict):
        social = social.get("notes", "")

    return Patient(
        id=data["id"],
        given_name=demo["name"]["given"],
        family_name=demo["name"]["family"],
        birth_date=demo["birthDate"],
        language=demo.get("preferredLanguage", "English"),
        conditions=[
            Condition(display=c["display"], status=c["status"],
                      notes=c.get("notes", ""), onset_date=c.get("onsetDate", ""))
            for c in data.get("conditions", [])
        ],
        allergies=[
            Allergy(substance=a["substance"], reaction=a["reaction"])
            for a in data.get("allergies", [])
        ],
        medications=[
            Medication(display=m["display"], dosage=m["dosage"], frequency=m["frequency"],
                       prescriber=m["prescriber"], status=m["status"])
            for m in data.get("medications", [])
        ],
        labs=[
            Lab(date=lab["date"], ordered_by=lab["orderedBy"], panels=[
                LabPanel(name=p["name"], results=[
                    LabResult(test=r["test"], value=r["value"], unit=r.get("unit", ""),
                              interpretation=r.get("interpretation", ""))
                    for r in p.get("results", [])
                ])
                for p in lab.get("panels", [])
            ])
            for lab in data.get("labs", [])
        ],
        encounters=[
            Encounter(date=e["date"], reason=e.get("reasonForVisit", "Visit"), notes=SOAPNotes(
                subjective=e.get("notes", {}).get("subjective", ""),
                objective=e.get("notes", {}).get("objective", ""),
                assessment=e.get("notes", {}).get("assessment", ""),
                plan=e.get("notes", {}).get("plan", ""),
            ))
            for e in data.get("encounters", [])
        ],
        messages=[_parse_message(m) for m in data.get("messages", [])],
        social_history=social,
    )


def load_patient_list() -> list[dict]:
    """Load the patient summary list from the API. Returns raw dicts (id, name only)."""
    return _fetch("/patients")


def load_inbox() -> list[dict]:
    """Load inbox items from the API. Returns raw dicts (patient_id, count)."""
    return _fetch("/inbox")


def load_patient(patient_id: str) -> Patient:
    """Load a full patient record and parse it into a Patient model."""
    return _parse_patient(_fetch(f"/patients/{patient_id}"))


def load_messages(patient_id: str) -> list[Message]:
    """Load messages for a patient, newest first, as Message models."""
    return [_parse_message(m) for m in _fetch(f"/patients/{patient_id}/messages")]


def load_concerns(patient_id: str) -> list:
    """Load concerns for a patient."""
    return _fetch(f"/patients/{patient_id}/concerns")


def send_reply(patient_id: str, message_id: str, body: str):
    """Post a provider reply to a message."""
    _post(f"/patients/{patient_id}/messages/{message_id}/reply", {"body": body})


# ======================
# UI components
# ======================
# Each render function takes model objects, never raw dicts.


def render_patient_selector(patients: list[dict], inbox: list[dict]) -> str:
    """Render the patient dropdown. Returns the selected patient ID."""
    new_counts: dict[str, int] = {}
    for item in inbox:
        pid = item["patient_id"]
        new_counts[pid] = new_counts.get(pid, 0) + 1

    def label(p):
        count = new_counts.get(p["id"], 0)
        if count == 0:
            return f"✅ {p['name']}"
        return f"⬜ {p['name']} ({count} new)"

    return st.selectbox(
        "Patient",
        options=[p["id"] for p in patients],
        format_func=lambda pid: label(next(p for p in patients if p["id"] == pid)),
    )


def render_conditions(patient: Patient):
    """Render active conditions and allergies."""
    conditions = patient.active_conditions
    if conditions:
        for c in conditions:
            st.markdown(f"- {c.display}")
            if c.notes:
                st.caption(f"  {c.notes[:120]}...")
    else:
        st.info("No active conditions.")

    if patient.allergies:
        st.markdown("**Allergies**")
        for a in patient.allergies:
            st.markdown(f"- ⚠️ {a.substance} ({a.reaction})")


def render_medications(patient: Patient):
    """Render active medications."""
    meds = patient.active_medications
    if meds:
        for m in meds:
            st.markdown(f"- **{m.display}** — {m.dosage} {m.frequency}")
            st.caption(f"  Prescribed by {m.prescriber}")
    else:
        st.info("No active medications.")


def render_labs(patient: Patient):
    """Render lab results as expandable panels."""
    if not patient.labs:
        st.info("No lab results.")
        return

    for lab in sorted(patient.labs, key=lambda l: l.date, reverse=True)[:5]:
        panel_names = ", ".join(p.name for p in lab.panels)
        with st.expander(f"{lab.date} — {panel_names}"):
            st.caption(f"Ordered by {lab.ordered_by}")
            for panel in lab.panels:
                for r in panel.results:
                    flag = " ⚠️" if r.interpretation in ("high", "low", "abnormal") else ""
                    st.markdown(f"- {r.test}: {r.value} {r.unit}{flag}")


def render_history(patient: Patient):
    """Render encounter history (SOAP notes) and social history."""
    if patient.encounters:
        for enc in sorted(patient.encounters, key=lambda e: e.date, reverse=True)[:5]:
            with st.expander(f"{enc.date} — {enc.reason}"):
                for key, label in [("subjective", "S"), ("objective", "O"),
                                   ("assessment", "A"), ("plan", "P")]:
                    value = getattr(enc.notes, key)
                    if value:
                        st.markdown(f"**{label}:** {value}")
    else:
        st.info("No encounter history.")

    if patient.social_history:
        st.markdown("**Social History**")
        st.caption(patient.social_history)


def render_concerns(concerns: list):
    """Render the concerns panel (populated by the agent)."""
    st.subheader("Concerns")
    if concerns:
        for concern in concerns:
            st.markdown(f"- {concern}")
    else:
        st.info("No concerns identified yet. The agent will populate this area.")


def render_inbox(messages: list[Message]) -> int:
    """Render the message list. Returns the index of the selected message."""
    st.subheader("Inbox")

    if not messages:
        st.info("No messages.")
        return 0

    new_count = sum(1 for m in messages if m.needs_response())
    st.caption(f"**{len(messages)}** messages · **{new_count}** new")

    labels = []
    for msg in messages:
        status = "⬜" if msg.needs_response() else "✅"
        labels.append(f"{status}  {msg.date[:10]}  {msg.subject}")

    return st.radio(
        "Select a message",
        options=range(len(messages)),
        format_func=lambda i: labels[i],
        label_visibility="collapsed",
    )


def render_conversation(msg: Message, patient_id: str):
    """Render the selected message conversation with reply form."""
    st.subheader("Conversation")

    st.markdown(f"#### {msg.subject}")

    # Status and category badges
    badges = []
    if msg.needs_response():
        badges.append(":orange-background[new]")
    else:
        badges.append(":green-background[responded]")
    badges.append(f":blue-background[{msg.category}]")
    # TODO: agent can add urgency badges here, e.g. ":red-background[urgent]"
    st.markdown("  ".join(badges))

    st.caption(msg.date[:10])
    st.divider()

    # Original message
    st.caption(f"From: {msg.sender.name}")
    st.markdown(msg.body)

    # Thread replies
    for entry in msg.thread:
        st.divider()
        st.caption(f"From: {entry.sender.name} · {entry.date[:10]}")
        st.markdown(entry.body)

    # Reply form
    st.divider()
    reply_text = st.text_area("Reply", key=f"reply_{msg.id}", placeholder="Type your response...")
    if st.button("Send", key=f"send_{msg.id}"):
        if reply_text.strip():
            send_reply(patient_id, msg.id, reply_text)
            st.rerun()


# ======================
# Page layout
# ======================


st.title("Lakeview Family Medicine")

# Load data
patient_list = load_patient_list()
inbox = load_inbox()
selected_id = render_patient_selector(patient_list, inbox)

st.divider()

patient = load_patient(selected_id)
messages = load_messages(selected_id)
concerns = load_concerns(selected_id)

# Row 1: Medical record + Concerns
col_record, col_concerns = st.columns([3, 2])

with col_record:
    st.subheader(patient.name)
    st.caption(f"DOB: {patient.birth_date} · {patient.language}")

    tab_conditions, tab_meds, tab_labs, tab_history = st.tabs(
        ["Conditions", "Medications", "Labs", "History"]
    )
    with tab_conditions:
        render_conditions(patient)
    with tab_meds:
        render_medications(patient)
    with tab_labs:
        render_labs(patient)
    with tab_history:
        render_history(patient)

with col_concerns:
    render_concerns(concerns)

# Row 2: Inbox + Conversation viewer
st.divider()
col_inbox, col_viewer = st.columns([2, 3])

with col_inbox:
    selected_msg_idx = render_inbox(messages)

with col_viewer:
    if messages:
        render_conversation(messages[selected_msg_idx], selected_id)
    else:
        st.subheader("Conversation")
        st.info("Select a patient to view messages.")
