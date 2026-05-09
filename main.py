#!/usr/bin/env python3
"""LIA — Tech monitoring & architecture intelligence CLI."""
import argparse
import json

from src.knowledge_base import init_db, save_entry, search_entries, url_exists
from src.ingestion import ingest
from src.classifier import classify
from src.researcher import deep_research
from src.competencies import query, compare
from src.articles_store import list_articles
from config import RELEVANCE_THRESHOLD


def cmd_ingest(args):
    print(f"[ingest] {args.url}")

    if url_exists(args.url):
        print("  already in KB — skipping")
        return

    content = ingest(args.url, force_video=args.video)
    print(f"  title    : {content['title']}")
    print(f"  type     : {content['type']}")

    print("  classifying...")
    classification = classify(content)
    domain = classification.get("domain")
    tags = ", ".join(classification.get("tags", []))
    qual = classification.get("qualification", {})
    relevance = qual.get("relevance_score", 0)
    print(f"  domain   : {domain} / {classification.get('subdomain')}")
    print(f"  tags     : {tags}")
    print(f"  scores   : relevance={relevance} novelty={qual.get('novelty_score')} "
          f"depth={qual.get('depth_score')} action={qual.get('actionability_score')}")

    if isinstance(relevance, int) and relevance < RELEVANCE_THRESHOLD:
        print(f"  [skip] relevance {relevance}/10 < threshold {RELEVANCE_THRESHOLD}")
        return

    if not args.no_research:
        print("  deep researching...")
        research = deep_research({**classification})
    else:
        research = {}

    entry_id = save_entry(content, classification, research)
    print(f"  saved KB : {entry_id}")

    if not args.no_course:
        from src.course_generator import generate_course
        from src.articles_store import save_article
        print("  generating course article...")
        md = generate_course(content, classification, research)
        slug = save_article(md, classification)
        print(f"  article  : articles/{slug}.md")

    try:
        from src.rag import add_to_index
        add_to_index(entry_id, content, classification, research)
        print("  indexed  : RAG")
    except Exception:
        pass

    print(f"  summary  : {classification.get('summary', '')[:240]}")


def cmd_query(args):
    question = " ".join(args.question)
    print(f"[query] {question}\n")
    print(query(question, domain=args.domain))


def cmd_compare(args):
    ctx = " ".join(args.context) if args.context else ""
    label = f" for: {ctx}" if ctx else ""
    print(f"[compare] {args.a} vs {args.b}{label}\n")
    print(compare(args.a, args.b, ctx))


def cmd_list(args):
    entries = search_entries(limit=args.limit)
    if not entries:
        print("Knowledge base is empty. Run: python main.py ingest <url>")
        return
    print(f"Knowledge Base — {len(entries)} entries\n")
    for e in entries:
        qual = json.loads(e.get("qualification") or "{}")
        tags = json.loads(e.get("tags") or "[]")
        print(f"  [{e['domain']:20}] {e['title'][:60]}")
        print(f"    relevance={qual.get('relevance_score','?')}/10  tags={', '.join(tags[:4])}")
        print(f"    {e['source_url']}")
        print()


def cmd_articles(args):
    articles = list_articles()
    if not articles:
        print("No articles generated yet.")
        return
    print(f"Generated Articles — {len(articles)} files\n")
    for a in articles:
        print(f"  {a['path']}  ({a['size']} bytes)")


def cmd_search(args):
    q = " ".join(args.query)
    entries = search_entries(query=q, limit=10)
    print(f"[search] '{q}' — {len(entries)} result(s)\n")
    for e in entries:
        print(f"  [{e['domain']}] {e['title']}")
        print(f"    {e['summary'][:160]}")
        print()


def cmd_serve(_args):
    from src.mcp_server import run_server
    run_server()


def cmd_bot(_args):
    from src.bot import run_bot
    run_bot()


def main():
    init_db()
    parser = argparse.ArgumentParser(
        prog="lia",
        description="LIA — Tech monitoring & architecture intelligence",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest", help="Ingest an article or YouTube video")
    p.add_argument("url")
    p.add_argument("--video", action="store_true", help="Force YouTube transcript")
    p.add_argument("--no-research", action="store_true", help="Skip deep research")
    p.add_argument("--no-course", action="store_true", help="Skip course generation")

    p = sub.add_parser("query", help="Architecture question answered from the knowledge base")
    p.add_argument("question", nargs="+")
    p.add_argument("--domain")

    p = sub.add_parser("compare", help="Compare two technologies using the knowledge base")
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--context", nargs="+")

    p = sub.add_parser("list", help="List knowledge base entries")
    p.add_argument("--limit", type=int, default=20)

    sub.add_parser("articles", help="List generated article files")

    p = sub.add_parser("search", help="Search the knowledge base")
    p.add_argument("query", nargs="+")

    sub.add_parser("serve", help="Start MCP server (for Claude Code integration)")
    sub.add_parser("bot", help="Start Telegram bot")

    args = parser.parse_args()
    {
        "ingest": cmd_ingest,
        "query": cmd_query,
        "compare": cmd_compare,
        "list": cmd_list,
        "articles": cmd_articles,
        "search": cmd_search,
        "serve": cmd_serve,
        "bot": cmd_bot,
    }[args.command](args)


if __name__ == "__main__":
    main()
