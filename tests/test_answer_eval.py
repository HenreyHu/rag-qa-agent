import pytest

from eval import answer_eval
from eval.answer_eval import (
    agent_answer_fn,
    citation_scores,
    evaluate,
    needs_review,
    number_check,
    numbers_in,
    parse_grade,
    summarize,
    summarize_cost,
)
from eval.gold_tools import Evidence, Question


def question(qid="L01", qtype="lookup", gold="US$22,938,469 thousand (about US$22.9 billion)"):
    evidence = (Evidence("Sea", 2025, ("95", "96"), "Total revenue"),)
    return Question(qid, qtype, "What was Sea's revenue?", gold, evidence, True)


HITS = [{"company": "Sea", "year": 2025, "pages": ["95"], "filing": "sea-2025"}]


def test_numbers_ignore_commas_years_and_trailing_zeros():
    assert numbers_in("FY2025 revenue US$22,938,469 thousand, up 36.40% on December 31, 2025") == {
        "22938469",
        "36.4",
    }


def test_number_check_counts_found_numbers_and_skips_citations():
    gold = "US$22,938,469 thousand (about US$22.9 billion)"
    assert number_check(gold, "Revenue was US$22.9 billion [Sea, FY2025, p.95].") == (1, 2)
    assert number_check(gold, "I don't know.") == (0, 2)
    assert number_check("Yes, in Singapore", "Yes") is None


def test_needs_review_flags_disagreements():
    assert needs_review("correct", (0, 2))
    assert needs_review("wrong", (2, 2))
    assert not needs_review("correct", (1, 2))
    assert not needs_review("abstained", (0, 2))
    assert not needs_review("correct", None)


def test_parse_grade():
    assert parse_grade('{"grade": "Partial", "reason": "misses FY2024"}') == (
        "partial",
        "misses FY2024",
    )
    assert parse_grade('Sure!\n{"grade": "correct", "reason": "ok"}')[0] == "correct"
    assert parse_grade("no json here")[0] == "error"
    assert parse_grade('{"grade": "great"}')[0] == "error"


def test_citation_scores_all_three_measures():
    scores = citation_scores(
        question(), "Revenue rose [Sea, FY2025, p.95] and [Sea, FY2025, p.200].", HITS
    )
    assert scores == {
        "n_citations": 2,
        "citations_correct": 1,
        "gold_cited": 1,
        "gold_total": 1,
        "citations_retrieved": 1,  # p.200 was never retrieved
    }


def test_citation_to_wrong_year_or_company_is_not_correct():
    scores = citation_scores(question(), "[Sea, FY2024, p.95] [Grab, FY2025, p.95]", HITS)
    assert scores["citations_correct"] == 0
    assert scores["gold_cited"] == 0


def test_evaluate_and_summarize_with_fakes():
    def fake_answer(text, k, filters, strategy):
        return {"answer": "US$22.9 billion [Sea, FY2025, p.95]", "hits": HITS}

    rows = evaluate(
        [question()],
        k=5,
        strategy="section",
        answer_fn=fake_answer,
        grade_fn=lambda q, g, a: ("correct", "matches"),
    )
    assert rows[0]["grade"] == "correct"
    assert rows[0]["number_match"] == "1/2"
    assert rows[0]["needs_review"] is False
    table = summarize(rows)
    assert "lookup" in table and "100%" in table


def test_filters_fn_is_passed_to_answer():
    seen = {}

    def fake_answer(text, k, filters, strategy):
        seen["filters"] = filters
        return {"answer": "I don't know.", "hits": []}

    evaluate(
        [question()],
        5,
        "section",
        filters_fn=lambda q: {"company": "Sea"},
        answer_fn=fake_answer,
        grade_fn=lambda q, g, a: ("abstained", ""),
    )
    assert seen["filters"] == {"company": "Sea"}


AGENT_RESULT = {
    "answer": "US$22.9 billion [Sea, FY2025, p.95]",
    "hits": HITS,
    "steps": 2,
    "tool_calls": 1,
    "hit_cap": False,
    "input_tokens": 6000,
    "output_tokens": 300,
    "seconds": 25.0,
}


def run_fake(result):
    return evaluate(
        [question()],
        5,
        "section",
        answer_fn=lambda text, k, filters, strategy: result,
        grade_fn=lambda q, g, a: ("correct", ""),
    )


def test_evaluate_carries_cost_columns_into_the_row():
    row = run_fake(AGENT_RESULT)[0]
    assert (row["steps"], row["tool_calls"], row["hit_cap"]) == (2, 1, False)
    assert (row["input_tokens"], row["output_tokens"], row["seconds"]) == (6000, 300, 25.0)


def test_rows_without_cost_numbers_still_evaluate():
    row = run_fake({"answer": "I don't know.", "hits": []})[0]
    assert "input_tokens" not in row


def test_every_cost_column_has_an_output_column():
    assert set(answer_eval.COST_COLUMNS) <= set(answer_eval.RESULT_COLUMNS)


def test_summarize_cost_reports_means_per_type_and_capped_runs():
    rows = [
        {**run_fake(AGENT_RESULT)[0]},
        {**run_fake({**AGENT_RESULT, "steps": 4, "input_tokens": 10000, "hit_cap": True})[0]},
    ]
    table = summarize_cost(rows)
    lookup = next(line for line in table.splitlines() if line.startswith("lookup"))
    assert lookup.split() == ["lookup", "2", "3.0", "1.0", "8,000", "300", "25.0", "1"]


def test_summarize_cost_for_basic_rag_has_tokens_but_no_steps():
    rag_result = {"answer": "x [Sea, FY2025, p.95]", "hits": HITS, "input_tokens": 3000}
    table = summarize_cost(run_fake(rag_result))
    lookup = next(line for line in table.splitlines() if line.startswith("lookup"))
    assert lookup.split()[:6] == ["lookup", "1", "-", "-", "3,000", "-"]


def test_summarize_cost_is_empty_without_any_timing():
    assert summarize_cost(run_fake({"answer": "x", "hits": []})) == ""


def test_agent_answer_fn_names_the_trace_after_the_question_id(monkeypatch, tmp_path):
    calls = []

    def fake_run_agent(text, qid, *, trace_dir):
        calls.append((text, qid, trace_dir))
        return AGENT_RESULT

    monkeypatch.setattr(answer_eval, "run_agent", fake_run_agent)
    answer_fn = agent_answer_fn([question()], tmp_path)
    result = answer_fn("What was Sea's revenue?", 5, None, "section")
    assert result is AGENT_RESULT
    assert calls == [("What was Sea's revenue?", "L01", tmp_path)]


def test_agent_answer_fn_rejects_duplicate_question_text(tmp_path):
    with pytest.raises(ValueError, match="unique"):
        agent_answer_fn([question("L01"), question("L02")], tmp_path)
