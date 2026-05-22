"""Index knowledge nodes from curriculum.yaml into ChromaDB."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.knowledge.loader import load_curriculum
from app.knowledge.chunker import latex_aware_split
from app.knowledge.embedder import BGEM3Embedder
from app.config import settings
import chromadb
from chromadb.config import Settings as ChromaSettings


def index_knowledge_base(curriculum_path: str):
    print(f"Loading curriculum from: {curriculum_path}")
    nodes = load_curriculum(curriculum_path)
    print(f"Loaded {len(nodes)} knowledge nodes")

    # Prepare chunks with metadata
    chunks = []
    metadatas = []
    ids = []

    for node in nodes:
        text = node.to_chunk_text()
        # Split long nodes into overlapping chunks
        sub_chunks = latex_aware_split(text, chunk_size=512, overlap=64)
        for i, chunk in enumerate(sub_chunks):
            chunk_id = f"{node.id}_{i}" if len(sub_chunks) > 1 else node.id
            chunks.append(chunk)
            ids.append(chunk_id)
            metadatas.append({
                "node_id": node.id,
                "title": node.title,
                "difficulty": node.difficulty,
                "bloom_level": node.bloom_level,
                "prerequisites": ",".join(node.prerequisites),
                "related": ",".join(node.related),
            })

    print(f"Created {len(chunks)} chunks from {len(nodes)} nodes")

    # Initialize ChromaDB with BGE-M3 embedder
    embedder = BGEM3Embedder(settings.embedding_model)

    client = chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )

    # Recreate collection (idempotent: delete if exists, then create)
    try:
        client.delete_collection("limits_continuity")
        print("Deleted existing collection 'limits_continuity'")
    except Exception:
        pass

    collection = client.create_collection(
        name="limits_continuity",
        embedding_function=embedder,
        metadata={"description": "高等数学极限与连续知识库"},
    )

    # Batch add chunks
    batch_size = 10
    for i in range(0, len(chunks), batch_size):
        batch_end = min(i + batch_size, len(chunks))
        collection.add(
            ids=ids[i:batch_end],
            documents=chunks[i:batch_end],
            metadatas=metadatas[i:batch_end],
        )
        print(f"Indexed chunks {i}-{batch_end - 1}/{len(chunks)}")

    print(f"Done. Collection count: {collection.count()}")


def test_retrieval(query: str = "等价无穷小替换什么时候不能用"):
    """Quick retrieval test."""
    from app.knowledge.retriever import HybridRetriever

    retriever = HybridRetriever()
    results = retriever.search(query, top_k=3)

    print(f"\nQuery: {query}")
    print("-" * 50)
    for r in results:
        print(f"[{r['id']}] score={r['score']:.3f}")
        print(r["content"][:200])
        print("-" * 30)


if __name__ == "__main__":
    curriculum_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "seed", "curriculum.yaml"
    )
    index_knowledge_base(curriculum_path)
    test_retrieval()
    test_retrieval("ε-δ语言是什么")
    test_retrieval("sin x / x 的极限")
