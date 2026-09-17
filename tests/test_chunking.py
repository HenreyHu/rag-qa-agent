from pathlib import Path

import pytest

from src.chunking import chunk_fixed, chunk_sections, chunk_tables, make_header
from src.config import (
    BODY_TOKENS,
    COMPANIES,
    HEADER_MAX_TOKENS,
    MAX_MODEL_TOKENS,
    OVERLAP_TOKENS,
    Filing,
)
from src.embedding import count_tokens
from src.parse_filing import Block, TableData

FILING = Filing("sea-2025", COMPANIES["sea"], 2025, Path("unused.htm"))
ITEM4 = "Item 4. Information on the Company"
ITEM5 = "Item 5. Operating and Financial Review and Prospects"
SUB_A = "A. Operating Results"
TOPICS = ("Overview", "Revenue", "Costs")


def sentences(count: int, tag: str) -> str:
    return " ".join(
        f"{tag} sentence {i} describes how revenue changed during the year." for i in range(count)
    )


def block(text, item, subitem="", topic="", level=0, page=1) -> Block:
    return Block(
        text=text,
        kind="heading" if level else "text",
        level=level,
        is_bold=bool(level),
        page=str(page),
        page_seq=page,
        item=item,
        subitem=subitem,
        section=" > ".join(part for part in (item, subitem, topic) if part),
    )


@pytest.fixture(scope="module")
def blocks() -> list[Block]:
    out = [block("ITEM 4. INFORMATION ON THE COMPANY", ITEM4, level=1, page=40)]
    out += [block(sentences(6, f"Business{i}"), ITEM4, page=40 + i // 4) for i in range(12)]
    out.append(block("ITEM 5. OPERATING AND FINANCIAL REVIEW", ITEM5, level=1, page=44))
    out.append(block(SUB_A, ITEM5, SUB_A, level=2, page=44))
    for topic in TOPICS:
        out.append(block(topic, ITEM5, SUB_A, topic, level=3, page=45))
        out += [block(sentences(4, f"{topic}{i}"), ITEM5, SUB_A, topic, page=45) for i in range(5)]
    out.append(block(sentences(60, "Long"), ITEM5, SUB_A, "Costs", page=46))
    table = TableData("", ["| a | b |", "|---|---|"], ["| x | 1 |"])
    out.append(
        Block(
            text=table.markdown(),
            kind="table",
            page="46",
            page_seq=46,
            item=ITEM5,
            subitem=SUB_A,
            section=f"{ITEM5} > {SUB_A} > Costs",
            table=table,
        )
    )
    return out


def body(chunk) -> str:
    return chunk.text.split("\n", 1)[1]


@pytest.mark.parametrize("chunker", [chunk_fixed, chunk_sections, chunk_tables])
def test_every_chunk_fits_the_model_window(blocks, chunker):
    chunks = chunker(blocks, FILING)
    assert chunks
    for chunk in chunks:
        assert chunk.n_tokens == count_tokens(chunk.text, special_tokens=True)
        assert chunk.n_tokens <= MAX_MODEL_TOKENS
        assert count_tokens(body(chunk)) <= BODY_TOKENS
        assert chunk.pages[0] == chunk.page


def test_fixed_windows_cover_the_text_with_overlap(blocks):
    text = "\n".join(b.text for b in blocks if b.kind != "table")
    bodies = [body(c) for c in chunk_fixed(blocks, FILING)]
    starts = [text.index(b) for b in bodies]
    assert starts == sorted(starts)
    assert starts[0] == 0
    assert starts[-1] + len(bodies[-1]) == len(text)
    for start, current, next_start in zip(starts, bodies, starts[1:], strict=False):
        overlap = text[next_start : start + len(current)]
        assert OVERLAP_TOKENS <= count_tokens(overlap) <= OVERLAP_TOKENS + 10


def test_fixed_chunks_record_every_page_they_touch(blocks):
    assert any(len(c.pages) > 1 for c in chunk_fixed(blocks, FILING))


def test_section_chunks_never_cross_item_or_sub_item_boundaries(blocks):
    narrative = [b for b in blocks if b.kind != "table"]

    def groups_of(line: str) -> set[tuple[str, str]]:
        return {
            (b.item, b.subitem)
            for b in narrative
            if line == b.text or (len(line) > 50 and line in b.text)
        }

    for chunk in chunk_sections(blocks, FILING):
        groups = set().union(*(groups_of(line) for line in body(chunk).split("\n")))
        assert len(groups) == 1, chunk.id


def test_section_chunks_start_topics_and_never_end_on_one(blocks):
    bodies = [body(c) for c in chunk_sections(blocks, FILING)]
    assert any(b.startswith("Revenue\n") for b in bodies)
    assert any(b.startswith("Costs\n") for b in bodies)
    assert not any(b.split("\n")[-1] in TOPICS for b in bodies)


def test_long_paragraph_is_split_at_sentence_ends(blocks):
    pieces = [
        line
        for c in chunk_sections(blocks, FILING)
        for line in body(c).split("\n")
        if line.startswith("Long")
    ]
    assert len(pieces) > 1
    assert all(piece.endswith("during the year.") for piece in pieces)


def test_header_names_company_year_and_section_and_is_capped():
    section = f"{ITEM5} > {SUB_A} > Revenue"
    assert make_header(FILING, section) == (
        f"Sea Limited | FY2025 annual report (20-F) | {section}"
    )
    long_header = make_header(FILING, " > ".join(["Very long section name"] * 30))
    assert long_header.startswith("Sea Limited | FY2025")
    assert count_tokens(long_header) <= HEADER_MAX_TOKENS


def test_chunks_are_deterministic_with_unique_ids(blocks):
    def run():
        chunks = (
            chunk_fixed(blocks, FILING)
            + chunk_sections(blocks, FILING)
            + chunk_tables(blocks, FILING)
        )
        return [(c.id, c.text) for c in chunks]

    first = run()
    assert first == run()
    assert len({chunk_id for chunk_id, _ in first}) == len(first)


def test_table_chunk_metadata(blocks):
    (chunk,) = chunk_tables(blocks, FILING)
    assert chunk.id == "sea-2025:table:0000:0"
    assert (chunk.is_table, chunk.strategy, chunk.company, chunk.year) == (
        True,
        "table",
        "Sea",
        2025,
    )
    meta = chunk.metadata()
    assert "id" not in meta and "text" not in meta
    assert meta["pages"] == ["46"]
