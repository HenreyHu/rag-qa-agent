from pathlib import Path

import pytest

from src.config import RAW_DIR
from src.parse_filing import FINANCIAL_STATEMENTS, Block, normalize, parse_filing, parse_html

FIXTURES = Path(__file__).parent / "fixtures"


def page_labels(blocks: list[Block]) -> list[str]:
    return list(dict.fromkeys(b.page for b in blocks))


def parse_body(body: str) -> list[Block]:
    return parse_html(f"<html><body>{body}</body></html>")[0]


def find(blocks: list[Block], prefix: str) -> Block:
    return next(b for b in blocks if b.text.startswith(prefix))


@pytest.fixture(scope="module")
def broadridge() -> list[Block]:
    return parse_filing(FIXTURES / "broadridge.htm")


@pytest.fixture(scope="module")
def donnelley() -> list[Block]:
    return parse_filing(FIXTURES / "donnelley.htm")


@pytest.fixture(scope="module")
def workiva() -> list[Block]:
    return parse_filing(FIXTURES / "workiva.htm")


class TestBroadridge:
    def test_nested_page_breaks_and_printed_labels(self, broadridge):
        assert page_labels(broadridge) == ["s1", "92", "93"]

    def test_back_links_comments_and_hidden_header_are_dropped(self, broadridge):
        texts = " ".join(b.text for b in broadridge)
        assert "Table of Contents" not in texts
        assert "Anchor" not in texts
        assert "HIDDEN" not in texts

    def test_headings_inside_one_row_tables(self, broadridge):
        headings = [(b.level, b.text) for b in broadridge if b.kind == "heading"]
        assert (1, "ITEM 5. OPERATING AND FINANCIAL REVIEW AND PROSPECTS") in headings
        assert (2, "A. Operating Results") in headings
        assert (3, "Revenue") in headings
        paragraph = find(broadridge, "We generate revenue")
        assert paragraph.page == "92"
        assert paragraph.section == (
            "Item 5. Operating and Financial Review and Prospects > A. Operating Results > Revenue"
        )
        assert find(broadridge, "Our results").page == "93"
        assert find(broadridge, "SEA LIMITED").item == "Front matter"

    def test_financial_table_markdown(self, broadridge):
        table = next(b for b in broadridge if b.kind == "table")
        assert table.page == "92"
        assert table.text.splitlines() == [
            "We generate revenue primarily from e-commerce. "
            + "The table below sets forth our revenue breakdown.",
            "For the Year Ended December 31,",
            "|  | 2024 | 2025 |",
            "|---|---|---|",
            "| Service revenue |  |  |",
            "| E-commerce | $10,862,263 | $14,545,894 |",
            "| Net loss | $(1,234) | $\N{EM DASH} |",
            "| Total revenue | $16,819,866 | $22,938,469 |",
        ]


class TestDonnelley:
    def test_page_labels_including_split_and_excluded_labels(self, donnelley):
        # The first page holds only the table of contents, which is dropped entirely.
        assert page_labels(donnelley) == ["144", "F-78", "F-20"]

    def test_table_of_contents_is_not_indexed(self, donnelley):
        assert not any("IDENTITY OF DIRECTORS" in b.text for b in donnelley)

    def test_items_on_one_page_then_financial_statement_override(self, donnelley):
        items = [b.item for b in donnelley if b.level == 1]
        assert items == [
            "Item 17. Financial Statements",
            "Item 18. Financial Statements",
            "Item 19. Exhibits",
        ]
        assert find(donnelley, "We have elected").item == "Item 17. Financial Statements"
        assert find(donnelley, "The exhibit index").item == "Item 19. Exhibits"
        cash = find(donnelley, "Cash and cash")
        assert (cash.page, cash.section) == ("F-78", f"{FINANCIAL_STATEMENTS} > SEA LIMITED")
        notes = find(donnelley, "The notes to")
        assert (notes.page, notes.item) == ("F-20", FINANCIAL_STATEMENTS)


class TestWorkiva:
    def test_hr_page_breaks_and_roman_label(self, workiva):
        assert page_labels(workiva) == ["s1", "i", "83"]
        assert find(workiva, "Forward-looking").page == "i"

    def test_hidden_inline_fact_is_dropped(self, workiva):
        assert find(workiva, "Revenue grew").text == "Revenue grew in 2025. See the table below."

    def test_bold_div_headings(self, workiva):
        sub_item = find(workiva, "A.Operating")
        assert (sub_item.level, sub_item.subitem) == (2, "A. Operating Results")
        topic = find(workiva, "Revenue by segment")
        assert topic.level == 3
        assert topic.item == "Item 5. Operating and Financial Review and Prospects"

    def test_percent_suffix_cells_and_lead_in_caption(self, workiva):
        table = next(b for b in workiva if b.kind == "table")
        assert table.text.splitlines() == [
            "Revenue grew in 2025. See the table below.",
            "| (in $ millions) | 2025 | 2024 |",
            "|---|---|---|",
            "| Deliveries | 1,800 | 1,493 |",
            "| Adjusted margin | 12.5% | (3.0)% |",
        ]


def test_self_closing_bold_div_does_not_bold_following_text():
    blocks = parse_body('<div style="font-weight:bold"/><p>plain text</p>')
    assert [(b.text, b.is_bold) for b in blocks] == [("plain text", False)]


def test_css3_page_break_syntax():
    blocks = parse_body('<p>one</p><div style="break-before: page">two</div><p>7</p>')
    assert [(b.text, b.page) for b in blocks] == [("one", "s1"), ("two", "7")]


def test_a_sentence_at_the_bottom_of_a_page_is_not_a_label():
    blocks = parse_body(
        '<p>First page.</p><hr style="page-break-after:always"/><p>Second page ends here.</p>'
    )
    assert [(b.text, b.page) for b in blocks] == [
        ("First page.", "s1"),
        ("Second page ends here.", "s2"),
    ]


def test_item_headings_without_space_and_cross_reference_guard():
    blocks = parse_body(
        "<p><b>ITEM 5. OPERATING RESULTS</b></p><p>text a</p>"
        "<p><b>ITEM16C. PRINCIPAL ACCOUNTANT FEES AND SERVICES</b></p><p>text b</p>"
        "<p><b>ITEM 3. KEY INFORMATION</b></p><p>text c</p>"
    )
    assert [b.item for b in blocks if b.text.startswith("text")] == [
        "Item 5. Operating Results",
        "Item 16C. Principal Accountant Fees and Services",
        "Item 16C. Principal Accountant Fees and Services",
    ]


def test_running_page_headers_are_not_topics():
    page = '<p><b>SEA LIMITED</b></p><p>Body text {}.</p><hr style="page-break-after:always"/>'
    blocks = parse_body("".join(page.format(i) for i in range(5)))
    assert not any(b.level for b in blocks)
    assert {b.section for b in blocks} == {"Front matter"}


def test_normalize_maps_unusual_whitespace_and_punctuation():
    raw = (
        "a\N{NO-BREAK SPACE}b\N{EM SPACE}c\N{ZERO WIDTH SPACE}d"
        "\N{NON-BREAKING HYPHEN}e\N{GREEK QUESTION MARK}  "
    )
    assert normalize(raw) == "a b cd-e;"


@pytest.mark.parametrize("path", sorted(RAW_DIR.glob("*_20-F.htm")), ids=lambda p: p.stem)
def test_real_filing_structure(path):
    blocks = parse_filing(path)
    labels = [b.page for b in {b.page_seq: b for b in blocks}.values()]
    assert sum(label.startswith("s") for label in labels) <= 5
    body_pages = [int(label) for label in labels if label.isdigit()]
    financial_pages = [int(label[2:]) for label in labels if label.startswith("F-")]
    for run in (body_pages, financial_pages):
        assert run == list(range(run[0], run[0] + len(run))), "page labels should have no gaps"
    items = [b.item for b in blocks if b.level == 1]
    assert len(items) >= 30
    assert any(item.startswith("Item 5. Operating and Financial Review") for item in items)
    assert all(b.item == FINANCIAL_STATEMENTS for b in blocks if b.page.startswith("F-"))
