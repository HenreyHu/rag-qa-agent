# Week 1 summary: ingestion and retrieval

## What was built

The pipeline downloads four annual reports (Form 20-F) from SEC EDGAR, parses them into page- and section-tagged blocks, chunks them two ways, embeds the chunks and stores them in Chroma.
A retrieval eval then checks whether the gold pages come back in the top 5 results.

| Step | File | What it does |
|---|---|---|
| Download | `scripts/download_filings.py` | Finds each company's latest two 20-F filings through the SEC submissions API and pins them (accession number, URL, sha256) in `data/filings.json`. |
| Parse | `src/parse_filing.py` | Splits the inline-XBRL HTML at CSS page breaks, tags every block with its printed page number, builds an Item / sub-item / topic section path, and turns data tables into markdown. |
| Chunk | `src/chunking.py` | Fixed-size windows of 450 tokens with 75 tokens of overlap, or section-aware chunks that never cross an Item or sub-item. Tables are separate chunks shared by both strategies. |
| Embed and store | `src/ingest.py`, `src/embedding.py` | Embeds each distinct chunk once with `BAAI/bge-small-en-v1.5` and rebuilds one Chroma collection per strategy. |
| Search | `src/retrieve.py` | `search(query, k, filters)`, with optional company and year filters. |
| Eval | `eval/questions.csv`, `eval/gold_tools.py`, `eval/retrieval_eval.py` | 30 gold questions, a checker that proves every gold page against the parsed text, and hit@k per strategy and question type. |

The filings are Sea Limited FY2025 and FY2024, and Grab Holdings FY2025 and FY2024.
They come from three different HTML generators (Broadridge, Donnelley and Workiva), so the parser relies only on signals they share.

### Corpus numbers

| Filing | Pages | Unlabeled pages | Tables | Fixed chunks | Section chunks | Table chunks |
|---|---|---|---|---|---|---|
| sea-2025 | 230 | 4 | 101 | 376 | 460 | 119 |
| sea-2024 | 226 | 4 | 96 | 360 | 445 | 113 |
| grab-2025 | 215 | 1 | 121 | 347 | 434 | 134 |
| grab-2024 | 258 | 1 | 142 | 452 | 558 | 154 |

The fixed collection holds 2,055 chunks and the section collection 2,417, including the same 520 table chunks.
No chunk exceeds the model's 512-token limit (the largest is 506).
Parsing takes about 1 second per filing, and embedding the 3,952 distinct chunks took about 5 minutes on CPU.

## Retrieval hit@5 (baseline, no metadata filters)

These numbers use the unverified eval set, so treat them as provisional until every question is checked by hand.

| Question type | n | Fixed strict@5 | Fixed any@5 | Section strict@5 | Section any@5 |
|---|---|---|---|---|---|
| Lookup | 10 | 90% | 90% | 90% | 90% |
| Narrative | 10 | 50% | 50% | 50% | 50% |
| Comparison | 10 | 10% | 70% | 10% | 80% |
| All | 30 | 50% | 70% | 50% | 73% |

Strict means every piece of evidence the question needs is in the top 5; any means at least one piece is.
The two only differ for comparison questions, which need evidence from two or more filings.
Per-question results are in `eval/results/retrieval_k5.csv`.

### What the misses show

1. **Comparison questions fail, as expected.**
   One unfiltered query rarely brings back evidence from two companies or two years in the same top 5.
   This is what the Week 3 agent (one sub-search per company and year) should fix.
2. **The wrong year wins.**
   The FY2024 report repeats much of the FY2025 text, especially risk factors and the business overview.
   For N06 (Grab's driver-partner risk), the top results were the same risk factor from the FY2024 report.
   Metadata filtering by year, the Week 2 experiment, targets this directly.
3. **"According to the annual report" pulls in boilerplate.**
   N08 and N09 name the report in the question, and retrieval returned cover, signature and financial statement index pages, which mention "annual report" constantly.
4. **The business overview outranks the analysis.**
   "What drove Shopee's revenue growth" returned the Item 4 description of Shopee (pages 50 to 52) instead of the Item 5 explanation on page 100.
5. **Balance-sheet lookups land on the discussion, not the statement.**
   L06 (Sea's cash) retrieved the liquidity discussion instead of the balance sheet table on page F-7.

The two chunking strategies tie on strict hit@5.
Section-aware chunking finds one more piece of comparison evidence, which is too small a difference to call on 30 questions.

## Known issues

- The eval set is unverified: every gold answer and page came from the parsed text, but no human has checked them against the reports yet.
- A gold page only lists pages that contain the exact evidence snippet, so a page stating the same fact in other words counts as a miss.
- Pages with no printed number get labels like `s152`; the financial statement index page is also filed under Item 19.
- Section detection is heuristic (see `notes/open-questions.md`).
- The PDF parser for the optional SGX report is not written yet; `pymupdf` and `pdfplumber` are installed for it.

## What to review first

1. **Page and section logic** in `src/parse_filing.py`: `_take_label` and `_assign_sections`.
   Everything else, including the eval, depends on page labels being right.
   `python -m src.parse_filing data/raw/sea-2025_20-F.htm --page 95` prints any page as the parser sees it.
2. **The two chunkers** in `src/chunking.py`: `chunk_fixed` and `chunk_sections`.
3. **Five random eval questions**, checked against the filing in a browser: open the URL from `data/filings.json`, Ctrl+F the evidence snippet, and confirm the printed page number.
   Then verify the rest and set `verified` to TRUE.

## How to reproduce

```powershell
$env:PYTHONUTF8 = "1"
.venv\Scripts\python.exe -m scripts.download_filings
.venv\Scripts\python.exe -m src.ingest
.venv\Scripts\python.exe -m eval.gold_tools check
.venv\Scripts\python.exe -m eval.retrieval_eval
```
