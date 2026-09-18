# Open questions

Ambiguities, blockers and judgment calls that came up during the build.
Each entry says what came up, what was decided for now, and what would change the decision.

## Parsing

### Pages without a printed page number

The cover, the table of contents, the signature page and the index page before the financial statements print no page number.
Their blocks get the label `s<physical page number>` (for example `s152`), which can never collide with a printed label.
The eval set never uses an `s` page as a gold page.
This would change if readers needed to cite those pages.

### The financial statement index page is filed under Item 19

The unlabeled index page that opens the financial statements comes before the first `F-` label, so it inherits the last Item heading (Item 19. Exhibits).
It only lists page numbers, so the wrong section is harmless for now.

### Section detection is heuristic

Sub-items ("A. Operating Results") are matched by their text alone, only outside the financial statements, and only in increasing letter order.
Topics are short, all-bold lines; a bold line that repeats on 5 or more pages is treated as a running page header instead.
Bold risk-factor headings are long sentences ending in a period, so they stay ordinary text and never appear in section paths.
This would change if Week 2 retrieval failures trace back to missing or wrong section paths.

### Workiva splits long tables at page breaks

When a Grab table continues on the next page, the HTML starts a new table there, usually repeating the header.
Each part becomes its own table chunk, which matches the printed pages but splits one logical table in two.

### Text-only tables get an empty header row

Two-column tables of prose (for example the auditor's critical audit matters) have no header row, because their first row is content.

## Eval

### Gold pages only count exact matches

A gold page lists every page where the evidence snippet appears word for word.
A page that states the same fact in other words (for example "US$22.9 billion" instead of "22,938,469") is not listed, so retrieving it counts as a miss.
If verification finds such pages, add them as `|` alternatives; `gold_tools check` will list them as warnings, not errors.

### Questions name the fiscal year and sometimes the report

Every question names the company and fiscal year, because the baseline has no filters and the FY2025 report repeats FY2024 figures.
Some narrative questions say "according to ... FY2025 annual report", which turned out to attract cover and signature pages.
That wording is kept on purpose, because real users phrase questions that way.

### Comparison questions need several filings

Each comparison question needs evidence from at least two filings; C10 needs all four.
Strict hit@5 requires all of them in one top 5, which a single query can rarely achieve, so the baseline is expected to be low.
