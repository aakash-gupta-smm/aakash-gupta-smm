"""
Engagement Agent — Aakash Gupta Personal System
Runs every weekday morning and emails a LinkedIn engagement brief.

WHY THIS SHAPE:
LinkedIn's API has no post/hashtag search, and scraping the feed to find posts
to comment on violates their ToS (real account-restriction risk). So this agent
does NOT touch LinkedIn at all. Instead it does the part that can be automated
honestly — deciding WHAT to say and WHERE to show up — and leaves the actual
commenting and connecting to Aakash, which takes ~15 minutes.

Each brief contains:
  1. Today's real news in his niche (from public marketing RSS feeds)
  2. A ready comment angle for each story, so he can react fast when it shows up
  3. A rotating slice of his target list — people he wants to be visible to
  4. The daily checklist (5 comments, 10-15 connects)

Usage:
    python agents/engagement_agent.py            # build + send
    python agents/engagement_agent.py --dry-run  # print, don't send
"""

import os
import re
import json
import html
import smtplib
import argparse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import anthropic

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_PASSWORD = os.environ["GMAIL_PASSWORD"]

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

TARGETS_FILE = "data/engagement_targets.json"
LOOKBACK_HOURS = 72

FEEDS = [
    ("Search Engine Land", "https://searchengineland.com/feed"),
    ("Search Engine Journal", "https://www.searchenginejournal.com/feed/"),
    ("SEL — Google Ads", "https://searchengineland.com/library/platforms/google/google-ads/feed"),
]

ACCENT = "#7c6af7"


# ── FEED INGEST ─────────────────────────────────────────────

def _clean(text: str) -> str:
    """RSS descriptions are HTML soup — flatten to plain text."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_feeds() -> list[dict]:
    """Pull recent items across all feeds."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    items: list[dict] = []

    for source, url in FEEDS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                root = ET.fromstring(resp.read())
        except Exception as e:
            print(f"  ⚠️  {source} failed: {e}")
            continue

        for node in root.findall(".//item"):
            pub_raw = node.findtext("pubDate")
            try:
                pub = parsedate_to_datetime(pub_raw)
                if pub.tzinfo is None:
                    pub = pub.replace(tzinfo=timezone.utc)
            except Exception:
                continue

            if pub < cutoff:
                continue

            items.append({
                "source": source,
                "title": _clean(node.findtext("title")),
                "link": (node.findtext("link") or "").strip(),
                "summary": _clean(node.findtext("description"))[:400],
                "published": pub.isoformat(),
            })

    # newest first, de-duped by title
    seen, unique = set(), []
    for it in sorted(items, key=lambda x: x["published"], reverse=True):
        key = it["title"].lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(it)

    return unique


# ── BRIEF GENERATION ────────────────────────────────────────

def build_brief(items: list[dict]) -> dict:
    """Ask Claude to pick the stories worth engaging with and write the angles."""

    condensed = "\n\n".join(
        f"[{i}] {it['title']}\nSource: {it['source']}\nLink: {it['link']}\n{it['summary'][:280]}"
        for i, it in enumerate(items[:28])
    )

    prompt = f"""You are preparing a daily LinkedIn engagement brief for Aakash Gupta.

ABOUT AAKASH
- Digital Marketing Manager, 4+ years, based in Ghaziabad, India
- Hands-on with Google Ads, Meta Ads, SEO, Shopify, social media
- Works with Indian SMEs and e-commerce brands
- Goal: grow LinkedIn reach, attract freelance work (Google Ads / Meta Ads / Shopify),
  and land a full-time Digital Marketing Manager role by Sep-Oct 2026

TODAY'S INDUSTRY NEWS
{condensed}

Pick the 4 stories most worth him engaging with today. Prefer stories that:
- Directly affect Google Ads, Meta Ads, SEO or e-commerce practitioners
- Will actually be discussed on LinkedIn today (platform changes, policy shifts, new features)
- He can speak to credibly from hands-on experience
Skip anything purely US-market, enterprise-only, or too niche for a working practitioner.

Return ONLY valid JSON:
{{
  "stories": [
    {{
      "index": <the [n] number from the list above>,
      "headline": "The story in max 10 words",
      "why": "One sentence on why it matters to an SME-focused marketer",
      "comment_angle": "A 2-3 sentence comment Aakash could leave on someone else's post about this. Written in his voice — specific, from experience, adds something the original post didn't say. Not flattery, not 'Great post!'. No hashtags."
    }}
  ],
  "post_ideas": [
    "A LinkedIn post idea based on today's news. One line.",
    "A second, different one. One line."
  ]
}}

Rules for comment_angle:
- It must add information or a real opinion, not agreement
- Professional English only. No Hinglish. No emojis.
- Never start with 'Great post' or 'Thanks for sharing'
- Sound like a practitioner who has run these campaigns, not a commentator

Return only the JSON. No markdown fences."""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", msg.content[0].text.strip())
    brief = json.loads(raw)

    # attach the real links back onto each pick
    for s in brief.get("stories", []):
        idx = s.get("index")
        if isinstance(idx, int) and 0 <= idx < len(items):
            s["link"] = items[idx]["link"]
            s["source"] = items[idx]["source"]
        else:
            s["link"] = ""
            s["source"] = ""

    return brief


# ── TARGET LIST ─────────────────────────────────────────────

def load_targets() -> list[dict]:
    """
    Aakash's own list of people/pages he wants to be visible to.
    Deliberately seeded empty — inventing LinkedIn URLs would send him to dead links.
    """
    if not os.path.exists(TARGETS_FILE):
        os.makedirs(os.path.dirname(TARGETS_FILE), exist_ok=True)
        with open(TARGETS_FILE, "w") as f:
            json.dump({"targets": []}, f, indent=2)
        return []

    with open(TARGETS_FILE) as f:
        return json.load(f).get("targets", [])


def todays_targets(targets: list[dict], per_day: int = 5) -> list[dict]:
    """Rotate through the list so he isn't hitting the same profiles daily."""
    if not targets:
        return []
    start = (datetime.now().timetuple().tm_yday * per_day) % len(targets)
    return [targets[(start + i) % len(targets)] for i in range(min(per_day, len(targets)))]


# ── EMAIL ───────────────────────────────────────────────────

def render_email(brief: dict, targets: list[dict]) -> str:
    today = datetime.now().strftime("%A, %d %B")

    stories_html = ""
    for i, s in enumerate(brief.get("stories", []), 1):
        link = s.get("link") or "#"
        stories_html += f"""
        <div style="background:#141418;border:1px solid #2a2a32;border-radius:10px;padding:20px;margin-bottom:14px;">
          <div style="color:{ACCENT};font-size:11px;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px;">
            {html.escape(s.get('source',''))}
          </div>
          <div style="color:#fff;font-size:17px;font-weight:600;line-height:1.4;margin-bottom:8px;">
            {i}. {html.escape(s.get('headline',''))}
          </div>
          <div style="color:#9a9aa4;font-size:14px;line-height:1.6;margin-bottom:14px;">
            {html.escape(s.get('why',''))}
          </div>
          <div style="background:#0d0d10;border-left:3px solid {ACCENT};padding:14px 16px;border-radius:0 6px 6px 0;">
            <div style="color:{ACCENT};font-size:11px;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;">
              Comment you can leave
            </div>
            <div style="color:#d8d8e0;font-size:14px;line-height:1.65;">
              {html.escape(s.get('comment_angle',''))}
            </div>
          </div>
          <a href="{html.escape(link)}" style="color:{ACCENT};font-size:13px;text-decoration:none;display:inline-block;margin-top:12px;">
            Read the story &rarr;
          </a>
        </div>"""

    if targets:
        rows = "".join(
            f"""<li style="margin-bottom:10px;">
                  <a href="{html.escape(t.get('url','#'))}" style="color:#fff;text-decoration:none;font-weight:600;">
                    {html.escape(t.get('name','Unknown'))}
                  </a>
                  <span style="color:#7a7a84;font-size:13px;"> — {html.escape(t.get('note',''))}</span>
                </li>"""
            for t in targets
        )
        targets_html = f"""<ul style="color:#ccc;font-size:15px;line-height:1.7;margin:0;padding-left:20px;">{rows}</ul>"""
    else:
        targets_html = f"""
          <div style="color:#9a9aa4;font-size:14px;line-height:1.7;">
            Your target list is empty. Add the people whose audience you want to reach —
            Indian marketers, agency founders, SME owners, recruiters — to
            <code style="color:{ACCENT};">data/engagement_targets.json</code>:
            <pre style="background:#0d0d10;padding:12px;border-radius:6px;color:#9a9aa4;font-size:12px;overflow-x:auto;">{{
  "targets": [
    {{"name": "Person Name",
     "url": "https://linkedin.com/in/...",
     "note": "why they matter"}}
  ]
}}</pre>
          </div>"""

    ideas = "".join(
        f"<li style='margin-bottom:8px;'>{html.escape(p)}</li>"
        for p in brief.get("post_ideas", [])
    )

    return f"""
<html><body style="margin:0;padding:20px;background:#f4f4f6;font-family:-apple-system,Segoe UI,Arial,sans-serif;">
<div style="max-width:640px;margin:auto;background:#08080a;border-radius:14px;padding:32px;">

  <div style="margin-bottom:28px;">
    <div style="color:#fff;font-size:23px;font-weight:700;">LinkedIn Engagement Brief</div>
    <div style="color:#6a6a74;font-size:13px;margin-top:4px;">{today} · 15 minutes</div>
  </div>

  <div style="background:{ACCENT};border-radius:10px;padding:18px 20px;margin-bottom:26px;">
    <div style="color:#fff;font-size:14px;line-height:1.7;">
      <strong>Today's target:</strong> 5 comments · 10-15 connection requests<br/>
      <span style="opacity:.85;font-size:13px;">
        Commenting is what actually grows your reach right now — it puts you in front of
        audiences you don't have yet.
      </span>
    </div>
  </div>

  <div style="color:{ACCENT};font-size:11px;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:14px;">
    What your niche is talking about today
  </div>
  {stories_html}

  <div style="color:{ACCENT};font-size:11px;letter-spacing:1.5px;text-transform:uppercase;margin:28px 0 14px;">
    Profiles to check today
  </div>
  <div style="background:#141418;border:1px solid #2a2a32;border-radius:10px;padding:20px;">
    {targets_html}
  </div>

  <div style="color:{ACCENT};font-size:11px;letter-spacing:1.5px;text-transform:uppercase;margin:28px 0 14px;">
    Post ideas from today's news
  </div>
  <div style="background:#141418;border:1px solid #2a2a32;border-radius:10px;padding:20px;">
    <ul style="color:#ccc;font-size:15px;line-height:1.7;margin:0;padding-left:20px;">{ideas}</ul>
  </div>

  <div style="color:#4a4a54;font-size:12px;margin-top:28px;line-height:1.6;">
    This brief does not touch LinkedIn — commenting and connecting stay manual,
    because automating them risks your account.
  </div>

</div>
</body></html>"""


def send_email(html_body: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"LinkedIn brief — {datetime.now().strftime('%d %b')} · 5 comments, 10 connects"
    msg["From"] = f"Aakash's Engagement Agent <{GMAIL_USER}>"
    msg["To"] = GMAIL_USER
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, GMAIL_USER, msg.as_string())


# ── ENTRY POINT ─────────────────────────────────────────────

def run(dry_run: bool = False):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Engagement Agent running...")

    items = fetch_feeds()
    print(f"  {len(items)} stories in the last {LOOKBACK_HOURS}h")
    if not items:
        print("  Nothing fresh — skipping today.")
        return

    brief = build_brief(items)
    print(f"  Picked {len(brief.get('stories', []))} stories")

    targets = todays_targets(load_targets())
    print(f"  {len(targets)} target profiles for today")

    body = render_email(brief, targets)

    if dry_run:
        out = "data/engagement_preview.html"
        os.makedirs("data", exist_ok=True)
        with open(out, "w") as f:
            f.write(body)
        for s in brief.get("stories", []):
            print(f"\n  • {s.get('headline')}\n    {s.get('comment_angle')}")
        print(f"\n  Preview written to {out} (not sent)")
        return

    send_email(body)
    print(f"  ✅ Brief sent to {GMAIL_USER}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    run(dry_run=ap.parse_args().dry_run)
