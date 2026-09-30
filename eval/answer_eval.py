"""Answer eval: is each answer right, and are its citations right?

Example:
    python -m eval.answer_eval --k 5

Per question it records:
- grade: a separate Claude call compares the answer to the gold answer (correct / partial / wrong /
  abstained).
- number_match: how many numbers in the gold answer also appear in the answer, as a plain-code
  cross-check on the grader. needs_review marks questions where the two disagree.
- citation scores: how many citations point at a gold page, how many gold pieces of evidence got
  cited, and whether each cited page was really among the retrieved chunks.

Limits: a citation counts as correct if ANY of its pages is a gold page, and gold pages only list
pages holding the exact evidence snippet, so a page that states the same fact in other words
counts as a wrong citation.
"""

import argparse
import csv
import json
import re

import anthropic

from eval.gold_tools import QUESTION_TYPES, Question, load_questions
from src import rag
from src.citations import Citation, parse_citations
from src.config import (
    GRADER_MODEL,
    RESULTS_DIR,
    ROOT,
    STRATEGIES,
    find_company,
    format_table,
    utf8_stdout,
)

GRADES = ("correct", "partial", "wrong", "abstained")

GRADER_PROMPT = """You are grading an answer to a question about a company annual report.

Question: {question}
Gold answer: {gold}
Model answer: {answer}

Choose one grade:
- correct: the model answer states the gold answer's facts. Rounding or a different unit is fine if the value is the same.
- partial: it gets some of what the gold answer needs but misses or gets wrong another part.
- wrong: it contradicts the gold answer or gives different facts.
- abstained: it says it does not know or cannot answer.

Ignore citations and formatting. Judge only the facts.
Reply with JSON only: {{"grade": "<one grade>", "reason": "<one short sentence>"}}"""

RESULT_COLUMNS = [
    "id",
    "type",
    "verified",
    "grade",
    "reason",
    "number_match",
    "needs_review",
    "n_citations",
    "citations_correct",
    "gold_cited",
    "gold_total",
    "citations_retrieved",
    "answer",
    "retrieved",
]

SUMMED = ("n_citations", "citations_correct", "gold_cited", "gold_total", "citations_retrieved")
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
YEAR = re.compile(r"(?:19|20)\d\d")
DATE = re.compile(r"[A-Z][a-z]+ \d{1,2},? (?:19|20)\d\d")  # "December 31, 2025"


def grade_answer(question: str, gold: str, answer: str) -> tuple[str, str]:
    """Ask Claude to grade one answer. Returns (grade, reason); grade is 'error' if unusable."""
    response = rag.get_client().messages.create(
        model=GRADER_MODEL,
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": GRADER_PROMPT.format(question=question, gold=gold, answer=answer),
            }
        ],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return parse_grade(text)


def parse_grade(text: str) -> tuple[str, str]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    try:
        data = json.loads(match[0]) if match else {}
    except json.JSONDecodeError:
        data = {}
    grade = str(data.get("grade", "")).strip().lower()
    if grade not in GRADES:
        return "error", f"unusable grader reply: {text[:80]!r}"
    return grade, str(data.get("reason", "")).strip()


def numbers_in(text: str) -> set[str]:
    """Numbers in a text as plain strings ('22,938,469' -> '22938469'). Fiscal years are ignored."""
    text = re.sub(r"FY\s*\d{4}", " ", text, flags=re.IGNORECASE)
    text = DATE.sub(" ", text)
    found = set()
    for raw in NUMBER.findall(text):
        number = raw.rstrip(",").replace(",", "")
        if "." in number:
            number = number.rstrip("0").rstrip(".")
        if YEAR.fullmatch(number) and "," not in raw:
            continue  # "December 31, 2025" would otherwise match every answer that says 2025
        found.add(number)
    return found


def number_check(gold: str, answer: str) -> tuple[int, int] | None:
    """(gold numbers found in the answer, gold numbers). None if the gold answer has no numbers."""
    wanted = numbers_in(gold)
    if not wanted:
        return None
    answer_body = re.sub(r"\[[^\]]*\]", " ", answer)  # citations contain page numbers, not facts
    return len(wanted & numbers_in(answer_body)), len(wanted)


def needs_review(grade: str, numbers: tuple[int, int] | None) -> bool:
    """The grader and the number check disagree, so a human should look."""
    if numbers is None:
        return False
    found, total = numbers
    return (grade == "correct" and found == 0) or (grade == "wrong" and found == total)


def _company(name: str) -> str | None:
    try:
        return find_company(name).short_name
    except KeyError:
        return None


def cites_evidence(citation: Citation, evidence) -> bool:
    return (
        _company(citation.company) == evidence.company
        and citation.year == evidence.year
        and bool(set(citation.pages) & set(evidence.pages))
    )


def was_retrieved(citation: Citation, hits: list[dict]) -> bool:
    return any(
        hit["company"] == _company(citation.company)
        and hit["year"] == citation.year
        and set(citation.pages) & set(hit["pages"])
        for hit in hits
    )


def citation_scores(question: Question, answer: str, hits: list[dict]) -> dict:
    citations = parse_citations(answer)
    return {
        "n_citations": len(citations),
        "citations_correct": sum(
            any(cites_evidence(c, e) for e in question.evidence) for c in citations
        ),
        "gold_cited": sum(any(cites_evidence(c, e) for c in citations) for e in question.evidence),
        "gold_total": len(question.evidence),
        "citations_retrieved": sum(was_retrieved(c, hits) for c in citations),
    }


def evaluate(
    questions: list[Question],
    k: int,
    strategy: str,
    filters_fn=None,
    answer_fn=rag.answer,
    grade_fn=grade_answer,
) -> list[dict]:
    """Answer and score every question. filters_fn(question) may return metadata filters."""
    rows = []
    for number, q in enumerate(questions, start=1):
        row = {"id": q.id, "type": q.type, "verified": q.verified}
        try:
            filters = filters_fn(q) if filters_fn else None
            result = answer_fn(q.question, k, filters, strategy)
            answer, hits = result["answer"], result["hits"]
            grade, reason = grade_fn(q.question, q.gold_answer, answer)
        except anthropic.APIError as exc:
            answer, hits, grade, reason = "", [], "error", f"API error: {exc}"
        numbers = number_check(q.gold_answer, answer)
        row.update(
            grade=grade,
            reason=reason,
            number_match="" if numbers is None else f"{numbers[0]}/{numbers[1]}",
            needs_review=needs_review(grade, numbers),
            **citation_scores(q, answer, hits),
            answer=answer,
            retrieved="; ".join(f"{hit['filing']} p.{'|'.join(hit['pages'])}" for hit in hits),
        )
        rows.append(row)
        print(f"[{number}/{len(questions)}] {q.id}: {grade}")
    return rows


def _pct(part: int, whole: int) -> str:
    return f"{part / whole:.0%}" if whole else "-"


def summarize(rows: list[dict]) -> str:
    header = [
        "type",
        "n",
        "correct",
        "partial",
        "wrong",
        "abstained",
        "cite_ok",
        "gold_cited",
        "cite_seen",
    ]
    table = []
    for qtype in (*QUESTION_TYPES, "all"):
        subset = [r for r in rows if qtype in ("all", r["type"])]
        if not subset:
            continue
        n = len(subset)
        sums = {key: sum(r[key] for r in subset) for key in SUMMED}
        table.append(
            [
                qtype,
                n,
                *(_pct(sum(r["grade"] == g for r in subset), n) for g in GRADES),
                _pct(sums["citations_correct"], sums["n_citations"]),
                _pct(sums["gold_cited"], sums["gold_total"]),
                _pct(sums["citations_retrieved"], sums["n_citations"]),
            ]
        )
    errors = sum(r["grade"] == "error" for r in rows)
    review = sum(r["needs_review"] for r in rows)
    notes = (
        "\ncite_ok: citations pointing at a gold page. gold_cited: gold evidence that got cited."
        "\ncite_seen: cited pages that were really retrieved."
        f"\n{errors} ungraded (error), {review} flagged needs_review (grader and number check disagree)."
    )
    return format_table(header, table) + notes


def write_results(rows: list[dict], name: str) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / name
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {k: str(v).upper() if isinstance(v, bool) else v for k, v in row.items()}
            )
    print(f"Per-question results: {path.relative_to(ROOT).as_posix()}")


def main() -> None:
    utf8_stdout()
    parser = argparse.ArgumentParser(description="Score answers on the eval set.")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--strategy", choices=STRATEGIES, default="section")
    parser.add_argument("--verified-only", action="store_true")
    parser.add_argument("--limit", type=int, help="only the first N questions (cheap smoke test)")
    args = parser.parse_args()

    questions = load_questions()
    if args.verified_only:
        questions = [q for q in questions if q.verified]
    if args.limit:
        questions = questions[: args.limit]
    rows = evaluate(questions, args.k, args.strategy)

    print(f"\nAnswer eval: {args.strategy} chunks, k={args.k}, {len(questions)} questions")
    print(summarize(rows))
    suffix = "_verified" if args.verified_only else ""
    write_results(rows, f"answers_{args.strategy}_k{args.k}{suffix}.csv")


if __name__ == "__main__":
    main()
