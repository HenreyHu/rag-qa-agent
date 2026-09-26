# rag-qa-agent

Agentic RAG over company annual reports, with citations and evals.

The agent answers questions about Sea Limited's and Grab Holdings' annual reports (SEC Form 20-F).
Every answer cites the report page it came from, and questions can compare companies or years.

## Status

Week 1 of 4 is done: ingestion, retrieval, and a retrieval eval.
The answer-generation step (Week 2) and the agent loop (Week 3) come next.

Baseline retrieval hit@5 (strict, no filters, all 30 questions verified by hand):

| Question type | Fixed-size chunks | Section-aware chunks |
|---|---|---|
| Lookup | 90% | 90% |
| Narrative | 50% | 50% |
| Comparison | 10% | 10% |
| All | 50% | 50% |

See [notes/week1-summary.md](notes/week1-summary.md) for what the misses show.

## How it works

1. `scripts/download_filings.py` pins the latest two 20-F filings per company from SEC EDGAR.
2. `src/parse_filing.py` splits each filing into printed pages and tags every block with its page number and section.
3. `src/chunking.py` builds fixed-size and section-aware chunks, with tables as separate markdown chunks.
4. `src/ingest.py` embeds the chunks with `BAAI/bge-small-en-v1.5` and stores them in a local Chroma collection per strategy.
5. `src/retrieve.py` searches a collection, optionally filtered by company and year.
6. `eval/retrieval_eval.py` measures whether the gold pages come back in the top k.

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
```

`python -m src.ingest --dry-run` parses and chunks without embedding, and writes everything to `data/processed/` for inspection.

## Tests

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
```
