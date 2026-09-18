import csv
import io

import pytest

from eval.gold_tools import (
    COLUMNS,
    Evidence,
    check,
    load_questions,
    pages_with,
    parse_row,
    snippet_matches,
    write_rows,
)
from eval.retrieval_eval import score, summarize


def row(**overrides) -> dict[str, str]:
    values = {
        "id": "C01",
        "type": "comparison",
        "question": "Whose revenue grew faster in FY2025, Sea or Grab?",
        "gold_answer": "Sea (36.4% vs 20.5%)",
        "gold_company": "Sea; grab",
        "gold_year": "2025;2025",
        "gold_page": "95|96; 88",
        "evidence": "Total revenue ... 22,938,469; Revenue ... 3,370",
        "verified": "FALSE",
    }
    values.update(overrides)
    return values


def test_parse_row_splits_evidence_and_page_alternatives():
    question = parse_row(row())
    assert question.evidence == (
        Evidence("Sea", 2025, ("95", "96"), "Total revenue ... 22,938,469"),
        Evidence("Grab", 2025, ("88",), "Revenue ... 3,370"),
    )
    assert question.evidence[1].filing == "grab-2025"
    assert question.verified is False


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"gold_year": "2025"}, "same number"),
        ({"type": "multi-hop"}, "type must be"),
        ({"verified": "yes"}, "verified must be"),
        ({"gold_company": "Shopee; Grab"}, "Unknown company"),
    ],
)
def test_invalid_rows_name_the_question(overrides, message):
    with pytest.raises(ValueError, match=f"C01: .*{message}"):
        parse_row(row(**overrides))


@pytest.mark.parametrize(
    ("value", "expected"), [("TRUE", True), ("true", True), ("FALSE", False), ("false", False)]
)
def test_verified_is_case_insensitive(value, expected):
    assert parse_row(row(verified=value)).verified is expected


def test_csv_round_trip_keeps_bom_and_lf(tmp_path):
    path = tmp_path / "questions.csv"
    lookup = row(id="L01", type="lookup", gold_company="Sea", gold_year="2024")
    write_rows([row(), lookup | {"gold_page": "F-4", "evidence": "Total revenue"}], path)
    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" not in raw
    assert [q.id for q in load_questions(path)] == ["C01", "L01"]


def test_a_cp1252_file_saved_by_excel_still_loads(tmp_path, capsys):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerow(row(question="What drove Sea\N{RIGHT SINGLE QUOTATION MARK}s growth?"))
    path = tmp_path / "questions.csv"
    path.write_bytes(buffer.getvalue().encode("cp1252"))
    (question,) = load_questions(path)
    assert question.question == "What drove Sea\N{RIGHT SINGLE QUOTATION MARK}s growth?"
    assert "CSV UTF-8" in capsys.readouterr().err


def test_duplicate_ids_are_rejected(tmp_path):
    path = tmp_path / "questions.csv"
    write_rows([row(), row()], path)
    with pytest.raises(ValueError, match="duplicate"):
        load_questions(path)


def test_snippet_parts_must_appear_in_order():
    text = "| Total revenue | 13,063,560 | 100.0 | 16,819,866 | 100.0 | 22,938,469 | 100.0 |"
    assert snippet_matches("Total revenue ... 22,938,469", text)
    assert snippet_matches("total   REVENUE", text)
    assert not snippet_matches("22,938,469 ... Total revenue", text)


def test_pages_with_lists_each_page_once():
    blocks = [
        {"page": "95", "text": "Total revenue rose"},
        {"page": "95", "text": "total revenue fell"},
        {"page": "F-5", "text": "Total revenue"},
        {"page": "96", "text": "Other income"},
    ]
    assert pages_with("total revenue", blocks) == ["95", "F-5"]


BLOCKS = {
    "sea-2025": [{"page": "95", "text": "| Total revenue | 16,819,866 | 22,938,469 |"}],
    "grab-2025": [{"page": "88", "text": "| Revenue | 3,370 | 2,797 |"}],
}


def test_check_accepts_evidence_on_its_pages():
    assert check([parse_row(row(gold_page="95; 88"))], BLOCKS) == ([], [])


def test_check_reports_wrong_and_unlabeled_pages():
    errors, warnings = check([parse_row(row(gold_page="95|s3; 90"))], BLOCKS)
    assert any("unlabeled" in e for e in errors)
    assert any("grab-2025" in e and "found on p.88" in e for e in errors)
    assert any("p.s3" in w for w in warnings)


def test_check_flags_cells_excel_would_treat_as_formulas():
    errors, _ = check([parse_row(row(gold_answer="-5% for Grab"))], BLOCKS)
    assert any("formula" in e for e in errors)


def hit(company="Sea", year=2025, pages=("95",)) -> dict:
    return {"company": company, "year": year, "pages": list(pages)}


def test_strict_and_any_hits():
    question = parse_row(row())
    assert score(question, [hit(pages=["94", "95"]), hit("Grab", 2025, ["88"])]) == [True, True]
    assert score(question, [hit(pages=["96"]), hit("Grab", 2024, ["88"])]) == [True, False]
    assert score(question, [hit("Sea", 2024, ["95"])]) == [False, False]


def test_summary_counts_hits_per_type_and_overall():
    rows = [
        {"strategy": "fixed", "type": "lookup", "strict_hit": True, "any_hit": True},
        {"strategy": "fixed", "type": "comparison", "strict_hit": False, "any_hit": True},
    ]
    lines = summarize(rows, ["fixed"], 5).splitlines()
    assert lines[0].split() == ["type", "n", "fixed", "strict@5", "fixed", "any@5"]
    assert lines[2].split() == ["lookup", "1", "1/1", "100%", "1/1", "100%"]
    assert lines[3].split() == ["comparison", "1", "0/1", "0%", "1/1", "100%"]
    assert lines[4].split() == ["all", "2", "1/2", "50%", "2/2", "100%"]
