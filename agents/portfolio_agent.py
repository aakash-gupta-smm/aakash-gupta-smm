"""
Portfolio Agent — Aakash Gupta Personal System
Every Sunday: emails Aakash asking about new projects/assignments.
When triggered with project details: generates case study and updates portfolio.json.
"""

import os
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import anthropic

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GMAIL_USER = os.environ["GMAIL_USER"]        # akashgupta8163@gmail.com
GMAIL_PASSWORD = os.environ["GMAIL_PASSWORD"]  # Gmail App Password

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

PORTFOLIO_FILE = "portfolio/data/portfolio.json"


def send_weekly_checkin():
    """
    Sends Aakash a weekly check-in email every Sunday.
    Asks about new projects, assignments, or learnings to add to the portfolio.
    """
    subject = "📁 Portfolio Update — Any new projects this week?"
    body = """
    <html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; background: #f9f9f9;">
    <div style="background: #080808; padding: 32px; border-radius: 12px; color: white;">
      <h2 style="margin: 0 0 8px 0; font-size: 22px;">Portfolio Weekly Check-in</h2>
      <p style="color: #888; margin: 0 0 32px 0; font-size: 14px;">Every Sunday · Your Personal Agent</p>

      <p style="font-size: 16px; line-height: 1.6; color: #f0f0f0;">
        Hey Aakash 👋<br/><br/>
        Quick check-in — did anything worth adding to your portfolio happen this week?
      </p>

      <div style="background: #1a1a1a; border: 1px solid #333; border-radius: 10px; padding: 24px; margin: 24px 0;">
        <p style="color: #7c6af7; font-size: 13px; letter-spacing: 1px; text-transform: uppercase; margin: 0 0 16px 0;">Things worth adding:</p>
        <ul style="color: #ccc; font-size: 15px; line-height: 2; margin: 0; padding-left: 20px;">
          <li>A new assignment from your Digital Marketing course</li>
          <li>A social media campaign you ran or optimised</li>
          <li>A brand strategy project you worked on</li>
          <li>A website or Shopify store you built</li>
          <li>An ad campaign with good results</li>
          <li>Any freelance work you completed</li>
        </ul>
      </div>

      <p style="font-size: 15px; color: #ccc; line-height: 1.6;">
        Just reply to this email with a few lines about what you did. I'll turn it into a proper portfolio case study and add it to your site automatically.
      </p>

      <p style="font-size: 13px; color: #555; margin-top: 32px;">
        Your portfolio: <a href="https://yourusername.github.io" style="color: #7c6af7;">yourusername.github.io</a>
      </p>
    </div>
    </body></html>
    """

    _send_email(GMAIL_USER, subject, body)
    print(f"✅ Weekly portfolio check-in sent to {GMAIL_USER}")


def generate_case_study(raw_input: str) -> dict:
    """
    Takes rough project notes from Aakash and generates a proper case study.
    Returns structured dict ready to add to portfolio.json.
    """
    prompt = f"""Aakash Gupta is a Social Media Manager and Brand Strategist. He's provided rough notes about a project he worked on. Turn this into a clean portfolio case study.

RAW NOTES:
{raw_input}

Generate a portfolio case study in this exact JSON format:
{{
  "title": "Clear, specific project title (max 8 words)",
  "category": "Social Media | Paid Ads | Brand Strategy | SEO | Web | Shopify | Course Assignment",
  "emoji": "One relevant emoji",
  "description": "2-3 sentences describing what he did and the result. Specific and professional. No fluff.",
  "highlights": ["Key result or action 1", "Key result or action 2", "Key result or action 3"],
  "tools": ["Tool1", "Tool2"],
  "date": "{datetime.now().strftime('%B %Y')}"
}}

Be specific. Use numbers if mentioned. Keep it professional. Return only valid JSON."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        return json.loads(message.content[0].text.strip())
    except Exception:
        return None


def add_project_to_portfolio(project: dict):
    """Add a new project to portfolio.json."""
    os.makedirs("portfolio/data", exist_ok=True)

    data = {"last_updated": "", "projects": []}
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE) as f:
            data = json.load(f)

    data["projects"].append(project)
    data["last_updated"] = datetime.now().strftime("%Y-%m-%d")

    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"✅ Added to portfolio: {project['title']}")


def _send_email(to: str, subject: str, html_body: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Aakash's Portfolio Agent <{GMAIL_USER}>"
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, to, msg.as_string())


def notify_update(project_title: str):
    """Email Aakash confirming portfolio was updated."""
    subject = f"✅ Portfolio updated — {project_title}"
    body = f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px;">
    <div style="background: #080808; padding: 32px; border-radius: 12px; color: white;">
      <h2 style="color: #7c6af7; margin: 0 0 16px 0;">Portfolio Updated ✅</h2>
      <p style="color: #ccc; font-size: 16px; line-height: 1.6;">
        <strong style="color: white;">"{project_title}"</strong> has been added to your portfolio.
      </p>
      <p style="margin-top: 24px;">
        <a href="https://yourusername.github.io" style="background: #7c6af7; color: white; padding: 12px 28px; border-radius: 40px; text-decoration: none; font-size: 14px; font-weight: 600;">View Your Portfolio →</a>
      </p>
    </div>
    </body></html>
    """
    _send_email(GMAIL_USER, subject, body)


# ── Entry points ────────────────────────────────────────────

def run_weekly_checkin():
    """Called every Sunday by GitHub Actions."""
    send_weekly_checkin()


def run_add_project(raw_notes: str):
    """
    Called when Aakash replies to the check-in email with project details.
    raw_notes: the text from his reply email
    """
    print(f"Generating case study from notes...")
    project = generate_case_study(raw_notes)

    if project:
        add_project_to_portfolio(project)
        notify_update(project["title"])
    else:
        print("❌ Could not parse project from notes.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "checkin":
        run_weekly_checkin()
    elif len(sys.argv) > 1:
        # Pass raw notes as argument for testing
        run_add_project(" ".join(sys.argv[1:]))
    else:
        run_weekly_checkin()
