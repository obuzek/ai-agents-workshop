"""
Tests for the workshop model proxy (app/llm_proxy.py). Anthropic is mocked out.
"""

import importlib
import json
import threading
import time

import pytest
import requests
from fastapi.testclient import TestClient

URL = "/llm/anthropic/v1/messages"
BODY = {"model": "claude-sonnet-5-5", "max_tokens": 100000, "messages": [{"role": "user", "content": "hi"}]}


class FakeResp:
    def __init__(self, status_code=200, content=b'{"type":"message","content":[]}', headers=None):
        self.status_code, self.content = status_code, content
        self.headers = headers or {"content-type": "application/json"}
        self.closed = False

    def iter_content(self, chunk_size=None):
        yield b"event: message_stop\n\n"

    def close(self):
        self.closed = True


class FakeUpstream:
    def __init__(self):
        self.calls = []
        self.response = FakeResp()
        self.error = None  # an exception to raise instead of answering
        self.delay = 0.0

    def __call__(self, url, headers=None, data=None, stream=False, timeout=None):
        self.calls.append({"url": url, "headers": headers, "body": json.loads(data), "stream": stream})
        time.sleep(self.delay)
        if self.error:
            raise self.error
        return self.response


def _reload(monkeypatch, mode):
    monkeypatch.setenv("EHR_MODE", mode)
    monkeypatch.delenv("EHR_API_URL", raising=False)
    monkeypatch.delenv("EHR_TENANT", raising=False)
    import app.store
    import app.llm_proxy
    import app.api
    importlib.reload(app.store)
    importlib.reload(app.llm_proxy)
    importlib.reload(app.api)
    return app.api, app.llm_proxy


@pytest.fixture
def proxy(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "real-key")
    monkeypatch.setenv("LLM_PROXY_TOKEN", "workshop-token")
    api, llm_proxy = _reload(monkeypatch, "server")
    fake = FakeUpstream()
    monkeypatch.setattr(llm_proxy.requests, "post", fake)
    llm_proxy._recent.clear()
    yield TestClient(api.app), fake
    monkeypatch.delenv("EHR_MODE")
    _reload(monkeypatch, "local")


def test_forwards_with_the_real_key_and_caps_max_tokens(proxy):
    client, fake = proxy
    resp = client.post(URL, json=BODY, headers={"x-api-key": "workshop-token", "anthropic-version": "2023-06-01"})
    assert resp.status_code == 200
    call = fake.calls[0]
    assert call["url"] == "https://api.anthropic.com/v1/messages"
    assert call["headers"]["x-api-key"] == "real-key"
    assert call["body"]["max_tokens"] == 8192


def test_wrong_or_missing_token_is_rejected(proxy):
    client, fake = proxy
    assert client.post(URL, json=BODY, headers={"x-api-key": "nope"}).status_code == 401
    assert client.post(URL, json=BODY).status_code == 401
    assert fake.calls == []


def test_only_allowlisted_models(proxy):
    client, fake = proxy
    resp = client.post(URL, json={**BODY, "model": "claude-opus-5-5"}, headers={"x-api-key": "workshop-token"})
    assert resp.status_code == 400 and fake.calls == []


def test_streaming_passes_through(proxy):
    client, fake = proxy
    resp = client.post(URL, json={**BODY, "stream": True}, headers={"x-api-key": "workshop-token"})
    assert resp.status_code == 200 and b"message_stop" in resp.content
    assert fake.calls[0]["stream"] is True


def test_not_served_in_local_mode(monkeypatch):
    api, _ = _reload(monkeypatch, "local")
    assert TestClient(api.app).post(URL, json=BODY, headers={"x-api-key": "x"}).status_code in (404, 405)


# --- Day-of workshop info (app/workshop_info.py) ---


def _info_client(monkeypatch, expires):
    monkeypatch.setenv("BOB_ACCESS_URL", "https://example.test/access")
    monkeypatch.setenv("BOB_ACCESS_CODE", "CODE-1")
    monkeypatch.setenv("WORKSHOP_INFO_EXPIRES", expires)
    import app.workshop_info
    importlib.reload(app.workshop_info)
    api, _ = _reload(monkeypatch, "server")
    return TestClient(api.app)


def test_bob_access_served_before_expiry_with_cors(monkeypatch):
    client = _info_client(monkeypatch, "2099-01-01T00:00:00Z")
    resp = client.get("/workshop/bob-access", headers={"Origin": "https://obuzek.github.io"})
    assert resp.status_code == 200 and resp.json() == {"url": "https://example.test/access", "code": "CODE-1"}
    assert resp.headers["access-control-allow-origin"] == "https://obuzek.github.io"
    assert "access-control-allow-origin" not in client.get("/workshop/bob-access", headers={"Origin": "https://evil.test"}).headers
    monkeypatch.delenv("EHR_MODE"); _reload(monkeypatch, "local")


def test_bob_access_refused_after_expiry_or_without_expiry(monkeypatch):
    client = _info_client(monkeypatch, "2000-01-01T00:00:00Z")
    assert client.get("/workshop/bob-access").status_code == 400
    client = _info_client(monkeypatch, "")
    assert client.get("/workshop/bob-access").status_code == 400
    monkeypatch.delenv("EHR_MODE"); _reload(monkeypatch, "local")


# --- Live-session hardening ---

AUTH = {"x-api-key": "workshop-token"}


def test_upstream_rate_limit_passes_through_with_retry_after(proxy):
    client, fake = proxy
    fake.response = FakeResp(429, b'{"type":"error","error":{"type":"rate_limit_error","message":"slow down"}}',
                             {"content-type": "application/json", "retry-after": "7", "request-id": "req_1"})
    resp = client.post(URL, json=BODY, headers=AUTH)
    assert resp.status_code == 429
    assert resp.headers["retry-after"] == "7" and resp.headers["request-id"] == "req_1"
    assert resp.json()["error"]["type"] == "rate_limit_error"
    assert fake.response.closed


def test_streaming_upstream_error_is_returned_as_json(proxy):
    client, fake = proxy
    fake.response = FakeResp(529, b'{"type":"error","error":{"type":"overloaded_error","message":"busy"}}')
    resp = client.post(URL, json={**BODY, "stream": True}, headers=AUTH)
    assert resp.status_code == 529 and resp.json()["error"]["type"] == "overloaded_error"


@pytest.mark.parametrize("error, status", [(requests.ConnectTimeout(), 504), (requests.ConnectionError(), 502)])
def test_unreachable_upstream_gives_a_clear_error(proxy, error, status):
    client, fake = proxy
    fake.error = error
    resp = client.post(URL, json=BODY, headers=AUTH)
    assert resp.status_code == status and resp.json()["type"] == "error"


@pytest.mark.parametrize("body", [[1, 2], {**BODY, "max_tokens": "lots"}])
def test_malformed_bodies_are_400_not_500(proxy, body):
    client, fake = proxy
    resp = client.post(URL, json=body, headers=AUTH)
    assert resp.status_code == 400 and fake.calls == []


def test_non_ascii_token_is_rejected_cleanly(proxy):
    client, _ = proxy
    resp = client.post(URL, json=BODY, headers={"x-api-key": "tök".encode("latin-1")})
    assert resp.status_code == 401


def test_proxy_rate_limit_says_when_to_retry(proxy, monkeypatch):
    client, _ = proxy
    monkeypatch.setenv("LLM_PROXY_RPM", "1")
    assert client.post(URL, json=BODY, headers=AUTH).status_code == 200
    resp = client.post(URL, json=BODY, headers=AUTH)
    assert resp.status_code == 429 and "retry-after" in resp.headers


def test_slow_model_call_does_not_block_other_requests(proxy):
    """A model call takes 30-90 s; the EHR must keep answering meanwhile."""
    _, fake = proxy
    fake.delay = 1.5
    from app import api
    with TestClient(api.app) as client:  # one event loop shared by both requests
        slow = threading.Thread(target=client.post, args=(URL,), kwargs={"json": BODY, "headers": AUTH})
        slow.start()
        time.sleep(0.2)
        start = time.monotonic()
        assert client.get("/health").status_code == 200
        assert time.monotonic() - start < 0.5
        slow.join()


def test_health_reports_proxy_configured_without_secrets(proxy):
    client, _ = proxy
    health = client.get("/health")
    assert health.json()["llm_proxy"] == "configured"
    assert "real-key" not in health.text and "workshop-token" not in health.text


def test_model_access_served_before_expiry(monkeypatch):
    monkeypatch.setenv("LLM_PROXY_TOKEN", "workshop-token")
    monkeypatch.setenv("PUBLIC_URL", "https://ehr.example.test")
    client = _info_client(monkeypatch, "2099-01-01T00:00:00Z")
    body = client.get("/workshop/model-access").json()
    assert body == {"model": "anthropic/claude-sonnet-5-5",
                    "custom_host": "https://ehr.example.test/llm/anthropic/v1", "api_key": "workshop-token"}
    monkeypatch.delenv("EHR_MODE"); _reload(monkeypatch, "local")


def test_model_access_refused_after_expiry(monkeypatch):
    monkeypatch.setenv("LLM_PROXY_TOKEN", "workshop-token")
    client = _info_client(monkeypatch, "2000-01-01T00:00:00Z")
    assert client.get("/workshop/model-access").status_code == 400
    monkeypatch.delenv("EHR_MODE"); _reload(monkeypatch, "local")


def test_seats_served_before_expiry_and_refused_after(monkeypatch):
    monkeypatch.setenv("WORKSHOP_SEATS", '[{"username": "seat01@example.test", "password": "pw-1"}, {"bad": 1}]')
    client = _info_client(monkeypatch, "2099-01-01T00:00:00Z")
    assert client.get("/workshop/seats").json() == {"seats": [{"username": "seat01@example.test", "password": "pw-1"}]}
    client = _info_client(monkeypatch, "2000-01-01T00:00:00Z")
    assert client.get("/workshop/seats").status_code == 400
    monkeypatch.delenv("EHR_MODE"); _reload(monkeypatch, "local")
