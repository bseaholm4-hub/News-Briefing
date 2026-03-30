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

# ── Focus areas ─────────────────────────────────────────────────────
FOCUS_AREAS = [
    "Russia-Ukraine War — front-line shifts, weapons deliveries, negotiations, sanctions enforcement",
    "Middle East — Israel-Gaza, Israel-Iran, Houthi activity, Gulf state diplomacy, ceasefire status",
    "China — military posturing (Taiwan Strait, South China Sea), trade war moves, Belt & Road, internal politics",
    "US Foreign Policy — alliance shifts, sanctions, diplomatic signals, defense posture changes",
    "Oil & Energy — Brent/WTI prices, OPEC+ moves, pipeline disruptions, Strait of Hormuz, LNG flows",
    "AI Race — frontier model releases, chip export controls, GPU supply, government regulation, US-China AI competition",
    "Global Trade & Tariffs — new tariffs, retaliatory measures, supply chain shifts, de-risking moves",
    "NATO & European Security — defense spending, troop deployments, EU policy, Eastern Europe",
    "Nuclear & Proliferation — Iran enrichment, North Korea tests, arms control agreements",
    "Emerging Flashpoints — any new or escalating conflict, coup, crisis, or major protest movement",
]

# ── Prompts ─────────────────────────────────────────────────────────

def build_gatherer_prompt(today: str) -> str:
    focus_block = "\n".join(f"  {i+1}. {area}" for i, area in enumerate(FOCUS_AREAS))

    return f"""You are a political intelligence analyst. Search for today's developments across every focus area below and produce a raw fact sheet.

TODAY'S DATE: {today}
All dates MUST be consistent with this. Do NOT hallucinate dates.

═══ FRESHNESS — NON-NEGOTIABLE ═══
• ONLY report what happened in the LAST 24 HOURS. The reader is already briefed on everything before today.
• If nothing happened on a topic, say so in one line and move on. Do NOT pad with background.

═══ FOCUS AREAS ═══
{focus_block}

═══ SOURCING — STRICT ═══
• Use Google Search for EVERY claim. Do NOT fabricate figures.
• IGNORE any source older than 48 hours. If the only results are older, the topic has no news today.
• **Two-source rule:** Only report a claim if you can confirm it in 2+ independent sources. Cite both — e.g., (Reuters, Mar 29; AFP, Mar 29).
• If a claim appears in only ONE source, you may still include it but you MUST flag it: mark it with "[single source]" so the editor knows.
• If you cannot find ANY reliable source for a claim, omit it entirely.

═══ OUTPUT ═══
For each focus area, write:

## [Topic]
- [Fact 1 with source]
- [Fact 2 with source]
- [Fact 3 if applicable]

If no news: "## [Topic]\\nNo significant developments." and move on.

Keep it factual and dense. No analysis, no filler, no AI pleasantries. Under 2,000 words total."""


def build_editor_prompt(today: str) -> str:
    return f"""You are a sharp political analyst writing a daily intelligence brief. Below is today's raw fact sheet. Your job is to turn each item into a short, opinionated analytical hit — the kind of thing a well-connected strategist would say over coffee to a CEO.

TODAY'S DATE: {today}. Use ONLY this date.

═══ VOICE & STYLE ═══
You are not a reporter. You are an analyst. Your reader is smart, busy, and already follows the news — they come to you for MEANING, not summary.

Think of your bold frames like a thesis statement from someone who has been covering this beat for 20 years. They should reveal WHY something matters — connect it to a historical pattern, a strategic consequence, a power shift, or a structural change. The reader should finish the bold sentence and think "I hadn't connected those dots."

For each update:
1. **Lead with the "so what" — a single bold sentence that reveals an insight the reader wouldn't get from the headline alone.** This must do ONE of the following:
   - Connect today's event to a pattern ("Third civilian target this week — Moscow is retaliating for each Ukrainian deep strike")
   - Name a specific consequence ("Tehran hit Israeli soil without a proxy buffer — the deterrence architecture that held since 1979 is gone")
   - Quantify a shift ("Brent at $115 means every $10 barrel adds ~$40B/year to Europe's import bill")
   - Reveal what's actually at stake ("The Islamabad talks aren't about peace — they're about whether Saudi Arabia picks a side")

   BANNED bold frame patterns — these are NOT insight, they are just relabeling the fact:
   - "X has officially Y" ("The conflict has officially gone direct")
   - "X continues to Y" ("Russia continues its campaign")
   - "X underscores/highlights/signals Y" ("This underscores the brutal nature")
   - "X is now the norm" ("Direct escalation is now the norm")
   - "X remains Y, but Z" ("Front lines remain static, but fluidity is increasing")

2. **Then give the fact** — tight, sourced, ONE sentence. Cut every unnecessary word. No full titles ("Netanyahu" not "Israeli Prime Minister Benjamin Netanyahu"). No filler ("It is worth noting" / "according to officials"). Just the fact and the source.

3. **One fact per hit. One hit per development.** Do NOT combine two unrelated stories into one hit. If the US is doing diplomacy in Islamabad AND facing domestic protests, those are two separate hits.

═══ EXAMPLES ═══

GOOD — insight the headline doesn't give you:
> **Tehran hit Israeli soil for the first time without a proxy buffer — the deterrence architecture that held since 1979 is gone.** Iran struck Eshtaol directly, hospitalizing seven; Israel hit Tehran government infrastructure hours earlier (Reuters, Mar 28).

BAD — just relabeling the fact:
> **Direct escalation between Israel and Iran is now the norm, with both sides striking deep into enemy territory.** Israel conducted air attacks on Tehran on March 28, targeting government infrastructure; Iran retaliated with an airstrike on Eshtaol, Israel, hospitalizing seven.

GOOD — connects dots:
> **Fifty-city "No Kings" protests signal the Iran war is becoming a domestic political liability — and midterm math just got harder for the GOP.** Mass demonstrations across the US and Europe on Mar 28 targeted the administration's foreign policy and executive overreach (AP, Mar 28).

BAD — newspaper summary:
> **Widespread "No Kings" protests across the US and Europe highlight growing domestic opposition to the Trump administration's foreign policy and perceived authoritarianism.**

═══ STRUCTURE ═══

**## Executive Summary**
3-4 bullets. Each bullet must pass this test: could someone tell WHAT DAY this was written just from the bullet? If not, it's too vague. Include a specific fact, number, or named development. One sharp sentence each, with the analytical frame built in.

**Then: one section per topic from the raw intel.**
- Use ## headers for each topic.
- **MAX 2-3 hits per section.** Merge related facts into one hit. Each hit = one bold frame + one sourced fact sentence.
- If the raw intel says "No significant developments," drop the topic entirely.

**## Watchlist**
2-3 bullets. Each must name a SPECIFIC scheduled event, deadline, vote, meeting, data release, or decision in the next 48 hours. State why it matters in the same sentence. If you cannot name a specific event, do not include a bullet.

BAD: "Oil futures movements today will gauge investor confidence."
GOOD: "OPEC+ emergency call reportedly being organized for midweek — any output hike announcement caps the price rally."

═══ RULES ═══
• **HARD LIMIT: 700 words max.** Brevity IS the product.
• Max 2-3 hits per section. No section exceeds 3 sentences total.
• ONE fact per hit. Do NOT jam two unrelated stories into one paragraph.
• Preserve all source citations from the raw intel.
• If a fact is tagged "[single source]", keep it but add *(unconfirmed)* after it.
• No meta-headers (Subject, Date, TO, FROM). Start directly with ## Executive Summary.
• No AI filler, no "certainly," no "here's your brief," no sign-offs.
• Cut every word that doesn't earn its place.

═══ RAW INTELLIGENCE ═══
"""


def call_gemini(prompt: str, use_search: bool = False, model: str = "gemini-2.5-flash") -> str:
    """Call Gemini API and return the response text.

    Args:
        prompt: The prompt to send.
        use_search: If True, enable Google Search grounding so the model
                    can pull real-time data before generating.
        model: Which Gemini model to use.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3 if use_search else 0.4,
            "maxOutputTokens": 8192,
        },
    }

    # Enable Google Search grounding for real-time data
    if use_search:
        payload["tools"] = [{"google_search": {}}]

    timeout = 180 if "pro" in model else 120
    response = requests.post(url, json=payload, timeout=timeout)
    if not response.ok:
        print(f"Gemini API error {response.status_code}: {response.text}")
        response.raise_for_status()

    data = response.json()

    # With grounding, the response may have multiple parts (text + search results).
    # Extract only the text parts.
    parts = data["candidates"][0]["content"]["parts"]
    text_parts = [p["text"] for p in parts if "text" in p]
    return "\n".join(text_parts)


def md_to_html(text: str) -> str:
    """Convert Gemini Markdown output to styled HTML."""
    # Convert markdown → HTML (tables, fenced code, etc.)
    raw_html = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "nl2br"],
    )

    # Strip any rogue meta-header lines Gemini sometimes injects at the top
    for label in ["Subject", "Date", "TO", "FROM", "SUBJECT", "DATE"]:
        raw_html = re.sub(
            rf"<p>\s*<strong>{label}:?</strong>.*?</p>", "", raw_html, flags=re.DOTALL | re.IGNORECASE
        )
        # Also catch non-bold variants like "TO: Chief of Staff"
        raw_html = re.sub(
            rf"<p>\s*{label}\s*:.*?</p>", "", raw_html, flags=re.DOTALL | re.IGNORECASE
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
    raw_report = call_gemini(build_gatherer_prompt(today), use_search=True, model="gemini-2.5-pro")
    print(f"Got raw intelligence ({len(raw_report)} chars)")

    # Step 2: Executive Editor
    print("Step 2: Calling Gemini as Executive Editor...")
    editor_input = build_editor_prompt(today) + raw_report
    final_report = call_gemini(editor_input, use_search=True)
    print(f"Got final report ({len(final_report)} chars)")

    # Send the polished report
    subject = f"Daily Intelligence Brief — {today}"
    print(f"Sending email to {RECIPIENT_EMAIL}...")
    send_email(subject, final_report)
    print("Email sent successfully!")


if __name__ == "__main__":
    main()
