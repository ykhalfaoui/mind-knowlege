import anthropic
from config import MODEL, MAX_CONTEXT_ENTRIES
from src.knowledge_base import search_entries, build_context

_client = anthropic.Anthropic()

_SYSTEM = """\
You are an expert software architect with access to a curated technology knowledge base
built from vetted articles, videos, and deep research.
Use the provided knowledge context as your primary source of truth.
Be concrete, reference specific technologies, and always surface trade-offs.
"""

_TEMPLATE = """\
# Knowledge Base Context

{context}

---

# Architecture Question

{question}

Provide a structured answer with: recommended approach, key trade-offs, technologies to use,
and any pitfalls to avoid. Ground your answer in the knowledge base above.
"""


def query(question: str, domain: str = None) -> str:
    entries = search_entries(query=question, domain=domain, limit=MAX_CONTEXT_ENTRIES)
    if not entries:
        entries = search_entries(limit=MAX_CONTEXT_ENTRIES)

    context = build_context(entries)
    prompt = _TEMPLATE.format(context=context, question=question)

    resp = _client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text
