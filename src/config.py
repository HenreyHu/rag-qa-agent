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

# Answer generation (src/rag.py). No temperature setting: this SDK/model rejects the argument,
# so runs can vary slightly; re-run a question before trusting a one-off difference.
ANSWER_MODEL = "claude-sonnet-5"
ANSWER_MAX_TOKENS = 1024
# A separate call grades each answer (eval/answer_eval.py); same model.
GRADER_MODEL = "claude-sonnet-5"
SYSTEM_PROMPT = (
    "Answer the question using only the provided context. "
    "Every claim must include a citation in the format [Company, FYyear, p.X]. "
    "If the answer is not in the context, say 'I don't know.' "
    "Do not use outside knowledge."
)

# Agent loop (src/agent.py). Same model as basic RAG so the RAG-vs-agent comparison changes
# one thing only: the loop and the tools, not the model.
AGENT_MODEL = ANSWER_MODEL
# Each step is one model turn (a tool call or the final answer). 8 allows two companies x two
# years plus a couple of reformulations; raise it only if traces show good runs being cut off.
AGENT_MAX_STEPS = 8
# Per turn, not per run. Tool calls are short; the final cited answer is the long one.
AGENT_MAX_TOKENS = 2048
AGENT_SYSTEM_PROMPT = f"""\
You answer questions about the annual reports (Form 20-F) of Sea Limited and Grab Holdings, \
fiscal years 2024 and 2025. You have two tools: search_reports and calculate.

How to work:
1. Decide what evidence the question needs. For a comparison across companies or years, make \
one search_reports call per company and year, with company and year as arguments, not in the \
query text. Never answer a comparison from one side's evidence.
2. Read the results before answering. If they look weak (the wrong year, the wrong section, \
or a related figure instead of the one asked for), search again with different wording: name \
the specific line item or topic, and drop filler such as "according to the annual report". \
Reformulate at most twice per sub-question.
3. Use calculate for every growth rate, ratio, difference or sum. Never do arithmetic \
yourself. Pass numbers exactly as they appear in the results, and keep the units consistent.
4. Use only what the search results contain. Do not use outside knowledge, and do not \
substitute a nearby figure (for example, cash plus restricted cash for cash).
5. Every claim must carry a citation in the format [Company, FYyear, p.X], copied from the \
header of the result that supports it. Cite only pages you actually retrieved.
6. If the evidence is still missing after searching, say "I don't know" and say what you \
could not find. A partial answer that names the missing half is better than a guess.

You have at most {AGENT_MAX_STEPS} steps, so do not repeat a search that already failed.
"""

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
