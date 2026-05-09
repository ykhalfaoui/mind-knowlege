import json
import anthropic
from config import MODEL

_client = anthropic.Anthropic()

_PROMPT = """\
You are a senior software architect doing deep technical research.
Based on the knowledge entry below, produce a research report as a JSON object (no markdown fences) with:

- related_technologies: list of {{name, description}} objects
- trade_offs: list of {{pro, con}} objects
- architectural_patterns: list of relevant design/architectural patterns
- ideal_use_cases: list of scenarios where this excels
- anti_patterns: list of situations where this is a poor choice
- emerging_trends: 2-3 sentences on future direction
- architecture_recommendations: list of concrete recommendations for system designers

Return ONLY valid JSON.

Knowledge Entry:
  Domain: {domain}
  Subdomain: {subdomain}
  Tags: {tags}
  Summary: {summary}
  Key Insights:
{insights}
"""


def deep_research(entry: dict) -> dict:
    insights = "\n".join(f"  - {i}" for i in entry.get("key_insights", []))
    prompt = _PROMPT.format(
        domain=entry.get("domain", ""),
        subdomain=entry.get("subdomain", ""),
        tags=", ".join(entry.get("tags", [])),
        summary=entry.get("summary", ""),
        insights=insights,
    )
    resp = _client.messages.create(
        model=MODEL,
        max_tokens=3072,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)
