"""Download each company's latest 20-F annual reports from SEC EDGAR.

The first run resolves the latest filings and pins them in data/filings.json.
Later runs download exactly those filings, so the eval set's gold pages stay valid.
Use --refresh to re-resolve the latest filings on purpose.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

from src.config import (
    COMPANIES,
    FORM_TYPE,
    MANIFEST_PATH,
    REPORTS_PER_COMPANY,
    ROOT,
    filing_key,
    load_env,
    utf8_stdout,
)

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}"
# SEC's fair-access policy allows 10 requests per second; this stays well under it.
REQUEST_INTERVAL_S = 0.2
MAX_ATTEMPTS = 4
USER_AGENT_RE = re.compile(r"^\S.*\s\S+@\S+\.\S+$")


def make_session() -> requests.Session:
    load_env()
    user_agent = os.environ.get("SEC_USER_AGENT", "").strip()
    if not USER_AGENT_RE.match(user_agent):
        sys.exit('Set SEC_USER_AGENT in .env to "Your Name you@example.com" (SEC requires it).')
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"})
    return session


def polite_get(session: requests.Session, url: str) -> requests.Response:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        time.sleep(REQUEST_INTERVAL_S)
        response = session.get(url, timeout=60)
        if response.status_code != 429 and response.status_code < 500:
            break
        if attempt < MAX_ATTEMPTS:
            time.sleep(2**attempt)
    response.raise_for_status()
    return response


def fetch_submissions(session: requests.Session, cik: int) -> dict:
    return polite_get(session, SUBMISSIONS_URL.format(cik=cik)).json()


def latest_annual_reports(submissions: dict, n: int) -> list[dict]:
    """The newest n annual reports, from the parallel arrays in filings.recent (newest first)."""
    recent = submissions["filings"]["recent"]
    reports = []
    for i, form in enumerate(recent["form"]):
        # An exact match skips 20-F/A amendments, which only restate parts of a report.
        if form != FORM_TYPE:
            continue
        reports.append(
            {
                "accession": recent["accessionNumber"][i],
                "filing_date": recent["filingDate"][i],
                "report_date": recent["reportDate"][i],
                "primary_document": recent["primaryDocument"][i],
            }
        )
        if len(reports) == n:
            break
    return reports


def resolve_manifest(session: requests.Session) -> list[dict]:
    entries = []
    for company in COMPANIES.values():
        reports = latest_annual_reports(
            fetch_submissions(session, company.cik), REPORTS_PER_COMPANY
        )
        if len(reports) < REPORTS_PER_COMPANY:
            sys.exit(f"Found only {len(reports)} {FORM_TYPE} filings for {company.full_name}.")
        for report in reports:
            # Both companies' fiscal years end on 31 December, so the period's year is the FY.
            fiscal_year = int(report["report_date"][:4])
            key = filing_key(company, fiscal_year)
            url = ARCHIVE_URL.format(
                cik=company.cik,
                accession=report["accession"].replace("-", ""),
                document=report["primary_document"],
            )
            entries.append(
                {
                    "key": key,
                    "company": company.key,
                    "cik": company.cik,
                    "fiscal_year": fiscal_year,
                    "form": FORM_TYPE,
                    **report,
                    "url": url,
                    "local_path": f"data/raw/{key}_{FORM_TYPE}.htm",
                }
            )
    return entries


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(session: requests.Session, url: str, dest: Path) -> tuple[str, int]:
    content = polite_get(session, url).content
    # Every inline-XBRL filing carries a hidden ix:header; anything else is an error page.
    if b"ix:header" not in content:
        sys.exit(f"{url} does not look like an inline-XBRL filing.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    return hashlib.sha256(content).hexdigest(), len(content)


def main() -> None:
    utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="re-resolve the latest filings and rewrite the manifest",
    )
    args = parser.parse_args()

    session = make_session()
    pinned = MANIFEST_PATH.exists() and not args.refresh
    if pinned:
        entries = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    else:
        entries = resolve_manifest(session)

    for entry in entries:
        dest = ROOT / entry["local_path"]
        if pinned and dest.exists() and sha256_of(dest) == entry["sha256"]:
            print(f"{entry['key']}: already downloaded")
            continue
        digest, size = download(session, entry["url"], dest)
        if pinned and digest != entry["sha256"]:
            sys.exit(f"{entry['key']}: the download does not match the pinned sha256.")
        entry["bytes"] = size
        entry["sha256"] = digest
        print(f"{entry['key']}: {size:,} bytes -> {entry['local_path']}")

    MANIFEST_PATH.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Manifest: {MANIFEST_PATH.relative_to(ROOT)} ({len(entries)} filings)")


if __name__ == "__main__":
    main()
