import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import animation, assess, chat, generate, path_planner, profile, sessions
from app.config import settings
from app.models.db_models import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("tutor")


def ensure_knowledge_base_indexed():
    """Auto-index knowledge base if ChromaDB collection is empty or missing."""
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        from app.knowledge.embedder import BGEM3Embedder

        client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        embedder = BGEM3Embedder(settings.embedding_model)
        collection = client.get_or_create_collection(
            name="complex_analysis",
            embedding_function=embedder,
        )
        if collection.count() == 0:
            logger.info("ChromaDB collection empty, indexing knowledge base...")
            from app.knowledge.loader import load_curriculum
            from app.knowledge.chunker import latex_aware_split

            curriculum_path = Path(__file__).parent.parent / "data" / "seed" / "curriculum.yaml"
            nodes = load_curriculum(str(curriculum_path))
            chunks, metadatas, ids = [], [], []
            for node in nodes:
                text = node.to_chunk_text()
                sub_chunks = latex_aware_split(text, chunk_size=512, overlap=64)
                for i, chunk in enumerate(sub_chunks):
                    chunk_id = f"{node.id}_{i}" if len(sub_chunks) > 1 else node.id
                    chunks.append(chunk)
                    ids.append(chunk_id)
                    metadatas.append({
                        "node_id": node.id, "title": node.title,
                        "difficulty": node.difficulty, "bloom_level": node.bloom_level,
                        "prerequisites": ",".join(node.prerequisites),
                        "related": ",".join(node.related),
                    })
            batch_size = 10
            for i in range(0, len(chunks), batch_size):
                batch_end = min(i + batch_size, len(chunks))
                collection.add(ids=ids[i:batch_end], documents=chunks[i:batch_end], metadatas=metadatas[i:batch_end])
            logger.info(f"Knowledge base indexed: {collection.count()} chunks from {len(nodes)} nodes")
        else:
            logger.info(f"Knowledge base already indexed: {collection.count()} chunks")
    except Exception:
        logger.exception("Failed to index knowledge base, continuing without KB retrieval")


def ensure_textbook_indexed():
    """Auto-index OCR'd textbook if ChromaDB 'textbook' collection is empty or missing."""
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        from app.knowledge.embedder import BGEM3Embedder

        client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        embedder = BGEM3Embedder(settings.embedding_model)

        try:
            collection = client.get_collection(name="textbook", embedding_function=embedder)
            if collection.count() > 0:
                logger.info(f"Textbook already indexed: {collection.count()} chunks")
                return
        except Exception:
            pass

        textbook_path = Path(__file__).parent.parent / "data" / "hit_textbook_full.txt"
        if not textbook_path.exists():
            logger.info("Textbook OCR file not found, skipping textbook index")
            return

        logger.info("Indexing textbook into ChromaDB...")
        from app.knowledge.textbook_loader import load_textbook

        chunks = load_textbook(str(textbook_path))
        if not chunks:
            logger.info("No textbook chunks extracted (OCR may be incomplete)")
            return

        try:
            client.delete_collection("textbook")
        except Exception:
            pass
        collection = client.create_collection(
            name="textbook",
            embedding_function=embedder,
            metadata={"description": "哈工大复变函数与积分变换教材"},
        )

        batch_size = 20
        for i in range(0, len(chunks), batch_size):
            batch_end = min(i + batch_size, len(chunks))
            batch = chunks[i:batch_end]
            collection.add(
                ids=[c.id for c in batch],
                documents=[c.to_searchable_text() for c in batch],
                metadatas=[c.to_metadata() for c in batch],
            )
        logger.info(f"Textbook indexed: {collection.count()} chunks from {len(chunks)} raw chunks")
    except Exception:
        logger.exception("Failed to index textbook, continuing without textbook retrieval")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting 苏格拉底教练 server...")
    init_db()
    logger.info(f"Turso database ready at {settings.turso_url}")
    import asyncio
    asyncio.get_running_loop().run_in_executor(None, ensure_knowledge_base_indexed)
    asyncio.get_running_loop().run_in_executor(None, ensure_textbook_indexed)
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="苏格拉底教练 2.0 — 多智能体复变函数辅导系统",
    version="2.0.0",
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


@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.endswith(".mp4"):
        response.headers["Cache-Control"] = "public, max-age=86400"
    return response


app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
app.include_router(generate.router, prefix="/api/generate", tags=["generate"])
app.include_router(assess.router, prefix="/api/assess", tags=["assess"])
app.include_router(path_planner.router, prefix="/api/path", tags=["path"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(animation.router, prefix="/api/animation", tags=["animation"])

# Serve frontend static files after API routes
_STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="frontend")
