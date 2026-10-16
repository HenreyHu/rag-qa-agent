# Write-up: RAG Q&A agent over Sea and Grab 20-F filings

## What this is

An agent that answers questions about the FY2024 and FY2025 annual reports (Form 20-F) of Sea Limited and Grab Holdings, with `[Company, FYyear, p.X]` citations. It was evaluated on 30 hand-verified questions: 10 lookups, 10 narrative, 10 comparisons.

## 1. Chunking trade-offs, and what tables broke

Evidence:
- Two strategies: fixed windows (450 tokens, 75 overlap; 2,055 chunks) and section-aware chunks that never cross an Item or sub-item (2,417 chunks). Tables are separate markdown chunks in both (520).
- They tied on retrieval: strict hit@5 was 50% for both. At k=10 fixed was 60% and section 57%; at k=20, 67% and 70%.
- The three filing generators (Broadridge, Donnelley, Workiva) format pages differently, so the parser only relies on signals they share.
- Tables: the balance sheet chunk was rarely retrieved by vector search. L06 (Sea's cash and cash equivalents, p.F-7) failed for this reason until the agent was told to name the statement in its search.

**Why the strategies tied.** Chunking is not the bottleneck here; retrieval is. Both strategies cut the text at sensible places (the parser uses the HTML block tags for paragraphs and tables, and page breaks only for page numbers), and both fail on the same questions: the wrong page, the wrong year, or one company missing. Those are ranking problems, not problems with where a chunk starts or ends. In `notes/failures.md` no failure was confirmed as a bad table either; L06 failed because the balance sheet chunk ranked too low.

**Next for tables.** Tag each table chunk with the name of its statement (for example "Consolidated Balance Sheet") so a search that names the statement finds it. I have not tested this.

## 2. Where retrieval failed, and why

Evidence:
- Baseline strict hit@5: lookup 90%, narrative 50%, comparison 10%.
- Comparison failed because one query rarely brings back both companies or both years. "Any" hit@5 was 73% but "strict" was 10%.
- The wrong year wins: the FY2024 report repeats much of the FY2025 text (N06).
- Naming the report in the question ("according to the annual report") pulls in cover and signature pages (N08, N09).
- The business overview outranks the analysis section (Shopee's revenue drivers).
- A perfect company and year filter (oracle) fixed only 2 of 30 questions, so filtering is not the main fix.
- Hybrid keyword + vector search raised strict hit@5 from 50% to 60% (narrative 50% to 80%), but comparison stayed at 10%.

**What I'd fix first: comparison.** It is the worst type (strict hit@5 of 10%), because one search for the whole question usually brings back only one company's pages. Basic RAG then said "I don't know" instead of answering (C01 is an example); it did not mix up the two companies. The agent fixes this by running one search per company and year, which is why C01 is answered correctly in run 3.

Lookups are the easiest (90%), since one fact sits on one page, but they still depend on ranking: L06 failed when the balance sheet ranked too low. Narrative questions are harder because the "why" is spread over text that has to match the meaning of the question, and the wrong year or the business overview often outranks the right section.

After comparison I would fix the wrong-year problem, but a company and year filter alone only fixed 2 of 30 questions, so it needs to be combined with better ranking.

## 3. When the agent loop helped, and when it only added cost

Results on the same 30 questions (5 of them were used to tune the prompt):

| Setup | Correct | Lookup | Narrative | Comparison |
|---|---|---|---|---|
| Basic RAG | 50% | 80% | 40% | 30% |
| Agent (vector), 3 runs | 90%, 90%, 93% | 80% | 90-100% | 100% |
| Agent + hybrid, 2 runs | 100%, 97% | 100% | 100% | 100%, 90% |

Cost per question: basic RAG about 2,500 input tokens and 3s; agent about 11,900 tokens and 8.6s; comparisons about 17-21k tokens.

Evidence:
- It helped most where basic RAG abstained (12 of 30 questions did): the agent searches again with different wording and runs one search per company and year.
- Lookups were already 80-90% with basic RAG, so the agent mostly added cost there, except where a retry fixed a miss (L06).
- Arithmetic goes through a `calculate` tool, so growth rates are not model guesses.
- Remaining weak spot: gold-page citations (about 64% in hybrid run 2; 50-72% across runs depending on the check). The agent often cites a different page that also supports the claim. All cited pages were really retrieved. I left this as a known limitation.

**Is about 5x the tokens worth it?** Not for every question. For lookups it is not worth it: basic RAG already got 80-90%, so the agent mostly adds cost. For comparisons and narrative questions it is worth it, because basic RAG abstained on 70% and 50% of them and the agent almost never did.

But about 5x the tokens (about 17-21k for a comparison) is too much to pay on every question. A better design would send simple lookups through basic RAG and use the agent only for comparisons and for questions where the first search is weak. From what I read, other systems reduce cost with both the algorithm and the architecture: a cap on the number of steps (mine is 8, and no run reached it), caching common searches, and reranking so fewer chunks go to the model. I have not tested any of these.

## 4. Method caveats (say these out loud)

- 5 of the 30 questions (L01, L06, N08, C01, C10) were used to tune the prompt, so the agent numbers are not a clean held-out result. Prompt changes were kept generic.
- Temperature cannot be set, so runs vary. Two or three runs per agent setup; only the last run of each used the final prompt (vector 93%, hybrid 97%). Hybrid is the default because it fixes retrieval misses (L06, L07) that prompt changes did not, not because of the small gap in accuracy.
- The grader is an LLM, cross-checked by a plain-code number check. One question (C03) is flagged for review.
- 30 questions is small: one question is 3.3 percentage points.

## 5. What I'd do with more time

1. **A better data bank, not a bigger question bank.** The failures were about structure: comparisons that need both companies, the wrong year, the wrong page. I would add a structured layer next to the text search: extract the financial statement line items into a table (company, year, metric, value, page), add richer metadata for filtering, and give the agent a lookup tool for it, so a comparison becomes a query instead of several text searches. That makes the system answer new questions without anyone writing them. I would still keep a small hand-verified test set, plus a held-out part that I never tune on, because without one I cannot tell whether a change helped. 5 of the current 30 were used to tune the prompt.
2. **Run each setup 3+ times.** Temperature cannot be set, so results vary. So will be taking average of the tests. the hybrid numbers come from only 2 runs.
3. **Route by question type.** Add a query router and a reranker. A small classifier  would send lookups to a single hybrid search and comparisons to the agent, which splits them into one search per company and year. A cross-encoder reranker over the combined results would then keep only the best chunks, which cuts the roughly 5× token cost without losing accuracy

## Resume bullet

- Built an agentic RAG system over Sea and Grab 20-F filings (Claude tool use, Chroma, BM25 + vector hybrid search, safe calculator tool, JSONL traces); on 30 hand-verified questions, raised answer accuracy from 50% to 90-100% and multi-hop comparison accuracy from 30% to 90-100% versus a single-retrieval baseline, at about 5x the tokens per question.
