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
# Positioned as Digital Marketing Manager targeting Shopify, Google Ads, Meta Ads freelance work
# and a full-time DM Manager switch by Sep-Oct 2026
TOPIC_POOL = [
    # Google Ads
    {"topic": "3 Google Ads mistakes that burn budget without anyone noticing", "pillar": "google-ads", "type": "tips"},
    {"topic": "How I structure a Google Ads campaign for a brand new business with zero history", "pillar": "google-ads", "type": "how-to"},
    {"topic": "Why most small businesses waste their first Google Ads budget — and how to fix it", "pillar": "google-ads", "type": "problem-solution"},
    {"topic": "Search vs Performance Max — which one should Indian SMEs actually run?", "pillar": "google-ads", "type": "insight"},

    # Meta Ads
    {"topic": "3 Meta Ads mistakes I see Indian SMEs make every single day", "pillar": "meta-ads", "type": "tips"},
    {"topic": "How I set up a Meta Ads funnel for an e-commerce brand from scratch", "pillar": "meta-ads", "type": "how-to"},
    {"topic": "Why your Meta Ads are getting clicks but zero sales", "pillar": "meta-ads", "type": "problem-solution"},
    {"topic": "The Meta Ads targeting mistake that kills ROAS before the campaign even starts", "pillar": "meta-ads", "type": "insight"},

    # Shopify & E-commerce
    {"topic": "What I check first when a Shopify store isn't converting despite good traffic", "pillar": "shopify", "type": "how-to"},
    {"topic": "5 Shopify store mistakes that silently kill conversions", "pillar": "shopify", "type": "tips"},
    {"topic": "How to set up a Shopify store that's actually built to convert — not just look good", "pillar": "shopify", "type": "how-to"},

    # SEO
    {"topic": "Why most business owners think SEO is dead — and why they're wrong", "pillar": "seo", "type": "insight"},
    {"topic": "The 3 SEO basics that move the needle for small businesses in 2026", "pillar": "seo", "type": "tips"},
    {"topic": "How I approach SEO for a brand new website with zero domain authority", "pillar": "seo", "type": "how-to"},

    # Digital Marketing Strategy (full-funnel)
    {"topic": "The difference between running ads and building a digital marketing strategy", "pillar": "strategy", "type": "insight"},
    {"topic": "How I plan a full-funnel digital marketing strategy for an Indian SME", "pillar": "strategy", "type": "how-to"},
    {"topic": "Why digital marketing without data is just expensive guesswork", "pillar": "strategy", "type": "insight"},

    # AI & Tools
    {"topic": "The AI tools that are actually changing how I work as a digital marketer", "pillar": "ai", "type": "tools"},
    {"topic": "How I use AI to cut my campaign reporting time by 70%", "pillar": "ai", "type": "tools"},

    # Career / Personal Brand
    {"topic": "4 years in marketing — what I wish I knew before running my first paid campaign", "pillar": "career", "type": "personal"},
    {"topic": "Why I'm expanding from social media to full-stack digital marketing in 2026", "pillar": "career", "type": "personal"},
    {"topic": "What no one tells you about becoming a Digital Marketing Manager in India", "pillar": "career", "type": "personal"},
]


def pick_topic() -> dict:
    """Pick a topic — rotate through pool based on week number."""
    week = datetime.now().isocalendar()[1]
    day = datetime.now().weekday()  # 0=Mon, 2=Wed, 4=Fri
    slot = {0: 0, 2: 1, 4: 2}.get(day, 0)
    index = (week * 3 + slot) % len(TOPIC_POOL)
    return TOPIC_POOL[index]


def generate_linkedin_post(topic: str, pillar: str, post_type: str) -> str:
    """Generate a LinkedIn post using Claude."""

    prompt = f"""Write a LinkedIn post for Aakash Gupta, a Digital Marketing Manager from Ghaziabad, India.

TOPIC: {topic}
PILLAR: {pillar}
TYPE: {post_type}

About Aakash:
- 4+ years experience in digital marketing — social media, paid ads, SEO, and e-commerce
- Currently working as Digital Marketing Manager at Assert IT Solutions
- Hands-on experience with Google Ads, Meta Ads, Shopify, SEO, and content strategy
- Has worked across tech, e-commerce, education and logistics sectors
- Open to freelance projects (Google Ads, Meta Ads, Shopify) and full-time Digital Marketing Manager roles (targeting Sep-Oct 2026 switch)
- Based in Ghaziabad, open to remote work

GOAL OF THIS POST:
Position Aakash as a skilled, experienced Digital Marketing Manager — not just a social media person.
The post should attract: (a) freelance clients who need Google Ads, Meta Ads, or Shopify help, and/or (b) recruiters/companies looking for a Digital Marketing Manager.
Every post should subtly signal expertise across the full digital marketing spectrum.

Write a LinkedIn post that:
1. Starts with a strong hook (first line must stop the scroll — a bold statement, surprising fact, or direct question)
2. Uses short paragraphs — max 2-3 lines each
3. Feels personal and real — written from his own experience, not generic advice
4. Is informative but not preachy
5. Ends with either a question to spark comments OR a clear CTA (DM me for a free audit, let's connect, etc.)
6. Uses line breaks and white space — LinkedIn posts with breathing room get more reads
7. Length: 150-250 words maximum
8. Professional English only. No Hinglish.
9. Add 3-5 relevant hashtags at the end

Do NOT:
- Start with "I am excited to share..."
- Use corporate buzzwords like "leverage", "synergy", "passionate about"
- Sound like a press release
- Add emojis in every line — use sparingly, only where it genuinely adds value
- Sound like a beginner or someone still learning — he knows this stuff and has done it

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
