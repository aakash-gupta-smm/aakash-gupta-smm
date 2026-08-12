"""
Shared topic rotation for the posting agents.

The agents originally picked a topic with a date formula (week * 3 + slot, or
week % len). Both wrapped modulo the pool size with no memory of what had gone
out, so old topics resurfaced — the text agent repeated a topic 7 weeks later,
and the carousel agent would have posted the SAME topic on Monday and Friday of
every week, since both fall in one ISO week.

This picks from the log instead: never repeat until the pool is exhausted, then
always take whatever has been unused the longest.
"""

import os
import re
import json
from collections import Counter


def _normalise(text: str) -> set[str]:
    """Content words only, for near-duplicate detection."""
    stop = {
        "the", "a", "an", "and", "or", "but", "for", "to", "of", "in", "on",
        "is", "are", "you", "your", "i", "my", "that", "this", "it", "with",
        "how", "why", "what", "when", "most", "some", "any",
    }
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in stop and len(w) > 2}


def _too_similar(candidate: str, existing: list[str], threshold: float = 0.6) -> bool:
    """
    True if `candidate` overlaps heavily with anything already published.

    Exact-match checking isn't enough — the model will happily produce
    "5 Google Ads mistakes burning budget" against an existing
    "5 Google Ads mistakes that quietly burn your budget".
    """
    cand = _normalise(candidate)
    if not cand:
        return True

    for old in existing:
        prev = _normalise(old)
        if not prev:
            continue
        overlap = len(cand & prev) / min(len(cand), len(prev))
        if overlap >= threshold:
            return True
    return False


def _published_entries(log_file: str) -> list[dict]:
    """Full log entries that actually went live, oldest first."""
    if not os.path.exists(log_file):
        return []
    try:
        with open(log_file) as f:
            entries = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    return [e for e in entries if e.get("status") == "published" and e.get("topic")]


def _published_topics(log_file: str) -> list[str]:
    """Topics that actually went live, oldest first. Failed posts don't count."""
    if not os.path.exists(log_file):
        return []
    try:
        with open(log_file) as f:
            entries = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    return [
        e["topic"] for e in entries
        if e.get("status") == "published" and e.get("topic")
    ]


def pick_topic(pool: list[dict], log_file: str) -> dict:
    """
    Choose the next topic from `pool`.

    Unused topics come first, in pool order. Once everything has run at least
    once, the least recently published one wins.
    """
    if not pool:
        raise ValueError("topic pool is empty")

    published = _published_topics(log_file)

    unused = [t for t in pool if t["topic"] not in published]
    if unused:
        return unused[0]

    # Everything has run — fall back to whatever has been idle longest.
    # A later index in `published` means more recently posted.
    last_used = {topic: i for i, topic in enumerate(published)}
    return min(pool, key=lambda t: last_used.get(t["topic"], -1))


def _underused_pillars(log_file: str, pillars: list[str], window: int = 12) -> list[str]:
    """Pillars least covered across the recent posts, least-covered first."""
    recent = _published_entries(log_file)[-window:]
    counts = Counter(e.get("pillar") for e in recent if e.get("pillar"))
    return sorted(pillars, key=lambda p: counts.get(p, 0))


def generate_topic(
    client,
    *,
    log_file: str,
    pillars: list[str],
    profile: str,
    style: str,
    fallback_pool: list[dict],
    model: str = "claude-sonnet-4-6",
    attempts: int = 3,
) -> dict:
    """
    Ask Claude for a fresh topic that hasn't been covered yet.

    A fixed pool eventually runs dry — Aakash's 22 text topics were fully
    exhausted in seven weeks, after which every post was a repeat. Generating
    per-run removes that ceiling.

    Falls back to rotating the static pool if generation fails or keeps
    producing near-duplicates, so a bad API call can never block a post.
    """
    published = _published_topics(log_file)
    priority = _underused_pillars(log_file, pillars)
    recent = published[-25:]

    avoid = "\n".join(f"- {t}" for t in recent) or "- (nothing published yet)"

    prompt = f"""Generate ONE new LinkedIn post topic for Aakash Gupta.

ABOUT AAKASH
{profile}

TOPIC SHAPE REQUIRED
{style}

PILLARS, least-covered first — prefer the ones near the top:
{", ".join(priority)}

ALREADY PUBLISHED — the new topic must not overlap with any of these,
not even as a rewording:
{avoid}

Return ONLY valid JSON:
{{"topic": "the topic line", "pillar": "one of the pillars above", "type": "insight | how-to | tips | problem-solution | personal"}}

Rules:
- Concrete and specific. "Google Ads tips" is useless; "Why Performance Max eats your branded search" is a topic.
- It must be something Aakash can speak to from hands-on experience with Indian SMEs and e-commerce brands.
- Professional English. No Hinglish. No hashtags. No emojis.
- Do not number it or add quotes around it.

Return only the JSON, no markdown fences."""

    for _ in range(attempts):
        try:
            msg = client.messages.create(
                model=model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", msg.content[0].text.strip())
            picked = json.loads(raw)
        except Exception as e:
            print(f"  ⚠️  topic generation failed: {e}")
            continue

        topic = (picked.get("topic") or "").strip()
        if not topic:
            continue
        if _too_similar(topic, published):
            print(f"  ↻ too close to an existing topic, retrying: {topic}")
            continue

        picked["topic"] = topic
        picked.setdefault("pillar", priority[0])
        picked.setdefault("type", "insight")
        return picked

    print("  ⚠️  falling back to the static pool")
    return pick_topic(fallback_pool, log_file)
