import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-6"

DB_PATH = Path("knowledge/knowledge.db")
KNOWLEDGE_DIR = Path("knowledge")
ARTICLES_DIR = Path("articles")

MAX_CONTENT_CHARS = 10_000
MAX_CONTEXT_ENTRIES = 8

# Minimum relevance score (1-10) to keep and process an article
RELEVANCE_THRESHOLD = int(os.getenv("RELEVANCE_THRESHOLD", "6"))

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
# Comma-separated chat IDs allowed to trigger the pipeline (empty = all)
TELEGRAM_ALLOWED_CHATS = [
    c.strip() for c in os.getenv("TELEGRAM_ALLOWED_CHATS", "").split(",") if c.strip()
]
