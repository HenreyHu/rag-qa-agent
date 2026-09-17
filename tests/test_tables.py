from src.chunking import split_table
from src.embedding import count_tokens
from src.parse_filing import TableData, build_table, parse_html


def parse_body(body: str):
    return parse_html(f"<html><body>{body}</body></html>")[0]


def test_one_row_layout_table_becomes_a_text_block():
    blocks = parse_body("<table><tr><td>&#9679;</td><td>Our platform grew.</td></tr></table>")
    assert [(b.kind, b.text) for b in blocks] == [("text", "\N{BLACK CIRCLE} Our platform grew.")]


def test_text_only_table_has_no_header_row():
    blocks = parse_body(
        "<table>"
        "<tr><td>Description of the Matter</td><td>Long text.</td></tr>"
        "<tr><td>How We Addressed the Matter</td><td>More text.</td></tr>"
        "</table>"
    )
    assert blocks[0].text.splitlines() == [
        "|  |  |",
        "|---|---|",
        "| Description of the Matter | Long text. |",
        "| How We Addressed the Matter | More text. |",
    ]


def test_pipe_inside_a_cell_is_escaped():
    table = build_table([[("Name", 1), ("2025", 1)], [("A | B", 1), ("5", 1)]])
    assert table.header[0] == "| Name | 2025 |"
    assert table.rows == ["| A \\| B | 5 |"]


def test_empty_tables_are_dropped():
    assert build_table([[("", 1), ("", 2)], [("", 3)]]) is None
    assert parse_body("<table><tr><td></td></tr><tr><td>&#160;</td></tr></table>") == []


def test_split_table_repeats_caption_and_header():
    table = TableData(
        caption="Revenue by segment",
        header=["| Segment | 2025 |", "|---|---|"],
        rows=[f"| Segment {i} with a fairly long descriptive name | {i},000 |" for i in range(60)],
    )
    parts = split_table(table, 120)
    assert len(parts) > 1
    for part in parts:
        assert part.split("\n")[:3] == ["Revenue by segment", "| Segment | 2025 |", "|---|---|"]
        assert count_tokens(part) <= 120
    assert [row for part in parts for row in part.split("\n")[3:]] == table.rows


def test_split_table_truncates_a_row_wider_than_the_budget():
    table = TableData(caption="", header=["| a |", "|---|"], rows=["| " + "word " * 300 + "|"])
    parts = split_table(table, 100)
    assert len(parts) == 1
    assert count_tokens(parts[0]) <= 100
