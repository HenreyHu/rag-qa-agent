import pytest

from src.citations import Citation, parse_citations, parse_pages


def one(text: str) -> Citation:
    (citation,) = parse_citations(text)
    return citation


def test_single_page():
    assert one("Revenue was $22.9B [Sea, FY2025, p.95].") == Citation("Sea", 2025, ("95",))


def test_pp_range_is_expanded():
    assert one("[Grab, FY2025, pp.88-90]").pages == ("88", "89", "90")


def test_list_of_pages():
    assert one("[Grab, FY2025, pp.88, 97, 98]").pages == ("88", "97", "98")


def test_repeated_p_prefix_and_and():
    assert one("[Sea, FY2024, p.12, p.14]").pages == ("12", "14")
    assert one("[Sea, FY2024, pp.12 and 14]").pages == ("12", "14")


def test_mixed_list_and_range():
    assert one("[Sea, FY2025, pp. 3, 5-6]").pages == ("3", "5", "6")


def test_f_pages_stay_labels():
    assert one("[Sea, FY2025, p.F-11]").pages == ("F-11",)
    assert one("[Sea, FY2025, pp.F-11-F-13]").pages == ("F-11", "F-12", "F-13")


def test_retrieve_format_matches():
    # src.retrieve.citation() renders multi-page chunks as "p.12, 13".
    assert one("[Sea, FY2025, p.12, 13]").pages == ("12", "13")


def test_multiple_citations_in_order():
    text = "Sea grew [Sea, FY2025, p.95] faster than Grab [Grab, FY2025, p.88]."
    assert [c.company for c in parse_citations(text)] == ["Sea", "Grab"]


def test_whitespace_and_case_tolerated():
    assert one("[ Sea ,  fy 2025 , P.95 ]") == Citation("Sea", 2025, ("95",))


@pytest.mark.parametrize(
    "text",
    [
        "[Sea, FY2025, p.95",  # missing closing bracket
        "Sea, FY2025, p.95]",  # missing opening bracket
        "[Sea, 2025, p.95]",  # no FY
        "[Sea, FY2025]",  # no page
        "[Sea, FY2025, p.]",  # empty page
        "[Sea, FY2025, p.abc]",  # non-numeric page
        "[Sea, FY2025, pp.99-12]",  # backwards range
        "[Sea, FY2025, pp.1-9999]",  # absurd range
    ],
)
def test_malformed_is_skipped(text):
    assert parse_citations(text) == []


def test_nested_opening_bracket_keeps_inner_citation():
    assert one("[[Sea, FY2025, p.95]").pages == ("95",)


def test_bad_citation_does_not_hide_good_one():
    text = "[Sea, FY2025, p.] but also [Grab, FY2025, p.88]"
    assert [c.company for c in parse_citations(text)] == ["Grab"]


def test_no_citations_and_idk():
    assert parse_citations("I don't know.") == []
    assert parse_citations("") == []


def test_parse_pages_rejects_empty():
    assert parse_pages("p.") is None
