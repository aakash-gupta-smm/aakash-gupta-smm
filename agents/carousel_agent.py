"""
Carousel Agent — Aakash Gupta Personal System
Generates a LinkedIn carousel (PDF document post) and publishes it.

LinkedIn weights document posts heavily for dwell time — they consistently
outreach plain text posts. This agent turns list-shaped topics into swipeable
carousels.

Usage:
    python agents/carousel_agent.py            # generate + post
    python agents/carousel_agent.py --dry-run  # generate PDF only, no posting
"""

import os
import re
import json
import argparse
import requests
from datetime import datetime

import anthropic
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color
from reportlab.lib.utils import simpleSplit

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── DESIGN TOKENS ───────────────────────────────────────────
SIZE = 1080                      # square carousel, best mobile fill
BG = (0.04, 0.04, 0.05)          # near-black
ACCENT = (0.486, 0.416, 0.969)   # #7C6AF7 — matches portfolio
WHITE = (1, 1, 1)
MUTED = (0.62, 0.62, 0.66)
MARGIN = 90

# ── CAROUSEL TOPICS ─────────────────────────────────────────
# Only list-shaped topics — these are the ones that work as carousels.
CAROUSEL_POOL = [
    {"topic": "5 Google Ads mistakes that quietly burn your budget", "pillar": "google-ads"},
    {"topic": "5 Meta Ads mistakes Indian SMEs make every day", "pillar": "meta-ads"},
    {"topic": "5 Shopify store mistakes that silently kill conversions", "pillar": "shopify"},
    {"topic": "6 SEO basics that actually move the needle in 2026", "pillar": "seo"},
    {"topic": "How to structure a Google Ads account from scratch — 6 steps", "pillar": "google-ads"},
    {"topic": "5 reasons your Meta Ads get clicks but no sales", "pillar": "meta-ads"},
    {"topic": "6 things I check before scaling any ad campaign", "pillar": "strategy"},
    {"topic": "5 landing page mistakes that waste your ad spend", "pillar": "strategy"},
    {"topic": "How to plan a full-funnel strategy for an SME — 6 steps", "pillar": "strategy"},
    {"topic": "6 AI tools I actually use as a digital marketer", "pillar": "ai"},
]


def pick_topic() -> dict:
    """Rotate through the pool by week number."""
    week = datetime.now().isocalendar()[1]
    return CAROUSEL_POOL[week % len(CAROUSEL_POOL)]


# ── CONTENT GENERATION ──────────────────────────────────────

def generate_carousel(topic: str, pillar: str) -> dict:
    """Ask Claude for structured carousel slides + the post caption."""

    prompt = f"""Create a LinkedIn carousel for Aakash Gupta, a Digital Marketing Manager from Ghaziabad, India.

TOPIC: {topic}
PILLAR: {pillar}

About Aakash:
- 4+ years in digital marketing — Google Ads, Meta Ads, SEO, Shopify, social media
- Digital Marketing Manager at Assert IT Solutions
- Works with Indian SMEs and e-commerce brands
- Open to freelance projects and full-time Digital Marketing Manager roles

Return ONLY valid JSON in exactly this shape:
{{
  "hook": "Cover slide headline. Max 9 words. Must stop the scroll.",
  "subhook": "One supporting line for the cover. Max 12 words.",
  "slides": [
    {{"title": "Short punchy point. Max 6 words.", "body": "2 sentences explaining it concretely. Specific, not generic."}}
  ],
  "cta": "Closing slide line. Max 10 words.",
  "caption": "The LinkedIn post caption that goes with this carousel. 80-120 words. Strong first line, short paragraphs, ends with a question or soft CTA. Professional English only, no Hinglish. 3-5 hashtags at the end."
}}

Rules:
- Give between 5 and 7 slides (match the number in the topic if stated)
- Each slide must teach something concrete — real numbers, real settings, real mistakes
- Write from lived experience, not textbook theory
- No corporate buzzwords (leverage, synergy, passionate about)
- Professional English only. No Hinglish.
- Do not sound like a beginner — he has done this work

Return only the JSON. No markdown fences, no commentary."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)  # strip fences if present
    return json.loads(raw)


# ── PDF RENDERING ───────────────────────────────────────────

def _wrap(text: str, font: str, size: int, width: int) -> list[str]:
    return simpleSplit(text, font, size, width)


# Glow anchors — rotated per slide so the deck doesn't feel like one flat template
_GLOW_SPOTS = [
    (SIZE * 0.82, SIZE * 0.84),
    (SIZE * 0.14, SIZE * 0.24),
    (SIZE * 0.90, SIZE * 0.30),
    (SIZE * 0.20, SIZE * 0.86),
]


def _glow(c: canvas.Canvas, cx: float, cy: float, radius: float,
          rgb=ACCENT, steps: int = 52, per_ring: float = 0.011):
    """
    Soft radial glow built from stacked translucent circles.

    PDF shading patterns ignore alpha, so a real radialGradient renders as a
    solid blob. Stacking low-alpha circles gives a genuine falloff instead.
    """
    for i in range(steps):
        t = i / steps                       # 0 = outermost ring
        c.setFillColor(Color(*rgb, alpha=per_ring))
        c.circle(cx, cy, radius * (1 - t), fill=1, stroke=0)


def _paint_bg(c: canvas.Canvas, index: int = 0):
    """Black base + soft accent glow + dot grid + corner rules."""
    # base
    c.setFillColorRGB(*BG)
    c.rect(0, 0, SIZE, SIZE, fill=1, stroke=0)

    # soft accent glow, anchored somewhere different on each slide
    gx, gy = _GLOW_SPOTS[index % len(_GLOW_SPOTS)]
    _glow(c, gx, gy, SIZE * 0.58)

    # fine dot grid for texture
    c.setFillColor(Color(1, 1, 1, alpha=0.045))
    step = 54
    for x in range(step, SIZE, step):
        for y in range(step, SIZE, step):
            c.circle(x, y, 1.5, fill=1, stroke=0)

    # hairline corner rules
    c.setStrokeColor(Color(1, 1, 1, alpha=0.10))
    c.setLineWidth(1)
    c.line(SIZE - MARGIN, SIZE - MARGIN + 40, SIZE - MARGIN, SIZE - MARGIN - 40)
    c.line(MARGIN - 40, MARGIN, MARGIN + 40, MARGIN)

    # alpha lives in the graphics state — reset it or every later draw inherits it
    c.setFillAlpha(1)
    c.setStrokeAlpha(1)


def _draw_slide_number(c: canvas.Canvas, n: int, total: int):
    c.setFillColorRGB(*MUTED)
    c.setFont("Helvetica", 26)
    c.drawRightString(SIZE - MARGIN, MARGIN - 30, f"{n}/{total}")


def _draw_footer(c: canvas.Canvas):
    c.setFillColorRGB(*MUTED)
    c.setFont("Helvetica", 24)
    c.drawString(MARGIN, MARGIN - 30, "Aakash Gupta  ·  Digital Marketing Manager")


def render_pdf(data: dict, path: str) -> str:
    """Render the carousel to a square PDF."""
    slides = data["slides"]
    total = len(slides) + 2  # cover + content + cta

    c = canvas.Canvas(path, pagesize=(SIZE, SIZE))
    content_w = SIZE - (MARGIN * 2)

    # ── Cover slide ──
    _paint_bg(c, 0)
    c.setFillColorRGB(*ACCENT)
    c.rect(MARGIN, SIZE - MARGIN - 12, 110, 12, fill=1, stroke=0)

    y = SIZE - 300
    c.setFillColorRGB(*WHITE)
    for line in _wrap(data["hook"], "Helvetica-Bold", 82, content_w):
        c.setFont("Helvetica-Bold", 82)
        c.drawString(MARGIN, y, line)
        y -= 96

    y -= 30
    c.setFillColorRGB(*MUTED)
    for line in _wrap(data["subhook"], "Helvetica", 38, content_w):
        c.setFont("Helvetica", 38)
        c.drawString(MARGIN, y, line)
        y -= 50

    c.setFillColorRGB(*ACCENT)
    c.setFont("Helvetica-Bold", 30)
    c.drawString(MARGIN, MARGIN + 20, "Swipe →")
    _draw_footer(c)
    c.showPage()

    # ── Content slides ──
    for i, s in enumerate(slides, start=1):
        _paint_bg(c, i)

        # oversized ghosted numeral, bleeding off the right edge
        c.setFillColor(Color(1, 1, 1, alpha=0.05))
        c.setFont("Helvetica-Bold", 460)
        c.drawRightString(SIZE + 40, 90, str(i))
        c.setFillAlpha(1)

        # accent number badge
        c.setFillColorRGB(*ACCENT)
        c.circle(MARGIN + 34, SIZE - MARGIN - 60, 38, fill=1, stroke=0)
        c.setFillColorRGB(*WHITE)
        c.setFont("Helvetica-Bold", 40)
        c.drawCentredString(MARGIN + 34, SIZE - MARGIN - 74, str(i))

        title_lines = _wrap(s["title"], "Helvetica-Bold", 66, content_w)
        body_lines = _wrap(s["body"], "Helvetica", 38, content_w)

        # optically centre the text block between badge and footer
        block_h = len(title_lines) * 80 + 40 + len(body_lines) * 54
        y = (SIZE + block_h) / 2 - 40

        c.setFillColorRGB(*WHITE)
        c.setFont("Helvetica-Bold", 66)
        for line in title_lines:
            c.drawString(MARGIN, y, line)
            y -= 80

        y -= 40
        c.setFillColorRGB(*MUTED)
        c.setFont("Helvetica", 38)
        for line in body_lines:
            c.drawString(MARGIN, y, line)
            y -= 54

        _draw_slide_number(c, i + 1, total)
        _draw_footer(c)
        c.showPage()

    # ── CTA slide ──
    _paint_bg(c, len(slides) + 1)
    cta_lines = _wrap(data["cta"], "Helvetica-Bold", 72, content_w)
    block_h = len(cta_lines) * 86 + 110
    y = (SIZE + block_h) / 2

    c.setFillColorRGB(*WHITE)
    c.setFont("Helvetica-Bold", 72)
    for line in cta_lines:
        c.drawString(MARGIN, y, line)
        y -= 86

    y -= 40
    c.setFillColorRGB(*ACCENT)
    c.setFont("Helvetica-Bold", 40)
    c.drawString(MARGIN, y, "Follow for more →")

    y -= 70
    c.setFillColorRGB(*MUTED)
    c.setFont("Helvetica", 32)
    c.drawString(MARGIN, y, "Google Ads · Meta Ads · SEO · Shopify")

    _draw_slide_number(c, total, total)
    _draw_footer(c)
    c.showPage()

    c.save()
    return path


# ── LINKEDIN DOCUMENT POST ──────────────────────────────────

def post_carousel(pdf_path: str, caption: str, title: str) -> bool:
    """Upload the PDF as a LinkedIn document and publish it as a post."""
    token = os.environ["LINKEDIN_ACCESS_TOKEN"]
    urn = os.environ["LINKEDIN_PERSON_URN"]

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202411",
    }

    # 1. initialize upload
    init = requests.post(
        "https://api.linkedin.com/rest/documents?action=initializeUpload",
        headers={**headers, "Content-Type": "application/json"},
        json={"initializeUploadRequest": {"owner": urn}},
    )
    if init.status_code not in (200, 201):
        print(f"❌ initializeUpload failed: {init.status_code} — {init.text}")
        return False

    value = init.json()["value"]
    upload_url = value["uploadUrl"]
    document_urn = value["document"]

    # 2. upload the bytes
    with open(pdf_path, "rb") as f:
        up = requests.put(
            upload_url,
            headers={"Authorization": f"Bearer {token}"},
            data=f.read(),
        )
    if up.status_code not in (200, 201):
        print(f"❌ document upload failed: {up.status_code} — {up.text}")
        return False

    # 3. create the post
    post = requests.post(
        "https://api.linkedin.com/rest/posts",
        headers={**headers, "Content-Type": "application/json"},
        json={
            "author": urn,
            "commentary": caption,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "content": {"media": {"id": document_urn, "title": title}},
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        },
    )
    if post.status_code in (200, 201):
        print("✅ Carousel published successfully.")
        return True

    print(f"❌ post creation failed: {post.status_code} — {post.text}")
    return False


# ── LOGGING ─────────────────────────────────────────────────

def save_log(topic: str, data: dict, success: bool):
    log_file = "data/carousel_log.json"
    os.makedirs("data", exist_ok=True)

    logs = []
    if os.path.exists(log_file):
        with open(log_file) as f:
            logs = json.load(f)

    logs.append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "topic": topic,
        "hook": data["hook"],
        "slides": len(data["slides"]),
        "caption": data["caption"],
        "status": "published" if success else "failed",
    })

    with open(log_file, "w") as f:
        json.dump(logs[-50:], f, indent=2)


# ── ENTRY POINT ─────────────────────────────────────────────

def run(dry_run: bool = False):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Carousel Agent running...")

    picked = pick_topic()
    topic = picked["topic"]
    print(f"  Topic: {topic}")

    data = generate_carousel(topic, picked["pillar"])
    print(f"  Generated {len(data['slides'])} slides")
    print(f"  Hook: {data['hook']}")

    os.makedirs("data/carousels", exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower())[:40].strip("-")
    pdf_path = f"data/carousels/{datetime.now().strftime('%Y%m%d')}-{slug}.pdf"
    render_pdf(data, pdf_path)
    print(f"  PDF: {pdf_path}")

    if dry_run:
        print("  Dry run — not posting.")
        return pdf_path

    success = post_carousel(pdf_path, data["caption"], data["hook"])
    save_log(topic, data, success)
    print("  Done.")
    return pdf_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="generate PDF without posting")
    args = ap.parse_args()
    run(dry_run=args.dry_run)
