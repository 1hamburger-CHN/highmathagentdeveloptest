"""Turso/libsql database client — persistent storage for profiles and sessions."""
import logging

import libsql_client

from app.config import settings

logger = logging.getLogger(__name__)

_client: libsql_client.Client | None = None


def get_db() -> libsql_client.Client:
    global _client
    if _client is None:
        _client = libsql_client.create_client(
            url=settings.turso_url,
            auth_token=settings.turso_token or None,
        )
    return _client


def init_db():
    """Create tables if they don't exist."""
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT DEFAULT '',
            profile_json TEXT DEFAULT '{}'
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            messages_json TEXT DEFAULT '[]'
        )
    """)
    # Index for listing sessions by user
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)
    """)
    logger.info("Turso database tables ready")


# --- User / Profile helpers ---

def get_user(user_id: str) -> dict | None:
    db = get_db()
    result = db.execute("SELECT id, name, profile_json FROM users WHERE id = ?", [user_id])
    rows = result.rows
    if not rows:
        return None
    return {"id": rows[0][0], "name": rows[0][1], "profile_json": rows[0][2]}


def upsert_user(user_id: str, profile_json: str):
    db = get_db()
    db.execute(
        "INSERT INTO users (id, profile_json) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET profile_json = excluded.profile_json",
        [user_id, profile_json],
    )


def delete_user(user_id: str):
    db = get_db()
    db.execute("DELETE FROM users WHERE id = ?", [user_id])


# --- Session helpers ---

def get_latest_session(user_id: str) -> dict | None:
    db = get_db()
    result = db.execute(
        "SELECT id, user_id, messages_json FROM sessions WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        [user_id],
    )
    rows = result.rows
    if not rows:
        return None
    return {"id": rows[0][0], "user_id": rows[0][1], "messages_json": rows[0][2]}


def upsert_session(session_id: str, user_id: str, messages_json: str):
    db = get_db()
    db.execute(
        "INSERT INTO sessions (id, user_id, messages_json) VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET messages_json = excluded.messages_json",
        [session_id, user_id, messages_json],
    )


def delete_sessions_for_user(user_id: str) -> int:
    db = get_db()
    result = db.execute("DELETE FROM sessions WHERE user_id = ?", [user_id])
    return result.rows_affected or 0
