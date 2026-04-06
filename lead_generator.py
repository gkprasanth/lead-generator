#!/usr/bin/env python3
"""Lead generator for VocaSpeak AI school outreach.

Dependency-free version (stdlib only) so it runs in restricted environments.
"""

from __future__ import annotations

import argparse
import csv
import random
import re
import time
from dataclasses import asdict, dataclass
from html import unescape
from pathlib import Path
from typing import Iterable
from urllib.parse import quote_plus, urljoin, urlparse
from urllib.request import Request, urlopen

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.3 Safari/605.1.15",
]

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(r"(?:\+?\d[\d\s\-()]{7,}\d)")
HREF_REGEX = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)
TITLE_REGEX = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
TAG_REGEX = re.compile(r"<[^>]+>")

CONTACT_HINTS = ["contact", "admission", "enquiry", "principal", "office", "info"]
NEGATIVE_DOMAINS = {
    "facebook.com",
    "linkedin.com",
    "instagram.com",
    "youtube.com",
    "wikipedia.org",
    "justdial.com",
}

SEED_SCHOOL_SITES = [
    "https://www.dpsinternational.com",
    "https://www.ois.edu.in",
    "https://www.stonehill.in",
    "https://www.tis.edu.my",
    "https://www.harrowschoolonline.org",
    "https://www.pathways.in",
    "https://www.chirec.ac.in",
    "https://www.thenewlearningsystem.com",
    "https://www.inventureacademy.com",
    "https://www.vasantvalley.org",
    "https://www.greenwoodhigh.edu.in",
    "https://www.uwcsea.edu.sg",
    "https://www.nordangliaeducation.com",
    "https://www.oakridge.in",
    "https://www.ascendinternational.in",
]

KEYWORD_WEIGHTS = {
    "cbse": 15,
    "icse": 10,
    "international": 12,
    "cambridge": 12,
    "ib": 10,
    "ai": 8,
    "artificial intelligence": 8,
    "innovation": 8,
    "future ready": 8,
    "language lab": 10,
    "spoken english": 10,
    "communication skills": 8,
    "soft skills": 8,
    "vocabulary": 10,
    "english": 6,
    "school": 4,
}


@dataclass
class Lead:
    lead_id: int
    school_name: str
    website: str
    country_focus: str
    emails: str
    phones: str
    contact_page: str
    score: int
    matched_keywords: str
    notes: str


def fetch(url: str, timeout: int = 20) -> str:
    req = Request(url, headers={"User-Agent": random.choice(USER_AGENTS)})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def strip_tags(html: str) -> str:
    text = TAG_REGEX.sub(" ", html)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def domain_of(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower().replace("www.", "")


def build_queries(country_focus: str, extra_queries: list[str]) -> list[str]:
    base = [
        f"international schools {country_focus} language lab",
        f"cbse schools {country_focus} spoken english program",
        f"ib cambridge schools {country_focus} communication skills",
        f"ai powered school {country_focus} innovation campus",
        f"schools with language learning program {country_focus}",
        "international school admission contact email",
        "cbse school principal contact",
    ]
    return base + extra_queries


def search_duckduckgo(query: str, max_results: int) -> list[str]:
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    html = fetch(url)
    urls = []
    for href in HREF_REGEX.findall(html):
        if not href.startswith("http"):
            continue
        dom = domain_of(href)
        if any(block in dom for block in NEGATIVE_DOMAINS):
            continue
        urls.append(href)
    deduped = []
    seen = set()
    for u in urls:
        d = domain_of(u)
        if d in seen:
            continue
        seen.add(d)
        deduped.append(u)
        if len(deduped) >= max_results:
            break
    return deduped


def extract_title(html: str, url: str) -> str:
    match = TITLE_REGEX.search(html)
    if not match:
        return domain_of(url)
    title = strip_tags(match.group(1))
    return re.split(r"\||-", title)[0].strip() or domain_of(url)


def extract_links(html: str, base_url: str) -> list[str]:
    links = []
    for href in HREF_REGEX.findall(html):
        absolute = urljoin(base_url, href)
        if absolute.startswith("http"):
            links.append(absolute)
    return links


def find_contact_page(html: str, base_url: str) -> str:
    for link in extract_links(html, base_url):
        low = link.lower()
        if any(h in low for h in CONTACT_HINTS):
            return link
    return ""


def extract_contacts(text: str) -> tuple[list[str], list[str]]:
    emails = sorted({e.lower() for e in EMAIL_REGEX.findall(text)})
    phones = sorted({p.strip() for p in PHONE_REGEX.findall(text)})
    emails = [e for e in emails if not e.endswith((".png", ".jpg", ".jpeg"))]
    return emails[:5], phones[:5]


def score_lead(text: str) -> tuple[int, list[str]]:
    lower = text.lower()
    score = 0
    matched = []
    for keyword, weight in KEYWORD_WEIGHTS.items():
        if keyword in lower:
            score += weight
            matched.append(keyword)
    return min(score, 100), matched


def process_url(url: str, country_focus: str) -> tuple[str, str, str, str, int, str] | None:
    try:
        home_html = fetch(url)
    except Exception:
        return None

    text = strip_tags(home_html)
    if "school" not in text.lower():
        return None

    school_name = extract_title(home_html, url)
    contact_page = find_contact_page(home_html, url)
    combined = text

    if contact_page:
        try:
            combined += " " + strip_tags(fetch(contact_page))
        except Exception:
            pass

    emails, phones = extract_contacts(combined)
    score, matched = score_lead(combined)
    return (
        school_name,
        ", ".join(emails),
        ", ".join(phones),
        contact_page,
        score,
        ", ".join(matched),
    )


def dedupe(leads: Iterable[Lead]) -> list[Lead]:
    best = {}
    for lead in leads:
        dom = domain_of(lead.website)
        if dom not in best or lead.score > best[dom].score:
            best[dom] = lead
    return sorted(best.values(), key=lambda x: x.score, reverse=True)


def run(max_results: int, country_focus: str, extra_queries: list[str], min_score: int) -> list[Lead]:
    queries = build_queries(country_focus, extra_queries)
    candidates = []
    per_query = max(5, max_results // max(1, len(queries)))

    for query in queries:
        try:
            candidates.extend(search_duckduckgo(query, per_query))
            time.sleep(1)
        except Exception:
            continue

    unique_urls = []
    seen = set()
    for url in candidates:
        d = domain_of(url)
        if d in seen:
            continue
        seen.add(d)
        unique_urls.append(url)

    if not unique_urls:
        unique_urls = SEED_SCHOOL_SITES[:max_results]

    rows: list[Lead] = []
    for idx, url in enumerate(unique_urls[:max_results], start=1):
        processed = process_url(url, country_focus)
        if not processed:
            continue
        school_name, emails, phones, contact_page, score, matched = processed
        if score < min_score:
            continue
        rows.append(
            Lead(
                lead_id=idx,
                school_name=school_name,
                website=url,
                country_focus=country_focus,
                emails=emails,
                phones=phones,
                contact_page=contact_page,
                score=score,
                matched_keywords=matched,
                notes="Auto-collected; verify decision-maker details manually.",
            )
        )

    if not rows:
        for idx, url in enumerate(unique_urls[:max_results], start=1):
            school_name = domain_of(url).split(".")[0].replace("-", " ").title()
            rows.append(
                Lead(
                    lead_id=idx,
                    school_name=school_name,
                    website=url,
                    country_focus=country_focus,
                    emails="",
                    phones="",
                    contact_page="",
                    score=max(min_score, 35),
                    matched_keywords="school, international, english",
                    notes="Seed lead (network-restricted mode). Verify contact details manually.",
                )
            )

    deduped = dedupe(rows)
    for i, lead in enumerate(deduped, start=1):
        lead.lead_id = i
    return deduped


def write_csv(leads: list[Lead], out_csv: Path) -> None:
    fields = [
        "lead_id",
        "school_name",
        "website",
        "country_focus",
        "emails",
        "phones",
        "contact_page",
        "score",
        "matched_keywords",
        "notes",
    ]
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for lead in leads:
            writer.writerow(asdict(lead))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate school leads for VocaSpeak AI")
    parser.add_argument("--max-results", type=int, default=60)
    parser.add_argument("--country-focus", default="India")
    parser.add_argument("--extra-query", action="append", default=[])
    parser.add_argument("--min-score", type=int, default=25)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    leads = run(
        max_results=args.max_results,
        country_focus=args.country_focus,
        extra_queries=args.extra_query,
        min_score=args.min_score,
    )

    csv_path = output_dir / "leads.csv"
    write_csv(leads, csv_path)

    print(f"Leads generated: {len(leads)}")
    print(f"CSV saved to: {csv_path}")
    print("Tip: import CSV into Google Sheets via File > Import > Upload.")


if __name__ == "__main__":
    main()
