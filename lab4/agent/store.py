"""
Agent store — Postgres with RLS, or JSON fallback.

When DATABASE_URL is set, concerns are stored in Postgres with Row-Level
Security enforcing provider isolation. Without DATABASE_URL, falls back to
the same flat JSON file used in Labs 1-3 (no RLS, single-user mode).
"""

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

try:
    import psycopg.rows
except ImportError:
    psycopg = None  # Postgres not available — JSON fallback only

from app.models import Concern, RelatedData

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

# ============================================================
# Postgres backend
# ============================================================

_pool = None


def _get_pool():
    """Lazy-init the connection pool."""
    global _pool
    if _pool is None:
        from psycopg_pool import ConnectionPool
        _pool = ConnectionPool(DATABASE_URL, min_size=2, max_size=10)
    return _pool


def _row_to_concern(row: dict) -> Concern:
    """Convert a database row dict to a Concern model."""
    return Concern(
        id=row["id"],
        patient_id=row["patient_id"],
        title=row["title"],
        summary=row["summary"],
        action=row["action"] or "",
        concern_type=row["concern_type"],
        urgency=row["urgency"],
        status=row["status"],
        onset=row["onset"],
        last_updated=str(row["last_updated"]),
        evidence=row["evidence"] or [],
        related=RelatedData(
            message_ids=row["related_message_ids"] or [],
            lab_dates=row["related_lab_dates"] or [],
            conditions=row["related_conditions"] or [],
            encounter_dates=row["related_encounter_dates"] or [],
        ),
    )


def _pg_get_concerns(patient_id: str, provider_id: str) -> list[Concern]:
    """Fetch concerns visible to this provider for this patient."""
    pool = _get_pool()
    with pool.connection() as conn:
        conn.execute("SELECT set_config('app.provider_id', %s, true)", (provider_id,))
        conn.row_factory = psycopg.rows.dict_row
        rows = conn.execute(
            "SELECT * FROM concerns WHERE patient_id = %s ORDER BY last_updated DESC",
            (patient_id,),
        ).fetchall()
        return [_row_to_concern(row) for row in rows]


def _pg_save_concerns(
    patient_id: str, provider_id: str, concerns: list[Concern]
) -> None:
    """Upsert concerns: update existing IDs, insert new ones, leave others untouched."""
    pool = _get_pool()
    with pool.connection() as conn:
        conn.execute("SELECT set_config('app.provider_id', %s, true)", (provider_id,))
        for c in concerns:
            conn.execute(
                """
                INSERT INTO concerns (
                    id, patient_id, provider_id, title, summary, action,
                    concern_type, urgency, status, onset, last_updated,
                    evidence, related_message_ids, related_lab_dates,
                    related_conditions, related_encounter_dates
                ) VALUES (
                    %(id)s, %(patient_id)s, %(provider_id)s, %(title)s,
                    %(summary)s, %(action)s, %(concern_type)s, %(urgency)s,
                    %(status)s, %(onset)s, %(last_updated)s, %(evidence)s,
                    %(related_message_ids)s, %(related_lab_dates)s,
                    %(related_conditions)s, %(related_encounter_dates)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    summary = EXCLUDED.summary,
                    action = EXCLUDED.action,
                    concern_type = EXCLUDED.concern_type,
                    urgency = EXCLUDED.urgency,
                    status = EXCLUDED.status,
                    onset = EXCLUDED.onset,
                    last_updated = EXCLUDED.last_updated,
                    evidence = EXCLUDED.evidence,
                    related_message_ids = EXCLUDED.related_message_ids,
                    related_lab_dates = EXCLUDED.related_lab_dates,
                    related_conditions = EXCLUDED.related_conditions,
                    related_encounter_dates = EXCLUDED.related_encounter_dates
                """,
                {
                    "id": c.id,
                    "patient_id": patient_id,
                    "provider_id": provider_id,
                    "title": c.title,
                    "summary": c.summary,
                    "action": c.action,
                    "concern_type": c.concern_type,
                    "urgency": c.urgency,
                    "status": c.status,
                    "onset": c.onset,
                    "last_updated": c.last_updated,
                    "evidence": c.evidence,
                    "related_message_ids": c.related.message_ids,
                    "related_lab_dates": c.related.lab_dates,
                    "related_conditions": c.related.conditions,
                    "related_encounter_dates": c.related.encounter_dates,
                },
            )


def _pg_resolve_concern(patient_id: str, concern_id: str, provider_id: str) -> bool:
    """Mark a concern as resolved. RLS ensures you can only resolve your own or shared."""
    pool = _get_pool()
    with pool.connection() as conn:
        conn.execute("SELECT set_config('app.provider_id', %s, true)", (provider_id,))
        result = conn.execute(
            "UPDATE concerns SET status = 'resolved' WHERE id = %s AND patient_id = %s",
            (concern_id, patient_id),
        )
        return result.rowcount > 0


def _pg_share_concern(concern_id: str, shared_with: str, shared_by: str) -> bool:
    """Share a concern with another provider."""
    pool = _get_pool()
    with pool.connection() as conn:
        conn.execute("SELECT set_config('app.provider_id', %s, true)", (shared_by,))
        conn.execute(
            """
            INSERT INTO shared_concerns (concern_id, shared_with, shared_by)
            VALUES (%s, %s, %s)
            ON CONFLICT (concern_id, shared_with) DO NOTHING
            """,
            (concern_id, shared_with, shared_by),
        )
        return True


def _pg_get_providers() -> list[dict]:
    """Get all providers (for the role switcher)."""
    pool = _get_pool()
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT id, display_name, role FROM providers ORDER BY role, display_name"
        ).fetchall()
        return [{"id": r[0], "display_name": r[1], "role": r[2]} for r in rows]


def _pg_get_provider_patients(provider_id: str) -> list[str]:
    """Get the patient IDs this provider is authorized for."""
    pool = _get_pool()
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT patient_id FROM provider_patients WHERE provider_id = %s ORDER BY patient_id",
            (provider_id,),
        ).fetchall()
        return [r[0] for r in rows]


def _pg_get_shared_by(concern_id: str, provider_id: str) -> str | None:
    """If this concern was shared with the provider, return who shared it."""
    pool = _get_pool()
    with pool.connection() as conn:
        conn.execute("SELECT set_config('app.provider_id', %s, true)", (provider_id,))
        row = conn.execute(
            "SELECT p.display_name FROM shared_concerns sc "
            "JOIN providers p ON sc.shared_by = p.id "
            "WHERE sc.concern_id = %s AND sc.shared_with = %s",
            (concern_id, provider_id),
        ).fetchone()
        return row[0] if row else None


# ============================================================
# JSON fallback (same as Labs 1-3, plus upsert for stability)
# ============================================================

STORE_PATH = Path(os.environ.get("AGENT_STORE", "data/agent_output.json"))


def _json_load_store() -> dict:
    if not STORE_PATH.exists():
        return {"patients": {}, "last_run": ""}
    with open(STORE_PATH) as f:
        return json.load(f)


def _json_save_store(store: dict):
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w") as f:
        json.dump(store, f, indent=2)


def _json_get_concerns(patient_id: str, provider_id: str) -> list[Concern]:
    store = _json_load_store()
    patient_data = store.get("patients", {}).get(patient_id)
    if patient_data is None:
        return []
    return [Concern.model_validate(c) for c in patient_data.get("concerns", [])]


def _json_save_concerns(
    patient_id: str, provider_id: str, concerns: list[Concern]
) -> None:
    store = _json_load_store()
    patients = store.setdefault("patients", {})
    existing = patients.get(patient_id, {"patient_id": patient_id, "concerns": []})

    existing_by_id = {c["id"]: c for c in existing.get("concerns", [])}
    for c in concerns:
        existing_by_id[c.id] = c.model_dump()

    existing["concerns"] = list(existing_by_id.values())
    patients[patient_id] = existing
    _json_save_store(store)


def _json_resolve_concern(patient_id: str, concern_id: str, provider_id: str) -> bool:
    store = _json_load_store()
    patient_data = store.get("patients", {}).get(patient_id)
    if patient_data is None:
        return False
    for c in patient_data.get("concerns", []):
        if c["id"] == concern_id:
            c["status"] = "resolved"
            _json_save_store(store)
            return True
    return False


# ============================================================
# Public API — delegates to Postgres or JSON
# ============================================================


def get_concerns(patient_id: str, provider_id: str) -> list[Concern]:
    """Get concerns visible to this provider for this patient."""
    if DATABASE_URL:
        return _pg_get_concerns(patient_id, provider_id)
    return _json_get_concerns(patient_id, provider_id)


def save_concerns(
    patient_id: str, provider_id: str, concerns: list[Concern]
) -> None:
    """Upsert concerns: update existing IDs, insert new, leave unmentioned untouched."""
    if DATABASE_URL:
        _pg_save_concerns(patient_id, provider_id, concerns)
    else:
        _json_save_concerns(patient_id, provider_id, concerns)


def resolve_concern(patient_id: str, concern_id: str, provider_id: str) -> bool:
    """Mark a concern as resolved."""
    if DATABASE_URL:
        return _pg_resolve_concern(patient_id, concern_id, provider_id)
    return _json_resolve_concern(patient_id, concern_id, provider_id)


def share_concern(concern_id: str, shared_with: str, shared_by: str) -> bool:
    """Share a concern with another provider. Only available with Postgres."""
    if not DATABASE_URL:
        logger.warning("Sharing not available without Postgres")
        return False
    return _pg_share_concern(concern_id, shared_with, shared_by)


def get_providers() -> list[dict]:
    """Get all providers. Returns empty list without Postgres."""
    if DATABASE_URL:
        return _pg_get_providers()
    return []


def get_provider_patients(provider_id: str) -> list[str]:
    """Get patient IDs this provider can access. Returns empty list without Postgres."""
    if DATABASE_URL:
        return _pg_get_provider_patients(provider_id)
    return []


def get_shared_by(concern_id: str, provider_id: str) -> str | None:
    """If this concern was shared with the provider, return who shared it."""
    if DATABASE_URL:
        return _pg_get_shared_by(concern_id, provider_id)
    return None


def using_postgres() -> bool:
    """Check if the Postgres backend is active."""
    return DATABASE_URL is not None
