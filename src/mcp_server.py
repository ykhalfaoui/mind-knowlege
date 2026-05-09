"""
LIA Knowledge MCP Server.

Exposes the knowledge base as tools that Claude Code can call natively.

Tools:
  search_knowledge      — semantic search across the KB
  compare_options       — A vs B comparison grounded in the KB
  get_domain_expertise  — all knowledge for a domain
  list_knowledge_domains— domains + entry counts
  ingest_url            — add a new article to the KB from a Claude session

Setup in Claude Code: add .claude/settings.json (already included in this repo).
"""
from __future__ import annotations

import asyncio
import logging
import sqlite3

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

from config import DB_PATH, MAX_CONTEXT_ENTRIES, RELEVANCE_THRESHOLD
from src.knowledge_base import build_context, init_db, save_entry, search_entries, url_exists
from src.rag import add_to_index, semantic_search

log = logging.getLogger(__name__)

server = Server("lia-knowledge")


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_knowledge",
            description=(
                "Search the LIA knowledge base built from curated tech articles and research. "
                "Returns relevant summaries, key insights, and architecture recommendations. "
                "Use this before making any technology choice or architecture decision."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for"},
                    "domain": {
                        "type": "string",
                        "description": "Optional domain filter: AI/ML, DevOps, Security, Frontend, Backend, Cloud, Data Engineering, Architecture",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="compare_options",
            description=(
                "Compare two technology options or architectural approaches using the knowledge base. "
                "Returns a structured comparison with trade-offs and a grounded recommendation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "option_a": {"type": "string", "description": "First option (e.g. Kafka)"},
                    "option_b": {"type": "string", "description": "Second option (e.g. RabbitMQ)"},
                    "context": {
                        "type": "string",
                        "description": "Context for the comparison (e.g. 'real-time user notifications at 10k msg/s')",
                    },
                },
                "required": ["option_a", "option_b"],
            },
        ),
        types.Tool(
            name="get_domain_expertise",
            description="Get all knowledge entries for a specific technology domain.",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Domain name (e.g. AI/ML, DevOps, Security)",
                    }
                },
                "required": ["domain"],
            },
        ),
        types.Tool(
            name="list_knowledge_domains",
            description="List all technology domains in the knowledge base with entry counts.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="ingest_url",
            description=(
                "Add a new article or YouTube video to the LIA knowledge base. "
                "Triggers the full pipeline: extraction → classification → deep research → course generation. "
                "Use when you find a relevant article during a work session."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL of the article or YouTube video"},
                    "no_course": {
                        "type": "boolean",
                        "description": "Set true to skip course generation (faster, just index the knowledge)",
                    },
                },
                "required": ["url"],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    args = arguments or {}
    loop = asyncio.get_event_loop()

    if name == "search_knowledge":
        result = await loop.run_in_executor(
            None, _search, args.get("query", ""), args.get("domain")
        )
    elif name == "compare_options":
        from src.competencies import compare
        result = await loop.run_in_executor(
            None, compare, args["option_a"], args["option_b"], args.get("context", "")
        )
    elif name == "get_domain_expertise":
        result = await loop.run_in_executor(None, _domain_expertise, args["domain"])
    elif name == "list_knowledge_domains":
        result = await loop.run_in_executor(None, _list_domains)
    elif name == "ingest_url":
        result = await loop.run_in_executor(
            None, _ingest, args["url"], bool(args.get("no_course", False))
        )
    else:
        result = f"Unknown tool: {name}"

    return [types.TextContent(type="text", text=str(result))]


# ---------------------------------------------------------------------------
# Implementation helpers
# ---------------------------------------------------------------------------

def _search(query: str, domain: str | None = None) -> str:
    entries_rag = semantic_search(query, domain=domain, n_results=MAX_CONTEXT_ENTRIES)
    if entries_rag:
        return "\n\n---\n\n".join(e["text"] for e in entries_rag)
    entries = search_entries(query=query, domain=domain, limit=MAX_CONTEXT_ENTRIES)
    if not entries:
        return (
            f"No knowledge found for '{query}'. "
            "Use ingest_url to add relevant articles on this topic."
        )
    return build_context(entries)


def _domain_expertise(domain: str) -> str:
    entries = search_entries(domain=domain, limit=20)
    if not entries:
        return f"No knowledge found for domain '{domain}'."
    return build_context(entries)


def _list_domains() -> str:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT domain, COUNT(*) FROM entries GROUP BY domain ORDER BY COUNT(*) DESC"
    ).fetchall()
    conn.close()
    if not rows:
        return "Knowledge base is empty. Use ingest_url to add articles."
    lines = ["Knowledge base domains:\n"]
    for domain, count in rows:
        lines.append(f"  {domain or 'Unknown':25} {count} entries")
    return "\n".join(lines)


def _ingest(url: str, no_course: bool = False) -> str:
    if url_exists(url):
        return f"Already in knowledge base: {url}"

    from src.ingestion import ingest as do_ingest
    from src.classifier import classify
    from src.researcher import deep_research

    content = do_ingest(url)
    classification = classify(content)
    qual = classification.get("qualification", {})
    relevance = qual.get("relevance_score", 0)

    if relevance < RELEVANCE_THRESHOLD:
        return (
            f"Not relevant enough (score: {relevance}/10, threshold: {RELEVANCE_THRESHOLD}).\n"
            f"Domain: {classification.get('domain')} | "
            f"Tags: {', '.join(classification.get('tags', []))}"
        )

    research = deep_research({**classification})
    entry_id = save_entry(content, classification, research)
    add_to_index(entry_id, content, classification, research)

    article_info = ""
    if not no_course:
        from src.course_generator import generate_course
        from src.articles_store import save_article
        md = generate_course(content, classification, research)
        slug = save_article(md, classification)
        article_info = f"\nArticle: articles/{slug}.md"

    return (
        f"Ingested successfully!\n"
        f"Domain   : {classification.get('domain')}\n"
        f"Tags     : {', '.join(classification.get('tags', []))}\n"
        f"Relevance: {relevance}/10\n"
        f"Summary  : {classification.get('summary', '')[:200]}"
        + article_info
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def _main() -> None:
    init_db()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="lia-knowledge",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def run_server() -> None:
    asyncio.run(_main())
