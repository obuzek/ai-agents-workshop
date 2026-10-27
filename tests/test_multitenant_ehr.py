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
        self.healthy = True

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


# --- Live-session hardening ---


@pytest.mark.parametrize("tenant", ["../other", "a b", "x" * 65, "tenant/../../secrets", "é"])
def test_malformed_tenant_ids_are_rejected(server, tenant):
    resp = server.get("/patients", headers={"X-Tenant": tenant.encode()})
    assert resp.status_code == 400


def test_login_style_tenant_ids_are_accepted(server):
    assert server.get("/patients", headers={"X-Tenant": "0123456789abcdef01234567"}).status_code == 200
    assert server.get("/patients", headers={"X-Tenant": "dev_student-01"}).status_code == 200


def test_health_reports_storage_without_identifiers(server, storage):
    server.get("/patients", headers={"X-Tenant": "tenant-h"})
    health = server.get("/health").json()
    assert health["mode"] == "server" and health["storage"] == "object-storage" and health["tenants"] == 1
    assert "tenant-h" not in str(health)


def test_reply_does_not_change_a_record_another_request_is_reading(server):
    from app import store
    server.get("/patients", headers={"X-Tenant": "tenant-cow"})
    token = store.current_tenant.set("tenant-cow")
    try:
        before = store.load_raw_patients()
        mid = before[0]["messages"][0]["id"]
        thread_len = len(before[0]["messages"][0].get("thread", []))
        store.save_reply(before[0]["id"], mid, "Dr. Test", "new reply", "2026-10-27T00:00:00Z")
        assert len(before[0]["messages"][0].get("thread", [])) == thread_len
        assert len(store.load_raw_patients()[0]["messages"][0]["thread"]) == thread_len + 1
    finally:
        store.current_tenant.reset(token)


def test_unexpected_errors_are_json(server, monkeypatch):
    from app import store
    monkeypatch.setattr(store, "load_raw_patients", lambda: 1 / 0)
    import app.api
    monkeypatch.setattr(app.api, "load_patients", lambda: 1 / 0)
    client = TestClient(app.api.app, raise_server_exceptions=False)
    resp = client.get("/patients", headers={"X-Tenant": "tenant-e"})
    assert resp.status_code == 500 and resp.json()["detail"] == "Internal error (ZeroDivisionError)"


# --- Object Storage client: retries ---


class _Resp:
    def __init__(self, status, body=None):
        self.status_code, self._body = status, body

    def json(self):
        return self._body

    def raise_for_status(self):
        import requests
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


@pytest.fixture
def cos(monkeypatch):
    from app import store
    client = store._ObjectStorage("bucket", "https://cos.test", "apikey")
    client.RETRY_DELAY = 0
    tokens = []

    def iam(url, **kwargs):
        tokens.append(url)
        return _Resp(200, {"access_token": f"t{len(tokens)}", "expiration": 9999999999})

    monkeypatch.setattr(store.requests, "post", iam)
    answers = []

    def request(method, url, headers=None, **kwargs):
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(store.requests, "request", request)
    return client, answers, tokens


def test_storage_retries_a_transient_failure_once(cos):
    import requests
    client, answers, _ = cos
    answers += [_Resp(503), _Resp(200, {"ok": 1})]
    assert client.get("k") == {"ok": 1}
    answers += [requests.ConnectionError(), _Resp(200)]
    client.put("k", {"a": 1})
    assert client.healthy is True


def test_storage_refreshes_a_rejected_token(cos):
    client, answers, tokens = cos
    answers += [_Resp(401), _Resp(404)]
    assert client.get("k") is None
    assert len(tokens) == 2  # fetched a fresh token after the 401


def test_storage_gives_up_after_the_retry(cos):
    import requests
    client, answers, _ = cos
    answers += [_Resp(500), _Resp(500)]
    with pytest.raises(requests.HTTPError):
        client.get("k")
    assert client.healthy is False


# --- Remote mode: a student's local EHR when the shared one is down ---


def test_remote_mode_reports_an_unreachable_shared_ehr_as_503(monkeypatch):
    import requests
    monkeypatch.delenv("EHR_MODE", raising=False)
    monkeypatch.setenv("EHR_API_URL", "https://shared-ehr.test")
    monkeypatch.setenv("EHR_TENANT", "student-1")
    import app.store
    import app.api
    importlib.reload(app.store)
    importlib.reload(app.api)
    try:
        assert app.store.EHR_MODE == "remote"

        def down(*args, **kwargs):
            raise requests.ConnectionError("refused")

        monkeypatch.setattr(app.store.requests, "request", down)
        resp = TestClient(app.api.app).get("/patients")
        assert resp.status_code == 503 and "shared-ehr.test" in resp.json()["detail"]
    finally:
        monkeypatch.delenv("EHR_API_URL")
        monkeypatch.delenv("EHR_TENANT")
        importlib.reload(app.store)
        importlib.reload(app.api)
