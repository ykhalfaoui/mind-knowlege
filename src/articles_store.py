import re
from datetime import datetime, timezone
from pathlib import Path

from config import ARTICLES_DIR


def save_article(markdown: str, classification: dict) -> str:
    """Save generated markdown article to ARTICLES_DIR. Returns the slug."""
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    domain = classification.get("domain", "article")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = _slugify(domain) + "-" + ts
    path = ARTICLES_DIR / f"{slug}.md"
    path.write_text(markdown, encoding="utf-8")
    return slug


def list_articles() -> list[dict]:
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    articles = []
    for f in sorted(ARTICLES_DIR.glob("*.md"), reverse=True):
        articles.append({"slug": f.stem, "path": str(f), "size": f.stat().st_size})
    return articles


def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:50]
