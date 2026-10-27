"""
Tests for each lab agent service's GET /lab, which tells the shared inbox UI
which lab is running and which optional endpoints it may call.
"""

import importlib

import pytest
from fastapi.testclient import TestClient

# Optional feature -> one GET endpoint the UI calls for it.
FEATURE_PROBES = {
    "masking": "/masking",
    "grounding": "/grounding",
    "roles": "/providers",
    "sharing": "/patients/patient-001/concerns/c1/shared-by",
}

EXPECTED = {
    1: [],
    2: ["masking"],
    3: ["masking", "grounding"],
    4: ["masking", "grounding", "roles", "sharing"],
}


@pytest.fixture
def lab_client(monkeypatch):
    """A TestClient for a lab's agent API, without its lifespan (no LLM or DB checks)."""
    # An empty DATABASE_URL keeps Lab 4 on its JSON store; dotenv won't override it.
    monkeypatch.setenv("DATABASE_URL", "")

    def make(lab: int) -> TestClient:
        return TestClient(importlib.import_module(f"lab{lab}.agent.api").app)

    return make


@pytest.mark.parametrize("lab", sorted(EXPECTED))
def test_lab_names_itself_and_its_features(lab_client, lab):
    resp = lab_client(lab).get("/lab")
    assert resp.status_code == 200
    assert resp.json() == {"lab": lab, "features": EXPECTED[lab]}


@pytest.mark.parametrize("lab", sorted(EXPECTED))
def test_listed_features_are_served_and_unlisted_ones_are_not(lab_client, lab, monkeypatch):
    client = lab_client(lab)
    if lab == 4:
        # Keep the Lab 4 probes off the real store.
        api = importlib.import_module("lab4.agent.api")
        monkeypatch.setattr(api, "get_providers", lambda: [])
        monkeypatch.setattr(api, "get_shared_by", lambda concern_id, provider_id: None)
    listed = client.get("/lab").json()["features"]
    for feature, path in FEATURE_PROBES.items():
        status = client.get(path).status_code
        if feature in listed:
            assert status == 200, f"lab{lab} lists {feature} but {path} answered {status}"
        else:
            assert status == 404, f"lab{lab} doesn't list {feature} but serves {path}"
