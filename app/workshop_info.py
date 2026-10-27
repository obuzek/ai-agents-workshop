"""
Day-of workshop details the docs show, without putting them in the repo.

The values (e.g. the backup IBM Bob access link and code) live only in this
server's environment. GET /workshop/bob-access returns them until
WORKSHOP_INFO_EXPIRES, then answers 400, and the docs hide the section.

Environment (server mode only):
    BOB_ACCESS_URL, BOB_ACCESS_CODE   the values to show
    WORKSHOP_INFO_EXPIRES             ISO 8601 timestamp, e.g. 2026-10-28T04:00:00Z
    WORKSHOP_INFO_ORIGINS             comma-separated origins allowed to read it (CORS)
"""

import os
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/workshop")
DEFAULT_ORIGINS = "https://obuzek.github.io,http://127.0.0.1:8004,http://localhost:8004"


def _cors(request: Request) -> dict:
    origin = request.headers.get("origin", "")
    allowed = {o.strip() for o in os.environ.get("WORKSHOP_INFO_ORIGINS", DEFAULT_ORIGINS).split(",") if o.strip()}
    headers = {"Cache-Control": "no-store"}
    if origin in allowed:
        headers.update({"Access-Control-Allow-Origin": origin, "Vary": "Origin"})
    return headers


def _expired() -> bool:
    expires = os.environ.get("WORKSHOP_INFO_EXPIRES", "")
    try:
        return datetime.now(timezone.utc) >= datetime.fromisoformat(expires.replace("Z", "+00:00"))
    except ValueError:
        return True  # no valid expiry configured: never serve


@router.get("/bob-access")
def bob_access(request: Request):
    url, code = os.environ.get("BOB_ACCESS_URL", ""), os.environ.get("BOB_ACCESS_CODE", "")
    if not (url and code) or _expired():
        return JSONResponse(status_code=400, content={"detail": "Not available"}, headers=_cors(request))
    return JSONResponse(content={"url": url, "code": code}, headers=_cors(request))


@router.get("/model-access")
def model_access(request: Request):
    """How to register the workshop model in Orchestrate (used by lab1/agent/deploy.py).

    Returns the model name, the proxy URL to use as its custom_host, and the proxy
    token for its connection. Like /bob-access, it stops answering after
    WORKSHOP_INFO_EXPIRES.
    """
    token = os.environ.get("LLM_PROXY_TOKEN", "")
    if not token or _expired():
        return JSONResponse(status_code=400, content={"detail": "Not available"}, headers=_cors(request))
    base = os.environ.get("PUBLIC_URL", "").rstrip("/") or f"https://{request.url.netloc}"
    return JSONResponse(content={
        "model": os.environ.get("WORKSHOP_MODEL", "anthropic/claude-sonnet-5-5"),
        "custom_host": f"{base}/llm/anthropic/v1",
        "api_key": token,
    }, headers={"Cache-Control": "no-store"})
