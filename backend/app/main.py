import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import assess, chat, generate, path_planner, profile
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("tutor")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting 苏格拉底教练 server...")
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

# Serve frontend static files after API routes
_STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="frontend")
