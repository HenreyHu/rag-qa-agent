"""Retrieval eval: are the gold pages among the top-k chunks, per chunking strategy and type?

Example:
    python -m eval.retrieval_eval --k 5

strict hit@k: every piece of gold evidence the question needs is in the top k.
any hit@k: at least one piece is (the two differ only for comparison questions).
"""

import argparse
import csv

from eval.gold_tools import QUESTION_TYPES, Evidence, Question, load_questions
from src.config import RESULTS_DIR, ROOT, STRATEGIES, format_table, utf8_stdout
from src.retrieve import search

RESULT_COLUMNS = [
    "strategy",
    "id",
    "type",
    "verified",
    "strict_hit",
    "any_hit",
    "evidence_found",
    "first_hit_rank",
    "retrieved",
]


def evidence_found(evidence: Evidence, hit: dict) -> bool:
    return (
        hit["company"] == evidence.company
        and hit["year"] == evidence.year
        and any(page in hit["pages"] for page in evidence.pages)
    )


def score(question: Question, hits: list[dict]) -> list[bool]:
    """For each piece of gold evidence, whether any retrieved chunk contains it."""
    return [any(evidence_found(e, hit) for hit in hits) for e in question.evidence]


def evaluate(questions: list[Question], strategies: list[str], k: int) -> list[dict]:
    rows = []
    for strategy in strategies:
        for q in questions:
            # No metadata filters: this is the unfiltered baseline (filtering is a Week 2 experiment).
            hits = search(q.question, k=k, strategy=strategy)
            matched = score(q, hits)
            first_rank = next(
                (
                    rank
                    for rank, hit in enumerate(hits, start=1)
                    if any(evidence_found(e, hit) for e in q.evidence)
                ),
                "",
            )
            rows.append(
                {
                    "strategy": strategy,
                    "id": q.id,
                    "type": q.type,
                    "verified": q.verified,
                    "strict_hit": all(matched),
                    "any_hit": any(matched),
                    "evidence_found": f"{sum(matched)}/{len(matched)}",
                    "first_hit_rank": first_rank,
                    "retrieved": "; ".join(
                        f"{hit['filing']} p.{'|'.join(hit['pages'])}" for hit in hits
                    ),
                }
            )
    return rows


def summarize(rows: list[dict], strategies: list[str], k: int) -> str:
    header = ["type", "n"] + [f"{s} {m}@{k}" for s in strategies for m in ("strict", "any")]
    table = []
    for qtype in (*QUESTION_TYPES, "all"):
        cells = []
        n = 0
        for strategy in strategies:
            subset = [r for r in rows if r["strategy"] == strategy and qtype in ("all", r["type"])]
            n = len(subset)
            for metric in ("strict_hit", "any_hit"):
                hits = sum(r[metric] for r in subset)
                cells.append(f"{hits}/{n} {hits / n:4.0%}" if n else "-")
        if n:
            table.append([qtype, n, *cells])
    return format_table(header, table)


def write_results(rows: list[dict], name: str) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / name
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            # TRUE/FALSE rather than Python's True/False, to match Excel.
            writer.writerow(
                {k: str(v).upper() if isinstance(v, bool) else v for k, v in row.items()}
            )
    print(f"Per-question results: {path.relative_to(ROOT).as_posix()}")


def main() -> None:
    utf8_stdout()
    parser = argparse.ArgumentParser(description="Measure retrieval hit@k on the eval set.")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--strategies", nargs="+", choices=STRATEGIES, default=list(STRATEGIES))
    parser.add_argument(
        "--verified-only", action="store_true", help="only score questions checked by hand"
    )
    args = parser.parse_args()

    questions = load_questions()
    verified = sum(q.verified for q in questions)
    total = len(questions)
    if args.verified_only:
        questions = [q for q in questions if q.verified]
        if not questions:
            parser.error("no questions are marked verified yet")
    rows = evaluate(questions, args.strategies, args.k)

    print(f"Retrieval hit@{args.k} on {len(questions)} questions ({verified}/{total} verified)")
    print(summarize(rows, args.strategies, args.k))
    suffix = "_verified" if args.verified_only else ""
    write_results(rows, f"retrieval_k{args.k}{suffix}.csv")


if __name__ == "__main__":
    main()
