"""Reset the Lab 4 Postgres database to a clean state for demos.

Truncates agent-generated data (concerns, shared_concerns, agent_runs)
while preserving provider and patient configuration.

Connects as the database owner (not app_user) so RLS doesn't interfere.

Usage:  uv run reset-db
"""

import os
import sys
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv


def _owner_url(database_url: str) -> str:
    """Rewrite DATABASE_URL to use the db owner (agent) instead of app_user."""
    parsed = urlparse(database_url)
    if parsed.username == "app_user":
        replaced = parsed._replace(
            netloc=f"agent:agent_dev@{parsed.hostname}:{parsed.port}"
        )
        return urlunparse(replaced)
    return database_url


def main():
    load_dotenv()

    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        print("DATABASE_URL is not set. Nothing to reset.")
        sys.exit(0)

    try:
        import psycopg
    except ImportError:
        print("psycopg is not installed. Run: uv sync --all-extras")
        sys.exit(1)

    owner_url = _owner_url(database_url)
    with psycopg.connect(owner_url) as conn:
        conn.execute("TRUNCATE concerns, shared_concerns")
        print("Done. Cleared all concerns and shares.")
