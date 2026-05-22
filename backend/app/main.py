from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import assess, chat, generate, path_planner, profile
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Init ChromaDB, load KB, warm up model connections
    yield


app = FastAPI(
    title="苏格拉底教练 — 多智能体辅导系统",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
app.include_router(generate.router, prefix="/api/generate", tags=["generate"])
app.include_router(assess.router, prefix="/api/assess", tags=["assess"])
app.include_router(path_planner.router, prefix="/api/path", tags=["path"])
