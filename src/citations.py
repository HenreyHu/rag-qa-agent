"""Parse `[Company, FYyear, p.X]` citations out of a model answer.

Pages stay strings because the filings use labels like "F-11" as well as plain numbers.
Malformed brackets are skipped rather than raised, so one bad citation never sinks a whole eval run.
"""

import re
from dataclasses import dataclass

# Innermost brackets only, so a stray "[" earlier in the text can't swallow a real citation.
BRACKET = re.compile(r"\[([^\[\]]+)\]")
BODY = re.compile(
    r"^\s*(?P<company>[^,]+?)\s*,\s*FY\s*(?P<year>\d{4})\s*,\s*(?P<pages>pp?\..+)$", re.IGNORECASE
)
PAGE_PREFIX = re.compile(r"^pp?\.\s*", re.IGNORECASE)
RANGE = re.compile(
    r"^(?:(?P<prefix>[A-Za-z])-)?(?P<start>\d+)\s*[-–—]\s*(?:[A-Za-z]-)?(?P<end>\d+)$"
)
PAGE = re.compile(r"^(?:[A-Za-z]-)?\d+$")
MAX_RANGE = 50  # a "range" wider than this is almost certainly not a page span


@dataclass(frozen=True)
class Citation:
    company: str
    year: int
    pages: tuple[str, ...]


def parse_pages(text: str) -> tuple[str, ...] | None:
    """'p.12', 'pp.12-14', 'p.12, p.14', 'pp. 3, 5-6 and F-11' -> page labels, or None if malformed."""
    pages: list[str] = []
    for token in re.split(r",|\band\b", text):
        token = PAGE_PREFIX.sub("", token.strip())
        if not token:
            continue
        span = RANGE.match(token)
        if span:
            start, end = int(span["start"]), int(span["end"])
            if not start <= end <= start + MAX_RANGE:
                return None
            prefix = f"{span['prefix']}-" if span["prefix"] else ""
            pages.extend(f"{prefix}{n}" for n in range(start, end + 1))
        elif PAGE.match(token):
            pages.append(token)
        else:
            return None
    return tuple(pages) if pages else None


def parse_citations(text: str) -> list[Citation]:
    """Every well-formed citation in the text, in order. Malformed ones are dropped."""
    citations = []
    for match in BRACKET.finditer(text):
        body = BODY.match(match[1])
        pages = parse_pages(body["pages"]) if body else None
        if body and pages:
            citations.append(Citation(body["company"].strip(), int(body["year"]), pages))
    return citations
