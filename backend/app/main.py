import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import assess, chat, generate, path_planner, profile, sessions
from app.config import settings
from app.models.db_models import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("tutor")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting 苏格拉底教练 server...")
    init_db()
    logger.info(f"Turso database ready at {settings.turso_url}")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="苏格拉底教练 — 多智能体辅导系统",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = uuid4().hex[:8]
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    logger.info(f"[{request_id}] {request.method} {request.url.path} → {response.status_code} ({elapsed:.2f}s)")
    return response


app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
app.include_router(generate.router, prefix="/api/generate", tags=["generate"])
app.include_router(assess.router, prefix="/api/assess", tags=["assess"])
app.include_router(path_planner.router, prefix="/api/path", tags=["path"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])

@app.get("/api/debug/turso")
async def debug_turso():
    """Diagnostic: test Turso connectivity."""
    import os
    import traceback as tb
    from app.config import settings
    from app.models.db_models import _available, _TURSO_HOST, _pipeline

    token_len = len(settings.turso_token) if settings.turso_token else 0
    proxy_vars = {k: os.environ.get(k, "") for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "NO_PROXY", "no_proxy"]}
    try:
        result = _pipeline([{"type": "execute", "stmt": {"sql": "SELECT 1 as test"}}])
        rows = result[0]["result"]["rows"]
        return {
            "turso_host": _TURSO_HOST,
            "token_len": token_len,
            "available": _available,
            "query_result": str(rows),
            "proxy_vars": proxy_vars,
            "status": "ok",
        }
    except Exception as e:
        return {
            "turso_host": _TURSO_HOST,
            "token_len": token_len,
            "available": _available,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": tb.format_exc()[-500:],
            "proxy_vars": proxy_vars,
            "status": "error",
        }

# Serve frontend static files after API routes
_STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="frontend")
