"""Week 2 experiments on retrieval: how many chunks (k) to fetch, and what a filter would buy.

Examples:
    python -m eval.experiments sweep                 # hit@k for k = 3, 5, 10, 20 (no API calls)
    python -m eval.experiments oracle --k 5          # filter to the right company and year
    python -m eval.experiments oracle --k 5 --answers   # also re-answer with Claude (costs API calls)

The sweep searches once at the largest k and slices the top 3, 5 and 10 from it: results come back
best first, so the top 3 of a top-20 search are exactly what a top-3 search returns.

The oracle filter cheats on purpose. It reads the right company and year from the gold evidence,
so it shows the best a working filter could do, not what a real one would achieve.
"""

import argparse
import csv

from eval import answer_eval
from eval.gold_tools import QUESTION_TYPES, Question, load_questions
from eval.retrieval_eval import score
from src.config import RESULTS_DIR, ROOT, STRATEGIES, format_table, utf8_stdout
from src.retrieve import search

SWEEP_KS = (3, 5, 10, 20)


def oracle_filters(question: Question) -> dict:
    """The companies and years the gold evidence lives in (lists become Chroma $in filters)."""
    return {
        "company": sorted({e.company for e in question.evidence}),
        "year": sorted({e.year for e in question.evidence}),
    }


def hit_rates(questions: list[Question], hits_by_id: dict[str, list[dict]]) -> dict[str, tuple]:
    """(strict hits, any hits, n) per question type, plus 'all'."""
    rates = {}
    for qtype in (*QUESTION_TYPES, "all"):
        subset = [q for q in questions if qtype in ("all", q.type)]
        matched = [score(q, hits_by_id[q.id]) for q in subset]
        rates[qtype] = (sum(all(m) for m in matched), sum(any(m) for m in matched), len(subset))
    return rates


def _cell(hits: int, n: int) -> str:
    return f"{hits}/{n} {hits / n:4.0%}" if n else "-"


def run_sweep(questions: list[Question], strategies: list[str]) -> list[dict]:
    rows = []
    for strategy in strategies:
        full = {q.id: search(q.question, k=max(SWEEP_KS), strategy=strategy) for q in questions}
        for k in SWEEP_KS:
            rates = hit_rates(questions, {qid: hits[:k] for qid, hits in full.items()})
            for qtype, (strict, any_hit, n) in rates.items():
                rows.append(
                    {
                        "strategy": strategy,
                        "k": k,
                        "type": qtype,
                        "n": n,
                        "strict": strict,
                        "any": any_hit,
                    }
                )
    return rows


def run_oracle(questions: list[Question], strategies: list[str], k: int) -> list[dict]:
    rows = []
    for strategy in strategies:
        plain = {q.id: search(q.question, k=k, strategy=strategy) for q in questions}
        filtered = {
            q.id: search(q.question, k=k, filters=oracle_filters(q), strategy=strategy)
            for q in questions
        }
        for name, hits_by_id in (("no filter", plain), ("oracle filter", filtered)):
            for qtype, (strict, any_hit, n) in hit_rates(questions, hits_by_id).items():
                rows.append(
                    {
                        "strategy": strategy,
                        "setting": name,
                        "type": qtype,
                        "n": n,
                        "strict": strict,
                        "any": any_hit,
                    }
                )
    return rows


def print_sweep(rows: list[dict]) -> None:
    for strategy in dict.fromkeys(r["strategy"] for r in rows):
        header = ["type", "n"] + [f"{m}@{k}" for k in SWEEP_KS for m in ("strict", "any")]
        table = []
        for qtype in (*QUESTION_TYPES, "all"):
            cells = []
            for k in SWEEP_KS:
                row = next(
                    r for r in rows if (r["strategy"], r["k"], r["type"]) == (strategy, k, qtype)
                )
                cells += [_cell(row["strict"], row["n"]), _cell(row["any"], row["n"])]
            table.append([qtype, row["n"], *cells])
        print(f"\n{strategy} chunks: retrieval hit@k")
        print(format_table(header, table))


def print_oracle(rows: list[dict], k: int) -> None:
    settings = ["no filter", "oracle filter"]
    for strategy in dict.fromkeys(r["strategy"] for r in rows):
        header = ["type", "n"] + [f"{s} {m}@{k}" for s in settings for m in ("strict", "any")]
        table = []
        for qtype in (*QUESTION_TYPES, "all"):
            cells = []
            for setting in settings:
                row = next(
                    r
                    for r in rows
                    if (r["strategy"], r["setting"], r["type"]) == (strategy, setting, qtype)
                )
                cells += [_cell(row["strict"], row["n"]), _cell(row["any"], row["n"])]
            table.append([qtype, row["n"], *cells])
        print(f"\n{strategy} chunks: what the right company and year buy at k={k}")
        print(format_table(header, table))


def write_rows(rows: list[dict], name: str) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / name
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nResults: {path.relative_to(ROOT).as_posix()}")


def main() -> None:
    utf8_stdout()
    parser = argparse.ArgumentParser(description="Week 2 retrieval experiments.")
    parser.add_argument("experiment", choices=["sweep", "oracle"])
    parser.add_argument("--k", type=int, default=5, help="oracle only")
    parser.add_argument("--strategies", nargs="+", choices=STRATEGIES, default=list(STRATEGIES))
    parser.add_argument("--answers", action="store_true", help="oracle only: also re-answer")
    parser.add_argument("--strategy", choices=STRATEGIES, default="section", help="for --answers")
    args = parser.parse_args()

    questions = load_questions()
    if args.experiment == "sweep":
        rows = run_sweep(questions, args.strategies)
        print_sweep(rows)
        write_rows(rows, "k_sweep.csv")
        return

    rows = run_oracle(questions, args.strategies, args.k)
    print_oracle(rows, args.k)
    write_rows(rows, f"oracle_retrieval_k{args.k}.csv")
    if args.answers:
        answers = answer_eval.evaluate(questions, args.k, args.strategy, filters_fn=oracle_filters)
        print(f"\nAnswer eval with the oracle filter: {args.strategy} chunks, k={args.k}")
        print(answer_eval.summarize(answers))
        answer_eval.write_results(answers, f"answers_{args.strategy}_k{args.k}_oracle.csv")


if __name__ == "__main__":
    main()
