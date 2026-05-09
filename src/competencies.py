import anthropic

from config import MAX_CONTEXT_ENTRIES, MODEL
from src.knowledge_base import build_context, search_entries
from src.rag import semantic_search

_client = anthropic.Anthropic()

_SYSTEM = """\
You are an expert software architect with access to a curated technology knowledge base
built from vetted articles, videos, and deep technical research.

Rules:
- Ground every recommendation in the knowledge base context provided.
- Always surface trade-offs explicitly.
- Be concrete: name specific technologies, versions, patterns.
- When the knowledge base is silent on a topic, say so clearly rather than hallucinating.
"""

_QUERY_TEMPLATE = """\
# Knowledge Base Context

{context}

---

# Question

{question}

Answer with:
1. Recommended approach (and why, based on the KB)
2. Key trade-offs
3. Technologies / tools to use
4. Pitfalls to avoid
"""

_COMPARE_TEMPLATE = """\
# Knowledge Base Context

{context}

---

# Comparison Request: {a} vs {b}
{ctx_line}

Provide:
1. Head-to-head comparison table (criteria rows)
2. When to choose {a}
3. When to choose {b}
4. Final recommendation with rationale from the knowledge base
5. Any hybrid or alternative approach worth considering
"""


def _resolve_context(question: str, domain: str = None) -> str:
    entries_rag = semantic_search(question, domain=domain, n_results=MAX_CONTEXT_ENTRIES)
    if entries_rag:
        return "\n\n---\n\n".join(e["text"] for e in entries_rag)
    entries = search_entries(query=question, domain=domain, limit=MAX_CONTEXT_ENTRIES)
    if not entries:
        entries = search_entries(limit=MAX_CONTEXT_ENTRIES)
    return build_context(entries)


def query(question: str, domain: str = None) -> str:
    context = _resolve_context(question, domain)
    prompt = _QUERY_TEMPLATE.format(context=context, question=question)
    resp = _client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


def compare(option_a: str, option_b: str, context_desc: str = "") -> str:
    search_q = f"{option_a} {option_b} {context_desc}"
    context = _resolve_context(search_q)
    ctx_line = f"Context: {context_desc}" if context_desc else ""
    prompt = _COMPARE_TEMPLATE.format(
        context=context, a=option_a, b=option_b, ctx_line=ctx_line
    )
    resp = _client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text
