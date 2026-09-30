from eval import experiments
from eval.experiments import hit_rates, oracle_filters, run_sweep
from eval.gold_tools import Evidence, Question


def question(qid, qtype, *evidence):
    return Question(qid, qtype, "q?", "a", tuple(evidence), True)


SEA = Evidence("Sea", 2025, ("95",), "x")
GRAB = Evidence("Grab", 2024, ("88",), "y")


def hit(company, year, page):
    return {"company": company, "year": year, "pages": [page], "filing": f"{company}-{year}"}


def test_oracle_filters_use_every_company_and_year_in_the_evidence():
    assert oracle_filters(question("C01", "comparison", SEA, GRAB)) == {
        "company": ["Grab", "Sea"],
        "year": [2024, 2025],
    }
    assert oracle_filters(question("L01", "lookup", SEA)) == {"company": ["Sea"], "year": [2025]}


def test_hit_rates_strict_needs_all_evidence_any_needs_one():
    both = question("C01", "comparison", SEA, GRAB)
    rates = hit_rates([both], {"C01": [hit("Sea", 2025, "95")]})
    assert rates["comparison"] == (0, 1, 1)
    assert rates["all"] == (0, 1, 1)


def test_sweep_searches_once_and_slices_top_k(monkeypatch):
    calls = []
    ranked = [hit("Grab", 2025, "1")] * 3 + [hit("Sea", 2025, "95")] + [hit("Grab", 2025, "2")] * 16

    def fake_search(text, k, filters=None, strategy="section"):
        calls.append(k)
        return ranked[:k]

    monkeypatch.setattr(experiments, "search", fake_search)
    rows = run_sweep([question("L01", "lookup", SEA)], ["section"])
    assert calls == [20]  # one search, not one per k
    strict = {r["k"]: r["strict"] for r in rows if r["type"] == "lookup"}
    assert strict == {3: 0, 5: 1, 10: 1, 20: 1}  # the gold page is the 4th result
