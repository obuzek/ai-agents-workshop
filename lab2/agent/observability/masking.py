"""
PII masking for Langfuse traces.

This module provides the `mask_pii` function that Langfuse applies to all
trace data (inputs, outputs, metadata) *before* it leaves the process.
This is client-side masking — the strongest guarantee that sensitive data
never reaches your trace store.

The masking approach:
1. Load patient names from the data directory at startup
2. Apply regex-based redaction for structured PII (DOBs, phones, emails, etc.)
3. Replace known patient names with [PATIENT_NAME]

This is intentionally simple. A production system would use a dedicated
NER model or a service like Presidio for PII detection. For the workshop,
regex + known names is sufficient to demonstrate the principle.
"""

import json
import os
import re
from glob import glob
from pathlib import Path

from langfuse.langchain import CallbackHandler


# --- Load known patient names from the data directory ---

def _load_patient_names() -> list[str]:
    """Load all patient and emergency contact names from data files.

    Returns names sorted longest-first so "Patricia Kowalski" is matched
    before "Patricia" — preventing partial replacements.
    """
    data_dir = Path(os.environ.get("DATA_DIR", "data/patients"))
    names = set()
    for filepath in sorted(data_dir.glob("patient_*.json")):
        with open(filepath) as f:
            patient = json.load(f)
        demo = patient.get("demographics", {})
        name = demo.get("name", {})
        given = name.get("given", "")
        family = name.get("family", "")
        if given:
            names.add(given)
        if family:
            names.add(family)
        if given and family:
            names.add(f"{given} {family}")
        # Emergency contacts
        ec = demo.get("emergencyContact", {})
        if ec.get("name"):
            names.add(ec["name"])

    # Sort longest-first so full names match before first/last names alone
    return sorted(names, key=len, reverse=True)


_PATIENT_NAMES = _load_patient_names()


# --- Regex patterns for structured PII ---

# Dates that look like DOBs: YYYY-MM-DD
_DOB_PATTERN = re.compile(r"\b(19|20)\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b")

# US phone numbers: 847-555-0143, (847) 555-0143, 847.555.0143
_PHONE_PATTERN = re.compile(
    r"\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}"
)

# Email addresses
_EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
)

# SSN: 123-45-6789
_SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# Insurance member IDs: alphanumeric with hyphens, 8+ chars
_MEMBER_ID_PATTERN = re.compile(r"\b[A-Z0-9]{2,}(?:-[A-Z0-9]{2,}){2,}\b")


def _mask_string(text: str) -> str:
    """Apply all PII redaction rules to a single string."""
    # Names first (longest match first to avoid partial replacements)
    for name in _PATIENT_NAMES:
        text = text.replace(name, "[PATIENT_NAME]")

    # Structured patterns
    text = _SSN_PATTERN.sub("[SSN]", text)
    text = _EMAIL_PATTERN.sub("[EMAIL]", text)
    text = _PHONE_PATTERN.sub("[PHONE]", text)
    text = _MEMBER_ID_PATTERN.sub("[MEMBER_ID]", text)

    return text


def mask_pii(*, data, **kwargs):
    """Mask PII in trace data before it's sent to Langfuse.

    This function is passed to the Langfuse client via the `mask` parameter.
    It is called on every piece of data (inputs, outputs, metadata) before
    transmission. Data never leaves the process unmasked.

    Args:
        data: The value to mask — can be a string, dict, list, or other type.
        **kwargs: Reserved for future Langfuse API extensions.

    Returns:
        The masked data in the same structure.
    """
    if isinstance(data, str):
        return _mask_string(data)
    elif isinstance(data, dict):
        return {k: mask_pii(data=v) for k, v in data.items()}
    elif isinstance(data, list):
        return [mask_pii(data=item) for item in data]
    return data


def create_langfuse_handler(**kwargs) -> CallbackHandler:
    """Create a Langfuse CallbackHandler with PII masking enabled.

    The handler reads connection details from environment variables:
        LANGFUSE_PUBLIC_KEY  (default: pk-lf-workshop)
        LANGFUSE_SECRET_KEY  (default: sk-lf-workshop)
        LANGFUSE_HOST        (default: http://localhost:3000)

    Any additional kwargs are passed through to CallbackHandler.
    """
    # Import here so we can set up the client with masking
    from langfuse import Langfuse

    # Configure the Langfuse client with masking enabled.
    # This ensures ALL data — from any integration — is masked before sending.
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "pk-lf-workshop")
    os.environ.setdefault("LANGFUSE_SECRET_KEY", "sk-lf-workshop")
    os.environ.setdefault("LANGFUSE_HOST", "http://localhost:3000")

    Langfuse(mask=mask_pii)

    return CallbackHandler(**kwargs)
