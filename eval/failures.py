"""Draft notes/failures.md from an answer-eval CSV: every non-correct answer, with a first-guess category.

Example:
    python -m eval.failures eval/results/answers_section_k5.csv

The categories are: wrong chunk, bad table, hallucination, multi-hop, over-abstention, and
incomplete answer (partial credit: the right page was retrieved but a detail is missing).
The guesses come from simple rules (see suggest_category); they are a starting point.
Read each answer and change the category wherever the rule got it wrong.
"""

import argparse
import csv
import textwrap
from pathlib import Path

from eval.gold_tools import Question, load_questions
from src.config import ROOT, utf8_stdout

CATEGORIES = (
    "wrong chunk",
    "bad table",
    "hallucination",
    "multi-hop",
    "over-abstention",
    "incomplete answer",
)
OUTPUT = ROOT / "notes" / "failures.md"


def retrieved_pages(cell: str) -> dict[str, set[str]]:
    """'sea-2025 p.95|96; grab-2025 p.88' -> {'sea-2025': {'95', '96'}, 'grab-2025': {'88'}}"""
    pages: dict[str, set[str]] = {}
    for part in filter(None, (p.strip() for p in cell.split(";"))):
        filing, _, labels = part.partition(" p.")
        pages.setdefault(filing, set()).update(labels.split("|"))
    return pages


def gold_retrieved(question: Question, cell: str) -> bool:
    """Was every piece of gold evidence in the retrieved chunks?"""
    seen = retrieved_pages(cell)
    return all(seen.get(e.filing, set()) & set(e.pages) for e in question.evidence)


def suggest_category(question: Question, row: dict) -> str:
    found = gold_retrieved(question, row["retrieved"])
    if question.type == "comparison" and not found:
        return "multi-hop"  # one search could not bring back both companies or years
    if row["grade"] == "partial" and found:
        return (
            "incomplete answer"  # right evidence, but the answer leaves out part of the gold answer
        )
    if row["grade"] == "abstained" and found:
        return "over-abstention"  # the evidence was there and the model still said "I don't know"
    if not found:
        return "wrong chunk"  # retrieval missed the gold page, so the model never saw it
    if int(row["citations_retrieved"]) < int(row["n_citations"]):
        return "hallucination"  # it cited a page that was never in its context
    return "bad table"  # evidence was retrieved and cited fine, yet the answer is wrong: check the chunk


def build_report(rows: list[dict], questions: dict[str, Question], source: str) -> str:
    failures = [r for r in rows if r["grade"] != "correct"]
    lines = [
        "# Week 2 failures",
        "",
        f"Source: `{source}`. {len(failures)} of {len(rows)} answers were not graded correct.",
        (
            f"Categories: {', '.join(CATEGORIES)}. The suggested category is a rule-based guess; "
            "confirm or change it after reading the answer and the retrieved chunks."
        ),
        "",
        "| Category | Count |",
        "|---|---|",
    ]
    counts = dict.fromkeys(CATEGORIES, 0)
    suggestions = {r["id"]: suggest_category(questions[r["id"]], r) for r in failures}
    for category in suggestions.values():
        counts[category] += 1
    lines += [f"| {c} | {n} |" for c, n in counts.items()]
    for row in failures:
        q = questions[row["id"]]
        lines += [
            "",
            f"## {q.id} ({q.type}): {row['grade']}",
            "",
            f"- Question: {q.question}",
            f"- Gold answer: {q.gold_answer}",
            f"- Model answer: {textwrap.shorten(row['answer'], 400, placeholder=' ...')}",
            f"- Grader: {row['reason']}",
            f"- Suggested category: {suggestions[q.id]}",
            "- Your category and why: ",
        ]
    return "\n".join(lines) + "\n"


def main() -> None:
    utf8_stdout()
    parser = argparse.ArgumentParser(description="Draft the failure notes from an answer eval.")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()

    with args.csv_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    questions = {q.id: q for q in load_questions()}
    report = build_report(rows, questions, args.csv_path.name)
    args.out.write_text(report, encoding="utf-8", newline="\n")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
