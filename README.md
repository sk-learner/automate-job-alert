# MNC Fresher Job Telegram Alerts

This is a small automation system for finding fresher software engineering openings at selected MNCs and sending new matches to Telegram.

It is designed for India-focused fresher searches, but you can tune the companies, locations, and keywords in `config.json`.

## What It Does

- Checks public job APIs for configured MNC career boards.
- Keeps only software engineering roles that look fresher/entry-level for 2026 or 2027 graduates.
- Rejects roles that look senior, experienced, internship-only, contract-only, or non-software.
- Stores seen jobs in SQLite so the same job is not sent repeatedly.
- Sends compact Telegram messages using a bot created with BotFather.
- Supports `--dry-run` to preview matches without sending Telegram messages.

## Setup

1. Install Python 3.10 or newer.
2. Copy `.env.example` to `.env`.
3. Fill in the Telegram bot values:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. Run a dry run:

```powershell
python .\job_alerts.py --dry-run
```

5. Send real Telegram alerts:

```powershell
python .\job_alerts.py
```

## Telegram Bot Setup

1. Open Telegram and search for `BotFather`.
2. Send `/newbot`.
3. Choose a bot name and username.
4. Copy the bot token. This is `TELEGRAM_BOT_TOKEN`.
5. Open your new bot in Telegram and send it any message, such as `start`.
6. Open this URL in a browser, replacing the token:

```text
https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
```

7. Find `chat":{"id":...}` in the response. That number is `TELEGRAM_CHAT_ID`.

Telegram is easier than WhatsApp for this automation because it does not need Meta business verification or expiring temporary tokens.

## Fully Automatic Cloud Scheduling

If your laptop is shut down, Windows Task Scheduler will not run. For full automation, use GitHub Actions so the script runs in the cloud.

1. Create a private GitHub repository.
2. Upload this project to that repository, including `.github/workflows/job-alerts.yml`.
3. In GitHub, open the repository and go to:

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

4. Add these secrets:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

5. Open:

```text
Actions -> MNC Fresher Job Alerts -> Run workflow
```

This tests it manually once. After that, GitHub Actions will run it every 2 hours.

The workflow uses GitHub Actions cache to remember `seen_jobs.sqlite3`, so the same job is not sent repeatedly.

## Scheduling On Windows

Open Task Scheduler and create a daily task that runs:

```text
Program: powershell.exe
Arguments: -ExecutionPolicy Bypass -File "C:\Users\sarat\Documents\Codex\2026-05-23\ok-listen-my-sister-is-looking\run-alerts.ps1"
```

Daily morning runs usually work best for job alerts.

## Tuning Freshers Strictness

Edit `config.json`:

- Add more MNCs under `sources`.
- Add fresher terms under `freshers_keywords`.
- Change allowed graduation years under `target_graduation_years`.
- Add rejection terms under `reject_keywords`.
- Add preferred cities under `preferred_locations`.

The filter intentionally errs on the strict side. If a role does not clearly look fresher/entry-level and linked to the 2026 or 2027 graduate batch, it is not sent.

## Included Service Companies

The starter config prioritizes broad web-search discovery for TCS, Infosys, Wipro, Cognizant, Accenture, Capgemini, HCLTech, Tech Mahindra, Deloitte, and IBM, then checks official career/program pages and selected global MNC API-backed boards.

Some large IT service companies publish fresher hiring through campaign pages instead of clean job APIs. Those are configured as `career_page` sources when the page can be read directly.

For official pages that block scripted reads, the config also uses `bing_search` sources. These look across the web for fresher hiring announcements, then apply the same strict software + fresher + 2026/2027 rules before sending anything.

Optional Google discovery is supported through `google_cse` sources. To enable it, create a Google Programmable Search Engine and add these GitHub secrets:

```text
GOOGLE_API_KEY
GOOGLE_CSE_ID
```

Without those secrets, the script skips Google CSE and still uses the free Bing RSS discovery.
