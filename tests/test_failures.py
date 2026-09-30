from eval.failures import build_report, gold_retrieved, retrieved_pages, suggest_category
from eval.gold_tools import Evidence, Question

SEA = Evidence("Sea", 2025, ("95",), "x")
GRAB = Evidence("Grab", 2025, ("88",), "y")


def q(qtype="lookup", *evidence):
    return Question("Q1", qtype, "q?", "gold", evidence or (SEA,), True)


def row(**overrides):
    base = {
        "id": "Q1",
        "grade": "wrong",
        "reason": "r",
        "answer": "a",
        "retrieved": "sea-2025 p.95|96",
        "n_citations": "1",
        "citations_retrieved": "1",
    }
    return base | overrides


def test_retrieved_pages_parses_the_csv_cell():
    assert retrieved_pages("sea-2025 p.95|96; grab-2025 p.88") == {
        "sea-2025": {"95", "96"},
        "grab-2025": {"88"},
    }


def test_gold_retrieved_needs_every_evidence():
    two = q("comparison", SEA, GRAB)
    assert not gold_retrieved(two, "sea-2025 p.95")
    assert gold_retrieved(two, "sea-2025 p.95; grab-2025 p.88")


def test_suggested_categories():
    assert suggest_category(q(), row(retrieved="sea-2025 p.1")) == "wrong chunk"
    assert suggest_category(q("comparison", SEA, GRAB), row()) == "multi-hop"
    assert suggest_category(q(), row(grade="abstained")) == "over-abstention"
    assert suggest_category(q(), row(citations_retrieved="0")) == "hallucination"
    assert suggest_category(q(), row(grade="partial")) == "incomplete answer"
    assert suggest_category(q(), row()) == "bad table"


def test_report_lists_only_non_correct_answers():
    rows = [row(), row(id="Q2", grade="correct")]
    text = build_report(rows, {"Q1": q(), "Q2": q()}, "x.csv")
    assert "## Q1" in text and "## Q2" not in text
    assert "1 of 2 answers" in text
