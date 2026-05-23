"""Turso database client via HTTP API — persistent storage for profiles and sessions."""
import json
import logging
from urllib.request import Request, urlopen
from urllib.error import URLError

from app.config import settings

logger = logging.getLogger(__name__)

# Turso HTTP API base URL (strip libsql:// prefix, use https://)
_TURSO_HOST = settings.turso_url.replace("libsql://", "https://")


def _pipeline(requests: list[dict]) -> list[dict]:
    """Send a batch of SQL statements to Turso via HTTP pipeline API."""
    if not settings.turso_token:
        raise RuntimeError("TURSO_TOKEN is not set")

    url = f"{_TURSO_HOST}/v2/pipeline"
    body = json.dumps({"requests": requests}).encode("utf-8")
    req = Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {settings.turso_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except URLError as e:
        logger.error(f"Turso API error: {e}")
        raise


def _execute(sql: str, params: list | None = None) -> dict:
    """Execute a single SQL statement with optional parameters."""
    stmt: dict = {"sql": sql}
    if params:
        stmt["args"] = [{"type": "text", "value": str(p)} for p in params]

    results = _pipeline([{"type": "execute", "stmt": stmt}])
    return results[0]["result"]


def init_db():
    """Create tables if they don't exist."""
    _execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, name TEXT DEFAULT '', profile_json TEXT DEFAULT '{}')")
    _execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, user_id TEXT, messages_json TEXT DEFAULT '[]')")
    _execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)")
    logger.info("Turso database tables ready")


# --- User / Profile helpers ---

def get_user(user_id: str) -> dict | None:
    result = _execute("SELECT id, name, profile_json FROM users WHERE id = ?", [user_id])
    rows = result.get("rows", [])
    if not rows:
        return None
    row = rows[0]
    return {"id": row[0]["value"], "name": row[1]["value"], "profile_json": row[2]["value"]}


def upsert_user(user_id: str, profile_json: str):
    _execute(
        "INSERT INTO users (id, profile_json) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET profile_json = excluded.profile_json",
        [user_id, profile_json],
    )


def delete_user(user_id: str):
    _execute("DELETE FROM users WHERE id = ?", [user_id])


# --- Session helpers ---

def get_latest_session(user_id: str) -> dict | None:
    result = _execute(
        "SELECT id, user_id, messages_json FROM sessions WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        [user_id],
    )
    rows = result.get("rows", [])
    if not rows:
        return None
    row = rows[0]
    return {"id": row[0]["value"], "user_id": row[1]["value"], "messages_json": row[2]["value"]}


def upsert_session(session_id: str, user_id: str, messages_json: str):
    _execute(
        "INSERT INTO sessions (id, user_id, messages_json) VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET messages_json = excluded.messages_json",
        [session_id, user_id, messages_json],
    )


def delete_sessions_for_user(user_id: str) -> int:
    result = _execute("DELETE FROM sessions WHERE user_id = ?", [user_id])
    return result.get("rows_affected", 0) or 0
