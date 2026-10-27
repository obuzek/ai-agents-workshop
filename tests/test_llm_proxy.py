"""
Tests for the workshop model proxy (app/llm_proxy.py). Anthropic is mocked out.
"""

import importlib
import json

import pytest
from fastapi.testclient import TestClient

URL = "/llm/anthropic/v1/messages"
BODY = {"model": "claude-sonnet-5-5", "max_tokens": 100000, "messages": [{"role": "user", "content": "hi"}]}


class FakeUpstream:
    def __init__(self):
        self.calls = []

    def __call__(self, url, headers=None, data=None, stream=False, timeout=None):
        self.calls.append({"url": url, "headers": headers, "body": json.loads(data), "stream": stream})

        class Resp:
            status_code = 200
            content = b'{"type":"message","content":[]}'
            headers = {"content-type": "application/json"}

            def iter_content(self, chunk_size=None):
                yield b"event: message_stop\n\n"

        return Resp()


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
