"""
rag.py — RAG pipeline for BotForge.
Handles PDF/URL ingestion, chunking, embedding and FAISS retrieval.
Each bot gets its own isolated vector store.
"""

import os
import re
import faiss
import pickle
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

VECTOR_DIR = Path(__file__).parent.parent / 'vector_stores'
VECTOR_DIR.mkdir(exist_ok=True)

EMBED_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
CHUNK_SIZE  = 500
CHUNK_OVERLAP = 50


# ── Text extraction ───────────────────────────────────────────────────────────

def _extract_pdf(path: str) -> str:
    import pymupdf
    doc = pymupdf.open(path)
    return '\n'.join(page.get_text() for page in doc)


def _extract_url(url: str) -> str:
    import requests
    from bs4 import BeautifulSoup
    r = requests.get(url, timeout=15)
    soup = BeautifulSoup(r.text, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'footer']):
        tag.decompose()
    return soup.get_text(separator='\n')


# ── Chunking ──────────────────────────────────────────────────────────────────

def _chunk(text: str) -> list[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = ' '.join(words[i:i + CHUNK_SIZE])
        chunks.append(chunk.strip())
        i += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if len(c) > 50]


# ── Ingest ────────────────────────────────────────────────────────────────────

def ingest_pdf(path: str, bot_id: str):
    text = _extract_pdf(path)
    _build_index(text, bot_id)


def ingest_url(url: str, bot_id: str):
    text = _extract_url(url)
    _build_index(text, bot_id)


def _build_index(text: str, bot_id: str):
    chunks = _chunk(text)
    embeddings = EMBED_MODEL.encode(chunks, show_progress_bar=False)
    embeddings = np.array(embeddings).astype('float32')

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    store_dir = VECTOR_DIR / bot_id
    store_dir.mkdir(exist_ok=True)

    faiss.write_index(index, str(store_dir / 'index.faiss'))
    with open(store_dir / 'chunks.pkl', 'wb') as f:
        pickle.dump(chunks, f)


# ── Retrieve ──────────────────────────────────────────────────────────────────

def retrieve(query: str, bot_id: str, top_k: int = 3) -> str:
    store_dir = VECTOR_DIR / bot_id
    if not (store_dir / 'index.faiss').exists():
        return ''

    index = faiss.read_index(str(store_dir / 'index.faiss'))
    with open(store_dir / 'chunks.pkl', 'rb') as f:
        chunks = pickle.load(f)

    q_vec = EMBED_MODEL.encode([query]).astype('float32')
    _, indices = index.search(q_vec, top_k)

    results = [chunks[i] for i in indices[0] if i < len(chunks)]
    return '\n\n---\n\n'.join(results)


def has_docs(bot_id: str) -> bool:
    return (VECTOR_DIR / bot_id / 'index.faiss').exists()
