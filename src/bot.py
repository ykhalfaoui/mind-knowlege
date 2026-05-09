"""
Telegram bot — listens for shared URLs and runs the full LIA pipeline.

Start: python main.py bot

In any chat where the bot is present:
  - Share a URL           → full pipeline (ingest + classify + research + course)
  - /compare A vs B       → technology comparison
  - /query <question>     → architecture question from the KB
  - /list                 → last 10 KB entries
  - /search <query>       → search the KB
"""
import asyncio
import logging
import re

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import RELEVANCE_THRESHOLD, TELEGRAM_ALLOWED_CHATS, TELEGRAM_TOKEN
from src.articles_store import save_article
from src.classifier import classify
from src.competencies import compare as kb_compare
from src.competencies import query as kb_query
from src.course_generator import generate_course
from src.ingestion import ingest
from src.knowledge_base import init_db, save_entry, search_entries, url_exists
from src.rag import add_to_index

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

URL_RE = re.compile(r"https?://[^\s]+")
COMPARE_RE = re.compile(r"(.+?)\s+vs\.?\s+(.+?)(?:\s+for\s+(.+))?$", re.IGNORECASE)


def _allowed(update: Update) -> bool:
    if not TELEGRAM_ALLOWED_CHATS:
        return True
    return str(update.effective_chat.id) in TELEGRAM_ALLOWED_CHATS


async def _reply(update: Update, text: str) -> None:
    await update.effective_message.reply_text(text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    text = update.effective_message.text or update.effective_message.caption or ""
    for url in URL_RE.findall(text):
        await _process_url(url, update)


async def _process_url(url: str, update: Update) -> None:
    loop = asyncio.get_event_loop()

    # Deduplication
    if url_exists(url):
        await _reply(update, f"Already in knowledge base: {url}")
        return

    await _reply(update, f"Ingesting {url} ...")
    try:
        content = await loop.run_in_executor(None, ingest, url)
    except Exception as exc:
        await _reply(update, f"Ingestion failed: {exc}")
        return

    await _reply(update, "Classifying...")
    try:
        classification = await loop.run_in_executor(None, classify, content)
    except Exception as exc:
        await _reply(update, f"Classification failed: {exc}")
        return

    qual = classification.get("qualification", {})
    relevance = qual.get("relevance_score", 0)
    domain = classification.get("domain", "")
    tags = ", ".join(classification.get("tags", [])[:5])

    if relevance < RELEVANCE_THRESHOLD:
        await _reply(
            update,
            f"Not relevant enough ({relevance}/10, threshold={RELEVANCE_THRESHOLD}).\n"
            f"Domain: {domain} | Tags: {tags}\nSkipping.",
        )
        return

    await _reply(update, f"Relevant! Score {relevance}/10 | {domain}\nDeep researching...")
    try:
        from src.researcher import deep_research
        research = await loop.run_in_executor(None, deep_research, {**classification})
    except Exception as exc:
        await _reply(update, f"Research warning: {exc}")
        research = {}

    entry_id = save_entry(content, classification, research)

    await _reply(update, "Generating course article...")
    try:
        article_md = await loop.run_in_executor(
            None, generate_course, content, classification, research
        )
        slug = save_article(article_md, classification)
        article_info = f"articles/{slug}.md"
    except Exception as exc:
        article_info = f"(generation failed: {exc})"

    try:
        add_to_index(entry_id, content, classification, research)
    except Exception:
        pass

    summary = classification.get("summary", "")[:280]
    await _reply(
        update,
        f"Done!\n"
        f"Domain : {domain}\n"
        f"Tags   : {tags}\n"
        f"Score  : {relevance}/10\n"
        f"Article: {article_info}\n\n"
        f"{summary}",
    )


async def cmd_compare(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    text = " ".join(context.args or [])
    m = COMPARE_RE.match(text)
    if not m:
        await _reply(update, "Usage: /compare <A> vs <B> [for <context>]")
        return
    a, b, ctx = m.group(1).strip(), m.group(2).strip(), (m.group(3) or "").strip()
    await _reply(update, f"Comparing {a} vs {b}...")
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, kb_compare, a, b, ctx
        )
        await _reply(update, result[:4000])
    except Exception as exc:
        await _reply(update, f"Compare failed: {exc}")


async def cmd_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    question = " ".join(context.args or [])
    if not question:
        await _reply(update, "Usage: /query <your architecture question>")
        return
    await _reply(update, "Searching knowledge base...")
    try:
        answer = await asyncio.get_event_loop().run_in_executor(
            None, kb_query, question, None
        )
        await _reply(update, answer[:4000])
    except Exception as exc:
        await _reply(update, f"Query failed: {exc}")


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    entries = search_entries(limit=10)
    if not entries:
        await _reply(update, "Knowledge base is empty.")
        return
    lines = [f"Knowledge Base ({len(entries)} recent)\n"]
    for e in entries:
        lines.append(f"[{e['domain']}] {e['title'][:55]}")
        lines.append(f"  {e['source_url']}")
    await _reply(update, "\n".join(lines))


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    q = " ".join(context.args or [])
    if not q:
        await _reply(update, "Usage: /search <query>")
        return
    entries = search_entries(query=q, limit=5)
    if not entries:
        await _reply(update, f"No results for '{q}'.")
        return
    lines = [f"Results for '{q}':\n"]
    for e in entries:
        lines.append(f"[{e['domain']}] {e['title']}")
        lines.append(f"  {e['summary'][:120]}")
    await _reply(update, "\n".join(lines))


def run_bot() -> None:
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN is not set in .env")
    init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("compare", cmd_compare))
    app.add_handler(CommandHandler("query", cmd_query))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("search", cmd_search))
    log.info("LIA bot started. Polling for messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
