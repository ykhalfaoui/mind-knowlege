import json

import anthropic

from config import MODEL

_client = anthropic.Anthropic()

_PROMPT = """\
You are an expert technical educator and writer working for a tech training platform.

Using the research data below, write a complete, high-quality technical article in Markdown.
The article must be educational, concrete, and include real, runnable code examples.
Write in the same language as the source content (French or English).

Follow this structure exactly:

# [Compelling, specific title]

> **TL;DR**: (2-3 sentences maximum — the key takeaway a busy engineer needs)

## Pourquoi c'est important / Why it matters
(Context, problem it solves, who cares and why)

## Concepts fondamentaux / Core Concepts
(Clear explanations. Use analogies. Define jargon. Build up progressively.)

## Comment ça marche / How it works
(Technical deep-dive. ASCII diagrams welcome. Be precise.)

## Exemples de code / Code Examples
(At minimum 2 real, runnable examples with inline comments explaining the WHY, not just the WHAT)

## Patterns d'architecture / Architecture Patterns
(How to integrate this in a real system. Sequence diagrams in ASCII if helpful.)

## Trade-offs

| Avantage | Limitation |
|----------|------------|
| ...      | ...        |

## Quand utiliser / Quand éviter

**Utiliser quand :**
- ...

**Éviter quand :**
- ...

## Points clés / Key Takeaways
- ...
- ...
- ...
- ...
- ...

---
*Source : {source_url}*
*Domaine : {domain} | Tags : {tags}*

---

Research data:
{research_json}

Classification:
  Domain: {domain}
  Tags: {tags}
  Key Insights:
{insights}
"""


def generate_course(content: dict, classification: dict, research: dict) -> str:
    insights = "\n".join(f"  - {i}" for i in classification.get("key_insights", []))
    research_json = json.dumps(research, indent=2, ensure_ascii=False)[:6000]
    prompt = _PROMPT.format(
        source_url=content.get("url", ""),
        domain=classification.get("domain", ""),
        tags=", ".join(classification.get("tags", [])),
        insights=insights,
        research_json=research_json,
    )
    resp = _client.messages.create(
        model=MODEL,
        max_tokens=6000,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text
