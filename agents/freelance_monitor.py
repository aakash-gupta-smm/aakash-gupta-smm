"""
Freelance Monitor — Aakash Gupta Personal System
Monitors Gmail for LinkedIn job alerts and drafts proposals.
Sends Aakash the opportunity + a ready-to-send proposal with the apply link.
"""

import os
import json
import imaplib
import email
import smtplib
import re
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import anthropic

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_PASSWORD = os.environ["GMAIL_PASSWORD"]

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

LOG_FILE = "data/freelance_log.json"


def fetch_linkedin_job_emails() -> list[dict]:
    """
    Connect to Gmail via IMAP and fetch unread LinkedIn job alert emails.
    Returns list of {subject, body, links}
    """
    results = []
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASSWORD)
        mail.select("inbox")

        # Search for unread emails from LinkedIn job alerts
        _, data = mail.search(None, '(UNSEEN FROM "jobalerts-noreply@linkedin.com")')
        email_ids = data[0].split()

        for eid in email_ids[-10:]:  # Process last 10 unread alerts
            _, msg_data = mail.fetch(eid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            subject = msg.get("subject", "")
            body = ""

            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
                    elif part.get_content_type() == "text/html" and not body:
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

            # Extract all URLs from body
            urls = re.findall(r'https?://[^\s<>"]+', body)
            linkedin_job_urls = [u for u in urls if "linkedin.com/jobs" in u]

            results.append({
                "subject": subject,
                "body": body[:2000],
                "apply_links": linkedin_job_urls[:5]
            })

            # Mark as read
            mail.store(eid, '+FLAGS', '\\Seen')

        mail.close()
        mail.logout()

    except Exception as e:
        print(f"  ❌ Gmail IMAP error: {e}")

    return results


def is_relevant_opportunity(subject: str, body: str) -> bool:
    """Quick check if the job alert contains Social Media freelance roles."""
    keywords = [
        "social media", "smm", "social media manager", "content creator",
        "digital marketing", "brand manager", "instagram", "freelance",
        "content strategy", "community manager", "paid social", "meta ads"
    ]
    text = (subject + " " + body).lower()
    return any(kw in text for kw in keywords)


def extract_jobs_from_email(email_body: str, apply_links: list) -> list[dict]:
    """Use Claude to extract individual job listings from the email body."""
    prompt = f"""This is a LinkedIn job alert email. Extract all individual job listings from it.

EMAIL CONTENT:
{email_body[:1500]}

APPLY LINKS FOUND: {apply_links}

For each job listing found, extract:
- Job title
- Company name
- Location (Remote / Hybrid / On-site + city)
- A brief 1-line description if available

Return a JSON array:
[
  {{
    "title": "Social Media Manager",
    "company": "Company Name",
    "location": "Remote",
    "description": "Brief description",
    "apply_link": "linkedin.com/jobs/... or empty string"
  }}
]

Only include Social Media, Digital Marketing, Brand Strategy, or Content related roles.
If no relevant roles found, return an empty array [].
Return only valid JSON."""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        return json.loads(message.content[0].text.strip())
    except Exception:
        return []


def generate_proposal(job_title: str, company: str, description: str) -> str:
    """Generate a ready-to-send proposal for the opportunity."""
    prompt = f"""Write a short, professional LinkedIn connection request message / proposal for this freelance opportunity.

JOB: {job_title} at {company}
DESCRIPTION: {description}

About Aakash Gupta:
- Social Media Manager with 4+ years experience
- Manages social media at Assert IT Solutions
- Experience in Meta Ads, Instagram growth, brand strategy
- Worked across tech, e-commerce, education, logistics
- Currently expanding skills in SEO, WordPress, Shopify, Google Ads
- Based in Ghaziabad, open to remote work
- Email: akashgupta8163@gmail.com

Write a proposal that:
1. Is concise — max 120 words
2. Opens with something specific to their role/company (not "I am interested in...")
3. Mentions 1-2 specific relevant achievements or skills
4. Ends with a clear next step (a question or CTA to connect)
5. Sounds like a real person, not a template
6. Professional English only

Return only the proposal message text."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()


def send_opportunity_email(opportunities: list):
    """Send Aakash an email with all found opportunities and ready proposals."""
    if not opportunities:
        return

    job_sections = ""
    for i, opp in enumerate(opportunities, 1):
        job_sections += f"""
        <div style="background: #1a1a1a; border: 1px solid #333; border-radius: 10px; padding: 24px; margin-bottom: 20px;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
            <div>
              <h3 style="color: white; margin: 0 0 4px 0; font-size: 17px;">{opp['title']}</h3>
              <p style="color: #7c6af7; margin: 0; font-size: 14px;">{opp['company']} · {opp['location']}</p>
            </div>
            <span style="background: #7c6af7; color: white; padding: 4px 12px; border-radius: 40px; font-size: 12px; white-space: nowrap;">#{i}</span>
          </div>

          <p style="color: #999; font-size: 14px; margin-bottom: 20px; line-height: 1.5;">{opp.get('description', '')}</p>

          <div style="background: #111; border-left: 3px solid #7c6af7; padding: 16px 20px; border-radius: 4px; margin-bottom: 16px;">
            <p style="color: #7c6af7; font-size: 11px; letter-spacing: 2px; text-transform: uppercase; margin: 0 0 10px 0;">Ready-to-Send Proposal</p>
            <p style="color: #ddd; font-size: 14px; line-height: 1.7; margin: 0; white-space: pre-wrap;">{opp['proposal']}</p>
          </div>

          {'<a href="' + opp["apply_link"] + '" style="background: #7c6af7; color: white; padding: 10px 24px; border-radius: 40px; text-decoration: none; font-size: 13px; font-weight: 600; display: inline-block;">Apply on LinkedIn →</a>' if opp.get('apply_link') else '<p style="color: #555; font-size: 13px;">Search manually on LinkedIn for this role.</p>'}
        </div>
        """

    html = f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 650px; margin: auto; padding: 20px; background: #f0f0f0;">
    <div style="background: #080808; padding: 32px; border-radius: 12px;">
      <h2 style="color: white; margin: 0 0 4px 0;">🎯 {len(opportunities)} Freelance Opportunit{'y' if len(opportunities)==1 else 'ies'} Found</h2>
      <p style="color: #666; font-size: 13px; margin: 0 0 32px 0;">{datetime.now().strftime('%d %B %Y')} · Social Media Manager roles</p>
      {job_sections}
      <p style="color: #555; font-size: 12px; margin-top: 24px;">Copy the proposal, personalise if needed, and send. Good luck! 🚀</p>
    </div>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🎯 {len(opportunities)} Freelance Opportunit{'y' if len(opportunities)==1 else 'ies'} — {datetime.now().strftime('%d %b')}"
    msg["From"] = f"Aakash's Agent <{GMAIL_USER}>"
    msg["To"] = GMAIL_USER
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, GMAIL_USER, msg.as_string())

    print(f"✅ Sent {len(opportunities)} opportunities to {GMAIL_USER}")


def save_log(opportunities: list):
    os.makedirs("data", exist_ok=True)
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            logs = json.load(f)
    for opp in opportunities:
        logs.append({"date": datetime.now().strftime("%Y-%m-%d"), **opp})
    with open(LOG_FILE, "w") as f:
        json.dump(logs[-100:], f, indent=2)


def run():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Freelance Monitor running...")

    emails = fetch_linkedin_job_emails()
    print(f"  Found {len(emails)} unread LinkedIn job alert email(s)")

    all_opportunities = []

    for e in emails:
        if not is_relevant_opportunity(e["subject"], e["body"]):
            continue

        jobs = extract_jobs_from_email(e["body"], e["apply_links"])
        print(f"  Extracted {len(jobs)} relevant job(s) from: {e['subject'][:60]}")

        for job in jobs:
            proposal = generate_proposal(job["title"], job["company"], job.get("description", ""))
            job["proposal"] = proposal
            all_opportunities.append(job)

    if all_opportunities:
        send_opportunity_email(all_opportunities)
        save_log(all_opportunities)
    else:
        print("  No relevant opportunities found today.")

    print("  Done.")


if __name__ == "__main__":
    run()
