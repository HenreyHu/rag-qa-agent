# rag-qa-agent

Agentic RAG over company annual reports, with citations and evals.

The agent answers questions about Sea Limited's and Grab Holdings' annual reports (SEC Form 20-F).
Every answer cites the report page it came from, and questions can compare companies or years.

## Status

Week 1 of 4: ingestion, retrieval, and a retrieval eval.
The answer-generation step (Week 2) and the agent loop (Week 3) come next.

## Setup (Windows)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
copy .env.example .env
```

Then fill in `SEC_USER_AGENT` in `.env`.
