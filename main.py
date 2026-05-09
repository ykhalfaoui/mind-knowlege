#!/usr/bin/env python3
"""Mind-Knowledge CLI — tech monitoring & architecture intelligence."""
import argparse
import json
import sys

from src.knowledge_base import init_db, save_entry, search_entries
from src.ingestion import ingest
from src.classifier import classify
from src.researcher import deep_research
from src.competencies import query


def cmd_ingest(args):
    print(f"[ingest] {args.url}")
    content = ingest(args.url, force_video=args.video)
    print(f"  title     : {content['title']}")
    print(f"  type      : {content['type']}")

    print("  classifying...")
    classification = classify(content)
    print(f"  domain    : {classification.get('domain')} / {classification.get('subdomain')}")
    print(f"  tags      : {', '.join(classification.get('tags', []))}")
    qual = classification.get("qualification", {})
    print(
        f"  scores    : relevance={qual.get('relevance_score')} "
        f"novelty={qual.get('novelty_score')} "
        f"depth={qual.get('depth_score')} "
        f"action={qual.get('actionability_score')}"
    )

    research = {}
    if not args.no_research:
        print("  deep researching...")
        research = deep_research({**classification, "key_insights": classification.get("key_insights", [])})

    entry_id = save_entry(content, classification, research)
    print(f"  saved     : {entry_id}")
    print(f"  summary   : {classification.get('summary', '')[:240]}")


def cmd_query(args):
    question = " ".join(args.question)
    print(f"[query] {question}\n")
    answer = query(question, domain=args.domain)
    print(answer)


def cmd_list(args):
    entries = search_entries(limit=args.limit)
    if not entries:
        print("Knowledge base is empty. Run: python main.py ingest <url>")
        return
    print(f"Knowledge Base — {len(entries)} entries\n")
    for e in entries:
        qual = json.loads(e.get("qualification") or "{}")
        tags = json.loads(e.get("tags") or "[]")
        r = qual.get("relevance_score", "?")
        print(f"  [{e['domain']:20}] {e['title'][:60]}")
        print(f"    relevance={r}/10  tags={', '.join(tags[:4])}")
        print(f"    {e['source_url']}")
        print()


def cmd_search(args):
    q = " ".join(args.query)
    entries = search_entries(query=q, limit=10)
    print(f"[search] '{q}' — {len(entries)} result(s)\n")
    for e in entries:
        print(f"  [{e['domain']}] {e['title']}")
        print(f"    {e['summary'][:160]}")
        print()


def main():
    init_db()
    parser = argparse.ArgumentParser(
        prog="mind-knowledge",
        description="Tech monitoring & architecture intelligence powered by Claude",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest", help="Ingest an article or YouTube video")
    p.add_argument("url", help="URL to ingest")
    p.add_argument("--video", action="store_true", help="Force YouTube transcript extraction")
    p.add_argument("--no-research", action="store_true", help="Skip deep research step")

    p = sub.add_parser("query", help="Ask an architecture question using the knowledge base")
    p.add_argument("question", nargs="+")
    p.add_argument("--domain", help="Filter context by domain")

    p = sub.add_parser("list", help="List all knowledge entries")
    p.add_argument("--limit", type=int, default=20)

    p = sub.add_parser("search", help="Search the knowledge base")
    p.add_argument("query", nargs="+")

    args = parser.parse_args()
    commands = {"ingest": cmd_ingest, "query": cmd_query, "list": cmd_list, "search": cmd_search}
    commands[args.command](args)


if __name__ == "__main__":
    main()
