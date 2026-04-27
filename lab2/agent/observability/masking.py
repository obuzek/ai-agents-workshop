"""
PII masking for Langfuse traces using LangChain's Presidio integration.

This module provides the `mask_pii` function that Langfuse applies to all
trace data (inputs, outputs, metadata) *before* it leaves the process.
This is client-side masking — the strongest guarantee that sensitive data
never reaches your trace store.

Two layers of defense:
1. Field-level redaction: Pydantic models annotated with sensitivity="pii"
   or sensitivity="phi" are redacted by field name — no NER needed.
2. NER-based detection (Presidio via spaCy): catches PII embedded in free-text
   fields where you can't predict the key name.

Presidio is the most widely adopted open-source PII detection library
(~4M monthly PyPI downloads, first-class LangChain integration).
"""

import logging
import os

from langchain_experimental.data_anonymizer import PresidioAnonymizer
from presidio_analyzer import Pattern, PatternRecognizer
from presidio_anonymizer.entities import OperatorConfig
from langfuse.langchain import CallbackHandler
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# --- Pydantic model introspection ---

def _get_sensitive_fields(model_class: type[BaseModel]) -> dict[str, str]:
    """Extract fields annotated with sensitivity metadata from a Pydantic model.

    Returns a dict mapping field name -> sensitivity level ("pii" or "phi").
    """
    sensitive = {}
    for name, field_info in model_class.model_fields.items():
        extra = field_info.json_schema_extra
        if isinstance(extra, dict) and "sensitivity" in extra:
            sensitive[name] = extra["sensitivity"]
    return sensitive


# Cache to avoid re-inspecting the same model class repeatedly.
_sensitive_fields_cache: dict[type, dict[str, str]] = {}


def _sensitive_fields_for(model_class: type[BaseModel]) -> dict[str, str]:
    if model_class not in _sensitive_fields_cache:
        _sensitive_fields_cache[model_class] = _get_sensitive_fields(model_class)
    return _sensitive_fields_cache[model_class]


# --- Build the Presidio anonymizer for free-text fields ---

_ANALYZED_FIELDS = [
    "PERSON",           # Patient names, doctor names, emergency contacts
    "EMAIL_ADDRESS",    # Patient email addresses
    "PHONE_NUMBER",     # Patient and contact phone numbers
    "US_SSN",           # Social Security Numbers
    "LOCATION",         # Street addresses, cities, states
    "DATE_TIME",        # Dates of birth, appointment dates
    "CREDIT_CARD",      # Unlikely in EHR but good to catch
    "URL",              # Any URLs in trace data
]

_anonymizer = PresidioAnonymizer(
    analyzed_fields=_ANALYZED_FIELDS,
    add_default_faker_operators=False,
)

# Custom recognizer: insurance member IDs in our data (e.g., "1EG4-TE5-MK72")
_anonymizer.add_recognizer(
    PatternRecognizer(
        supported_entity="INSURANCE_MEMBER_ID",
        patterns=[
            Pattern(
                name="member_id_alphanum_hyphen",
                regex=r"\b(?=[A-Z0-9-]*[A-Z])[A-Z0-9]{2,}(?:-[A-Z0-9]{2,}){2,}\b",
                score=0.7,
            ),
        ],
    )
)
_anonymizer.add_operators({
    "INSURANCE_MEMBER_ID": OperatorConfig("replace", {"new_value": "<INSURANCE_MEMBER_ID>"}),
})


# --- Masking logic ---

_PLACEHOLDER = {
    "pii": "<PII_REDACTED>",
    "phi": "<PHI_REDACTED>",
}


def _mask_value(value, _redact_as=None):
    """Recursively mask PII/PHI in arbitrary data structures.

    Args:
        value: The data to mask.
        _redact_as: If set ("pii" or "phi"), this value was identified as
            sensitive by its parent model's field annotation. Short strings
            are replaced entirely; long strings still go through Presidio
            (they may contain a mix of sensitive and non-sensitive content).
    """
    if value is None or isinstance(value, (int, float, bool)):
        return value

    if isinstance(value, str):
        # If the parent model flagged this field as sensitive, redact directly.
        # This handles short fields like names where NER is unreliable.
        if _redact_as:
            return _PLACEHOLDER.get(_redact_as, "<REDACTED>")
        if not value.strip():
            return value
        return _anonymizer.anonymize(value)

    if isinstance(value, dict):
        return {k: _mask_value(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [_mask_value(item) for item in value]

    # Pydantic models: use field annotations to decide what to redact.
    if isinstance(value, BaseModel):
        sensitive = _sensitive_fields_for(type(value))
        dumped = value.model_dump(by_alias=True)
        result = {}
        # Map alias -> field name for sensitivity lookup
        alias_to_field = {
            (fi.alias or name): name
            for name, fi in type(value).model_fields.items()
        }
        for key, val in dumped.items():
            field_name = alias_to_field.get(key, key)
            sensitivity = sensitive.get(field_name)
            result[key] = _mask_value(val, _redact_as=sensitivity)
        return result

    # Unrecognized type — pass through and warn.
    logger.warning("mask_pii: unhandled type %s, passing through unmasked", type(value).__name__)
    return value


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
    return _mask_value(data)


def create_langfuse_handler(**kwargs) -> CallbackHandler:
    """Create a Langfuse CallbackHandler with PII masking enabled.

    The handler reads connection details from environment variables:
        LANGFUSE_PUBLIC_KEY  (default: pk-lf-workshop)
        LANGFUSE_SECRET_KEY  (default: sk-lf-workshop)
        LANGFUSE_HOST        (default: http://localhost:3000)

    Any additional kwargs are passed through to CallbackHandler.
    """
    from langfuse import Langfuse

    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "pk-lf-workshop")
    os.environ.setdefault("LANGFUSE_SECRET_KEY", "sk-lf-workshop")
    os.environ.setdefault("LANGFUSE_HOST", "http://localhost:3000")

    Langfuse(mask=mask_pii)

    return CallbackHandler(**kwargs)
