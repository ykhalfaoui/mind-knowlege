# Mind-Knowledge — Tech Monitoring & Architecture Intelligence

## What this project does

A CLI pipeline that turns raw articles and YouTube videos into a structured,
queryable knowledge base — then uses that knowledge as grounded context
when Claude answers architecture questions.

```
[Article / Video URL]
       │
       ▼
  src/ingestion.py       ← extract text content
       │
       ▼
  src/classifier.py      ← Claude: domain, tags, summary, qualification scores
       │
       ▼
  src/researcher.py      ← Claude: deep research, trade-offs, arch recommendations
       │
       ▼
  knowledge/knowledge.db ← SQLite knowledge base
       │
       ▼
  src/competencies.py    ← Claude answers architecture questions using the KB as context
```

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...
```

## CLI Usage

```bash
# Ingest an article (classify + deep research)
python main.py ingest https://example.com/some-tech-article

# Ingest a YouTube video (transcript extraction)
python main.py ingest https://youtube.com/watch?v=... --video

# Ingest without deep research (faster)
python main.py ingest https://example.com/article --no-research

# Ask an architecture question grounded in the knowledge base
python main.py query "Should I use Kafka or RabbitMQ for event streaming?"

# Filter context by domain
python main.py query "Best approach for ML model serving?" --domain AI/ML

# List all knowledge entries
python main.py list

# Search the knowledge base
python main.py search "vector database"
```

## Knowledge Schema

Each entry stored in SQLite contains:

| Field | Description |
|---|---|
| `domain` | Primary tech domain (AI/ML, DevOps, Security…) |
| `subdomain` | Specific area within domain |
| `tags` | 4-8 descriptive tags |
| `summary` | 2-3 sentence summary |
| `key_insights` | 3-5 actionable insights |
| `qualification` | Scores: relevance, novelty, depth, actionability (1-10) |
| `recommended_for` | Scenarios that benefit most |
| `deep_research` | Trade-offs, patterns, recommendations, anti-patterns |

## Model

All Claude calls use `claude-sonnet-4-6`. Change in `config.py`.

## Extending

- **New input channels**: add extractors in `src/ingestion.py`
- **API server**: wrap `main.py` commands in FastAPI endpoints
- **Telegram bot**: hook `cmd_ingest` to a bot message handler
- **Vector search**: replace SQLite LIKE search with embeddings (e.g. ChromaDB)
