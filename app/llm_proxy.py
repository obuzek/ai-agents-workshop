"""
A small pass-through proxy to Anthropic's API, served by the shared workshop EHR.

watsonx Orchestrate registers the model as an Anthropic model whose host is this
proxy (the model's `custom_host`). Orchestrate sends requests here with the
workshop proxy token as its API key; the proxy checks the token, swaps in the
real Anthropic key, and forwards the request. The real key lives only in this
server's environment, so it never reaches attendees' machines or Orchestrate.

Configure with environment variables (server mode only):
    ANTHROPIC_API_KEY     the real key
    LLM_PROXY_TOKEN       what Orchestrate's model connection sends as its API key
    LLM_PROXY_MODELS      comma-separated allowlist (default: claude-sonnet-5-5,claude-haiku-5-5)
    LLM_PROXY_MAX_TOKENS  cap on max_tokens per request (default 8192)
    LLM_PROXY_RPM         requests per minute across the proxy (default 600)
"""

import hmac
import json
import os
import threading
import time
from collections import deque

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

UPSTREAM = "https://api.anthropic.com"
# Headers we pass through to Anthropic; everything else (including the caller's key) is dropped.
FORWARD_HEADERS = {"content-type", "anthropic-version", "anthropic-beta", "accept"}

router = APIRouter(prefix="/llm/anthropic")
_recent: deque[float] = deque()
_rate_lock = threading.Lock()


def _settings() -> dict:
    return {
        "key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "token": os.environ.get("LLM_PROXY_TOKEN", ""),
        "models": {m.strip() for m in os.environ.get("LLM_PROXY_MODELS", "claude-sonnet-5-5,claude-haiku-5-5").split(",") if m.strip()},
        "max_tokens": int(os.environ.get("LLM_PROXY_MAX_TOKENS", "8192")),
        "rpm": int(os.environ.get("LLM_PROXY_RPM", "600")),
    }


def _check_rate(rpm: int):
    now = time.monotonic()
    with _rate_lock:
        while _recent and now - _recent[0] > 60:
            _recent.popleft()
        if len(_recent) >= rpm:
            raise HTTPException(status_code=429, detail="Workshop model proxy is busy; retry in a few seconds")
        _recent.append(now)


@router.post("/{path:path}")
async def forward(path: str, request: Request):
    cfg = _settings()
    if not (cfg["key"] and cfg["token"]):
        raise HTTPException(status_code=503, detail="Model proxy isn't configured")
    supplied = request.headers.get("x-api-key") or request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    if not hmac.compare_digest(supplied, cfg["token"]):
        raise HTTPException(status_code=401, detail="Invalid proxy token")
    if path.strip("/") != "v1/messages":
        raise HTTPException(status_code=404, detail="Only /v1/messages is proxied")

    try:
        body = json.loads(await request.body())
    except ValueError:
        raise HTTPException(status_code=400, detail="Body must be JSON")
    if body.get("model") not in cfg["models"]:
        raise HTTPException(status_code=400, detail=f"Model not allowed; use one of {sorted(cfg['models'])}")
    body["max_tokens"] = min(int(body.get("max_tokens") or cfg["max_tokens"]), cfg["max_tokens"])
    _check_rate(cfg["rpm"])

    headers = {k: v for k, v in request.headers.items() if k.lower() in FORWARD_HEADERS}
    headers.setdefault("anthropic-version", "2023-06-01")
    headers["x-api-key"] = cfg["key"]
    upstream = requests.post(f"{UPSTREAM}/v1/messages", headers=headers, data=json.dumps(body),
                             stream=bool(body.get("stream")), timeout=300)

    if body.get("stream"):
        return StreamingResponse(upstream.iter_content(chunk_size=None), status_code=upstream.status_code,
                                 media_type=upstream.headers.get("content-type", "text/event-stream"))
    return Response(content=upstream.content, status_code=upstream.status_code,
                    media_type=upstream.headers.get("content-type", "application/json"))
