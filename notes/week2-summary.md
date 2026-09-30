# Week 2 summary: basic RAG

## What was built

`src/rag.py` retrieves the top-k chunks, asks Claude to answer only from them, and returns the answer with `[Company, FYyear, p.X]` citations.
If the answer is not in the chunks, the prompt tells the model to say "I don't know."
An answer eval then scores all 30 verified questions, and two retrieval experiments test the choice of k and the value of a company and year filter.

| Step | File | What it does |
|---|---|---|
| Settings | `src/config.py` | Answer model, grader model, max answer length and the strict system prompt. |
| Answer | `src/rag.py` | `answer(question, k, filters, strategy)` returns the answer text and the chunks the model saw. |
| Citations | `src/citations.py` | Parses `p.`, `pp.`, ranges, lists and pages like `F-11`; skips malformed brackets. |
| Answer eval | `eval/answer_eval.py` | A separate Claude call grades each answer (correct, partial, wrong, abstained). A plain-code number check cross-checks the grader. Citations are scored three ways. |
| Experiments | `eval/experiments.py` | Retrieval hit@k for k = 3, 5, 10, 20, and retrieval with an oracle company and year filter. Neither needs API calls. |
| Failure notes | `eval/failures.py`, `notes/failures.md` | Drafts a category for every non-correct answer; the final categories were set by reading each answer. |

## Answer baseline (section chunks, k = 5, no filters)

| Question type | n | Correct | Partial | Wrong | Abstained |
|---|---|---|---|---|---|
| Lookup | 10 | 80% | 10% | 0% | 10% |
| Narrative | 10 | 40% | 10% | 0% | 50% |
| Comparison | 10 | 30% | 0% | 0% | 70% |
| All | 30 | 50% | 7% | 0% | 43% |

Citations across all 30 answers:

| Measure | Result |
|---|---|
| Citations that point at a gold page | 28 of 45 (62%) |
| Gold evidence that got cited | 19 of 42 (45%) |
| Cited pages that were really retrieved | 45 of 45 (100%) |

The grader and the number check never disagreed (0 questions flagged `needs_review`).
Per-question results are in `eval/results/answers_section_k5.csv`.
Only section chunks were run through the answer eval; the two chunking strategies tied on retrieval in Week 1.

## Retrieval experiments

Strict means every piece of evidence a question needs is in the top k.

| k | Fixed strict | Fixed any | Section strict | Section any |
|---|---|---|---|---|
| 3 | 47% | 67% | 47% | 67% |
| 5 | 50% | 70% | 50% | 73% |
| 10 | 60% | 87% | 57% | 83% |
| 20 | 67% | 90% | 70% | 90% |

- Lookups reach 100% by k = 10. Narrative questions only improve at k = 20 (50% to 80%).
- Comparison strict stays at 10% until k = 20 (20% to 30%), while "any" reaches 90%: one search finds one side of a comparison, rarely both.

Oracle filter at k = 5, which reads the right company and year from the gold evidence (an upper bound, not a real filter):

| Chunks | Strict, no filter | Strict, oracle | Any, no filter | Any, oracle |
|---|---|---|---|---|
| Fixed | 50% | 57% | 70% | 77% |
| Section | 50% | 57% | 73% | 80% |

The perfect filter fixes 2 of 30 questions and leaves comparison strict at 10%.
Going to k = 10 gives about the same strict gain with no filter, at the cost of twice as much text in the prompt.
Per-question results are in `eval/results/k_sweep.csv` and `eval/results/oracle_retrieval_k5.csv`.

## What the failures show

Details, with a category for every failure, are in `notes/failures.md`.

| Category | Count |
|---|---|
| Wrong chunk | 7 |
| Multi-hop | 6 |
| Incomplete answer | 2 |
| Bad table, hallucination, over-abstention | 0 |

1. **Nothing was answered wrongly.** All 15 failures are abstentions (13) or partial answers (2), so the strict prompt does what it should.
2. **Retrieval is the bottleneck.** The answer score (50%) matches strict hit@5 (50%). When the evidence reaches the model, it mostly answers correctly.
3. **Multi-hop failed as expected.** Seven of ten comparison questions were abstained. Six saw only one company's evidence and said so; C07 missed both headcount tables.
4. **The wrong year cost two narrative questions** (N06, N09). Most other misses are the wrong page inside the right filing, which a company and year filter cannot fix.
5. **No citation was invented.** Every cited page was among the retrieved chunks. Citation accuracy is lower (62%) because a citation only counts if it points at a listed gold page.

## Known issues

- **No temperature setting.** The installed SDK rejects the argument for this model, so repeat runs can differ slightly. Re-run a question before trusting a one-off change.
- **The LLM grader is strict.** L10 and N07 were graded partial for leaving out one detail of the gold answer. The grader has not been checked by hand beyond the failures.
- **Gold pages list only pages containing the exact evidence snippet,** so a correct citation to a page that states the fact differently counts as wrong.
- **Not yet run:** answer eval at k = 10, and answers with the oracle filter (`python -m eval.experiments oracle --k 5 --answers`). Both cost API calls.
- 30 questions is small: one question is 3.3 points.

## What to review first

1. **`eval/results/answers_section_k5.csv`.** Read the 15 correct answers as well as the failures, to check the grader was fair.
2. **The final category on each entry in `notes/failures.md`,** and change any you disagree with.
3. **`build_context` and `answer` in `src/rag.py`.** The prompt layout decides what the model sees.

## Into Week 3

The agent should search once per company and year, which targets the six comparison failures directly.
Two cheap fixes are worth testing for the wrong-chunk failures: a company and year filter inferred from the question, and a hybrid of keyword and vector search for questions that name the report.
