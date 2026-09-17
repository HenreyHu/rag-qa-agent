"""Parse an EDGAR inline-XBRL 20-F (HTML) into text and table blocks tagged with page and section.

EDGAR HTML has no real pages, but filings mark printed page breaks with CSS and print a page
label ("45", "F-12") at the bottom of each page. Blocks carry that printed label, because it is
what a reader sees and what the filing's own table of contents refers to.
"""

from __future__ import annotations

import argparse
import re
import time
from collections import Counter
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag
from bs4.element import PreformattedString

from src.config import utf8_stdout

BLOCK_TAGS = frozenset(
    {"p", "div", "li", "ul", "ol", "br", "hr", "center", "blockquote", "pre", "dl", "dt", "dd"}
    | {"table", "tr", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6"}
)
SKIP_TAGS = frozenset({"head", "script", "style", "template", "ix:header"})

# Matched against a style string with whitespace removed and lowercased.
PAGE_BREAK_RE = re.compile(r"(?:page-break-|(?<![-\w])break-)(before|after):(?:always|page)")
FONT_WEIGHT_RE = re.compile(r"font-weight:([a-z0-9]+)")

LABEL_RE = re.compile(r"\d{1,3}|F-\d{1,3}|[ivxlc]{1,6}")
# Sea FY2025 prints "ITEM16C." with no space.
ITEM_RE = re.compile(r"ITEM\s*(\d{1,2})([A-K]?)\s*\.\s*(.*)", re.IGNORECASE)
# No style requirement: Grab bolds sub-items ("A.Operating Results"), Sea underlines them.
SUBITEM_RE = re.compile(r"([A-H])\.\s*([A-Z].{2,90})")
TOC_ROW_RE = re.compile(r"(?:PART|ITEM)\s+[\dIVX]", re.IGNORECASE)

MAX_HEADING_CHARS = 120
# A bold line on this many pages is a running page header, not a section topic.
RUNNING_HEADER_MIN_PAGES = 5
MAX_LEAD_IN_CHARS = 400
LEAD_IN_RE = re.compile(r"following tables?|tables? below", re.IGNORECASE)
FRONT_MATTER = "Front matter"
FINANCIAL_STATEMENTS = "Item 18. Financial Statements"
SMALL_WORDS = frozenset(
    {"a", "an", "and", "as", "at", "but", "by", "for", "from", "in", "into", "nor", "of", "on"}
    | {"or", "per", "the", "to", "vs", "with"}
)

VALUE_RE = re.compile(
    r"\(?[-\N{MINUS SIGN}]?(?:US\$|S\$|\$|RMB|\N{EURO SIGN}|\N{POUND SIGN})?"
    r"[-\N{MINUS SIGN}]?\d[\d,]*(?:\.\d+)?\)?%?\)?"
)
YEAR_RE = re.compile(r"(?:19|20)\d\d")
DASH_VALUES = frozenset({"-", "--", "\N{EM DASH}", "\N{EN DASH}", "\N{MINUS SIGN}"})
PREFIX_CELLS = frozenset({"$", "US$", "S$", "RMB", "\N{EURO SIGN}", "\N{POUND SIGN}"})
SUFFIX_CELLS = frozenset({")", "%", ")%", "%)"})

# An explicit map rather than NFKC, which would also rewrite superscripts and fractions.
_TRANSLATION = str.maketrans(
    {
        **dict.fromkeys(["\N{NO-BREAK SPACE}", "\N{NARROW NO-BREAK SPACE}"], " "),
        **{chr(c): " " for c in range(0x2002, 0x200B)},  # en space through hair space
        **dict.fromkeys(
            ["\N{ZERO WIDTH SPACE}", "\N{ZERO WIDTH NO-BREAK SPACE}", "\N{SOFT HYPHEN}"]
        ),
        "\N{NON-BREAKING HYPHEN}": "-",
        "\N{GREEK QUESTION MARK}": ";",
    }
)
_SPACE_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    return _SPACE_RE.sub(" ", text.translate(_TRANSLATION)).strip()


@dataclass
class TableData:
    caption: str
    header: list[str]  # the markdown header row and its separator line
    rows: list[str]  # markdown body rows

    def markdown(self) -> str:
        lines = [self.caption] if self.caption else []
        return "\n".join(lines + self.header + self.rows)


@dataclass
class Block:
    text: str
    kind: str = "text"  # "text", "heading" or "table"
    level: int = 0  # heading level: 1 = Item, 2 = sub-item ("A."), 3 = bold topic line
    is_bold: bool = False
    page: str = ""  # printed page label, or "s<page_seq>" when the page has none
    page_seq: int = 0  # physical page number within the document, from 1
    item: str = ""
    subitem: str = ""
    section: str = ""
    table: TableData | None = None


def _style(tag: Tag) -> str:
    return "".join(str(tag.get("style", "")).split()).lower()


def _is_hidden(tag: Tag, style: str) -> bool:
    return tag.name in SKIP_TAGS or "display:none" in style


def _bold(tag: Tag, style: str, inherited: bool) -> bool:
    if tag.name in ("b", "strong"):
        return True
    match = FONT_WEIGHT_RE.search(style)
    if not match:
        return inherited
    weight = match.group(1)
    if weight.isdigit():
        return int(weight) >= 600
    if weight in ("bold", "bolder"):
        return True
    if weight in ("normal", "lighter"):
        return False
    return inherited


def _inline_text(node: Tag) -> str:
    parts: list[str] = []

    def visit(parent: Tag) -> None:
        for child in parent.children:
            if isinstance(child, NavigableString):
                if not isinstance(child, PreformattedString):
                    parts.append(str(child))
            elif not _is_hidden(child, _style(child)):
                is_block = child.name in BLOCK_TAGS
                if is_block:
                    parts.append(" ")
                visit(child)
                if is_block:
                    parts.append(" ")

    visit(node)
    return normalize("".join(parts))


def _colspan(cell: Tag) -> int:
    try:
        return max(1, int(str(cell.get("colspan", "1")).strip()))
    except ValueError:
        return 1


def _table_rows(table: Tag) -> list[list[tuple[str, int]]]:
    """(text, colspan) for each visible cell of each row that belongs to this table."""
    rows = []
    for tr in table.find_all("tr"):
        if tr.find_parent("table") is not table or _is_hidden(tr, _style(tr)):
            continue
        cells = [
            (_inline_text(cell), _colspan(cell))
            for cell in tr.find_all(("td", "th"), recursive=False)
            if not _is_hidden(cell, _style(cell))
        ]
        if cells:
            rows.append(cells)
    return rows


def _is_value(text: str) -> bool:
    if YEAR_RE.fullmatch(text):
        return False
    return text in DASH_VALUES or bool(VALUE_RE.fullmatch(text))


def _merge_affixes(cells: list[str]) -> None:
    # EDGAR tables put "$" and the closing ")" or "%" of a number in cells of their own.
    for i, text in enumerate(cells):
        if text in PREFIX_CELLS:
            j = next((j for j in range(i + 1, len(cells)) if cells[j]), None)
            if j is not None and _is_value(cells[j]):
                cells[j] = text + cells[j]
                cells[i] = ""
        elif text in SUFFIX_CELLS:
            j = next((j for j in range(i - 1, -1, -1) if cells[j]), None)
            if j is not None:
                cells[j] += text
                cells[i] = ""


def _count_header_rows(grid: list[list[str]]) -> int:
    has_value = [any(_is_value(c) for c in row if c) for row in grid]
    if not any(has_value):
        return 0  # text-only tables (e.g. "Description of the Matter | ...") are all content
    label_col = min(j for row in grid for j, c in enumerate(row) if c)
    count = 0
    for i, row in enumerate(grid):
        filled = [j for j, c in enumerate(row) if c]
        # A row with only a label in the label column ("Revenue:") starts the body.
        if has_value[i] or (i > 0 and filled == [label_col]):
            break
        count += 1
    return min(count, 4, len(grid) - 1)


def _md_row(cells: list[str]) -> str:
    return "| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |"


def build_table(rows: list[list[tuple[str, int]]]) -> TableData | None:
    """Turn (text, colspan) rows into a markdown table with EDGAR layout quirks removed."""
    width = max(sum(span for _, span in row) for row in rows)
    grid: list[list[str]] = []
    placements: list[list[tuple[int, int]]] = []
    for row in rows:
        cells = [""] * width
        placed = []
        col = 0
        for text, span in row:
            cells[col] = text  # a spanning cell's text goes in its first column only
            placed.append((col, span))
            col += span
        _merge_affixes(cells)
        if any(cells):  # spacer rows would otherwise count as header rows
            grid.append(cells)
            placements.append(placed)
    if not grid:
        return None

    n_header = _count_header_rows(grid)
    header_cols: list[list[str]] = [[] for _ in range(width)]
    captions = []
    for r in range(n_header):
        filled = [(col, span) for col, span in placements[r] if grid[r][col]]
        if len(filled) == 1:
            captions.append(grid[r][filled[0][0]])  # e.g. "For the Year Ended December 31,"
            continue
        for col, span in filled:
            # Header text covers every column it spans, so it survives spacer-column removal.
            for c in range(col, min(col + span, width)):
                header_cols[c].append(grid[r][col])

    body = [row for row in grid[n_header:] if any(row)]
    keep = [c for c in range(width) if any(row[c] for row in body)]
    if not keep:
        return None
    header = [" ".join(dict.fromkeys(header_cols[c])) for c in keep]
    return TableData(
        caption="\n".join(captions),
        header=[_md_row(header), "|" + "|".join("---" for _ in keep) + "|"],
        rows=[_md_row([row[c] for c in keep]) for row in body],
    )


class _Walker:
    """Walks the DOM in document order, splitting text into blocks and blocks into pages."""

    def __init__(self) -> None:
        self.pages: list[list[Block]] = [[]]
        self.stats: Counter[str] = Counter()
        self._parts: list[tuple[str, bool]] = []
        self._cell_depth = 0

    def run(self, body: Tag) -> list[list[Block]]:
        self._walk(body, bold=False)
        self._flush()
        return self.pages

    def _flush(self) -> None:
        text = normalize("".join(part for part, _ in self._parts))
        if text:
            is_bold = all(bold for part, bold in self._parts if part.strip())
            self.pages[-1].append(Block(text=text, is_bold=is_bold))
        self._parts = []

    def _page_break(self) -> None:
        self._flush()
        self.stats["page_breaks"] += 1
        if self.pages[-1]:
            self.pages.append([])
        else:
            self.stats["empty_pages_skipped"] += 1

    def _boundary(self) -> None:
        if self._cell_depth:
            self._parts.append((" ", False))
        else:
            self._flush()

    def _walk(self, node: Tag, bold: bool) -> None:
        for child in node.children:
            if isinstance(child, NavigableString):
                # Comments (Sea puts <!--Anchor--> before headings) and CDATA are not text.
                if not isinstance(child, PreformattedString):
                    self._parts.append((str(child), bold))
                continue
            style = _style(child)
            if _is_hidden(child, style):
                continue
            breaks = PAGE_BREAK_RE.findall(style)
            if "before" in breaks:
                self._page_break()
            if child.name == "table" and not self._cell_depth:
                self._table(child, bold)
            else:
                # Sea FY2024 splits page labels as F-7<div style="display:inline">8</div>.
                is_block = child.name in BLOCK_TAGS and "display:inline" not in style
                if is_block:
                    self._boundary()
                self._walk(child, _bold(child, style, bold))
                if is_block:
                    self._boundary()
            if "after" in breaks:
                self._page_break()

    def _table(self, table: Tag, bold: bool) -> None:
        self._flush()
        rows = _table_rows(table)
        if not rows:
            return
        if len(rows) == 1:
            # One-row tables are layout: bullets, footnotes, and every heading in Sea's filings.
            self.stats["one_row_tables"] += 1
            self._cell_depth += 1
            self._walk(table, _bold(table, _style(table), bold))
            self._cell_depth -= 1
            self._flush()
            return
        nested_breaks = sum(1 for tag in table.find_all(True) if PAGE_BREAK_RE.search(_style(tag)))
        self.stats["page_breaks_inside_tables"] += nested_breaks
        row_texts = [" ".join(text for text, _ in row if text) for row in rows]
        if sum(1 for text in row_texts if TOC_ROW_RE.match(text)) >= 5:
            self.stats["toc_tables_dropped"] += 1
            return
        data = build_table(rows)
        if data is None:
            self.stats["empty_tables_dropped"] += 1
            return
        self.stats["tables"] += 1
        self.pages[-1].append(Block(text=data.markdown(), kind="table", table=data))


def _take_label(page: list[Block]) -> str | None:
    """Remove and return the printed page label: the last non-table block, if it looks like one."""
    for i in range(len(page) - 1, -1, -1):
        if page[i].kind == "table":
            continue
        candidate = page[i].text.replace(" ", "")
        if LABEL_RE.fullmatch(candidate):
            del page[i]
            return candidate
        return None
    return None


def _is_toc_link(block: Block) -> bool:
    return block.kind == "text" and block.text.lower() == "table of contents"


def _attach_lead_ins(blocks: list[Block]) -> None:
    # "The following table sets forth..." tells the embedding what an otherwise bare table is.
    for prev, block in pairwise(blocks):
        if block.table is None or prev.kind == "table":
            continue
        lead_in = prev.text
        if not (lead_in.endswith(":") or LEAD_IN_RE.search(lead_in)):
            continue
        if len(lead_in) > MAX_LEAD_IN_CHARS:
            lead_in = lead_in.rsplit(". ", 1)[-1][-MAX_LEAD_IN_CHARS:]
        block.table.caption = "\n".join(filter(None, [lead_in, block.table.caption]))
        block.text = block.table.markdown()


def _title(text: str) -> str:
    text = text.strip().rstrip(".").strip()
    if not text.isupper():
        return text
    words = text.lower().split()
    return " ".join(
        w if i and w in SMALL_WORDS else re.sub(r"[a-z]", lambda m: m.group().upper(), w, count=1)
        for i, w in enumerate(words)
    )


def _running_headers(blocks: list[Block]) -> set[str]:
    pages_by_text: dict[str, set[int]] = {}
    for b in blocks:
        if b.is_bold and len(b.text) <= MAX_HEADING_CHARS:
            pages_by_text.setdefault(b.text, set()).add(b.page_seq)
    return {text for text, pages in pages_by_text.items() if len(pages) >= RUNNING_HEADER_MIN_PAGES}


def _assign_sections(blocks: list[Block]) -> None:
    running_headers = _running_headers(blocks)
    item = subitem = topic = ""
    item_key: tuple[int, str] = (0, "")
    subitem_letter = ""
    in_financials = False
    for b in blocks:
        if b.page.startswith("F-") and not in_financials:
            # Items 17-19 share a page before the F-pages, so without this override every
            # financial statement page would be filed under Item 19 (Exhibits).
            in_financials = True
            item, subitem, topic, subitem_letter = FINANCIAL_STATEMENTS, "", "", ""
        text = b.text
        short = len(text) <= MAX_HEADING_CHARS
        item_match = ITEM_RE.fullmatch(text) if b.kind == "text" and short else None
        if item_match and not in_financials and (b.is_bold or text.isupper()):
            key = (int(item_match.group(1)), item_match.group(2).upper())
            if key > item_key:  # guards against cross-references that look like headings
                item_key = key
                item = f"Item {key[0]}{key[1]}. {_title(item_match.group(3))}".strip()
                subitem = topic = subitem_letter = ""
                b.kind, b.level = "heading", 1
        # Sub-items belong to the 20-F Items; lettered lists inside financial statement notes don't.
        if b.kind == "text" and item and short and not in_financials:
            sub_match = SUBITEM_RE.fullmatch(text)
            if sub_match and not text.endswith(".") and sub_match.group(1) > subitem_letter:
                subitem_letter = sub_match.group(1)
                subitem = f"{subitem_letter}. {_title(sub_match.group(2))}"
                topic = ""
                b.kind, b.level = "heading", 2
        if (
            b.kind == "text"
            and b.is_bold
            and short
            and not text.endswith(".")
            and re.search(r"[A-Za-z]{3}", text)
            and text not in running_headers
        ):
            topic = text
            b.kind, b.level = "heading", 3
        b.item = item or FRONT_MATTER
        b.subitem = subitem
        b.section = " > ".join(part for part in (b.item, subitem, topic) if part)


def parse_html(html: bytes | str) -> tuple[list[Block], Counter[str]]:
    soup = BeautifulSoup(html, "html.parser")
    walker = _Walker()
    pages = walker.run(soup.body or soup)
    blocks: list[Block] = []
    for seq, page in enumerate((p for p in pages if p), start=1):
        page = [b for b in page if not _is_toc_link(b)]
        label = _take_label(page) or f"s{seq}"
        for b in page:
            b.page, b.page_seq = label, seq
        blocks.extend(page)
    _attach_lead_ins(blocks)
    _assign_sections(blocks)
    walker.stats["pages"] = len([p for p in pages if p])
    return blocks, walker.stats


def parse_filing(path: Path) -> list[Block]:
    return parse_html(path.read_bytes())[0]


def _label_runs(labels: list[str]) -> str:
    """Compress page labels into runs, so gaps and odd labels stand out: '3..150, F-2..F-79'."""
    runs: list[list] = []
    for label in labels:
        match = re.fullmatch(r"(F-)?(\d+)", label)
        key = (match.group(1) or "", int(match.group(2))) if match else None
        last = runs[-1] if runs else None
        if last and key and last[2] and key == (last[2][0], last[2][1] + 1):
            last[1], last[2] = label, key
        else:
            runs.append([label, label, key])
    return ", ".join(first if first == last else f"{first}..{last}" for first, last, _ in runs)


def main() -> None:
    utf8_stdout()
    parser = argparse.ArgumentParser(description="Print a parse report for one filing.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--page", help="also print every block on this printed page, e.g. F-5")
    args = parser.parse_args()

    start = time.perf_counter()
    blocks, stats = parse_html(args.path.read_bytes())
    elapsed = time.perf_counter() - start

    labels = {b.page_seq: b.page for b in blocks}
    unlabeled = [seq for seq, label in labels.items() if label.startswith("s")]
    kinds = Counter(b.kind for b in blocks)
    table_chars = sum(len(b.text) for b in blocks if b.kind == "table")
    text_chars = sum(len(b.text) for b in blocks if b.kind != "table")
    print(f"{args.path.name}: parsed in {elapsed:.1f}s")
    print(f"pages: {len(labels)} ({len(unlabeled)} unlabeled: {unlabeled})")
    print(f"labels: {_label_runs([labels[s] for s in sorted(labels)])}")
    print(f"blocks: {dict(kinds)}; characters: {text_chars:,} text, {table_chars:,} tables")
    print(f"walker: {dict(stats)}")
    items = [b for b in blocks if b.level == 1]
    print(f"items ({len(items)}):")
    for b in items:
        print(f"  p.{b.page:<6} {b.item}")
    subitems = Counter(b.item for b in blocks if b.level == 2)
    print(f"sub-items per item: {dict(subitems)}")
    print(f"topic headings: {sum(1 for b in blocks if b.level == 3)}")
    if args.page:
        print(f"\n--- page {args.page} ---")
        for b in blocks:
            if b.page == args.page:
                print(f"[{b.kind}{b.level or ''}{' bold' if b.is_bold else ''}] {b.section}")
                print(f"{b.text}\n")


if __name__ == "__main__":
    main()
