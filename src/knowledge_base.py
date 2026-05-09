import json
import sqlite3
import uuid
from datetime import datetime, timezone

from config import DB_PATH


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id              TEXT PRIMARY KEY,
                title           TEXT NOT NULL,
                source_url      TEXT UNIQUE,
                type            TEXT,
                domain          TEXT,
                subdomain       TEXT,
                tags            TEXT,
                summary         TEXT,
                key_insights    TEXT,
                qualification   TEXT,
                recommended_for TEXT,
                deep_research   TEXT,
                raw_content     TEXT,
                created_at      TEXT
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_domain ON entries(domain)"
        )


def url_exists(url: str) -> bool:
    with _conn() as conn:
        row = conn.execute(
            "SELECT id FROM entries WHERE source_url = ?", (url,)
        ).fetchone()
    return row is not None


def save_entry(content: dict, classification: dict, research: dict = None) -> str:
    entry_id = str(uuid.uuid4())
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO entries VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                entry_id,
                content.get("title", ""),
                content.get("url", ""),
                content.get("type", "article"),
                classification.get("domain", ""),
                classification.get("subdomain", ""),
                json.dumps(classification.get("tags", []), ensure_ascii=False),
                classification.get("summary", ""),
                json.dumps(classification.get("key_insights", []), ensure_ascii=False),
                json.dumps(classification.get("qualification", {}), ensure_ascii=False),
                json.dumps(classification.get("recommended_for", []), ensure_ascii=False),
                json.dumps(research or {}, ensure_ascii=False),
                content.get("content", "")[:5000],
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    return entry_id


def search_entries(
    query: str = None, domain: str = None, limit: int = 10
) -> list[dict]:
    with _conn() as conn:
        conn.row_factory = sqlite3.Row
        if domain:
            rows = conn.execute(
                "SELECT * FROM entries WHERE domain LIKE ? ORDER BY created_at DESC LIMIT ?",
                (f"%{domain}%", limit),
            ).fetchall()
        elif query:
            like = f"%{query}%"
            rows = conn.execute(
                """SELECT * FROM entries
                   WHERE title LIKE ? OR summary LIKE ? OR tags LIKE ? OR domain LIKE ?
                   ORDER BY created_at DESC LIMIT ?""",
                (like, like, like, like, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM entries ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
    return [dict(r) for r in rows]


def build_context(entries: list[dict]) -> str:
    parts = []
    for e in entries:
        tags = json.loads(e.get("tags") or "[]")
        insights = json.loads(e.get("key_insights") or "[]")
        research = json.loads(e.get("deep_research") or "{}")
        block = (
            f"## {e['title']}\n"
            f"Domain: {e['domain']} / {e.get('subdomain', '')}\n"
            f"Tags: {', '.join(tags)}\n"
            f"Summary: {e['summary']}\n"
            "Key Insights:\n" + "\n".join(f"  - {i}" for i in insights)
        )
        recs = research.get("architecture_recommendations", [])
        if recs:
            if isinstance(recs, list):
                block += "\nArch Recommendations:\n" + "\n".join(f"  - {r}" for r in recs)
            else:
                block += f"\nArch Recommendations: {recs}"
        parts.append(block)
    return "\n\n---\n\n".join(parts)


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)
