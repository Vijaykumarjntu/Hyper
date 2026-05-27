"""
memory.py — Chunk page text, embed it, and upsert into Pinecone.
Embeddings: SentenceTransformer (local, no API key needed)
LLM: not needed here — this is pure ingestion
"""

import os
import hashlib

from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

# ── Clients ───────────────────────────────────────────────────────────────────
_pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY", ""))
_model = SentenceTransformer("all-MiniLM-L6-v2")   # local, runs on CPU fine

INDEX_NAME = os.getenv("PINECONE_INDEX", "hyper-memory")
CHUNK_SIZE = 500          # characters per chunk
CHUNK_OVERLAP = 50        # overlap between consecutive chunks
EMBED_DIM = 384           # all-MiniLM-L6-v2 output dimension


def _get_or_create_index():
    existing = [i.name for i in _pc.list_indexes()]
    if INDEX_NAME not in existing:
        _pc.create_index(
            name=INDEX_NAME,
            dimension=EMBED_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    return _pc.Index(INDEX_NAME)


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Sliding-window character-level chunking.
    Simple and deterministic — swap for a sentence splitter if needed.
    """
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return [c.strip() for c in chunks if c.strip()]


def _chunk_id(page_id: str, chunk_index: int, text: str) -> str:
    """Stable, deterministic vector ID."""
    digest = hashlib.md5(text.encode()).hexdigest()[:8]
    return f"{page_id}__chunk{chunk_index}__{digest}"


def _embed(texts: list[str]) -> list[list[float]]:
    """Local embedding — no API call, no cost, no rate limits."""
    embeddings = _model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()


async def upsert_to_pinecone(page_data: dict) -> dict:
    """
    Chunk → embed → upsert.

    Args:
        page_data: output of notion.extract_page_text()

    Returns:
        {"chunks": int}
    """
    index = _get_or_create_index()

    chunks = _chunk_text(page_data["text"])
    if not chunks:
        return {"chunks": 0}

    vectors = []
    batch_size = 64         # SentenceTransformer sweet spot
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        embeddings = _embed(batch)
        for j, (chunk, embedding) in enumerate(zip(batch, embeddings)):
            chunk_idx = i + j
            vectors.append({
                "id": _chunk_id(page_data["page_id"], chunk_idx, chunk),
                "values": embedding,
                "metadata": {
                    "page_id": page_data["page_id"],
                    "title": page_data["title"],
                    "url": page_data["url"],
                    "last_edited": page_data["last_edited"],
                    "chunk_index": chunk_idx,
                    "text": chunk,          # store raw text for retrieval
                },
            })

    # Upsert in batches of 100
    for i in range(0, len(vectors), 100):
        index.upsert(vectors=vectors[i : i + 100])

    return {"chunks": len(vectors)}
