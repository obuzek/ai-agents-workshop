"""
Tests that patient JSON data files validate against the Pydantic models.

If someone adds a field to the JSON data or changes a field name, this test
fails — catching drift between the data files and the Python models.
"""

import json
from pathlib import Path

import jsonschema
import pytest
from pydantic import ValidationError

from app.models import Patient

DATA_DIR = Path(__file__).parent.parent / "data" / "patients"


def _patient_files():
    """Yield (patient_id, filepath) for each JSON data file."""
    for filepath in sorted(DATA_DIR.glob("*.json")):
        yield filepath.stem.replace("_", "-"), filepath


@pytest.mark.parametrize(
    "patient_id,filepath",
    list(_patient_files()),
    ids=[pid for pid, _ in _patient_files()],
)
def test_patient_json_validates_against_model(patient_id, filepath):
    """Every patient JSON file must parse cleanly through Patient.model_validate()."""
    with open(filepath) as f:
        data = json.load(f)

    try:
        patient = Patient.model_validate(data)
    except ValidationError as e:
        pytest.fail(f"{filepath.name} failed validation:\n{e}")

    assert patient.id == patient_id
    assert patient.name.strip()  # must have a non-empty name


@pytest.mark.parametrize(
    "patient_id,filepath",
    list(_patient_files()),
    ids=[pid for pid, _ in _patient_files()],
)
def test_round_trip_preserves_keys(patient_id, filepath):
    """model_dump(by_alias=True) must produce keys matching the original JSON.

    This catches alias mismatches — e.g., if the model uses 'onset_date' but
    the JSON has 'onsetDate', the alias must be set correctly.
    """
    with open(filepath) as f:
        data = json.load(f)

    patient = Patient.model_validate(data)
    dumped = patient.model_dump(by_alias=True)

    # Check top-level keys from the original JSON are present in the dump
    for key in data:
        assert key in dumped, (
            f"{filepath.name}: JSON key '{key}' missing from model_dump output. "
            f"Add a field or alias for it in the Patient model."
        )


# --- JSON Schema validation ---

_PATIENT_SCHEMA = Patient.model_json_schema()


@pytest.mark.parametrize(
    "patient_id,filepath",
    list(_patient_files()),
    ids=[pid for pid, _ in _patient_files()],
)
def test_patient_json_conforms_to_json_schema(patient_id, filepath):
    """Every patient JSON file must conform to the JSON Schema generated from the Pydantic model.

    This validates the data against the schema itself (not just Pydantic parsing),
    catching issues like extra fields not in the schema or type mismatches that
    Pydantic might silently coerce.
    """
    with open(filepath) as f:
        data = json.load(f)

    try:
        jsonschema.validate(instance=data, schema=_PATIENT_SCHEMA)
    except jsonschema.ValidationError as e:
        pytest.fail(f"{filepath.name} does not conform to Patient JSON Schema:\n{e.message}")
