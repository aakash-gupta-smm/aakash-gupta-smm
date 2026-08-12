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
import json


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
