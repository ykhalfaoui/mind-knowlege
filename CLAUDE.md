# LIA — Tech Monitoring & Architecture Intelligence

## Vision

A collaborator shares an interesting article or video in a Telegram channel.
LIA ingests it, decides if it's worth processing, does deep research, generates
a complete educational course, stores the knowledge, and uses it to answer
architecture questions with grounded, evidence-based recommendations.

## Full Pipeline

```
[Telegram Channel]
      | URL shared by a collaborator
      v
 [src/bot.py]              listen for URLs
      |
      v
 [src/ingestion.py]        extract text (article) or transcript (YouTube)
      |
      v
 [src/classifier.py]       Claude: domain / tags / summary / qualification scores
      |
      v
 [Relevance Gate]          relevance_score >= RELEVANCE_THRESHOLD (default 6/10)
      |                    if below -> notify "not relevant" and stop
      |
      v
 [src/researcher.py]       Claude: deep research, trade-offs, arch recommendations
      |
      v
 [src/knowledge_base.py]   SQLite: structured storage
      |
      v
 [src/course_generator.py] Claude: full Markdown article with code examples
      |
      v
 [src/articles_store.py]   articles/<slug>.md (ready to publish)
      |
      v
 [src/rag.py]              ChromaDB: semantic vector index
      |
      v
 [src/competencies.py]     Claude answers architecture questions using KB as context
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in ANTHROPIC_API_KEY and TELEGRAM_TOKEN
```

## CLI

```bash
# Start the Telegram bot
python main.py bot

# Ingest manually (full pipeline)
python main.py ingest https://example.com/article
python main.py ingest https://youtu.be/xxx --video
python main.py ingest https://example.com/article --no-research --no-course

# Architecture query (grounded in KB)
python main.py query "Should I use GraphQL or REST for a mobile app?"
python main.py query "Best ML model serving strategy?" --domain AI/ML

# Compare two technologies
python main.py compare Kafka RabbitMQ --context high throughput event streaming
python main.py compare PostgreSQL MongoDB --context user profile storage

# Browse knowledge
python main.py list
python main.py search "vector database"
python main.py articles
```

## Telegram Bot Commands

In any chat where the bot is present:

- Share a URL → triggers the full pipeline automatically
- `/compare Kafka vs RabbitMQ for high throughput` → comparison
- `/query Should I use microservices?` → architecture question
- `/list` → last 10 KB entries
- `/search vector database` → search the KB

## Knowledge Schema (SQLite)

| Field | Description |
|---|---|
| `domain` | Primary tech domain |
| `subdomain` | Specific area |
| `tags` | 4-8 descriptive tags |
| `summary` | 2-3 sentence summary |
| `key_insights` | 3-5 actionable insights |
| `qualification` | Scores 1-10: relevance, novelty, depth, actionability |
| `recommended_for` | Target scenarios |
| `deep_research` | Trade-offs, patterns, anti-patterns, arch recommendations |

## Generated Articles

Each article saved in `articles/<domain>-<timestamp>.md` with this structure:
- TL;DR
- Why it matters
- Core Concepts
- How it works
- Code Examples (2+)
- Architecture Patterns
- Trade-offs table
- When to use / When NOT to use
- Key Takeaways

## Extending

- **Publish to site**: add a publisher in `src/publisher.py` that pushes `articles/*.md` to GitHub Pages, Ghost, or Notion
- **Slack/Discord**: replace `src/bot.py` with a Slack bolt or Discord bot
- **Richer embeddings**: swap ChromaDB default for `text-embedding-3-small` via OpenAI, or use Cohere
- **Scheduled digests**: cron that calls `python main.py list` and posts weekly summary to Telegram
