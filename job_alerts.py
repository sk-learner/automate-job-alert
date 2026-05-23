import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib import error, parse, request


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
DB_PATH = ROOT / "seen_jobs.sqlite3"
ENV_PATH = ROOT / ".env"
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass(frozen=True)
class Job:
    source_id: str
    company: str
    title: str
    location: str
    url: str
    description: str


@dataclass(frozen=True)
class Match:
    job: Job
    confidence: str
    score: int
    reasons: tuple[str, ...]


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data)

    def text(self) -> str:
        return normalize(" ".join(self.parts))


def load_env(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


def load_config(path: Path = CONFIG_PATH) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def html_to_text(html: str) -> str:
    parser = TextExtractor()
    parser.feed(html or "")
    return normalize(parse.unquote(parser.text()))


def fetch_json(url: str) -> dict | list:
    req = request.Request(url, headers=REQUEST_HEADERS)
    with request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(url: str) -> str:
    req = request.Request(url, headers=REQUEST_HEADERS)
    with request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def greenhouse_jobs(source: dict) -> Iterable[Job]:
    board = source["board"]
    company = source["company"]
    url = f"https://boards-api.greenhouse.io/v1/boards/{parse.quote(board)}/jobs?content=true"
    payload = fetch_json(url)
    for item in payload.get("jobs", []):
        offices = item.get("offices") or []
        location = item.get("location", {}).get("name") or ", ".join(
            office.get("name", "") for office in offices
        )
        yield Job(
            source_id=f"greenhouse:{board}:{item.get('id')}",
            company=company,
            title=normalize(item.get("title", "")),
            location=normalize(location),
            url=item.get("absolute_url", ""),
            description=html_to_text(item.get("content", "")),
        )


def lever_jobs(source: dict) -> Iterable[Job]:
    site = source["site"]
    company = source["company"]
    url = f"https://api.lever.co/v0/postings/{parse.quote(site)}?mode=json"
    payload = fetch_json(url)
    for item in payload:
        categories = item.get("categories") or {}
        location = categories.get("location", "")
        text_parts = [
            item.get("descriptionPlain", ""),
            item.get("additionalPlain", ""),
            categories.get("team", ""),
            categories.get("commitment", ""),
        ]
        yield Job(
            source_id=f"lever:{site}:{item.get('id')}",
            company=company,
            title=normalize(item.get("text", "")),
            location=normalize(location),
            url=item.get("hostedUrl", ""),
            description=normalize(" ".join(text_parts)),
        )


def career_page_jobs(source: dict) -> Iterable[Job]:
    url = source["url"]
    page_text = html_to_text(fetch_text(url))
    yield Job(
        source_id=f"career_page:{source['company']}:{url}",
        company=source["company"],
        title=normalize(source.get("title", f"{source['company']} early career hiring")),
        location=normalize(source.get("location", "India")),
        url=url,
        description=page_text,
    )


def domain_allowed(url: str, allowed_domains: list[str]) -> bool:
    hostname = parse.urlparse(url).hostname or ""
    hostname = hostname.lower()
    return any(hostname == domain.lower() or hostname.endswith(f".{domain.lower()}") for domain in allowed_domains)


def bing_search_jobs(source: dict) -> Iterable[Job]:
    query = source["query"]
    company = source["company"]
    allowed_domains = source.get("allowed_domains", [])
    max_results = int(source.get("max_results", 5))
    rss_url = "https://www.bing.com/search?" + parse.urlencode({"q": query, "format": "rss"})
    xml_text = fetch_text(rss_url)
    root = ET.fromstring(xml_text)
    emitted = 0
    for item in root.findall("./channel/item"):
        title = normalize(item.findtext("title", ""))
        link = normalize(item.findtext("link", ""))
        description = html_to_text(item.findtext("description", ""))
        if allowed_domains and not domain_allowed(link, allowed_domains):
            continue
        digest = hashlib.sha256(link.encode("utf-8")).hexdigest()[:16]
        yield Job(
            source_id=f"bing_search:{company}:{digest}",
            company=company,
            title=title,
            location=normalize(source.get("location", "India")),
            url=link,
            description=description,
        )
        emitted += 1
        if emitted >= max_results:
            break


def google_cse_jobs(source: dict) -> Iterable[Job]:
    api_key = os.environ.get("GOOGLE_API_KEY")
    cse_id = os.environ.get("GOOGLE_CSE_ID")
    if not api_key or not cse_id:
        return
    company = source["company"]
    allowed_domains = source.get("allowed_domains", [])
    max_results = min(int(source.get("max_results", 5)), 10)
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": source["query"],
        "num": max_results,
        "sort": source.get("sort", "date"),
    }
    api_url = "https://www.googleapis.com/customsearch/v1?" + parse.urlencode(params)
    payload = fetch_json(api_url)
    for item in payload.get("items", []):
        link = normalize(item.get("link", ""))
        if allowed_domains and not domain_allowed(link, allowed_domains):
            continue
        digest = hashlib.sha256(link.encode("utf-8")).hexdigest()[:16]
        yield Job(
            source_id=f"google_cse:{company}:{digest}",
            company=company,
            title=normalize(item.get("title", "")),
            location=normalize(source.get("location", "India")),
            url=link,
            description=normalize(item.get("snippet", "")),
        )


def fetch_jobs(config: dict) -> list[Job]:
    jobs: list[Job] = []
    for source in config["sources"]:
        try:
            if source["type"] == "greenhouse":
                jobs.extend(greenhouse_jobs(source))
            elif source["type"] == "lever":
                jobs.extend(lever_jobs(source))
            elif source["type"] == "career_page":
                jobs.extend(career_page_jobs(source))
            elif source["type"] == "bing_search":
                jobs.extend(bing_search_jobs(source))
            elif source["type"] == "google_cse":
                jobs.extend(google_cse_jobs(source))
            else:
                print(f"Skipping unknown source type: {source}", file=sys.stderr)
        except (error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
            print(f"Could not read {source.get('company', source)}: {exc}", file=sys.stderr)
    return jobs


def contains_any(text: str, keywords: list[str]) -> bool:
    text_l = text.lower()
    return any(keyword.lower() in text_l for keyword in keywords)


def matching_keywords(text: str, keywords: list[str]) -> list[str]:
    text_l = text.lower()
    return [keyword for keyword in keywords if keyword.lower() in text_l]


def is_preferred_location(job: Job, config: dict) -> bool:
    combined = f"{job.location} {job.description}".lower()
    return contains_any(combined, config["preferred_locations"])


def has_target_graduation_year(job: Job, config: dict) -> bool:
    years = [re.escape(str(year)) for year in config.get("target_graduation_years", [])]
    if not years:
        return True
    year_group = "|".join(years)
    searchable = f"{job.title} {job.location} {job.description}".lower()
    context_words = (
        r"batch|yop|year of passing|passing year|passout|passing out|"
        r"graduates?|engineering graduates?|mtech|m\.tech|btech|b\.tech|"
        r"be/btech|me/mtech|class"
    )
    patterns = [
        rf"\b(?:{context_words})\b[\w\W]{{0,80}}\b(?:{year_group})\b",
        rf"\b(?:{year_group})\b[\w\W]{{0,80}}\b(?:{context_words})\b",
    ]
    return any(re.search(pattern, searchable) for pattern in patterns)


def is_fresher_software_role(job: Job, config: dict) -> bool:
    searchable = f"{job.title} {job.location} {job.description}".lower()
    title_l = job.title.lower()
    if not contains_any(searchable, config["software_keywords"]):
        return False
    if not contains_any(searchable, config["freshers_keywords"]):
        return False
    if not has_target_graduation_year(job, config):
        return False
    if contains_any(title_l, config["reject_keywords"]):
        return False
    if contains_any(searchable, config["reject_keywords"]):
        return False
    if not is_preferred_location(job, config):
        return False
    return True


def is_trusted_source(job: Job, config: dict) -> bool:
    trusted_domains = config.get("trusted_domains", [])
    return bool(trusted_domains and domain_allowed(job.url, trusted_domains))


def is_priority_company(job: Job, config: dict) -> bool:
    priority_companies = [company.lower() for company in config.get("priority_companies", [])]
    return job.company.lower() in priority_companies


def looks_like_hiring_page(job: Job) -> bool:
    haystack = f"{job.title} {job.url} {job.description[:500]}".lower()
    hiring_terms = [
        "career",
        "careers",
        "job",
        "jobs",
        "hiring",
        "apply",
        "campus",
        "off-campus",
        "freshers",
        "fresher",
        "graduate",
        "entry-level",
        "entry level",
        "nqt",
        "genc",
        "students-and-new-grads",
        "students and graduates",
    ]
    return any(term in haystack for term in hiring_terms)


def score_personalized_match(job: Job, config: dict) -> Match | None:
    searchable = f"{job.title} {job.location} {job.description}".lower()
    title_l = job.title.lower()
    reject_hits = matching_keywords(title_l, config.get("reject_keywords", []))
    if reject_hits:
        return None

    priority_company = is_priority_company(job, config)
    trusted_source = is_trusted_source(job, config)
    software_hits = matching_keywords(searchable, config.get("software_keywords", []))
    fresher_hits = matching_keywords(searchable, config.get("freshers_keywords", []))
    program_hits = matching_keywords(searchable, config.get("role_program_keywords", []))
    degree_hits = matching_keywords(searchable, config.get("profile", {}).get("degrees", []))
    skill_hits = matching_keywords(searchable, config.get("profile", {}).get("skills", []))
    has_year = has_target_graduation_year(job, config)
    has_location = is_preferred_location(job, config)

    if not priority_company and not trusted_source:
        return None
    if not (fresher_hits or has_year or program_hits):
        return None
    if not (software_hits or program_hits or skill_hits):
        return None
    if not looks_like_hiring_page(job):
        return None
    if not trusted_source and not (fresher_hits or has_year):
        return None
    if not (fresher_hits or has_year) and not (program_hits and looks_like_hiring_page(job)):
        return None

    score = 0
    reasons: list[str] = []
    if priority_company:
        score += 20
        reasons.append("priority MNC/top IT company")
    if trusted_source:
        score += 15
        reasons.append("official or trusted source")
    if has_year:
        score += 25
        years = "/".join(str(year) for year in config.get("target_graduation_years", []))
        reasons.append(f"matches target batch {years}")
    if fresher_hits:
        score += 20
        reasons.append(f"fresher signal: {', '.join(fresher_hits[:3])}")
    if software_hits:
        score += 20
        reasons.append(f"software role signal: {', '.join(software_hits[:3])}")
    if program_hits:
        score += 15
        reasons.append(f"campus program signal: {', '.join(program_hits[:3])}")
    if degree_hits:
        score += 10
        reasons.append(f"degree fit: {', '.join(degree_hits[:3])}")
    if skill_hits:
        score += min(10, len(skill_hits) * 2)
        reasons.append(f"skill fit: {', '.join(skill_hits[:4])}")
    if has_location:
        score += 10
        reasons.append("preferred India/remote location")

    minimum_score = int(config.get("minimum_match_score", 45))
    if score < minimum_score:
        return None

    score = min(score, 100)
    confidence = "High match" if score >= int(config.get("high_match_score", 75)) else "Medium match"
    return Match(job=job, confidence=confidence, score=score, reasons=tuple(reasons[:5]))


def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS seen_jobs (
            source_id TEXT PRIMARY KEY,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            first_seen_at TEXT NOT NULL
        )
        """
    )
    return conn


def unseen_jobs(conn: sqlite3.Connection, jobs: Iterable[Job]) -> list[Job]:
    fresh: list[Job] = []
    for job in jobs:
        row = conn.execute(
            "SELECT 1 FROM seen_jobs WHERE source_id = ?",
            (job.source_id,),
        ).fetchone()
        if row is None:
            fresh.append(job)
    return fresh


def mark_seen(conn: sqlite3.Connection, jobs: Iterable[Job]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.executemany(
        """
        INSERT OR IGNORE INTO seen_jobs (source_id, company, title, url, first_seen_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [(job.source_id, job.company, job.title, job.url, now) for job in jobs],
    )
    conn.commit()


def format_message(matches: list[Match]) -> str:
    lines = ["Personalized MNC fresher job alerts:"]
    for idx, match in enumerate(matches, start=1):
        job = match.job
        lines.extend(
            [
                "",
                f"{idx}. {match.confidence} ({match.score}/100)",
                f"{job.company} - {job.title}",
                f"Location: {job.location or 'Not listed'}",
                f"Why: {'; '.join(match.reasons)}",
                job.url,
            ]
        )
    return "\n".join(lines)


def send_whatsapp(message: str) -> None:
    token = os.environ.get("WHATSAPP_TOKEN")
    phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
    recipient = os.environ.get("WHATSAPP_TO")
    missing = [
        name
        for name, value in {
            "WHATSAPP_TOKEN": token,
            "WHATSAPP_PHONE_NUMBER_ID": phone_number_id,
            "WHATSAPP_TO": recipient,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing WhatsApp environment values: {', '.join(missing)}")

    url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "text",
        "text": {"preview_url": True, "body": message},
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with request.urlopen(req, timeout=30) as response:
        response.read()


def main() -> int:
    parser = argparse.ArgumentParser(description="Send WhatsApp alerts for fresher MNC software roles.")
    parser.add_argument("--dry-run", action="store_true", help="Print matches without sending WhatsApp.")
    parser.add_argument("--mark-seen", action="store_true", help="Mark dry-run matches as seen.")
    args = parser.parse_args()

    load_env()
    config = load_config()
    conn = connect_db()

    jobs = fetch_jobs(config)
    scored = [match for job in jobs if (match := score_personalized_match(job, config))]
    scored.sort(key=lambda match: match.score, reverse=True)
    new_jobs = unseen_jobs(conn, [match.job for match in scored])
    new_ids = {job.source_id for job in new_jobs}
    new_matches = [match for match in scored if match.job.source_id in new_ids]
    limited = new_matches[: int(config.get("max_alerts_per_run", 10))]

    if not limited:
        print("No new personalized MNC fresher software matches found.")
        return 0

    message = format_message(limited)
    print(message)

    if args.dry_run:
        if args.mark_seen:
            mark_seen(conn, [match.job for match in limited])
        return 0

    send_whatsapp(message)
    mark_seen(conn, [match.job for match in limited])
    print(f"Sent {len(limited)} WhatsApp alert(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
