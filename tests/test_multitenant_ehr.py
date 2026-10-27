"""
Tests for the shared workshop EHR (EHR_MODE=server): tenants must not see each
other's data, and requests without a tenant are rejected.
"""

import importlib

import pytest
from fastapi.testclient import TestClient

REPLY_PATH = "/patients/patient-001/messages/{mid}/reply"


@pytest.fixture
def server(monkeypatch):
    monkeypatch.setenv("EHR_MODE", "server")
    monkeypatch.delenv("EHR_API_URL", raising=False)
    monkeypatch.delenv("EHR_TENANT", raising=False)
    import app.store
    import app.api
    importlib.reload(app.store)
    importlib.reload(app.api)
    yield TestClient(app.api.app)
    # Restore local mode for any later tests.
    monkeypatch.delenv("EHR_MODE")
    importlib.reload(app.store)
    importlib.reload(app.api)


def _first_message_id(client, tenant):
    return client.get("/patients/patient-001/messages", headers={"X-Tenant": tenant}).json()[0]["id"]


def _thread_bodies(client, tenant, message_id):
    messages = client.get("/patients/patient-001/messages", headers={"X-Tenant": tenant}).json()
    msg = next(m for m in messages if m["id"] == message_id)
    return [t["body"] for t in msg.get("thread", [])]


def test_requests_without_tenant_are_rejected(server):
    assert server.get("/patients").status_code == 401
    assert server.get("/health").status_code == 200


def test_tenants_start_with_the_same_patients(server):
    a = server.get("/patients", headers={"X-Tenant": "tenant-a"}).json()
    b = server.get("/patients", headers={"X-Tenant": "tenant-b"}).json()
    assert len(a) == 12 and a == b


def test_replies_stay_within_a_tenant(server):
    mid = _first_message_id(server, "tenant-a")
    resp = server.post(REPLY_PATH.format(mid=mid), json={"body": "only for A"}, headers={"X-Tenant": "tenant-a"})
    assert resp.status_code == 200

    assert "only for A" in _thread_bodies(server, "tenant-a", mid)
    assert "only for A" not in _thread_bodies(server, "tenant-b", mid)


def test_server_mode_never_writes_the_json_files(server, tmp_path):
    from app import store
    before = {p.name: p.read_text() for p in store.DATA_DIR.glob("*.json")}
    mid = _first_message_id(server, "tenant-c")
    server.post(REPLY_PATH.format(mid=mid), json={"body": "in memory"}, headers={"X-Tenant": "tenant-c"})
    after = {p.name: p.read_text() for p in store.DATA_DIR.glob("*.json")}
    assert before == after


def test_records_endpoint_returns_full_records(server):
    records = server.get("/records", headers={"X-Tenant": "tenant-d"}).json()
    assert len(records) == 12 and "messages" in records[0]
