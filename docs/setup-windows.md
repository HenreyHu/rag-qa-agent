# Setup and run (Windows)

You need Windows with Python 3.12. Run every command from the repo folder in PowerShell. Only the steps marked "needs an API key" call Claude, and each person needs their own Anthropic API key (your `.env` file is gitignored, so keys are never uploaded).

### 1. Install

```powershell
cd rag-qa-agent
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
copy .env.example .env
```

### 2. Add your keys

Open `.env` and set two values:

- `SEC_USER_AGENT`: your name and email. SEC EDGAR requires it to download the filings.
- `ANTHROPIC_API_KEY`: your Anthropic API key. Only steps 4 and 5 need it.

### 3. Build the search index (no API key)

```powershell
$env:PYTHONUTF8 = "1"
.venv\Scripts\python.exe -m scripts.download_filings
.venv\Scripts\python.exe -m src.ingest
```

The first command downloads the four 20-F filings from SEC EDGAR. The second parses them, cuts them into chunks and embeds them into a local Chroma database (about 5 minutes on a CPU). To preview the parsing and chunking without embedding, add `--dry-run` to the second command; it writes the result to `data/processed/`.

Check that search works:

```powershell
.venv\Scripts\python.exe -m src.retrieve "What was Sea's total revenue in 2025?" --company Sea --year 2025
```

### 4. Ask questions (needs an API key)

The agent and basic RAG commands are in [Try it](../README.md#try-it). To run basic RAG directly:

```powershell
.venv\Scripts\python.exe -m src.rag "What was Sea's total revenue in 2025?" --company Sea --year 2025
```

### 5. Reproduce the results

Each command below produces one of the tables in [Results](../README.md#results). Run them as `.venv\Scripts\python.exe -m <command>`.

| Command | What it does | Calls Claude? |
|---|---|---|
| `eval.gold_tools check` | Checks that every gold page for the 30 questions really contains its evidence | No |
| `eval.retrieval_eval` | Retrieval hit@5 for both chunking strategies, by question type | No |
| `eval.experiments sweep` | Retrieval hit@k for k = 3, 5, 10 and 20 | No |
| `eval.experiments oracle --k 5` | What a perfect company and year filter would gain | No |
| `eval.answer_eval` | Answers all 30 questions with basic RAG, then grades them | Yes, about 60 calls |
| `eval.answer_eval --mode agent --tag my-run` | The same, with the agent (results saved under the tag) | Yes, more tokens per question |

The two experiments make no Claude calls unless you add `--answers`.

### 6. Tests and lint

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
```
