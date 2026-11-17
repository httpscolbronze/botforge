
"""
rag.py — RAG pipeline for BotForge.

Handles PDF/URL ingestion, chunking, embedding and FAISS retrieval.
Each bot gets its own isolated vector store.
"""

import re
import pickle
import threading
from pathlib import Path
from urllib.parse import urlparse

import faiss
import numpy as np
import requests

from sentence_transformers import SentenceTransformer


# ── Configuration ──────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
VECTOR_DIR = BASE_DIR / "vector_stores"
VECTOR_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "all-MiniLM-L6-v2"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

EMBED_MODEL = None
MODEL_LOCK = threading.Lock()


def _get_model():
    """Load the embedding model only when first needed."""

    global EMBED_MODEL

    if EMBED_MODEL is None:
        with MODEL_LOCK:
            if EMBED_MODEL is None:
                EMBED_MODEL = SentenceTransformer(MODEL_NAME)

    return EMBED_MODEL


def _get_store_dir(bot_id: str) -> Path:
    """Return a safe vector-store directory for a bot."""

    if not isinstance(bot_id, str) or not re.fullmatch(
        r"[a-zA-Z0-9_-]{1,64}", bot_id
    ):
        raise ValueError("Invalid bot ID")

    return VECTOR_DIR / bot_id


# ── Text extraction ────────────────────────────────────────────

def _extract_pdf(path: str) -> str:
    """Extract text from a PDF."""

    import pymupdf

    with pymupdf.open(path) as doc:
        return "\n".join(
            page.get_text() for page in doc
        )


def _extract_url(url: str) -> str:
    """Extract readable text from a webpage."""

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Please provide a valid HTTP or HTTPS URL")

    response = requests.get(
        url,
        timeout=15,
        headers={
            "User-Agent": "BotForge/1.0"
        }
    )

    response.raise_for_status()

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup([
        "script",
        "style",
        "nav",
        "footer",
        "header"
    ]):
        tag.decompose()

    return soup.get_text(separator="\n", strip=True)


# ── Chunking ───────────────────────────────────────────────────

def _chunk(text: str) -> list[str]:
    """Split text into overlapping word-based chunks."""

    words = text.split()

    if not words:
        return []

    chunks = []
    step = CHUNK_SIZE - CHUNK_OVERLAP

    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + CHUNK_SIZE]).strip()

        if len(chunk) > 50:
            chunks.append(chunk)

    return chunks


# ── Ingestion ──────────────────────────────────────────────────

def ingest_pdf(path: str, bot_id: str):
    """Extract and index a PDF for a bot."""

    text = _extract_pdf(path)
    _build_index(text, bot_id)


def ingest_url(url: str, bot_id: str):
    """Extract and index a webpage for a bot."""

    text = _extract_url(url)
    _build_index(text, bot_id)


def _build_index(text: str, bot_id: str):
    """Generate embeddings and save a FAISS index."""

    chunks = _chunk(text)

    if not chunks:
        raise ValueError("No usable text found in the document")

    model = _get_model()

    embeddings = model.encode(
        chunks,
        show_progress_bar=False,
        convert_to_numpy=True
    )

    embeddings = np.asarray(
        embeddings,
        dtype=np.float32
    )

    if not np.isfinite(embeddings).all():
        raise ValueError("Invalid embedding values generated")

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    store_dir = _get_store_dir(bot_id)
    store_dir.mkdir(parents=True, exist_ok=True)

    faiss.write_index(
        index,
        str(store_dir / "index.faiss")
    )

    with open(store_dir / "chunks.pkl", "wb") as f:
        pickle.dump(chunks, f)


# ── Retrieval ──────────────────────────────────────────────────

def retrieve(
    query: str,
    bot_id: str,
    top_k: int = 3
) -> str:
    """Retrieve the most relevant document chunks."""

    if not isinstance(query, str) or not query.strip():
        return ""

    if top_k <= 0:
        return ""

    store_dir = _get_store_dir(bot_id)

    index_path = store_dir / "index.faiss"
    chunks_path = store_dir / "chunks.pkl"

    if not index_path.exists() or not chunks_path.exists():
        return ""

    index = faiss.read_index(str(index_path))

    with open(chunks_path, "rb") as f:
        chunks = pickle.load(f)

    if not chunks or index.ntotal == 0:
        return ""

    model = _get_model()

    query_embedding = model.encode(
        [query],
        convert_to_numpy=True
    )

    query_embedding = np.asarray(
        query_embedding,
        dtype=np.float32
    )

    k = min(top_k, index.ntotal)

    _, indices = index.search(query_embedding, k)

    results = []

    for idx in indices[0]:

        if 0 <= idx < len(chunks):
            results.append(chunks[idx])

    return "\n\n---\n\n".join(results)


# ── Document status ────────────────────────────────────────────

def has_docs(bot_id: str) -> bool:
    """Check whether a bot has an indexed document."""

    store_dir = _get_store_dir(bot_id)

    return (
        (store_dir / "index.faiss").exists()
        and (store_dir / "chunks.pkl").exists()
    )
