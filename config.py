import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-6"
DB_PATH = Path("knowledge/knowledge.db")
KNOWLEDGE_DIR = Path("knowledge")
MAX_CONTENT_CHARS = 10_000
MAX_CONTEXT_ENTRIES = 8
