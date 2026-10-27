"""
A small pass-through proxy to Anthropic's API, served by the shared workshop EHR.

watsonx Orchestrate registers the model as an Anthropic model whose host is this
proxy (the model's `custom_host`). Orchestrate sends requests here with the
workshop proxy token as its API key; the proxy checks the token, swaps in the
real Anthropic key, and forwards the request. The real key lives only in this
server's environment, so it never reaches attendees' machines or Orchestrate.

Configure with environment variables (server mode only):
    ANTHROPIC_API_KEY       the real key
    LLM_PROXY_TOKEN         what Orchestrate's model connection sends as its API key
    LLM_PROXY_MODELS        comma-separated allowlist (default: claude-sonnet-5-5,claude-haiku-5-5)
    LLM_PROXY_MAX_TOKENS    cap on max_tokens per request (default 8192)
    LLM_PROXY_RPM           requests per minute across the proxy (default 600)
    LLM_PROXY_CONCURRENCY   model calls in flight at once; more wait their turn (default 64)

Model calls take 30-90 s. Each one runs on this module's own thread pool, so
they never block the event loop or use up the threads the EHR endpoints run on.
Errors are returned in Anthropic's error format so the caller's retry logic works.
"""

import asyncio
import hmac
import json
import logging
import os
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import requests
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

logger = logging.getLogger(__name__)

UPSTREAM = "https://api.anthropic.com"
# Headers we pass through to Anthropic; everything else (including the caller's key) is dropped.
FORWARD_HEADERS = {"content-type", "anthropic-version", "anthropic-beta", "accept"}
# Response headers passed back, so the caller can see why a call failed and when to retry.
RETURN_HEADERS = {"retry-after", "request-id", "x-should-retry"}
UPSTREAM_TIMEOUT = (10, 300)  # (connect, read between bytes) seconds

router = APIRouter(prefix="/llm/anthropic")
_recent: deque[float] = deque()
_rate_lock = threading.Lock()
_pool = ThreadPoolExecutor(max_workers=int(os.environ.get("LLM_PROXY_CONCURRENCY", "64")),
                           thread_name_prefix="llm-proxy")


def _settings() -> dict:
    return {
        "key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "token": os.environ.get("LLM_PROXY_TOKEN", ""),
        "models": {m.strip() for m in os.environ.get("LLM_PROXY_MODELS", "claude-sonnet-5-5,claude-haiku-5-5").split(",") if m.strip()},
        "max_tokens": int(os.environ.get("LLM_PROXY_MAX_TOKENS", "8192")),
        "rpm": int(os.environ.get("LLM_PROXY_RPM", "600")),
    }


def configured() -> bool:
    """Whether the proxy has its key and token (for /health; never the values)."""
    cfg = _settings()
    return bool(cfg["key"] and cfg["token"])


def _error(status: int, kind: str, message: str, headers: dict | None = None) -> JSONResponse:
    """An error in Anthropic's format, which Anthropic clients know how to read and retry."""
    return JSONResponse(status_code=status, headers=headers,
                        content={"type": "error", "error": {"type": kind, "message": message}})


def _rate_ok(rpm: int) -> bool:
    now = time.monotonic()
    with _rate_lock:
        while _recent and now - _recent[0] > 60:
            _recent.popleft()
        if len(_recent) >= rpm:
            return False
        _recent.append(now)
        return True


def _response_headers(upstream) -> dict:
    return {k: v for k, v in upstream.headers.items() if k.lower() in RETURN_HEADERS}


async def _relay(upstream):
    """Yield the upstream stream's chunks, reading each on the proxy's thread pool."""
    loop = asyncio.get_running_loop()
    chunks = upstream.iter_content(chunk_size=None)
    try:
        while (chunk := await loop.run_in_executor(_pool, next, chunks, None)) is not None:
            yield chunk
    except requests.RequestException as e:
        # Headers are already sent, so report the failure as an SSE error event.
        logger.warning("Model stream from Anthropic broke off: %s", type(e).__name__)
        error = {"type": "error", "error": {"type": "api_error", "message": "Upstream stream interrupted"}}
        yield f"event: error\ndata: {json.dumps(error)}\n\n".encode()
    finally:
        upstream.close()


@router.post("/{path:path}")
async def forward(path: str, request: Request):
    cfg = _settings()
    if not (cfg["key"] and cfg["token"]):
        return _error(503, "api_error", "Model proxy isn't configured")
    supplied = request.headers.get("x-api-key") or request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    if not hmac.compare_digest(supplied.encode(), cfg["token"].encode()):
        return _error(401, "authentication_error", "Invalid proxy token")
    if path.strip("/") != "v1/messages":
        return _error(404, "not_found_error", "Only /v1/messages is proxied")

    try:
        body = json.loads(await request.body())
        if not isinstance(body, dict):
            raise ValueError
        requested = body.get("max_tokens") or cfg["max_tokens"]
        if isinstance(requested, bool) or not isinstance(requested, int):
            raise ValueError
    except ValueError:
        return _error(400, "invalid_request_error", "Body must be a JSON object with an integer max_tokens")
    if body.get("model") not in cfg["models"]:
        return _error(400, "invalid_request_error", f"Model not allowed; use one of {sorted(cfg['models'])}")
    body["max_tokens"] = min(requested, cfg["max_tokens"])
    if not _rate_ok(cfg["rpm"]):
        return _error(429, "rate_limit_error", "Workshop model proxy is busy; retry in a few seconds",
                      headers={"retry-after": "5"})

    headers = {k: v for k, v in request.headers.items() if k.lower() in FORWARD_HEADERS}
    headers.setdefault("anthropic-version", "2023-06-01")
    headers["x-api-key"] = cfg["key"]
    stream = bool(body.get("stream"))

    def call():
        return requests.post(f"{UPSTREAM}/v1/messages", headers=headers, data=json.dumps(body),
                             stream=stream, timeout=UPSTREAM_TIMEOUT)

    try:
        upstream = await asyncio.get_running_loop().run_in_executor(_pool, call)
    except requests.Timeout:
        logger.warning("Model call to Anthropic timed out")
        return _error(504, "timeout_error", "Anthropic didn't answer in time")
    except requests.RequestException as e:
        logger.warning("Model call to Anthropic failed: %s", type(e).__name__)
        return _error(502, "api_error", "Couldn't reach Anthropic")

    if upstream.status_code >= 400:
        logger.warning("Anthropic answered %s (request-id %s)", upstream.status_code, upstream.headers.get("request-id", "-"))
    media_type = upstream.headers.get("content-type", "text/event-stream" if stream else "application/json")
    if stream and upstream.status_code < 400:
        return StreamingResponse(_relay(upstream), status_code=upstream.status_code,
                                 media_type=media_type, headers=_response_headers(upstream))
    try:
        content = await asyncio.get_running_loop().run_in_executor(_pool, lambda: upstream.content)
    except requests.RequestException as e:
        logger.warning("Reading Anthropic's answer failed: %s", type(e).__name__)
        return _error(502, "api_error", "Anthropic's answer was cut off")
    finally:
        upstream.close()
    return Response(content=content, status_code=upstream.status_code, media_type=media_type,
                    headers=_response_headers(upstream))
