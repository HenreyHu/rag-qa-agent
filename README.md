# rag-qa-agent

Agentic RAG over company annual reports, with citations and evals.

The agent answers questions about Sea Limited's and Grab Holdings' annual reports (SEC Form 20-F).
Every answer cites the report page it came from, and questions can compare companies or years.

## Status

Week 2 of 4 is done: basic RAG with page citations, an answer eval, and two retrieval experiments.
The agent loop (Week 3) comes next.

Baseline results on the 30 verified questions (section chunks, k = 5, no filters):

| Question type | Retrieval strict hit@5 | Answer correct | Answer abstained |
|---|---|---|---|
| Lookup | 90% | 80% | 10% |
| Narrative | 50% | 40% | 50% |
| Comparison | 10% | 30% | 70% |
| All | 50% | 50% | 43% |

No answer was graded wrong: every failure is an abstention or a partial answer, and retrieval is the bottleneck.
See [notes/week1-summary.md](notes/week1-summary.md) and [notes/week2-summary.md](notes/week2-summary.md) for the details, and [notes/failures.md](notes/failures.md) for every failed question.

Retrieval strict hit@k, all 30 questions (chunking strategy: fixed / section):

| k | 3 | 5 | 10 | 20 |
|---|---|---|---|---|
| Strict hit@k | 47% / 47% | 50% / 50% | 60% / 57% | 67% / 70% |

## How it works

1. `scripts/download_filings.py` pins the latest two 20-F filings per company from SEC EDGAR.
2. `src/parse_filing.py` splits each filing into printed pages and tags every block with its page number and section.
3. `src/chunking.py` builds fixed-size and section-aware chunks, with tables as separate markdown chunks.
4. `src/ingest.py` embeds the chunks with `BAAI/bge-small-en-v1.5` and stores them in a local Chroma collection per strategy.
5. `src/retrieve.py` searches a collection, optionally filtered by company and year.
6. `eval/retrieval_eval.py` measures whether the gold pages come back in the top k.
7. `src/rag.py` asks Claude to answer from the top-k chunks only, citing `[Company, FYyear, p.X]`; `src/citations.py` parses those citations.
8. `eval/answer_eval.py` grades each answer and its citations; `eval/experiments.py` sweeps k and tests an oracle company and year filter.

## Setup (Windows)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
copy .env.example .env
```

Then set `SEC_USER_AGENT` in `.env` to your name and email; SEC EDGAR requires it.

## Run

```powershell
$env:PYTHONUTF8 = "1"
.venv\Scripts\python.exe -m scripts.download_filings
.venv\Scripts\python.exe -m src.ingest
.venv\Scripts\python.exe -m src.retrieve "What was Sea's total revenue in 2025?" --company Sea --year 2025
.venv\Scripts\python.exe -m eval.gold_tools check
.venv\Scripts\python.exe -m eval.retrieval_eval
.venv\Scripts\python.exe -m src.rag "What was Sea's total revenue in 2025?" --company Sea --year 2025
.venv\Scripts\python.exe -m eval.answer_eval
.venv\Scripts\python.exe -m eval.experiments sweep
.venv\Scripts\python.exe -m eval.experiments oracle --k 5
```

`eval.answer_eval` makes about 60 Claude calls (30 answers and 30 grades); the two experiments make none unless you add `--answers`.

`python -m src.ingest --dry-run` parses and chunks without embedding, and writes everything to `data/processed/` for inspection.

## Tests

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
```
