# MNC Fresher Job WhatsApp Alerts

This is a small automation system for finding fresher software engineering openings at selected MNCs and sending new matches to WhatsApp.

It is designed for India-focused fresher searches, but you can tune the companies, locations, and keywords in `config.json`.

## What It Does

- Checks public job APIs for configured MNC career boards.
- Keeps only software engineering roles that look fresher/entry-level for 2026 or 2027 graduates.
- Rejects roles that look senior, experienced, internship-only, contract-only, or non-software.
- Stores seen jobs in SQLite so the same job is not sent repeatedly.
- Sends a compact WhatsApp message using the official Meta WhatsApp Cloud API.
- Supports `--dry-run` to preview matches without sending WhatsApp messages.

## Setup

1. Install Python 3.10 or newer.
2. Copy `.env.example` to `.env`.
3. Fill in the WhatsApp Cloud API values:
   - `WHATSAPP_TOKEN`
   - `WHATSAPP_PHONE_NUMBER_ID`
   - `WHATSAPP_TO`
4. Run a dry run:

```powershell
python .\job_alerts.py --dry-run
```

5. Send real WhatsApp alerts:

```powershell
python .\job_alerts.py
```

## WhatsApp Cloud API Notes

You need an official WhatsApp Business app from Meta. The script uses Meta's Cloud API endpoint:

```text
https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/messages
```

For production use, the recipient number must be allowed by your WhatsApp Business setup and message templates may be required outside the 24-hour customer service window. For a personal/family alert workflow, start with Meta's test number first.

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
WHATSAPP_TOKEN
WHATSAPP_PHONE_NUMBER_ID
WHATSAPP_TO
```

5. Open:

```text
Actions -> MNC Fresher Job Alerts -> Run workflow
```

This tests it manually once. After that, GitHub Actions will run it every day at 9:00 AM India time.

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

The starter config includes official career/program pages for TCS, Infosys, Wipro, Cognizant, Capgemini, HCLTech, and Accenture, plus API-backed career boards for selected global MNCs.

Some large IT service companies publish fresher hiring through campaign pages instead of clean job APIs. Those are configured as `career_page` sources when the page can be read directly.

For official pages that block scripted reads, the config also uses `bing_search` sources. These search only within official company domains such as `tcs.com`, `infosys.com`, `careers.wipro.com`, and `careers.cognizant.com`, then apply the same strict software + fresher + 2026/2027 rules before sending anything.
