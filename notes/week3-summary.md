# Week 3 summary: the agent layer

## What was built

- `src/tools.py`: `search_reports(query, company?, year?)` (returns the top 5 chunks with `[Company, FYyear, p.X]` citations) and `calculate(expression)` (an `ast` whitelist, no `eval`). Mistakes by the model come back as `Error: ...` text so it can retry.
- `src/agent.py`: a Claude tool-use loop (`claude-sonnet-5`). Step cap of 8; if the model is still calling tools at the cap, one extra call is made with tools switched off so there is always an answer. Every step is written to a JSONL trace (`eval/results/traces/<tag>/<qid>.jsonl`, viewable with `python -m eval.show_trace <qid>`).
- `eval/answer_eval.py --mode agent --tag <name>`: scores the agent with the same grader, number check and citation checks as basic RAG, and adds turns, tool calls, tokens and seconds.
- Optional hybrid search (`src/retrieve.py`): own Okapi BM25 fused with vector search by reciprocal rank fusion. Switch on with `AGENT_SEARCH_MODE=hybrid`; the default is still vector.
- Prompt rule added after L06 failed: do not conclude a figure is missing after one search; try two differently worded searches, and for a reported line item name the statement it would appear in.

## Results (30 verified questions)

| | Correct | Partial | Abstained | Lookup | Narrative | Comparison |
|---|---|---|---|---|---|---|
| Basic RAG (Week 2) | 50% | - | 43% | 80% | 40% | 30% |
| Basic RAG re-run | 57% (17/30) | 1 | 12 | 9/10 | 5/10 | 3/10 |
| Agent, run 1 | 90% | | | 80% | 90% | 100% |
| Agent, run 2 | 90% | 3 (L07, N09, C10) | | | | |
| Agent + hybrid, run 1 | 100% (30/30) | 0 | 0 | 100% | 100% | 100% |
| Agent + hybrid, run 2 (prompt rules 5-6 added) | 97% (29/30) | 1 (C07) | 0 | 100% | 100% | 90% |

Done criterion (comparison accuracy clearly above the 30% baseline): met. Comparison went from 30% to 100% (agent) and stayed 100% with hybrid.

## Cost

| | Turns | Tool calls | Input tokens | Seconds |
|---|---|---|---|---|
| Basic RAG re-run | 1 | 0 | about 2,500 | 3.1 |
| Agent (vector), all | 2.5 | 2.1 | about 11,900 | 8.6 |
| Agent (hybrid), all | 2.4 | 2.0 | about 10,400 | 7.8 |
| Agent (hybrid), comparison | 2.9 | 3.8 | about 17,600 | 8.0 |

The agent uses roughly 4 to 5 times the input tokens of basic RAG (comparison questions about 7 times). No run hit the step cap. Every page the agent cited had really been retrieved (cite_seen 100%); citations matching the gold pages were lower (about 64 to 72% correct, 50 to 64% gold pages cited).

## Where the agent helped, and where it only added cost

- Helped most on comparisons and narrative questions: it splits a comparison into one search per company and year, and searches again when the first results are weak. Basic RAG abstained on 12 of 30 questions; the agent almost never did.
- Lookups were already good with basic RAG (80 to 90%). The agent adds cost there with little gain, except where it retries (L06).
- Hybrid search improved retrieval hit@5 (strict, section chunks) from 50% to 60%, narrative 50% to 80%, comparison unchanged at 10%. With the agent, which searches repeatedly, the gain showed up as fewer tokens and 30/30 in one run.

## Remaining failures

- Vector runs 1 and 2 had partial answers on L07 (net income attributable instead of total) and N09 (left out "never paid a dividend"), plus C10 in run 2, and L06 abstained in run 1. Both L07 and N09 were correct in both hybrid runs, after a generic prompt change (lead with the direct answer, give the headline total when a figure has variants, cite the primary statement over a note).
- Hybrid run 2: C07 gave the 6.6% headcount growth but left out the two headcount figures (partial).
- Gold-page citations are still low (about 64% in hybrid run 2): the agent often cites a different page that also supports the claim. All cited pages were really retrieved (100%).
- C03 is flagged `needs_review`: the grader and the number check disagree (the gold numbers are years, which the check ignores).

## Caveats

- Five of the 30 questions (L01, L06, N08, C01, C10) were used to tune the prompt, so the agent numbers are not a clean held-out result. Prompt changes were kept generic.
- The model's temperature cannot be set, so individual questions vary between runs. Hybrid has two complete runs (100%, 97%), but the prompt changed between them, and the vector setup has not been re-run with the new prompt (API credits ran out), so the default is still vector. The first attempt at a second hybrid run hung on one API call and was discarded; the client now has a 60s timeout with retries.
- The grader is an LLM, with a number check alongside it.

## Next (Week 4)

Repeat hybrid runs for variance, tighten citations (cite the gold page), fix partial answers (L07, N09), and write the final write-up.
