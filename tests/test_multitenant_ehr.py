"""
Tests for the shared workshop EHR (EHR_MODE=server): tenants must not see each
other's data, and requests without a tenant are rejected.
"""

import copy
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


# --- Persistence to Object Storage (faked) ---


class FakeStorage:
    def __init__(self):
        self.objects, self.fail_reads, self.puts = {}, False, []

    def get(self, key):
        if self.fail_reads:
            raise ConnectionError("storage down")
        return self.objects.get(key)

    def put(self, key, data):
        self.puts.append(key)
        self.objects[key] = copy.deepcopy(data)


@pytest.fixture
def storage(server):
    from app import store
    fake = FakeStorage()
    store._storage = fake
    yield fake


def _restart():
    """Simulate the EHR process restarting: in-memory tenant data is gone."""
    from app import store
    store._tenant_data.clear()


def test_replies_survive_a_restart(server, storage):
    mid = _first_message_id(server, "tenant-p")
    server.post(REPLY_PATH.format(mid=mid), json={"body": "persist me"}, headers={"X-Tenant": "tenant-p"})
    assert storage.puts == ["tenants/tenant-p/records.json"]

    _restart()
    assert "persist me" in _thread_bodies(server, "tenant-p", mid)
    assert "persist me" not in _thread_bodies(server, "tenant-q", mid)


def test_new_tenant_starts_from_original_data_without_writing(server, storage):
    assert len(server.get("/patients", headers={"X-Tenant": "tenant-new"}).json()) == 12
    assert storage.puts == []  # nothing saved until the tenant changes something


def test_storage_outage_returns_503_and_never_overwrites(server, storage):
    mid = _first_message_id(server, "tenant-r")
    server.post(REPLY_PATH.format(mid=mid), json={"body": "saved before outage"}, headers={"X-Tenant": "tenant-r"})
    _restart()
    storage.fail_reads = True

    assert server.get("/patients", headers={"X-Tenant": "tenant-r"}).status_code == 503
    resp = server.post(REPLY_PATH.format(mid=mid), json={"body": "during outage"}, headers={"X-Tenant": "tenant-r"})
    assert resp.status_code == 503
    assert storage.puts == ["tenants/tenant-r/records.json"]  # the saved copy was never overwritten

    storage.fail_reads = False
    bodies = _thread_bodies(server, "tenant-r", mid)
    assert "saved before outage" in bodies and "during outage" not in bodies
