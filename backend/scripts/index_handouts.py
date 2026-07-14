"""Index chapter handouts + exercise PDFs into ChromaDB.

Collections: handouts (by chapter), exercises (by problem type)
"""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.knowledge.embedder import BGEM3Embedder
from app.config import settings
import chromadb
from chromadb.config import Settings as ChromaSettings

HANDOUT_FILES = [
    ("handout_ch1.txt", 1, "复数与复变函数"),
    ("handout_ch2.txt", 2, "解析函数"),
    ("handout_ch3.txt", 3, "复变函数的积分"),
    ("handout_ch4.txt", 4, "级数"),
    ("handout_ch5.txt", 5, "留数"),
]

EXERCISE_FILE = "exercises_xinhuo.txt"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "extracted")
CHUNK_SIZE = 512
OVERLAP = 64


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    chunks = []
    pos = 0
    while pos < len(text):
        end = min(pos + size, len(text))
        chunk = text[pos:end].strip()
        if len(chunk) >= 30:
            chunks.append(chunk)
        pos += size - overlap
    return chunks


def index_handouts(client, embedder):
    print("\n=== Indexing Chapter Handouts ===")
    try:
        client.delete_collection("handouts")
    except Exception:
        pass
    collection = client.create_collection(
        name="handouts", embedding_function=embedder,
        metadata={"description": "哈工大复变函数章节讲义"},
    )
    for filename, chapter, title in HANDOUT_FILES:
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            print(f"  SKIP: {filepath} not found")
            continue
        with open(filepath, encoding="utf-8") as f:
            raw = f.read()
        pages = re.split(r"\[Page \d+\]", raw)
        ids, docs, metas = [], [], []
        for pi, page_text in enumerate(pages):
            page_text = page_text.strip()
            if len(page_text) < 20:
                continue
            for ci, chunk in enumerate(chunk_text(page_text)):
                ids.append(f"ho-ch{chapter}-p{pi+1}-{ci}")
                docs.append(f"第{chapter}章 {title}\n\n{chunk}")
                metas.append({"source": "handout", "chapter": chapter, "chapter_title": title})
        for i in range(0, len(ids), 20):
            b = min(i + 20, len(ids))
            collection.add(ids=ids[i:b], documents=docs[i:b], metadatas=metas[i:b])
        print(f"  Ch{chapter} {title}: {len(ids)} chunks")
    print(f"  Total: {collection.count()}")


def index_exercises(client, embedder):
    print("\n=== Indexing Exercise Book ===")
    filepath = os.path.join(DATA_DIR, EXERCISE_FILE)
    if not os.path.exists(filepath):
        print(f"  SKIP: {filepath} not found")
        return
    try:
        client.delete_collection("exercises")
    except Exception:
        pass
    collection = client.create_collection(
        name="exercises", embedding_function=embedder,
        metadata={"description": "薪火复变综合训练选择填空解析"},
    )
    with open(filepath, encoding="utf-8") as f:
        raw = f.read()
    pages = re.split(r"\[Page \d+\]", raw)
    ids, docs, metas = [], [], []
    page_idx = 0
    for pi, page_text in enumerate(pages):
        page_text = page_text.strip()
        if len(page_text) < 20:
            continue
        page_idx += 1
        for ci, chunk in enumerate(chunk_text(page_text)):
            ids.append(f"ex-p{page_idx}-{ci}")
            ptype = "choice" if any(kw in chunk for kw in ["A.", "B.", "C.", "D."]) else "general"
            docs.append(f"复变函数习题解析\n\n{chunk}")
            metas.append({"source": "exercises", "type": ptype, "page": page_idx})
    for i in range(0, len(ids), 20):
        b = min(i + 20, len(ids))
        collection.add(ids=ids[i:b], documents=docs[i:b], metadatas=metas[i:b])
    print(f"  Total: {collection.count()}")


if __name__ == "__main__":
    embedder = BGEM3Embedder(settings.embedding_model)
    client = chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    index_handouts(client, embedder)
    index_exercises(client, embedder)
    print("\nDone.")
