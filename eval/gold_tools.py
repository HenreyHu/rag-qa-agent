"""Load, validate and search the eval gold set (eval/questions.csv).

Examples:
    python -m eval.gold_tools check
    python -m eval.gold_tools find "Total revenue ... 22,938,469" --company Sea --year 2025

Column format: gold_company, gold_year, gold_page and evidence hold one ';'-separated entry per
piece of evidence a question needs (comparison questions need two or more). A gold_page entry may
list acceptable alternative pages with '|'. An evidence entry is a short verbatim snippet; '...'
separates parts that must appear in that order within one block of text.
"""

import argparse
import csv
import io
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from src.config import (
    PROCESSED_DIR,
    QUESTIONS_PATH,
    filing_key,
    find_company,
    utf8_stdout,
)

COLUMNS = [
    "id",
    "type",
    "question",
    "gold_answer",
    "gold_company",
    "gold_year",
    "gold_page",
    "evidence",
    "verified",
]
QUESTION_TYPES = ("lookup", "narrative", "comparison")
QUESTIONS_PER_TYPE = 10
ITEM_SEPARATOR = ";"
# Not "/": Excel silently turns a cell like "4/5" into a date.
ALTERNATIVE_SEPARATOR = "|"
SNIPPET_GAP = "..."
MAX_SNIPPET_WORDS = 12
# Excel treats cells starting with these as formulas.
FORMULA_PREFIXES = ("=", "+", "-", "@")


@dataclass(frozen=True)
class Evidence:
    company: str  # short name, e.g. "Sea"
    year: int  # fiscal year of the filing that contains the evidence
    pages: tuple[str, ...]  # acceptable printed page labels
    snippet: str

    @property
    def filing(self) -> str:
        return filing_key(find_company(self.company), self.year)


@dataclass(frozen=True)
class Question:
    id: str
    type: str
    question: str
    gold_answer: str
    evidence: tuple[Evidence, ...]
    verified: bool


def _split(cell: str, separator: str) -> list[str]:
    return [part.strip() for part in cell.split(separator)]


def parse_row(row: dict[str, str]) -> Question:
    qid = row["id"].strip()
    try:
        columns = ("gold_company", "gold_year", "gold_page", "evidence")
        lists = [_split(row[column], ITEM_SEPARATOR) for column in columns]
        if len({len(values) for values in lists}) != 1:
            raise ValueError(f"{', '.join(columns)} need the same number of ';' entries")
        if row["type"].strip() not in QUESTION_TYPES:
            raise ValueError(f"type must be one of {QUESTION_TYPES}")
        verified = row["verified"].strip().lower()
        if verified not in ("true", "false"):
            raise ValueError("verified must be TRUE or FALSE")
        evidence = tuple(
            Evidence(
                company=find_company(company).short_name,
                year=int(year),
                pages=tuple(_split(pages, ALTERNATIVE_SEPARATOR)),
                snippet=snippet,
            )
            for company, year, pages, snippet in zip(*lists, strict=True)
        )
    except (KeyError, ValueError) as exc:
        raise ValueError(f"{qid}: {exc}") from exc
    return Question(
        id=qid,
        type=row["type"].strip(),
        question=row["question"].strip(),
        gold_answer=row["gold_answer"].strip(),
        evidence=evidence,
        verified=verified == "true",
    )


def read_rows(path: Path = QUESTIONS_PATH) -> list[dict[str, str]]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Excel's plain "CSV" format saves with the Windows code page instead of UTF-8.
        print(f"warning: {path.name} is not UTF-8; re-save it as 'CSV UTF-8'.", file=sys.stderr)
        text = raw.decode("cp1252")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if reader.fieldnames != COLUMNS:
        raise ValueError(f"{path.name} must have the columns {COLUMNS}, not {reader.fieldnames}")
    return list(reader)


def write_rows(rows: list[dict[str, str]], path: Path = QUESTIONS_PATH) -> None:
    # The BOM makes Excel open the file as UTF-8; "\n" keeps CRLF noise out of git diffs.
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_questions(path: Path = QUESTIONS_PATH) -> list[Question]:
    questions = [parse_row(row) for row in read_rows(path)]
    duplicates = [qid for qid, n in Counter(q.id for q in questions).items() if n > 1]
    if duplicates:
        raise ValueError(f"duplicate question ids: {duplicates}")
    return questions


def load_blocks() -> dict[str, list[dict]]:
    """Parsed blocks per filing, as written by `python -m src.ingest`."""
    blocks = {}
    for path in sorted(PROCESSED_DIR.glob("*_blocks.jsonl")):
        with path.open(encoding="utf-8") as f:
            blocks[path.name.removesuffix("_blocks.jsonl")] = [json.loads(line) for line in f]
    if not blocks:
        sys.exit("No parsed blocks found; run `python -m src.ingest --dry-run` first.")
    return blocks


def _squash(text: str) -> str:
    return " ".join(text.lower().split())


def _find_parts(snippet: str, text: str) -> int | None:
    """Position of the snippet's first part if all its parts appear in order, else None."""
    haystack = _squash(text)
    first = None
    position = 0
    for part in filter(None, (_squash(p) for p in snippet.split(SNIPPET_GAP))):
        found = haystack.find(part, position)
        if found < 0:
            return None
        first = found if first is None else first
        position = found + len(part)
    return first


def snippet_matches(snippet: str, text: str) -> bool:
    return _find_parts(snippet, text) is not None


def pages_with(snippet: str, blocks: list[dict]) -> list[str]:
    return list(dict.fromkeys(b["page"] for b in blocks if snippet_matches(snippet, b["text"])))


def check(questions: list[Question], blocks: dict[str, list[dict]]) -> tuple[list[str], list[str]]:
    """Errors and warnings for a gold set, checked against the parsed filings."""
    errors: list[str] = []
    warnings: list[str] = []
    counts = Counter(q.type for q in questions)
    if len(questions) == QUESTIONS_PER_TYPE * len(QUESTION_TYPES) and any(
        counts[t] != QUESTIONS_PER_TYPE for t in QUESTION_TYPES
    ):
        warnings.append(f"expected {QUESTIONS_PER_TYPE} questions per type, got {dict(counts)}")
    for q in questions:
        cells = [q.question, q.gold_answer, *(e.snippet for e in q.evidence)]
        errors += [
            f"{q.id}: {cell[:30]!r} starts with a character Excel treats as a formula"
            for cell in cells
            if cell.startswith(FORMULA_PREFIXES)
        ]
        if q.type == "comparison" and len({e.filing for e in q.evidence}) < 2:
            warnings.append(f"{q.id}: a comparison question should need evidence from 2+ filings")
        for e in q.evidence:
            label = f"{q.id}: {e.snippet!r} ({e.filing})"
            if e.filing not in blocks:
                errors.append(f"{label}: no parsed blocks for this filing")
                continue
            if any(page.startswith("s") for page in e.pages):
                errors.append(f"{label}: unlabeled pages (s...) can't be gold pages")
            if len(e.snippet.replace(SNIPPET_GAP, " ").split()) > MAX_SNIPPET_WORDS:
                warnings.append(f"{label}: snippets should be {MAX_SNIPPET_WORDS} words or fewer")
            found = pages_with(e.snippet, blocks[e.filing])
            if not set(e.pages) & set(found):
                where = f"p.{', p.'.join(found)}" if found else "no page"
                errors.append(f"{label}: not on p.{'|'.join(e.pages)}; found on {where}")
                continue
            warnings += [
                f"{label}: listed page p.{page} doesn't contain the snippet"
                for page in e.pages
                if page not in found
            ]
    return errors, warnings


def _context(snippet: str, text: str, width: int = 90) -> str:
    squashed = " ".join(text.split())
    start = _find_parts(snippet, text) or 0
    prefix = "..." if start > width else ""
    return prefix + squashed[max(0, start - width) : start + 2 * width] + "..."


def cmd_check(_: argparse.Namespace) -> int:
    questions = load_questions()
    errors, warnings = check(questions, load_blocks())
    counts = Counter(q.type for q in questions)
    verified = sum(q.verified for q in questions)
    summary = ", ".join(f"{t} {counts[t]}" for t in QUESTION_TYPES)
    print(f"{len(questions)} questions ({summary}); {verified} verified by hand")
    for message in warnings:
        print(f"warning: {message}")
    for message in errors:
        print(f"error: {message}")
    print(f"{len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


def cmd_find(args: argparse.Namespace) -> int:
    company = find_company(args.company) if args.company else None
    matches = 0
    for key, filing_blocks in load_blocks().items():
        if company and not key.startswith(f"{company.key}-"):
            continue
        if args.year and not key.endswith(f"-{args.year}"):
            continue
        for b in filing_blocks:
            if snippet_matches(args.text, b["text"]):
                matches += 1
                print(f"{key} p.{b['page']} [{b['kind']}] {b['section']}")
                print(f"    {_context(args.text, b['text'])}")
    print(f"{matches} matching blocks")
    return 0


def main() -> None:
    utf8_stdout()
    parser = argparse.ArgumentParser(description="Check or search the eval gold set.")
    commands = parser.add_subparsers(required=True)
    check_parser = commands.add_parser("check", help="validate eval/questions.csv")
    check_parser.set_defaults(run=cmd_check)
    find_parser = commands.add_parser("find", help="list the pages where a snippet appears")
    find_parser.add_argument("text", help="snippet; use '...' between parts")
    find_parser.add_argument("--company", help="Sea or Grab")
    find_parser.add_argument("--year", type=int, help="fiscal year of the report")
    find_parser.set_defaults(run=cmd_find)
    args = parser.parse_args()
    sys.exit(args.run(args))


if __name__ == "__main__":
    main()
