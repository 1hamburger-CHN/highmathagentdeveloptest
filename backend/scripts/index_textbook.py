"""Index OCR'd textbook into ChromaDB 'textbook' collection.

Usage: python scripts/index_textbook.py [--textbook-path PATH]
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.knowledge.textbook_loader import load_textbook
from app.knowledge.embedder import BGEM3Embedder
from app.config import settings
import chromadb
from chromadb.config import Settings as ChromaSettings


def index_textbook(textbook_path: str):
    print(f"Loading textbook from: {textbook_path}")
    chunks = load_textbook(textbook_path)

    if not chunks:
        print("No chunks found — is the OCR complete?")
        return

    print(f"Indexing {len(chunks)} chunks into ChromaDB...")

    embedder = BGEM3Embedder(settings.embedding_model)
    client = chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )

    try:
        client.delete_collection("textbook")
        print("Deleted existing 'textbook' collection")
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
        print(f"Indexed chunks {i}-{batch_end - 1}/{len(chunks)}")

    print(f"Done. Collection count: {collection.count()}")

    print("\n--- Quick retrieval test ---")
    results = collection.query(query_texts=["留数定理如何计算实积分"], n_results=2)
    for i, (ids, docs) in enumerate(zip(results["ids"][0], results["documents"][0])):
        print(f"  [{ids}] {docs[:200] if docs else '(empty)'}...")


if __name__ == "__main__":
    default_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "hit_textbook_full.txt"
    )
    path = sys.argv[1] if len(sys.argv) > 1 else default_path
    index_textbook(path)
