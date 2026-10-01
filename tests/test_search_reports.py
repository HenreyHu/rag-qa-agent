import json

import pytest

from src import tools
from src.tools import search_reports, tool_schemas

HIT = {
    "id": "sea-2025:section:00001",
    "text": "Sea Limited | FY2025 annual report (20-F) | Item 5 > Results\n"
    "Total revenue was US$22,938,469 thousand.",
    "company": "Sea",
    "year": 2025,
    "pages": ["95"],
    "section": "Item 5 > Results",
    "is_table": False,
    "score": 0.8,
}


@pytest.fixture
def calls(monkeypatch):
    """Replace the vector search with a stub, so no embedding model or Chroma is needed."""
    recorded = []

    def fake_search(query, k=5, filters=None, strategy="section"):
        recorded.append({"query": query, "k": k, "filters": filters})
        return [HIT]

    monkeypatch.setattr(tools, "search", fake_search)
    return recorded


def test_result_shows_citation_section_and_text_without_the_repeated_header(calls):
    out = search_reports("total revenue", "Sea", 2025)
    assert "[Sea, FY2025, p.95] | text | Item 5 > Results" in out
    assert "Total revenue was US$22,938,469 thousand." in out
    assert "annual report (20-F)" not in out  # the chunk's own header line was dropped


def test_tables_are_labelled(calls, monkeypatch):
    table = {**HIT, "is_table": True}
    monkeypatch.setattr(tools, "search", lambda *a, **k: [table])
    assert "| table |" in search_reports("revenue", "Sea", 2025)


def test_filters_are_canonicalised_and_k_is_fixed(calls):
    search_reports("revenue", "sea", "2025")  # lowercase name, year sent as text
    assert calls[0]["filters"] == {"company": "Sea", "year": 2025}
    assert calls[0]["k"] == tools.SEARCH_K


def test_no_filters_and_empty_strings_mean_unfiltered(calls):
    search_reports("revenue")
    search_reports("revenue", "", None)
    assert [c["filters"] for c in calls] == [{}, {}]


@pytest.mark.parametrize(
    ("company", "year", "expect"),
    [
        ("Shopee", 2025, "unknown company"),
        ("Sea", 2019, "no FY2019 report"),
        (None, 2019, "no FY2019 report"),
        ("Sea", "abc", "year must be a number"),
    ],
)
def test_bad_arguments_return_an_error_and_skip_the_search(calls, company, year, expect):
    out = search_reports("revenue", company, year)
    assert out.startswith("Error:")
    assert expect in out
    assert calls == []


def test_unknown_company_error_lists_the_valid_choices(calls):
    out = search_reports("revenue", "Shopee")
    assert "Sea" in out
    assert "Grab" in out


@pytest.mark.parametrize("query", ["", "   ", None])
def test_empty_query_returns_an_error(calls, query):
    assert search_reports(query).startswith("Error:")
    assert calls == []


def test_no_results_message(monkeypatch):
    monkeypatch.setattr(tools, "search", lambda *a, **k: [])
    assert search_reports("zzz", "Sea", 2025).startswith("No results")


def test_seen_collects_the_raw_hits(calls):
    seen = []
    search_reports("revenue", "Sea", 2025, seen=seen)
    assert seen == [HIT]


def test_schemas_match_the_registry_and_are_json_serialisable():
    schemas = tool_schemas()
    json.dumps(schemas)  # the SDK sends these as JSON
    assert [s["name"] for s in schemas] == ["search_reports", "calculate"]
    search_props = schemas[0]["input_schema"]["properties"]
    assert search_props["company"]["enum"] == ["Sea", "Grab"]
    assert search_props["year"]["enum"] == [2024, 2025]
    assert schemas[0]["input_schema"]["required"] == ["query"]
    assert schemas[1]["input_schema"]["required"] == ["expression"]
    assert all(s["description"] for s in schemas)