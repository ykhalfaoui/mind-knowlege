import json
import anthropic
from config import MODEL

_client = anthropic.Anthropic()

_PROMPT = """\
Analyze the following content and return a JSON object (no markdown fences) with exactly these fields:

- domain: primary tech domain ("AI/ML", "DevOps", "Security", "Frontend", "Backend", "Cloud", "Data Engineering", "Architecture", "Mobile", "Blockchain", "Other")
- subdomain: specific area within the domain
- tags: list of 4-8 relevant lowercase tags
- summary: 2-3 sentence summary of the key points
- key_insights: list of 3-5 concrete, actionable insights
- qualification:
    relevance_score: 1-10 (relevance to modern software engineering)
    novelty_score: 1-10 (how new or innovative this is)
    depth_score: 1-10 (technical depth and rigor)
    actionability_score: 1-10 (how useful for building real systems)
- recommended_for: list of scenarios or roles that benefit most from this

Return ONLY valid JSON.

Title: {title}
Content:
{content}
"""


def classify(content: dict) -> dict:
    prompt = _PROMPT.format(
        title=content["title"],
        content=content["content"][:8000],
    )
    resp = _client.messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.content[0].text.strip()
    # strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)
