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

from topic_rotation import generate_topic

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# LinkedIn versions EXPIRE — they only keep a rolling set active, and a stale one
# fails the whole flow at step 1 with 426 NONEXISTENT_VERSION. If that happens,
# probe for a live version (POST initializeUpload against 2026xx candidates) and
# bump this. Verified active: 202508, 202503, 202502.
LINKEDIN_VERSION = "202508"

LOG_FILE = "data/carousel_log.json"

# ── DESIGN TOKENS ───────────────────────────────────────────
SIZE = 1080                      # square carousel, best mobile fill
BG = (0.035, 0.035, 0.043)       # near-black
ACCENT = (0.486, 0.416, 0.969)   # #7C6AF7 — matches portfolio
ACCENT2 = (0.157, 0.310, 0.855)  # #2850DA — cooler blue for the mesh
WHITE = (1, 1, 1)
MUTED = (0.66, 0.66, 0.72)
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


PILLARS = ["google-ads", "meta-ads", "shopify", "seo", "strategy", "ai", "analytics"]

PROFILE = """- Digital Marketing Manager, 5+ years, based in Ghaziabad, India
- Hands-on with Google Ads, Meta Ads, SEO, Shopify, social media
- Has worked with 20+ brands across tech, e-commerce, education and logistics
- Targets Indian SMEs and e-commerce brands"""

CAROUSEL_STYLE = """A list-shaped topic that works as a swipeable carousel — it must
have a countable structure, e.g. "5 X mistakes...", "6 steps to...", "4 things I check
before...". State the number in the topic. Between 5 and 7 items."""


def pick_topic() -> dict:
    """Generate a fresh carousel topic; the static pool is only a fallback."""
    return generate_topic(
        client,
        log_file=LOG_FILE,
        pillars=PILLARS,
        profile=PROFILE,
        style=CAROUSEL_STYLE,
        fallback_pool=CAROUSEL_POOL,
    )


# ── CONTENT GENERATION ──────────────────────────────────────

def generate_carousel(topic: str, pillar: str) -> dict:
    """Ask Claude for structured carousel slides + the post caption."""

    prompt = f"""Create a LinkedIn carousel for Aakash Gupta, a Digital Marketing Manager from Ghaziabad, India.

TOPIC: {topic}
PILLAR: {pillar}

About Aakash:
- 5+ years in digital marketing — Google Ads, Meta Ads, SEO, Shopify, social media
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


# Per-slide mesh layouts: (primary glow, secondary glow) as (x%, y%, radius%)
_MESH = [
    ((0.86, 0.86, 0.62), (0.10, 0.20, 0.44)),
    ((0.12, 0.22, 0.60), (0.90, 0.78, 0.42)),
    ((0.92, 0.28, 0.58), (0.16, 0.82, 0.46)),
    ((0.18, 0.84, 0.60), (0.86, 0.22, 0.44)),
]


def _glow(c: canvas.Canvas, cx: float, cy: float, radius: float,
          rgb=ACCENT, steps: int = 60, per_ring: float = 0.026):
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
    """Black base + two-tone mesh glow + grid + orbit rings."""
    # base
    c.setFillColorRGB(*BG)
    c.rect(0, 0, SIZE, SIZE, fill=1, stroke=0)

    primary, secondary = _MESH[index % len(_MESH)]

    # two-tone mesh glow — purple lead, blue support
    px, py, pr = primary
    _glow(c, SIZE * px, SIZE * py, SIZE * pr, rgb=ACCENT, per_ring=0.026)

    sx, sy, sr = secondary
    _glow(c, SIZE * sx, SIZE * sy, SIZE * sr, rgb=ACCENT2, per_ring=0.020)

    # structural grid lines
    c.setStrokeColor(Color(1, 1, 1, alpha=0.035))
    c.setLineWidth(1)
    for g in range(135, SIZE, 135):
        c.line(g, 0, g, SIZE)
        c.line(0, g, SIZE, g)

    # dot grid on the intersections for texture
    c.setFillColor(Color(1, 1, 1, alpha=0.10))
    for x in range(135, SIZE, 135):
        for y in range(135, SIZE, 135):
            c.circle(x, y, 2.4, fill=1, stroke=0)

    # large concentric orbit rings, centred on the primary glow
    c.setStrokeColor(Color(1, 1, 1, alpha=0.055))
    c.setLineWidth(1.4)
    for r in (SIZE * 0.30, SIZE * 0.46, SIZE * 0.62):
        c.circle(SIZE * px, SIZE * py, r, fill=0, stroke=1)

    # accent rule in the top-right corner
    c.setStrokeColor(Color(*ACCENT, alpha=0.55))
    c.setLineWidth(3)
    c.line(SIZE - MARGIN - 70, SIZE - MARGIN + 34, SIZE - MARGIN, SIZE - MARGIN + 34)

    # readability scrim — text is left-aligned, so darken the left column and
    # let the mesh stay bright on the right where nothing is set.
    # Nested rects all anchored at x=0: the alpha accumulates toward the left
    # with no seams. Abutting strips would band visibly instead.
    layers = 44
    for i in range(layers):
        c.setFillColor(Color(0, 0, 0, alpha=0.016))
        c.rect(0, 0, SIZE * 0.88 * (1 - i / layers), SIZE, fill=1, stroke=0)

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
        "LinkedIn-Version": LINKEDIN_VERSION,
    }

    # 1. initialize upload
    init = requests.post(
        "https://api.linkedin.com/rest/documents?action=initializeUpload",
        headers={**headers, "Content-Type": "application/json"},
        json={"initializeUploadRequest": {"owner": urn}},
    )
    if init.status_code not in (200, 201):
        print(f"❌ initializeUpload failed: {init.status_code} — {init.text}")
        if init.status_code == 426:
            print("   → LinkedIn-Version has expired. Probe for a live version and bump LINKEDIN_VERSION.")
        return False

    value = init.json()["value"]
    upload_url = value["uploadUrl"]
    document_urn = value["document"]

    # 2. upload the bytes.
    # Content-Type is REQUIRED here — the pre-signed URL 400s without it, and
    # requests does not set one automatically for a raw bytes body.
    with open(pdf_path, "rb") as f:
        up = requests.put(
            upload_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/pdf",
            },
            data=f.read(),
        )
    if up.status_code not in (200, 201):
        print(f"❌ document upload failed: {up.status_code} — {up.text[:300]}")
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

def save_log(topic: str, pillar: str, data: dict, success: bool):
    log_file = LOG_FILE
    os.makedirs("data", exist_ok=True)

    logs = []
    if os.path.exists(log_file):
        with open(log_file) as f:
            logs = json.load(f)

    logs.append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "topic": topic,
        "pillar": pillar,
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
    pillar = picked["pillar"]
    print(f"  Topic: {topic}  [{pillar}]")

    data = generate_carousel(topic, pillar)
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
    save_log(topic, pillar, data, success)

    if not success:
        # Exit non-zero so the workflow goes red. Returning 0 here is how the
        # earlier failures stayed invisible for days.
        raise SystemExit("Carousel failed to publish — see the error above.")

    print("  Done.")
    return pdf_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="generate PDF without posting")
    args = ap.parse_args()
    run(dry_run=args.dry_run)
