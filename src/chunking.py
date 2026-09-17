"""Turn parsed blocks into chunks: two strategies for narrative text, one shared for tables.

Every chunk's text is a one-line context header plus a body of at most BODY_TOKENS tokens, so
header + body + [CLS] + [SEP] always fits bge-small's 512-token window.
"""

from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import asdict, dataclass
from itertools import groupby

from src.config import BODY_TOKENS, HEADER_MAX_TOKENS, OVERLAP_TOKENS, SOFT_BREAK_MIN_TOKENS, Filing
from src.embedding import count_tokens, tokenize
from src.parse_filing import Block, TableData

SENTENCE_END_RE = re.compile(r'(?<=[.!?;])\s+(?=["\N{LEFT DOUBLE QUOTATION MARK}(]?[A-Z0-9])')


@dataclass
class Chunk:
    id: str
    text: str  # context header + body: exactly what gets embedded and stored
    filing: str
    company: str
    year: int
    page: str
    pages: list[str]  # every page the body touches, so a citation of any of them can match
    page_seq: int
    section: str
    item: str
    is_table: bool
    strategy: str  # "fixed", "section" or "table"
    n_tokens: int  # including [CLS] and [SEP]

    def metadata(self) -> dict:
        meta = asdict(self)
        del meta["id"], meta["text"]
        return meta


def _snap(word_ids: list[int | None], pos: int, lo: int) -> int:
    """Move a cut point back to the start of a word, so no word is split between chunks.

    Falls back to the original position if no word boundary exists above lo.
    """
    p = pos
    while lo < p < len(word_ids) and word_ids[p] == word_ids[p - 1]:
        p -= 1
    return p if p > lo else pos


def _truncate(text: str, max_tokens: int) -> str:
    enc = tokenize(text)
    if len(enc.ids) <= max_tokens:
        return text
    end = _snap(enc.word_ids, max_tokens, lo=0)
    return text[: enc.offsets[end - 1][1]]


def make_header(filing: Filing, section: str) -> str:
    # Tables and mid-section paragraphs rarely name the company or year; the header does, so
    # the embedding can tell Sea's revenue table from Grab's.
    header = f"{filing.company.full_name} | FY{filing.fiscal_year} annual report (20-F) | {section}"
    return _truncate(header, HEADER_MAX_TOKENS)


def _make_chunk(
    filing: Filing,
    chunk_id: str,
    strategy: str,
    body: str,
    span: list[Block],
) -> Chunk:
    first = span[0]
    text = f"{make_header(filing, first.section)}\n{body}"
    return Chunk(
        id=chunk_id,
        text=text,
        filing=filing.key,
        company=filing.company.short_name,
        year=filing.fiscal_year,
        page=first.page,
        pages=list(dict.fromkeys(b.page for b in span)),
        page_seq=first.page_seq,
        section=first.section,
        item=first.item,
        is_table=strategy == "table",
        strategy=strategy,
        n_tokens=count_tokens(text, special_tokens=True),
    )


def chunk_fixed(blocks: list[Block], filing: Filing) -> list[Chunk]:
    """Fixed-size token windows over the filing's whole narrative, ignoring section boundaries."""
    narrative = [b for b in blocks if b.kind != "table"]
    if not narrative:
        return []
    starts = []
    position = 0
    for b in narrative:
        starts.append(position)
        position += len(b.text) + 1
    text = "\n".join(b.text for b in narrative)
    # One tokenization of the whole text; bodies are sliced from the original string by character
    # offsets, because decoding tokens would lowercase everything (bge's vocabulary is uncased).
    enc = tokenize(text)
    offsets, word_ids, n = enc.offsets, enc.word_ids, len(enc.ids)

    chunks: list[Chunk] = []
    start = 0
    while start < n:
        end = min(start + BODY_TOKENS, n)
        if end < n:
            end = _snap(word_ids, end, lo=start + 1)
        char_start, char_end = offsets[start][0], offsets[end - 1][1]
        first = bisect_right(starts, char_start) - 1
        last = bisect_right(starts, char_end - 1) - 1
        chunk_id = f"{filing.key}:fixed:{len(chunks):05d}"
        body = text[char_start:char_end]
        chunks.append(_make_chunk(filing, chunk_id, "fixed", body, narrative[first : last + 1]))
        if end == n:
            break
        # The overlap keeps a sentence that straddles a cut whole in at least one chunk.
        start = _snap(word_ids, max(end - OVERLAP_TOKENS, start + 1), lo=start + 1)
    return chunks


def _token_windows(text: str) -> list[str]:
    enc = tokenize(text)
    pieces = []
    start, n = 0, len(enc.ids)
    while start < n:
        end = min(start + BODY_TOKENS, n)
        if end < n:
            end = _snap(enc.word_ids, end, lo=start + 1)
        pieces.append(text[enc.offsets[start][0] : enc.offsets[end - 1][1]])
        start = end
    return pieces


def _split_long(text: str) -> list[str]:
    """Split a block over the budget at sentence ends, then by token windows as a last resort."""
    if count_tokens(text) <= BODY_TOKENS:
        return [text]
    pieces: list[str] = []
    current: list[str] = []
    size = 0
    for sentence in SENTENCE_END_RE.split(text):
        n = count_tokens(sentence)
        if current and (n > BODY_TOKENS or size + n > BODY_TOKENS):
            pieces.append(" ".join(current))
            current, size = [], 0
        if n > BODY_TOKENS:
            pieces.extend(_token_windows(sentence))
            continue
        current.append(sentence)
        size += n
    if current:
        pieces.append(" ".join(current))
    return pieces


def chunk_sections(blocks: list[Block], filing: Filing) -> list[Chunk]:
    """Pack whole paragraphs into chunks that never cross an Item or sub-item boundary."""
    chunks: list[Chunk] = []

    def emit(items: list[tuple[Block, str, int]]) -> None:
        chunk_id = f"{filing.key}:section:{len(chunks):05d}"
        body = "\n".join(piece for _, piece, _ in items)
        chunks.append(_make_chunk(filing, chunk_id, "section", body, [b for b, _, _ in items]))

    narrative = (b for b in blocks if b.kind != "table")
    for _, group in groupby(narrative, key=lambda b: (b.item, b.subitem)):
        current: list[tuple[Block, str, int]] = []
        size = 0
        for block in group:
            for piece in _split_long(block.text):
                n = count_tokens(piece)
                overflow = size + n > BODY_TOKENS
                # Topic headings ("Revenue", "Overview") start a new chunk only once the current
                # one has some substance; otherwise every short subsection becomes its own chunk.
                soft_break = block.level == 3 and size >= SOFT_BREAK_MIN_TOKENS
                if current and (overflow or soft_break):
                    carried: list[tuple[Block, str, int]] = []
                    if overflow:
                        # Move trailing headings to the next chunk, next to the text they introduce.
                        while current and current[-1][0].kind == "heading":
                            carried.insert(0, current.pop())
                        if sum(t for *_, t in carried) + n > BODY_TOKENS:
                            current += carried
                            carried = []
                    if current:
                        emit(current)
                    current = carried
                    size = sum(t for *_, t in current)
                current.append((block, piece, n))
                size += n
        if current:
            emit(current)
    return chunks


def split_table(table: TableData, budget: int) -> list[str]:
    """Split a table into bodies of at most `budget` tokens, repeating caption and header in each."""
    caption = _truncate(table.caption, budget // 4) if table.caption else ""
    fixed = ([caption] if caption else []) + table.header
    fixed_size = count_tokens("\n".join(fixed))
    parts: list[list[str]] = []
    rows: list[str] = []
    size = fixed_size
    for row in table.rows:
        n = count_tokens(row)
        if rows and size + n > budget:
            parts.append(rows)
            rows, size = [], fixed_size
        rows.append(row)
        size += n
    parts.append(rows)
    # _truncate is a safety net for pathological rows wider than the whole budget.
    return [_truncate("\n".join(fixed + part), budget) for part in parts]


def chunk_tables(blocks: list[Block], filing: Filing) -> list[Chunk]:
    """One chunk per table (split by rows if needed); identical for both strategies' collections."""
    chunks = []
    tables = [b for b in blocks if b.table is not None]
    for t, block in enumerate(tables):
        for part, body in enumerate(split_table(block.table, BODY_TOKENS)):
            chunk_id = f"{filing.key}:table:{t:04d}:{part}"
            chunks.append(_make_chunk(filing, chunk_id, "table", body, [block]))
    return chunks
