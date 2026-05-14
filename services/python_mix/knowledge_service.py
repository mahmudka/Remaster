"""
RAG knowledge service: Claude API + KnowledgeBase in MS SQL.
Uses Haiku for structured extraction, Sonnet for mix plan generation.
"""
import json
import os
import anthropic
from db import get_best_parameters

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ.get("CLAUDE_API_KEY", ""))
    return _client


def extract_rules_from_chunk(chunk: str, book_title: str) -> list[dict]:
    """Haiku: extract structured rules from a book chunk."""
    client = _get_client()
    resp = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2000,
        system=(
            "You extract audio mixing and mastering rules from book text. "
            "Reply ONLY with valid JSON. No extra text."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Extract rules from this excerpt of '{book_title}'.\n"
                f"Format: [{{\"parameter\", \"value\", \"unit\", \"genre\", \"rationale\"}}]\n"
                f"genre is null if rule applies to all genres.\n\n"
                f"Text: {chunk}"
            )
        }]
    )
    try:
        return json.loads(resp.content[0].text)
    except Exception:
        return []


def generate_mix_plan(track_profile: dict, genre: str) -> dict:
    """Sonnet: generate a full MixPlan JSON from track analysis + DB rules."""
    client  = _get_client()
    rules   = get_best_parameters(genre)
    rules_json = json.dumps(rules[:40], ensure_ascii=False)  # cap tokens

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=(
            "You are a professional audio engineer. "
            "Analyse the track profile and generate a concrete mix plan. "
            "Every decision must reference a source (book + chapter/page). "
            "Reply in JSON only."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Track: {json.dumps(track_profile)}\n"
                f"Knowledge rules: {rules_json}\n\n"
                "Generate a MixPlan JSON with keys:\n"
                "  tracks: [{{track, eq:[{{freq,gain_db,type}}], comp:{{threshold_db,ratio,attack_ms,release_ms,makeup_db}}, gain_db, pan, rationale, book_source}}]\n"
                "  bus: {{threshold_db, ratio, attack_ms, release_ms}}\n"
                "  reverb: {{room_size, wet}}\n"
                "  delay: {{delay_ms, feedback, wet}}\n"
                "  sources: [\"BookName Ch.X\"]\n"
                "Note: reverb and delay are applied on the final assembled mix, not on individual stems."
            )
        }]
    )
    try:
        text = resp.content[0].text
        # Strip markdown code fences if present
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        return {"error": str(e), "raw": resp.content[0].text[:500]}
