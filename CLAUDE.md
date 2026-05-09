# LIA — Tech Monitoring & Architecture Intelligence

## Vision

A collaborator shares an article or video in a Telegram channel.
LIA ingests it, qualifies it (relevance gate), does deep research,
generates a complete educational course, and indexes it in the knowledge base.
Claude Code consumes this KB via MCP to make grounded architecture decisions.

## Full Pipeline

```
[Telegram Channel]  ←  collaborator shares a URL
      |
      v
 [src/bot.py]             detect URL, check dedup
      |
      v
 [src/ingestion.py]       direct fetch → fallback: Jina Reader (JS/paywalled pages)
      |
      v
 [src/classifier.py]      Claude: domain / tags / summary / qualification scores (1-10)
      |
      v
 [Relevance Gate]         score >= RELEVANCE_THRESHOLD (default 6)
      |                   below → notify Telegram "not relevant" and stop
      v
 [src/researcher.py]      Claude: deep research, trade-offs, arch recommendations
      |
      v
 [src/knowledge_base.py]  SQLite (dedup on source_url)
      |
      v
 [src/course_generator.py] Claude: full Markdown course with code examples
      |
      v
 [articles/<slug>.md]     ready to publish
      |
      v
 [src/rag.py]             ChromaDB semantic index (optional, fallback to SQLite LIKE)
      |
      v
 [src/mcp_server.py]      ←── Claude Code calls these tools natively
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill ANTHROPIC_API_KEY and TELEGRAM_TOKEN
```

## MCP Server (Claude Code Integration)

The `.claude/settings.json` in this repo registers LIA as an MCP server.
Once the server is running, Claude Code can call these tools in any session:

| Tool | What it does |
|------|--------------|
| `search_knowledge` | Semantic search across the KB |
| `compare_options` | A vs B comparison grounded in the KB |
| `get_domain_expertise` | All knowledge for a domain |
| `list_knowledge_domains` | Domains + entry counts |
| `ingest_url` | Add an article from within a Claude session |

**Start the MCP server:**
```bash
python main.py serve
```

**Example Claude Code session:**
```
Claude, should I use Kafka or Redis Streams for this use case?
→ Claude calls compare_options("Kafka", "Redis Streams", "real-time order events")
→ Gets grounded answer from your actual KB
```

## CLI

```bash
# Full pipeline (ingest + classify + research + course)
python main.py ingest https://example.com/article
python main.py ingest https://youtu.be/xxx --video
python main.py ingest https://example.com/article --no-research --no-course  # fast

# Architecture decisions grounded in the KB
python main.py query "GraphQL or REST for a mobile-first app?"
python main.py compare Kafka RabbitMQ --context high throughput event streaming

# Browse the KB
python main.py list
python main.py search "vector database"
python main.py articles

# Start services
python main.py bot      # Telegram bot
python main.py serve    # MCP server for Claude Code
```

## Telegram Bot Commands

| Action | Result |
|--------|--------|
| Share a URL | Full pipeline triggered automatically |
| `/compare Kafka vs RabbitMQ for high throughput` | Technology comparison |
| `/query Should I use microservices?` | Architecture question |
| `/list` | Last 10 KB entries |
| `/search vector database` | Search the KB |

## Knowledge Schema

| Field | Description |
|-------|-------------|
| `domain` | AI/ML, DevOps, Security, Frontend, Backend, Cloud… |
| `subdomain` | Specific sub-area |
| `tags` | 4-8 lowercase tags |
| `summary` | 2-3 sentence summary |
| `key_insights` | 3-5 actionable insights |
| `qualification` | Scores 1-10: relevance, novelty, depth, actionability |
| `deep_research` | Trade-offs, patterns, anti-patterns, arch recommendations |

## Extending

- **Publish site**: add `src/publisher.py` → push `articles/*.md` to GitHub Pages / Ghost
- **Richer RAG**: swap ChromaDB default embeddings for multilingual model
- **Scheduled digest**: cron → `python main.py list` → weekly Telegram summary
- **More input channels**: Slack / Discord → same pipeline, different `bot.py`
