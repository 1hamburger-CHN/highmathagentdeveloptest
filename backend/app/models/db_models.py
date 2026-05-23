"""Database abstraction — Turso via HTTP API with graceful fallback."""
import json
import logging

import requests

from app.config import settings

logger = logging.getLogger(__name__)

_TURSO_HOST = settings.turso_url.replace("libsql://", "https://")
_available = True  # Tables pre-created in Turso; init_db is best-effort


def _pipeline(requests_list: list[dict]) -> list[dict]:
    """Send a batch of SQL statements to Turso via HTTP pipeline API."""
    if not settings.turso_token:
        raise RuntimeError("TURSO_TOKEN is not set")

    url = f"{_TURSO_HOST}/v2/pipeline"
    resp = requests.post(
        url,
        json={"requests": requests_list},
        headers={"Authorization": f"Bearer {settings.turso_token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _execute(sql: str, params: list | None = None) -> dict | None:
    if not _available:
        return None
    stmt: dict = {"sql": sql}
    if params:
        stmt["args"] = [{"type": "text", "value": str(p)} for p in params]
    results = _pipeline([{"type": "execute", "stmt": stmt}])
    return results[0]["result"]


def init_db():
    """Create tables if they don't exist. Non-fatal on failure."""
    global _available
    try:
        _execute_raw("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, name TEXT DEFAULT '', profile_json TEXT DEFAULT '{}')")
        _execute_raw("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, user_id TEXT, messages_json TEXT DEFAULT '[]')")
        _execute_raw("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)")
        _available = True
        logger.info("Turso database ready")
    except Exception as e:
        _available = False
        logger.warning(f"Turso unavailable — running without persistence: {e}")


def _execute_raw(sql: str, params: list | None = None) -> dict:
    stmt: dict = {"sql": sql}
    if params:
        stmt["args"] = [{"type": "text", "value": str(p)} for p in params]
    results = _pipeline([{"type": "execute", "stmt": stmt}])
    return results[0]["result"]


# --- User helpers ---

def get_user(user_id: str) -> dict | None:
    if not _available:
        return None
    try:
        result = _execute("SELECT id, name, profile_json FROM users WHERE id = ?", [user_id])
        rows = result.get("rows", []) if result else []
        if not rows:
            return None
        row = rows[0]
        return {"id": row[0]["value"], "name": row[1]["value"], "profile_json": row[2]["value"]}
    except Exception as e:
        logger.error(f"get_user failed: {e}")
        return None


def upsert_user(user_id: str, profile_json: str):
    if not _available:
        return
    _execute(
        "INSERT INTO users (id, profile_json) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET profile_json = excluded.profile_json",
        [user_id, profile_json],
    )


def delete_user(user_id: str):
    if not _available:
        return
    try:
        _execute("DELETE FROM users WHERE id = ?", [user_id])
    except Exception as e:
        logger.error(f"delete_user failed: {e}")


# --- Session helpers ---

def get_latest_session(user_id: str) -> dict | None:
    if not _available:
        return None
    try:
        result = _execute(
            "SELECT id, user_id, messages_json FROM sessions WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            [user_id],
        )
        rows = result.get("rows", []) if result else []
        if not rows:
            return None
        row = rows[0]
        return {"id": row[0]["value"], "user_id": row[1]["value"], "messages_json": row[2]["value"]}
    except Exception as e:
        logger.error(f"get_latest_session failed: {e}")
        return None


def upsert_session(session_id: str, user_id: str, messages_json: str):
    if not _available:
        return
    _execute(
        "INSERT INTO sessions (id, user_id, messages_json) VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET messages_json = excluded.messages_json",
        [session_id, user_id, messages_json],
    )


def delete_sessions_for_user(user_id: str) -> int:
    if not _available:
        return 0
    try:
        result = _execute("DELETE FROM sessions WHERE user_id = ?", [user_id])
        return result.get("rows_affected", 0) or 0 if result else 0
    except Exception as e:
        logger.error(f"delete_sessions_for_user failed: {e}")
        return 0
