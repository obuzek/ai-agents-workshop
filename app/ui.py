"""
Streamlit UI for the EHR inbox system.

Start the backend and UI in two terminals:
    uv run uvicorn app.api:app --reload --port 8000
    uv run streamlit run app/ui.py --server.port 8501

Set API_URL to point the UI at a different backend (default: http://localhost:8000).
"""

import os
import time

import streamlit as st
import requests

from app.models import (
    Patient, Message, Condition, Allergy, Medication,
    Lab, LabPanel, LabResult, Encounter, SOAPNotes, Sender, ThreadEntry,
)

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Lakeview Family Medicine", layout="wide")

# Style radio buttons to look like tabs
st.markdown("""
<style>
    /* Hide the radio bullet and reflow as horizontal tab bar */
    div[data-testid="stHorizontalBlock"] div[role="radiogroup"] {
        gap: 0 !important;
    }
    div[role="radiogroup"] > label {
        background-color: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        border-radius: 0;
        padding: 0.5rem 1rem;
        cursor: pointer;
        font-size: 0.875rem;
    }
    div[role="radiogroup"] > label[data-checked="true"],
    div[role="radiogroup"] > label:has(input:checked) {
        border-bottom-color: rgb(255, 75, 75);
        font-weight: 600;
    }
    /* Hide the radio circle */
    div[role="radiogroup"] > label > div:first-child {
        display: none;
    }
</style>
""", unsafe_allow_html=True)


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


def trigger_agent(patient_id: str):
    """Trigger the agent for a single patient in the background."""
    _post(f"/patients/{patient_id}/run", {})


def mark_concern_resolved(patient_id: str, concern_id: str):
    """Mark a concern as resolved."""
    _post(f"/patients/{patient_id}/concerns/{concern_id}/resolve", {})


def get_agent_status() -> dict:
    """Get the agent's current status (running, last_run, etc.)."""
    try:
        resp = requests.get(f"{API_URL}/agent/status", timeout=3)
        resp.raise_for_status()
        return resp.json()
    except (requests.ConnectionError, requests.Timeout):
        return {"running": False, "last_run": "", "error": "Agent unavailable"}


# ======================
# UI components
# ======================
# Each render function takes model objects, never raw dicts.


def render_patient_selector(patients: list[dict], inbox: list[dict],
                            all_concerns: dict[str, list]) -> str:
    """Render the patient dropdown. Returns the selected patient ID."""
    new_counts: dict[str, int] = {}
    for item in inbox:
        pid = item["patient_id"]
        new_counts[pid] = new_counts.get(pid, 0) + 1

    def max_urgency(pid: str) -> str:
        """Return the highest urgency among unresolved concerns for a patient."""
        concerns = all_concerns.get(pid, [])
        urgencies = {c.get("urgency", "routine") for c in concerns
                     if c.get("status") != "resolved"}
        if "urgent" in urgencies:
            return "urgent"
        if "soon" in urgencies:
            return "soon"
        return "none"

    def label(p):
        count = new_counts.get(p["id"], 0)
        urgency = max_urgency(p["id"])
        icon = {"urgent": "\U0001f534", "soon": "\U0001f7e1", "none": "\u2705"}[urgency]
        if count == 0:
            return f"{icon} {p['name']}"
        return f"{icon} {p['name']} ({count} new)"

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

    highlight_date = st.session_state.get("highlight_lab_date")

    for lab in sorted(patient.labs, key=lambda l: l.date, reverse=True)[:5]:
        panel_names = ", ".join(p.name for p in lab.panels)
        expanded = (lab.date == highlight_date)
        label = f"{lab.date} — {panel_names}"
        if expanded:
            label = f">>> {label}"
        with st.expander(label, expanded=expanded):
            st.caption(f"Ordered by {lab.ordered_by}")
            for panel in lab.panels:
                for r in panel.results:
                    flag = " ⚠️" if r.interpretation in ("high", "low", "abnormal") else ""
                    st.markdown(f"- {r.test}: {r.value} {r.unit}{flag}")

    # Clear after rendering so it doesn't stick
    if highlight_date:
        del st.session_state["highlight_lab_date"]


def render_history(patient: Patient):
    """Render encounter history (SOAP notes) and social history."""
    highlight_date = st.session_state.get("highlight_encounter_date")

    if patient.encounters:
        for enc in sorted(patient.encounters, key=lambda e: e.date, reverse=True)[:5]:
            expanded = (enc.date == highlight_date)
            label = f"{enc.date} — {enc.reason}"
            if expanded:
                label = f">>> {label}"
            with st.expander(label, expanded=expanded):
                for key, lbl in [("subjective", "S"), ("objective", "O"),
                                 ("assessment", "A"), ("plan", "P")]:
                    value = getattr(enc.notes, key)
                    if value:
                        st.markdown(f"**{lbl}:** {value}")
    else:
        st.info("No encounter history.")

    if highlight_date:
        del st.session_state["highlight_encounter_date"]

    if patient.social_history:
        st.markdown("**Social History**")
        st.caption(patient.social_history)


def render_concerns(concerns: list, patient_id: str, messages: list[Message] = None):
    """Render the concerns panel (populated by the agent)."""
    st.subheader("Concerns")

    # Agent controls
    status = get_agent_status()
    col_btn, col_status = st.columns([1, 2])
    with col_btn:
        if status.get("running"):
            st.button("Agent Running...", disabled=True)
        else:
            if st.button("Run Agent"):
                trigger_agent(patient_id)
                st.rerun()
    with col_status:
        if status.get("running"):
            st.caption("Agent is processing patients...")
        elif status.get("last_run"):
            st.caption(f"Last run: {status['last_run'][:19]}")
        if status.get("error"):
            st.caption(f"Error: {status['error']}")

    # Auto-refresh while agent is running
    if status.get("running"):
        time.sleep(3)
        st.rerun()

    # Display concerns sorted by urgency
    urgency_order = {"urgent": 0, "soon": 1, "routine": 2}
    if concerns:
        concerns = sorted(concerns, key=lambda c: urgency_order.get(c.get("urgency", "routine"), 99))
        msg_subjects = {m.id: m.subject for m in messages} if messages else {}
        for concern in concerns:
            urgency = concern.get("urgency", "routine")
            status_val = concern.get("status", "")
            badge_color = {"urgent": "red", "soon": "orange", "routine": "blue"}.get(urgency, "blue")
            status_badge = {"unresolved": ":orange-background[needs reply]",
                            "monitoring": ":blue-background[monitoring]",
                            "resolved": ":green-background[resolved]"}.get(status_val, "")

            with st.expander(f":{badge_color}-background[{urgency}]  {concern.get('title', 'Concern')}"):
                # Action — the most important line
                action = concern.get("action", "")
                if action:
                    st.markdown(f"**Do:** {action}")

                st.markdown(concern.get("summary", ""))

                # Type, onset, status
                meta_parts = []
                ctype = concern.get("concern_type", "")
                if ctype:
                    meta_parts.append(ctype.replace("_", " ").title())
                onset = concern.get("onset", "")
                if onset:
                    meta_parts.append(f"since {onset}")
                if status_badge:
                    meta_parts.append(status_badge)
                if meta_parts:
                    st.markdown(" · ".join(meta_parts))

                # Evidence
                if concern.get("evidence"):
                    st.markdown("**Evidence:**")
                    for e in concern["evidence"]:
                        st.markdown(f"- {e}")

                # Related links
                related = concern.get("related", {})
                msg_ids = related.get("message_ids", [])
                lab_dates = related.get("lab_dates", [])
                conditions = related.get("conditions", [])
                encounter_dates = related.get("encounter_dates", [])

                has_links = msg_ids or lab_dates or conditions or encounter_dates
                if has_links:
                    st.markdown("**Related:**")

                for mid in msg_ids:
                    subject = msg_subjects.get(mid, mid)
                    col_label, col_btn = st.columns([3, 1])
                    with col_label:
                        st.markdown(f"- {subject}")
                    with col_btn:
                        if st.button("Open", key=f"jump_{concern.get('id','')}_{mid}"):
                            st.session_state["jump_to_message"] = mid
                            st.rerun()

                for ld in lab_dates:
                    col_label, col_btn = st.columns([3, 1])
                    with col_label:
                        st.markdown(f"- Labs from {ld}")
                    with col_btn:
                        if st.button("Open", key=f"lab_{concern.get('id','')}_{ld}"):
                            st.session_state["highlight_lab_date"] = ld
                            st.session_state["active_record_tab"] = "Labs"
                            st.rerun()

                for cond in conditions:
                    col_label, col_btn = st.columns([3, 1])
                    with col_label:
                        st.markdown(f"- {cond}")
                    with col_btn:
                        if st.button("Open", key=f"cond_{concern.get('id','')}_{cond}"):
                            st.session_state["active_record_tab"] = "Conditions"
                            st.rerun()

                for ed in encounter_dates:
                    col_label, col_btn = st.columns([3, 1])
                    with col_label:
                        st.markdown(f"- Visit {ed}")
                    with col_btn:
                        if st.button("Open", key=f"enc_{concern.get('id','')}_{ed}"):
                            st.session_state["highlight_encounter_date"] = ed
                            st.session_state["active_record_tab"] = "History"
                            st.rerun()

                # Mark resolved button
                if concern.get("status") != "resolved":
                    if st.button("Mark Resolved", key=f"resolve_{concern.get('id', '')}"):
                        mark_concern_resolved(patient_id, concern.get("id", ""))
                        st.rerun()
    else:
        st.info("No concerns identified yet. Click 'Run Agent' to analyze this patient.")


def render_inbox(messages: list[Message]) -> int:
    """Render the message list. Returns the index of the selected message."""
    st.subheader("Inbox")

    if not messages:
        st.info("No messages.")
        return 0

    # Check if a concern link wants to jump to a specific message
    jump_to = st.session_state.pop("jump_to_message", None)
    default_idx = 0
    if jump_to:
        for i, m in enumerate(messages):
            if m.id == jump_to:
                default_idx = i
                break

    new_count = sum(1 for m in messages if m.needs_response())
    st.caption(f"**{len(messages)}** messages · **{new_count}** new")

    labels = []
    for msg in messages:
        status = "⬜" if msg.needs_response() else "✅"
        labels.append(f"{status}  {msg.date[:10]}  {msg.subject}")

    return st.radio(
        "Select a message",
        options=range(len(messages)),
        index=default_idx,
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
all_concerns = {p["id"]: load_concerns(p["id"]) for p in patient_list}
selected_id = render_patient_selector(patient_list, inbox, all_concerns)

st.divider()

patient = load_patient(selected_id)
messages = load_messages(selected_id)
concerns = all_concerns.get(selected_id, [])

# Row 1: Medical record + Concerns
col_record, col_concerns = st.columns([3, 2])

with col_record:
    st.subheader(patient.name)
    st.caption(f"DOB: {patient.birth_date} · {patient.language}")

    tab_names = ["Conditions", "Medications", "Labs", "History"]
    # Allow concern links to switch the active tab
    default_tab = st.session_state.pop("active_record_tab", "Conditions")
    if default_tab not in tab_names:
        default_tab = "Conditions"
    active_tab = st.radio(
        "Record section",
        tab_names,
        index=tab_names.index(default_tab),
        horizontal=True,
        label_visibility="collapsed",
    )
    if active_tab == "Conditions":
        render_conditions(patient)
    elif active_tab == "Medications":
        render_medications(patient)
    elif active_tab == "Labs":
        render_labs(patient)
    elif active_tab == "History":
        render_history(patient)

with col_concerns:
    render_concerns(concerns, selected_id, messages)

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
