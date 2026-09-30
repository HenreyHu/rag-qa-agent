# Week 2 failures

Source: `answers_section_k5.csv`. 15 of 30 answers were not graded correct.
Categories: wrong chunk, bad table, hallucination, multi-hop, over-abstention, plus incomplete answer (right page retrieved, one detail missing). The suggested category is the tool's rule-based first guess; the final category after reading each answer and its retrieved pages is on the 'Final category' line. Confirm these yourself before relying on them.

| Category | Count |
|---|---|
| wrong chunk | 7 |
| multi-hop | 6 |
| incomplete answer | 2 |
| bad table | 0 |
| hallucination | 0 |
| over-abstention | 0 |

## L06 (lookup): abstained

- Question: What were Sea's cash and cash equivalents as of December 31, 2025?
- Gold answer: US$4,158,920 thousand (about US$4.2 billion)
- Model answer: I don't know. The provided context includes figures for "Cash, cash equivalents and restricted cash at end of year" for 2025 (US$6,419,467 thousand) [Sea, FY2025, p.107], but this combined figure includes restricted cash. The specific breakout of cash and cash equivalents alone (excluding restricted cash) as of December 31, 2025 is not provided in the given context.
- Grader: The model explicitly states it does not know the specific cash and cash equivalents figure, providing only a combined cash+restricted cash number instead.
- Suggested category: wrong chunk
- Final category: wrong chunk. retrieval returned the cash-flow total (p.107, includes restricted cash) instead of the balance sheet (p.F-7), so the model rightly refused to guess.

## L10 (lookup): partial

- Question: How large a share repurchase program did Grab's board authorize in February 2026?
- Gold answer: Up to $500 million of Class A Ordinary Shares, with no fixed end date
- Model answer: In February 2026, Grab's board of directors authorized a new share repurchase program under which the company may repurchase up to $500 million worth of its Class A ordinary shares [Grab, FY2025, p.135][Grab, FY2025, p.49, 50].
- Grader: Matches the $500 million amount and share class but omits the detail that there is no fixed end date.
- Suggested category: bad table
- Final category: incomplete answer. gold page was retrieved and cited; the answer has the $500 million but omits 'no fixed end date'. A strict-grading or over-specific-gold issue, not a retrieval failure.

## N01 (narrative): abstained

- Question: What drove the growth of Sea's e-commerce (Shopee) service revenue in FY2025?
- Gold answer: Mainly GMV growth (GMV grew 26.8% to US$127.4 billion), and secondarily a higher monetization rate on GMV
- Model answer: I don't know. The provided context does not include information specifically on the drivers of Sea's e-commerce (Shopee) service revenue growth for FY2025. The FY2025 excerpts discuss GMV, gross orders, business overview, and seller/buyer operations [Sea, FY2025, p.50, 51][Sea, FY2025, p.51, 52], but do not detail the drivers of e-commerce service revenue growth for that year. The revenue ...
- Grader: The model states it does not know rather than providing the facts from the gold answer.
- Suggested category: wrong chunk
- Final category: wrong chunk. retrieved the Item 4 business description instead of the Item 5 discussion of what drove revenue (known from Week 1).

## N03 (narrative): abstained

- Question: What explains the increase in Sea's digital entertainment (Garena) revenue in FY2025?
- Gold answer: A larger active user base and deeper paying-user penetration (average Game QAUs rose 5.7% to 657.7 million)
- Model answer: I don't know. The provided context states that Garena's FY2025 revenue was $2,408.8 million [Sea, FY2025, p.F-3], but it does not include information explaining the reasons for the increase in that revenue.
- Grader: The model explicitly states it does not know the reasons for the revenue increase.
- Suggested category: wrong chunk
- Final category: wrong chunk. saw the Garena revenue figure but not the Item 5 explanation of the increase.

## N06 (narrative): abstained

- Question: What risk does Grab's FY2025 annual report describe around the status of its driver-partners?
- Gold answer: Being required to reclassify driver-partners as employees, provide more benefits, or face unionization, with adverse business, financial, tax and legal consequences
- Model answer: I don't know. The provided context does not contain a discussion in Grab's FY2025 annual report specifically about risks related to the classification or status of its driver-partners (e.g., employment/independent contractor status). The FY2025 excerpts provided address risks related to incentives, cash payment reliance, autonomous vehicle investments, and general business execution risks ...
- Grader: The model explicitly states it does not know and fails to provide the gold answer's facts.
- Suggested category: wrong chunk
- Final category: wrong chunk. wrong year: retrieved the FY2024 risk factors and other FY2025 risks, not the driver-partner classification risk.

## N07 (narrative): partial

- Question: Which regulatory change in Indonesia does Grab's FY2025 report say could cap its commissions?
- Gold answer: A draft decree would lower the commission cap to a flat 10% and treat driver-partners as quasi-employees needing insurance and pension contributions
- Model answer: According to Grab's FY2025 report, in Indonesia, there have been media speculations that the government is considering a draft presidential decree that would mandate a reduction in the maximum commission Grab can charge its driver-partners. If adopted, this would lower the current 20% cap (comprising a 15% commission cap and a 5% optional supporting fee cap under Ministry of Transportation ...
- Grader: Correctly states the 10% flat cap but omits the quasi-employee/insurance and pension contribution aspect from the gold answer.
- Suggested category: bad table
- Final category: incomplete answer. gold page p.16 was retrieved; the answer gets the commission cap but omits the quasi-employee insurance and pension part.

## N08 (narrative): abstained

- Question: According to Sea's FY2025 annual report, what happened to Free Fire in India?
- Gold answer: Since early 2022 Free Fire has been unavailable in the Google Play Store and iOS App Store in India because of government actions, and it remains unavailable
- Model answer: I don't know.
- Grader: The model stated it does not know the answer.
- Suggested category: wrong chunk
- Final category: wrong chunk. the question says 'according to the annual report', which pulls in boilerplate pages (cover, index); the Free Fire India passage never reached the model.

## N09 (narrative): abstained

- Question: What is Grab's dividend policy, according to its FY2025 annual report?
- Gold answer: It has never declared or paid a cash dividend and intends to retain future earnings, with no dividends expected in the foreseeable future
- Model answer: I don't know. The provided context does not include Grab's dividend policy from its FY2025 annual report; the dividend policy information available is from the FY2024 annual report [Grab, FY2024, p.168], not FY2025.
- Grader: The model declined to answer, citing lack of FY2025 data, instead of stating the dividend policy facts.
- Suggested category: wrong chunk
- Final category: wrong chunk. wrong year: only the FY2024 dividend policy (p.168) was retrieved plus FY2025 financial statement pages, and the model correctly declined to answer from FY2024.

## C01 (comparison): abstained

- Question: Whose total revenue grew faster in FY2025, Sea's or Grab's?
- Gold answer: Sea's: 36.4% (US$16.8 billion to US$22.9 billion) vs about 20% for Grab ($2,797 million to $3,370 million)
- Model answer: I don't know. The provided context contains only Grab Holdings Limited's financial data and does not include any information about Sea's total revenue, so a comparison cannot be made. Based on the available context, Grab's total revenue grew 20% year-over-year, from $2,797 million in 2024 to $3,370 million in 2025 [Grab, FY2025, p.54].
- Grader: Model states it cannot compare due to missing Sea data, only providing Grab's figures, so it did not answer the comparison question.
- Suggested category: multi-hop
- Final category: multi-hop. only Grab evidence was retrieved; the question needs Sea's revenue too.

## C02 (comparison): abstained

- Question: Which company had more employees at the end of 2025, Sea or Grab, and by roughly how much?
- Gold answer: Sea, with about 102,700 employees vs Grab's 12,012 full-time employees (about 8.5 times as many)
- Model answer: I don't know. The context provided contains employee data only for Grab, not for Sea, so a comparison cannot be made.
- Grader: Model states it does not know and cannot make the comparison.
- Suggested category: multi-hop
- Final category: multi-hop. only Grab's headcount was retrieved; Sea's was missing.

## C03 (comparison): abstained

- Question: Which company has had the same auditor for longer, according to their FY2025 reports: Sea or Grab?
- Gold answer: Sea: Ernst & Young LLP has audited it since 2010, while KPMG LLP has audited Grab since 2015
- Model answer: I don't know. The provided context only contains information about Grab's auditor (KPMG LLP, serving since 2015) [Grab, FY2025, p.F-3, F-4]. There is no information about Sea's auditor or when they began serving as such, so a comparison cannot be made.
- Grader: The model states it does not know Sea's auditor tenure and cannot make the comparison.
- Suggested category: multi-hop
- Final category: multi-hop. only Grab's auditor was retrieved; Sea's was missing.

## C05 (comparison): abstained

- Question: In FY2025, which grew faster: Shopee's GMV or Grab's deliveries GMV?
- Gold answer: Shopee's GMV: up 26.8% to US$127.4 billion vs 21% for Grab's deliveries GMV (to $14.2 billion)
- Model answer: I don't know. The provided context contains no information about Shopee's GMV, only Grab's figures [Grab, FY2025, p.96][Grab, FY2025, p.98].
- Grader: The model states it does not know Shopee's GMV and does not provide the comparison.
- Suggested category: multi-hop
- Final category: multi-hop. only Grab's deliveries GMV was retrieved; Shopee's GMV was missing.

## C07 (comparison): abstained

- Question: How did Grab's full-time headcount change between the end of 2024 and the end of 2025?
- Gold answer: It rose by 745, from 11,267 to 12,012 full-time employees (about 6.6%)
- Model answer: I don't know. The provided context does not contain information about Grab's full-time headcount at the end of 2024 or 2025.
- Grader: The model stated it did not know and provided no headcount figures.
- Suggested category: multi-hop
- Final category: wrong chunk. one company but two years: neither headcount table (p.161, p.117) was retrieved. The same facts answered L03, so the wording matters. Needs both filings too.

## C09 (comparison): abstained

- Question: Compare Shopee's GMV growth in FY2024 with Grab's deliveries GMV growth in FY2025.
- Gold answer: Shopee's GMV grew 28.0% in FY2024 (to US$100.5 billion), faster than the 21% growth of Grab's deliveries GMV in FY2025 (to $14.2 billion)
- Model answer: I don't know. The provided context contains no information about Shopee's GMV growth in FY2024. It only includes data on Grab's deliveries GMV growth, which increased 21% to $14.2 billion in 2025 from $11.7 billion in 2024 [Grab, FY2025, p.98].
- Grader: Model provided Grab's GMV growth correctly but declined to answer regarding Shopee's GMV growth, stating it didn't know.
- Suggested category: multi-hop
- Final category: multi-hop. Grab's FY2025 deliveries GMV was retrieved; Shopee's FY2024 GMV was not.

## C10 (comparison): abstained

- Question: In each of FY2024 and FY2025, which company grew its revenue faster, Sea or Grab?
- Gold answer: Sea both years: 28.8% vs 19% for Grab in FY2024, and 36.4% vs 20% in FY2025
- Model answer: I don't know. The provided context contains only Grab Holdings Limited's financial data; there is no information about Sea's revenue figures for FY2024 or FY2025 [Grab, FY2025, p.F-54] [Grab, FY2024, p.F-54].
- Grader: The model declined to answer, stating it lacked data on Sea's revenue.
- Suggested category: multi-hop
- Final category: multi-hop. only Grab's revenue was retrieved; Sea's revenue for both years was missing.

## What the failures show

1. **Nothing was answered wrongly.** All 15 failures are abstentions (13) or partial answers (2). The strict prompt does its job: when the evidence is missing, the model says so instead of guessing.
2. **Retrieval is the bottleneck, not the model.** 13 of 15 failures trace to the right evidence never reaching the model, either the wrong page or one side of a comparison. The answer score (50%) matches the strict hit@5 score (50%).
3. **Comparisons fail as predicted.** Six of the seven abstained comparison questions had evidence for only one company; the seventh (C07) missed both headcount tables.
4. **The wrong year shows up twice** (N06, N09), which a year filter would target. Most other wrong-chunk cases sit inside the right filing, so a company and year filter cannot fix them.
5. **No bad-table failure was confirmed.** L06 is the closest (the balance sheet table was not retrieved), but the cause was ranking, not parsing.
