# Write-up: RAG Q&A agent over Sea and Grab 20-F filings

> DRAFT SCAFFOLD. The numbers and evidence below come from the repo's eval files. The plan says the findings should be in your own words, so each section ends with a **Your take** prompt. Replace those with what you actually concluded, and cut anything you can't explain in an interview.

## What this is

An agent that answers questions about the FY2024 and FY2025 annual reports (Form 20-F) of Sea Limited and Grab Holdings, with `[Company, FYyear, p.X]` citations. It was evaluated on 30 hand-verified questions: 10 lookups, 10 narrative, 10 comparisons.

## 1. Chunking trade-offs, and what tables broke

Evidence:
- Two strategies: fixed windows (450 tokens, 75 overlap; 2,055 chunks) and section-aware chunks that never cross an Item or sub-item (2,417 chunks). Tables are separate markdown chunks in both (520).
- They tied on retrieval: strict hit@5 was 50% for both. At k=10 fixed was 60% and section 57%; at k=20, 67% and 70%.
- The three filing generators (Broadridge, Donnelley, Workiva) format pages differently, so the parser only relies on signals they share.
- Tables: the balance sheet chunk was rarely retrieved by vector search. L06 (Sea's cash and cash equivalents, p.F-7) failed for this reason until the agent was told to name the statement in its search.

**Your take:** why did the two strategies tie? What would you try next for tables?

## 2. Where retrieval failed, and why

Evidence:
- Baseline strict hit@5: lookup 90%, narrative 50%, comparison 10%.
- Comparison failed because one query rarely brings back both companies or both years. "Any" hit@5 was 73% but "strict" was 10%.
- The wrong year wins: the FY2024 report repeats much of the FY2025 text (N06).
- Naming the report in the question ("according to the annual report") pulls in cover and signature pages (N08, N09).
- The business overview outranks the analysis section (Shopee's revenue drivers).
- A perfect company and year filter (oracle) fixed only 2 of 30 questions, so filtering is not the main fix.
- Hybrid keyword + vector search raised strict hit@5 from 50% to 60% (narrative 50% to 80%), but comparison stayed at 10%.

**Your take:** which of these would you fix first in a real system, and why?

## 3. When the agent loop helped, and when it only added cost

Results on the same 30 questions (5 of them were used to tune the prompt):

| Setup | Correct | Lookup | Narrative | Comparison |
|---|---|---|---|---|
| Basic RAG | 50% | 80% | 40% | 30% |
| Agent (vector), 2 runs | 90%, 90% | 80% | 90% | 100% |
| Agent + hybrid, 2 runs | 100%, 97% | 100% | 100% | 100%, 90% |

Cost per question: basic RAG about 2,500 input tokens and 3s; agent about 11,900 tokens and 8.6s; comparisons about 17-21k tokens.

Evidence:
- It helped most where basic RAG abstained (12 of 30 questions did): the agent searches again with different wording and runs one search per company and year.
- Lookups were already 80-90% with basic RAG, so the agent mostly added cost there, except where a retry fixed a miss (L06).
- Arithmetic goes through a `calculate` tool, so growth rates are not model guesses.
- Remaining weak spot: gold-page citations (about 64%). The agent cites a different page that also supports the claim. All cited pages were really retrieved.

**Your take:** is a roughly 5x token cost worth it? For which question types?

## 4. Method caveats (say these out loud)

- 5 of the 30 questions (L01, L06, N08, C01, C10) were used to tune the prompt, so the agent numbers are not a clean held-out result. Prompt changes were kept generic.
- Temperature cannot be set, so runs vary. Two runs per agent setup; the vector setup was not re-run after the last prompt change.
- The grader is an LLM, cross-checked by a plain-code number check. One question (C03) is flagged for review.
- 30 questions is small: one question is 3.3 percentage points.

## 5. What I'd do with more time

Fill in your own list. Candidates from the evidence: a reranker, better table extraction, a larger eval set with a held-out split, citing the primary statement page more reliably, running each setup 3+ times for variance.

## Resume bullet (draft, check the numbers before use)

- Built an agentic RAG system over Sea and Grab 20-F filings (Claude tool use, Chroma, BM25 + vector hybrid search, safe calculator tool, JSONL traces); on 30 hand-verified questions, raised answer accuracy from 50% to 90-100% and multi-hop comparison accuracy from 30% to 90-100% versus a single-retrieval baseline, at about 5x the tokens per question.
