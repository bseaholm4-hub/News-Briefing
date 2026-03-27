import os
import re
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import requests
import markdown

# ── Config from GitHub Secrets ──────────────────────────────────────
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GMAIL_ADDRESS = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", GMAIL_ADDRESS)

# ── Step 1: Intelligence Gatherer Prompt ────────────────────────────
GATHERER_PROMPT = """You are a Senior Geopolitical Intelligence Analyst specializing in global supply chains and energy security. Your goal is to provide a high-density intelligence brief on the 2026 global crisis.

Focus Areas:
- **Middle East Conflict:** Update on the 5-day pause, Iran power grid status, and Israeli ground movements.
- **China Fuel Export Ban:** Current status of refined fuel exports and impact on the Asia-Pacific region.
- **The 'Total Economic Siege':** Specific updates on the Strait of Hormuz (mines/tolls) and the global fertilizer/food crisis.
- **Supply Chain Data:** Latest Brent crude prices, tanker rates, and any major port disruptions (e.g., Rotterdam cyberattacks).

Constraint: Use Markdown headers. Prioritize data points and actionable intelligence over prose."""

# ── Step 2: Executive Editor Prompt ─────────────────────────────────
EDITOR_PROMPT = """Below is a raw intelligence report from our field analysts. Please rewrite and enhance this for a Chief of Staff at a global logistics firm.

Instructions:
- **Executive Summary:** Start with a 3-bullet 'Bottom Line Up Front' (BLUF).
- **Supply Chain Impact:** Explicitly call out risks to shipping lanes and lead times for high-tech hardware.
- **The 'Delta':** If the input mentions a change from yesterday (e.g., a new port closure or price spike), highlight it in **bold**.
- **Formatting:** Use professional, concise language. Remove all AI conversational filler. Format as a clean, structured report ready for an automated email.

Raw Intelligence to Refine:
"""


def call_gemini(prompt: str) -> str:
    """Call Gemini API and return the response text."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 4096,
        },
    }

    response = requests.post(url, json=payload, timeout=60)
    if not response.ok:
        print(f"Gemini API error {response.status_code}: {response.text}")
        response.raise_for_status()

    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def md_to_html(text: str) -> str:
    """Convert Gemini Markdown output to styled HTML."""
    # Convert markdown → HTML (tables, fenced code, etc.)
    raw_html = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "nl2br"],
    )

    # Strip any rogue Subject/Date lines Gemini sometimes injects at the top
    raw_html = re.sub(
        r"<p>\s*<strong>Subject:.*?</p>", "", raw_html, flags=re.DOTALL
    )
    raw_html = re.sub(
        r"<p>\s*<strong>Date:</strong>.*?</p>", "", raw_html, flags=re.DOTALL
    )
    return raw_html


def send_email(subject: str, body: str):
    """Send an email via Gmail SMTP using an App Password."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = RECIPIENT_EMAIL

    # Plain-text fallback (strip markdown bold markers for readability)
    plain = body.replace("**", "")
    msg.attach(MIMEText(plain, "plain"))

    # Convert Gemini markdown → real HTML
    content_html = md_to_html(body)
    timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    html_body = f"""\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"></head>
<body style="margin:0; padding:0; background:#f4f4f4;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="background:#f4f4f4;">
<tr><td align="center" style="padding:24px 8px;">

  <!-- Main card -->
  <table role="presentation" width="640" cellpadding="0" cellspacing="0"
         style="background:#ffffff; border-radius:8px;
                box-shadow:0 1px 4px rgba(0,0,0,0.08);
                border:1px solid #e2e2e2;">

    <!-- Header banner -->
    <tr>
      <td style="background:#0f172a; padding:20px 32px; border-radius:8px 8px 0 0;">
        <h1 style="margin:0; font-family:'Segoe UI',Helvetica,Arial,sans-serif;
                    font-size:20px; font-weight:600; color:#ffffff;
                    letter-spacing:0.3px;">
          &#128225; DAILY INTELLIGENCE BRIEF
        </h1>
        <p style="margin:6px 0 0; font-family:'Segoe UI',Helvetica,Arial,sans-serif;
                  font-size:13px; color:#94a3b8;">
          {datetime.now().strftime("%A, %B %d, %Y")} &middot; CLASSIFICATION: INTERNAL
        </p>
      </td>
    </tr>

    <!-- Body content -->
    <tr>
      <td style="padding:28px 32px; font-family:'Segoe UI',Helvetica,Arial,sans-serif;
                 font-size:14px; color:#1e293b; line-height:1.7;">

        <style>
          h2 {{ margin:28px 0 10px; font-size:16px; color:#0f172a;
               border-bottom:2px solid #e2e8f0; padding-bottom:6px; }}
          h3 {{ margin:20px 0 6px; font-size:14px; color:#334155; }}
          ul {{ padding-left:20px; margin:8px 0; }}
          li {{ margin-bottom:6px; }}
          strong {{ color:#0f172a; }}
          hr {{ border:none; border-top:1px solid #e2e8f0; margin:24px 0; }}
          table {{ border-collapse:collapse; width:100%; margin:12px 0; }}
          th, td {{ border:1px solid #e2e8f0; padding:8px 12px;
                    font-size:13px; text-align:left; }}
          th {{ background:#f8fafc; font-weight:600; color:#334155; }}
        </style>

        {content_html}

      </td>
    </tr>

    <!-- Footer -->
    <tr>
      <td style="background:#f8fafc; padding:16px 32px;
                 border-top:1px solid #e2e8f0; border-radius:0 0 8px 8px;">
        <p style="margin:0; font-family:'Segoe UI',Helvetica,Arial,sans-serif;
                  font-size:11px; color:#94a3b8;">
          Generated by Gemini&nbsp;2.5&nbsp;Flash &middot; {timestamp}
          <br>This is an automated report. Do not reply.
        </p>
      </td>
    </tr>

  </table>
</td></tr>
</table>
</body>
</html>"""
    msg.attach(MIMEText(html_body, "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, RECIPIENT_EMAIL, msg.as_string())


def main():
    today = datetime.now().strftime("%A, %B %d, %Y")
    print(f"Running daily Gemini automation — {today}")

    # Step 1: Intelligence Gatherer
    print("Step 1: Calling Gemini as Intelligence Gatherer...")
    raw_report = call_gemini(GATHERER_PROMPT)
    print(f"Got raw intelligence ({len(raw_report)} chars)")

    # Step 2: Executive Editor
    print("Step 2: Calling Gemini as Executive Editor...")
    editor_input = EDITOR_PROMPT + raw_report
    final_report = call_gemini(editor_input)
    print(f"Got final report ({len(final_report)} chars)")

    # Send the polished report
    subject = f"Daily Intelligence Brief — {today}"
    print(f"Sending email to {RECIPIENT_EMAIL}...")
    send_email(subject, final_report)
    print("Email sent successfully!")


if __name__ == "__main__":
    main()
