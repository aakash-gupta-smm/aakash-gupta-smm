"""
LinkedIn Agent — Aakash Gupta Personal System
Generates and posts content 3x per week (Mon/Wed/Fri).
Uses LinkedIn API (OAuth token) — no password needed.
"""

import os
import json
import random
import requests
from datetime import datetime
import anthropic

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
LINKEDIN_ACCESS_TOKEN = os.environ["LINKEDIN_ACCESS_TOKEN"]
LINKEDIN_PERSON_URN = os.environ["LINKEDIN_PERSON_URN"]  # urn:li:person:XXXX

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── CONTENT TOPICS ──────────────────────────────────────────
# Rotates through these so posts stay varied
TOPIC_POOL = [
    # SMM & Strategy
    {"topic": "One thing I've learned about social media strategy that no course teaches you", "pillar": "smm", "type": "insight"},
    {"topic": "Why most brands post every day but still get zero engagement", "pillar": "smm", "type": "problem-solution"},
    {"topic": "How I build a social media strategy for a brand from scratch", "pillar": "smm", "type": "how-to"},
    {"topic": "The difference between posting content and building a brand on social media", "pillar": "smm", "type": "insight"},
    {"topic": "3 Meta Ads mistakes I see Indian SMEs make every single day", "pillar": "paid-ads", "type": "tips"},
    {"topic": "What happens when you optimise for reach instead of results", "pillar": "smm", "type": "insight"},
    # Digital Marketing / Learning
    {"topic": "Why I'm adding SEO, Shopify and WordPress to my skillset in 2026", "pillar": "learning", "type": "personal"},
    {"topic": "The AI tools that are actually changing how I work as a social media manager", "pillar": "ai", "type": "tools"},
    {"topic": "What I wish I knew about paid ads before I ran my first campaign", "pillar": "paid-ads", "type": "personal"},
    {"topic": "How digital marketing is changing with AI — and what that means for marketers", "pillar": "ai", "type": "insight"},
    # Career / Personal Brand
    {"topic": "4 years in social media — here's what actually matters", "pillar": "career", "type": "personal"},
    {"topic": "What no one tells you about working as a social media manager in India", "pillar": "career", "type": "personal"},
    {"topic": "Why I'm building in public — my 2026 learning journey", "pillar": "learning", "type": "personal"},
]


def pick_topic() -> dict:
    """Pick a topic — rotate through pool based on day of week."""
    day = datetime.now().weekday()  # 0=Mon, 2=Wed, 4=Fri
    index = (datetime.now().isocalendar()[1] * 3 + [0, 1, 2].index(day) if day in [0, 2, 4] else 0) % len(TOPIC_POOL)
    return TOPIC_POOL[index]


def generate_linkedin_post(topic: str, pillar: str, post_type: str) -> str:
    """Generate a LinkedIn post using Claude."""

    prompt = f"""Write a LinkedIn post for Aakash Gupta, a Social Media Manager and Brand Strategist from Ghaziabad, India.

TOPIC: {topic}
PILLAR: {pillar}
TYPE: {post_type}

About Aakash:
- 4+ years experience in social media management
- Currently managing social media at Assert IT Solutions
- Experience across tech, e-commerce, education and logistics
- Currently learning Digital Marketing with AI (WordPress, SEO, Shopify, Google Ads, Meta Ads)
- Based in Ghaziabad, open to remote freelance and full-time roles

Write a LinkedIn post that:
1. Starts with a strong hook (first line must stop the scroll — a bold statement, surprising fact, or direct question)
2. Uses short paragraphs — max 2-3 lines each
3. Feels personal and real — written from his own experience, not generic advice
4. Is informative but not preachy
5. Ends with either a question to spark comments OR a clear CTA (DM me, follow for more, etc.)
6. Uses line breaks and white space — LinkedIn posts with breathing room get more reads
7. Length: 150-250 words maximum
8. Professional English only. No Hinglish.
9. Add 3-5 relevant hashtags at the end

Do NOT:
- Start with "I am excited to share..."
- Use corporate buzzwords like "leverage", "synergy", "passionate about"
- Sound like a press release
- Add emojis in every line — use sparingly, only where it genuinely adds value

Return only the post text. Nothing else."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()


def post_to_linkedin(post_text: str) -> bool:
    """Post to LinkedIn using the Share API."""
    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    payload = {
        "author": LINKEDIN_PERSON_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": post_text},
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code in (200, 201):
        print(f"✅ LinkedIn post published successfully.")
        return True
    else:
        print(f"❌ LinkedIn post failed: {resp.status_code} — {resp.text}")
        return False


def save_post_log(topic: str, post_text: str, success: bool):
    """Save post to log file for dashboard."""
    log_file = "data/linkedin_log.json"
    os.makedirs("data", exist_ok=True)

    logs = []
    if os.path.exists(log_file):
        with open(log_file) as f:
            logs = json.load(f)

    logs.append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "topic": topic,
        "post": post_text,
        "status": "published" if success else "failed"
    })

    # Keep last 50
    with open(log_file, "w") as f:
        json.dump(logs[-50:], f, indent=2)


def run():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] LinkedIn Agent running...")

    topic_data = pick_topic()
    topic = topic_data["topic"]
    pillar = topic_data["pillar"]
    post_type = topic_data["type"]

    print(f"  Topic: {topic}")
    post_text = generate_linkedin_post(topic, pillar, post_type)
    print(f"  Generated post ({len(post_text)} chars)")

    success = post_to_linkedin(post_text)
    save_post_log(topic, post_text, success)

    print(f"  Done.")


if __name__ == "__main__":
    run()
