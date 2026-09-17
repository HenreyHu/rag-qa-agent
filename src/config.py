"""Project-wide paths, model settings and the company registry."""

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MANIFEST_PATH = DATA_DIR / "filings.json"
CHROMA_DIR = ROOT / "chroma_db"
QUESTIONS_PATH = ROOT / "eval" / "questions.csv"
RESULTS_DIR = ROOT / "eval" / "results"

FORM_TYPE = "20-F"
REPORTS_PER_COMPANY = 2

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
# bge was trained with this instruction on queries only; passages are embedded without it.
QUERY_PROMPT = "Represent this sentence for searching relevant passages: "

# bge-small silently truncates input past 512 tokens, so every budget is measured with its tokenizer.
MAX_MODEL_TOKENS = 512
BODY_TOKENS = 450
OVERLAP_TOKENS = 75
HEADER_MAX_TOKENS = 60  # 60 + 450 + [CLS] + [SEP] = 512
SOFT_BREAK_MIN_TOKENS = 200

COLLECTIONS = {"fixed": "filings_fixed", "section": "filings_section"}
STRATEGIES = tuple(COLLECTIONS)


@dataclass(frozen=True)
class Company:
    key: str
    short_name: str
    full_name: str
    cik: int
    ticker: str


COMPANIES = {
    c.key: c
    for c in (
        Company("sea", "Sea", "Sea Limited", 1703399, "SE"),
        Company("grab", "Grab", "Grab Holdings Limited", 1855612, "GRAB"),
    )
}


def find_company(name: str) -> Company:
    """Look up a company by registry key, short name or ticker, ignoring case."""
    wanted = name.strip().lower()
    for company in COMPANIES.values():
        if wanted in (company.key, company.short_name.lower(), company.ticker.lower()):
            return company
    raise KeyError(f"Unknown company {name!r}; expected one of {sorted(COMPANIES)}")


@dataclass(frozen=True)
class Filing:
    key: str
    company: Company
    fiscal_year: int
    path: Path


def filing_key(company: Company, fiscal_year: int) -> str:
    return f"{company.key}-{fiscal_year}"


def load_filings() -> list[Filing]:
    """The filings pinned in data/filings.json by scripts/download_filings.py."""
    entries = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return [
        Filing(e["key"], COMPANIES[e["company"]], e["fiscal_year"], ROOT / e["local_path"])
        for e in entries
    ]


def load_env() -> None:
    load_dotenv(ROOT / ".env")


def utf8_stdout() -> None:
    # Filings contain characters such as U+25CF that a piped cp1252 Windows console can't encode.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def format_table(header: list[str], rows: list[list], text_columns: int = 1) -> str:
    """A plain-text table: the first `text_columns` columns left-aligned, the rest right-aligned."""
    cells = [header] + [[str(value) for value in row] for row in rows]
    widths = [max(len(row[i]) for row in cells) for i in range(len(header))]

    def line(row: list[str]) -> str:
        parts = [
            value.ljust(width) if i < text_columns else value.rjust(width)
            for i, (value, width) in enumerate(zip(row, widths, strict=True))
        ]
        return "  ".join(parts).rstrip()

    rule = "  ".join("-" * width for width in widths)
    return "\n".join([line(cells[0]), rule, *(line(row) for row in cells[1:])])
