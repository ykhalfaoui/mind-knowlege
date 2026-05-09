"""
Semantic search layer using ChromaDB.
Falls back gracefully if ChromaDB is unavailable.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from config import KNOWLEDGE_DIR, MAX_CONTEXT_ENTRIES

log = logging.getLogger(__name__)

_COLLECTION_NAME = "knowledge"


def _get_collection():
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(KNOWLEDGE_DIR / "chroma"))
        return client.get_or_create_collection(_COLLECTION_NAME)
    except Exception as exc:
        log.warning("ChromaDB unavailable: %s", exc)
        return None


def add_to_index(entry_id: str, content: dict, classification: dict, research: dict) -> None:
    col = _get_collection()
    if col is None:
        return
    insights = classification.get("key_insights", [])
    recs = research.get("architecture_recommendations", [])
    if isinstance(recs, str):
        recs = [recs]
    document = "\n".join(
        filter(
            None,
            [
                content.get("title", ""),
                classification.get("summary", ""),
                *insights,
                *recs,
            ],
        )
    )
    metadata = {
        "domain": classification.get("domain", ""),
        "subdomain": classification.get("subdomain", ""),
        "tags": ", ".join(classification.get("tags", [])),
        "source_url": content.get("url", ""),
        "title": content.get("title", ""),
    }
    try:
        col.upsert(ids=[entry_id], documents=[document], metadatas=[metadata])
    except Exception as exc:
        log.warning("RAG index failed: %s", exc)


def semantic_search(
    query: str, domain: Optional[str] = None, n_results: int = MAX_CONTEXT_ENTRIES
) -> list[dict]:
    col = _get_collection()
    if col is None:
        return []
    try:
        count = col.count()
        if count == 0:
            return []
        where = {"domain": domain} if domain else None
        results = col.query(
            query_texts=[query],
            n_results=min(n_results, count),
            where=where,
        )
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        return [{"text": d, **m} for d, m in zip(docs, metas)]
    except Exception as exc:
        log.warning("RAG search failed: %s", exc)
        return []
