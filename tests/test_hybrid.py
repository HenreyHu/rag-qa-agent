from types import SimpleNamespace

import pytest

from src import retrieve
from src.retrieve import Bm25Index, hybrid_search, tokenize

TEXTS = [
    "Sea Limited | FY2025 | Balance sheet\nTotal current assets 100 cash and cash equivalents 41",
    "Sea Limited | FY2025 | Risk factors\nWe face regulation risk in many markets",
    "Grab | FY2024 | Balance sheet\nTotal current assets 55 cash and cash equivalents 9",
]
METADATAS = [
    {"company": "Sea", "year": 2025},
    {"company": "Sea", "year": 2025},
    {"company": "Grab", "year": 2024},
]


@pytest.fixture
def index():
    return Bm25Index(["a", "b", "c"], TEXTS, METADATAS)


def test_tokenize_lowercases_and_splits_on_punctuation():
    assert tokenize("Cash-equivalents, US$4,158,920") == [
        "cash",
        "equivalents",
        "us",
        "4",
        "158",
        "920",
    ]


def test_bm25_returns_only_chunks_that_contain_a_query_word(index):
    ids = [hit["id"] for hit in index.top("cash equivalents", 5, {})]
    assert sorted(ids) == ["a", "c"]


def test_bm25_prefers_the_chunk_with_the_rarer_matching_word(index):
    # "regulation" appears only in chunk b, "assets" in two, so b wins on its single rare word.
    assert index.top("regulation assets", 3, {})[0]["id"] == "b"


def test_bm25_hits_look_like_vector_hits(index):
    hit = index.top("regulation", 1, {})[0]
    assert hit["id"] == "b"
    assert hit["text"] == TEXTS[1]
    assert (hit["company"], hit["year"]) == ("Sea", 2025)
    assert hit["score"] > 0


@pytest.mark.parametrize(
    ("filters", "expected"),
    [
        ({"company": "Grab"}, ["c"]),
        ({"year": 2024}, ["c"]),
        ({"company": ["Sea", "Grab"], "year": 2025}, ["a"]),
        ({"company": "Sea", "year": None}, ["a"]),  # None means "no filter"
    ],
)
def test_bm25_applies_metadata_filters(index, filters, expected):
    assert [hit["id"] for hit in index.top("balance sheet assets", 5, filters)] == expected


def test_bm25_limits_results(index):
    assert len(index.top("cash", 1, {})) == 1


def test_bm25_ignores_words_not_in_the_corpus(index):
    assert index.top("zzzzz", 5, {}) == []


def make_hit(chunk_id):
    return {"id": chunk_id, "score": 0.5, "text": chunk_id, "company": "Sea", "year": 2025}


def test_hybrid_fuses_two_rankings_by_reciprocal_rank(monkeypatch):
    # Vector order: b, a. Keyword order: a, c. Chunk a is in both, so it wins.
    monkeypatch.setattr(retrieve, "search", lambda *args, **kwargs: [make_hit("b"), make_hit("a")])
    keyword = SimpleNamespace(top=lambda query, n, filters: [make_hit("a"), make_hit("c")])
    monkeypatch.setattr(retrieve, "get_bm25", lambda strategy: keyword)

    hits = hybrid_search("query", 3)
    assert [hit["id"] for hit in hits] == ["a", "b", "c"]
    k = retrieve.RRF_K
    assert hits[0]["score"] == pytest.approx(1 / (k + 2) + 1 / (k + 1))
    assert hits[1]["score"] == pytest.approx(1 / (k + 1))
    assert hits[2]["score"] == pytest.approx(1 / (k + 2))


def test_hybrid_returns_at_most_k_and_passes_filters_to_both_rankings(monkeypatch):
    seen = {}

    def fake_vector(query, n, filters, strategy):
        seen["vector"] = (n, filters)
        return [make_hit("a"), make_hit("b")]

    def fake_keyword(query, n, filters):
        seen["keyword"] = (n, filters)
        return [make_hit("c")]

    monkeypatch.setattr(retrieve, "search", fake_vector)
    monkeypatch.setattr(retrieve, "get_bm25", lambda strategy: SimpleNamespace(top=fake_keyword))

    hits = hybrid_search("query", 2, {"company": "sea", "year": 2025})
    assert len(hits) == 2
    expected = (retrieve.CANDIDATES, {"company": "Sea", "year": 2025})
    assert seen["vector"] == expected
    assert seen["keyword"] == expected


def test_search_dispatches_hybrid_mode(monkeypatch):
    monkeypatch.setattr(retrieve, "hybrid_search", lambda *args: "hybrid result")
    assert retrieve.search("query", 5, None, "section", "hybrid") == "hybrid result"
