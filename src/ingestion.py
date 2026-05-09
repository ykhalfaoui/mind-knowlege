"""
Content extraction from URLs and YouTube videos.

Strategy for articles:
  1. Direct HTTP fetch + BeautifulSoup
  2. Fallback: Jina Reader (https://r.jina.ai/) — handles JS pages,
     Medium, Substack, LinkedIn, etc.
"""
import re

import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi

from config import MAX_CONTENT_CHARS

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MindKnowledge/1.0)"}
MIN_CONTENT_LENGTH = 400  # chars — below this, assume extraction failed


def ingest(url: str, force_video: bool = False) -> dict:
    if force_video or _is_youtube(url):
        return _extract_video(url)
    return _extract_article(url)


def _is_youtube(url: str) -> bool:
    return "youtube.com" in url or "youtu.be" in url


def _extract_article(url: str) -> dict:
    # Strategy 1: direct fetch
    try:
        resp = requests.get(url, timeout=20, headers=HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        content = soup.get_text(separator="\n", strip=True)
        if len(content) >= MIN_CONTENT_LENGTH:
            title = soup.find("title")
            return {
                "title": title.get_text(strip=True) if title else url,
                "content": content[:MAX_CONTENT_CHARS],
                "url": url,
                "type": "article",
            }
    except Exception:
        pass

    # Strategy 2: Jina Reader fallback (handles JS, paywalls, Medium …)
    return _extract_via_jina(url)


def _extract_via_jina(url: str) -> dict:
    jina_url = f"https://r.jina.ai/{url}"
    resp = requests.get(jina_url, timeout=30, headers=HEADERS)
    resp.raise_for_status()
    text = resp.text.strip()
    lines = text.split("\n")
    title = lines[0].lstrip("# ").strip() if lines else url
    return {
        "title": title,
        "content": text[:MAX_CONTENT_CHARS],
        "url": url,
        "type": "article",
    }


def _extract_video(url: str) -> dict:
    video_id = _video_id(url)
    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["fr", "en"])
    text = " ".join(t["text"] for t in transcript)
    return {
        "title": f"Video [{video_id}]",
        "content": text[:MAX_CONTENT_CHARS],
        "url": url,
        "type": "video",
    }


def _video_id(url: str) -> str:
    for pattern in [r"youtube\.com/watch\?v=([^&]+)", r"youtu\.be/([^?]+)"]:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    raise ValueError(f"Cannot extract video ID from: {url}")
