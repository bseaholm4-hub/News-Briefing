# Daily Gemini Brief

Automated daily prompt → Gemini API → Email pipeline, powered by GitHub Actions.

Runs every morning at 6:00 AM CT. Zero infrastructure, zero cost.

---

## Setup (5 minutes)

### 1. Create the GitHub repo

```bash
git init gemini-daily-automation
cd gemini-daily-automation
# Copy these files in, then:
git add .
git commit -m "Initial setup"
git remote add origin https://github.com/YOUR_USERNAME/gemini-daily-automation.git
git push -u origin main
```

### 2. Create a Gmail App Password

You need an **App Password**, not your regular Gmail password.

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Make sure **2-Step Verification** is turned ON
3. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
4. Create a new app password (name it "Gemini Daily Brief")
5. Copy the 16-character password — you'll need it in the next step

### 3. Add GitHub Secrets

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these 4 secrets:

| Secret Name          | Value                                      |
| -------------------- | ------------------------------------------ |
| `GEMINI_API_KEY`     | Your Gemini API key                        |
| `GMAIL_ADDRESS`      | Your Gmail address                         |
| `GMAIL_APP_PASSWORD` | The 16-char app password from step 2       |
| `RECIPIENT_EMAIL`    | Email to receive the brief (can be same)   |
| `GEMINI_PROMPT`      | *(Optional)* Custom prompt — see below     |

### 4. Test it

Go to **Actions** tab → **Daily Gemini Brief** → **Run workflow** → **Run workflow**

You should receive an email within a minute or two.

---

## Customizing the Prompt

Set the `GEMINI_PROMPT` secret to whatever you want. If not set, it defaults to:

> "Give me a daily briefing on the latest developments in AI, supply chain technology, and enterprise SaaS. Keep it concise and actionable."

You can change this anytime in GitHub Secrets without touching the code.

---

## Adjusting the Schedule

The cron is set to `0 12 * * *` (12:00 UTC = 6:00 AM CDT).

During Central Standard Time (Nov–Mar), 6:00 AM CT = 12:00 UTC.  
During Central Daylight Time (Mar–Nov), 6:00 AM CT = 11:00 UTC.

To adjust, edit `.github/workflows/daily-brief.yml`.

**Note:** GitHub Actions cron can run up to ~15 minutes late. If exact timing matters, consider a cloud scheduler instead.

---

## Changing the Gemini Model

The script uses `gemini-2.0-flash` by default. To use a different model, edit the `url` variable in `main.py`:

```python
# Options: gemini-2.0-flash, gemini-2.5-pro, etc.
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={GEMINI_API_KEY}"
```
