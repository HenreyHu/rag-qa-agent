# Eval set verification worksheet

For each row: the evidence snippet's actual location in the parsed filing text, pulled automatically. Read the excerpt, compare it against `gold_answer`, then flip `verified` to TRUE in questions.csv yourself (or tell me and I'll do the CSV edit).

Legend: **on claimed page** = snippet found exactly on the page(s) listed in `gold_page`. **found elsewhere** = snippet exists but not on the claimed page — check `gold_page`. **not found** = snippet doesn't match parsed text at all — check wording/typos.

---

## L01 (lookup) — verified=FALSE

**Q:** What was Sea's total revenue in FY2025?

**gold_answer:** US$22,938,469 thousand (about US$22.9 billion)

- evidence on **sea-2025**, claimed page(s) `95|96|99|F-11`, snippet: `Total revenue ... 22,938,469`
  - on claimed page ✅
  - p.95 [table] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Revenue
    > ...akdown. For the Year Ended December 31, (thousands, except for percentages) | | 2023 US$ | 2023 Percentage of Total Revenue | 2024 US$ | 2024 Percentage of Total Revenue | 2025 US$ | 2025 Percentage of Total Revenue | |---|---|---|---|---|---|---| | Service revenue | | | | | | | | E-commerce (Shopee) | 7,885,185 | 60.3 | 10,862,...
  - p.96 [table] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Revenue
    > ...locations where the services were provided or goods were sold, both in absolute amount and as a percentage of total revenue for the periods indicated. For the Year Ended December 31, (thousands, except for percentages) | | 2023 US$ | 2023 Percentage of Total Revenue | 2024 US$ | 2024 Percentage of Total Revenue | 2025 US$ | 2025...
  - p.99 [table] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Results of Operations
    > ...period. For the Year Ended December 31, (thousands, except for percentages) | | 2023 US$ | 2023 Percentage of Total Revenue | 2024 US$ | 2024 Percentage of Total Revenue | 2025 US$ | 2025 Percentage of Total Revenue | |---|---|---|---|---|---|---| | Selected Consolidated Statements of Operations Data: | | | | | | | | Revenue: | ...
  - p.F-11 [table] Item 18. Financial Statements > CONSOLIDATED STATEMENTS OF OPERATIONS
    > ...revenue | | 11,942,385 | 15,261,263 | 20,913,061 | | Sales of goods | | 1,121,175 | 1,558,603 | 2,025,408 | | Total revenue | | 13,063,560 | 16,819,866 | 22,938,469 | | Cost of revenue | | | | | | Cost of service | | (6,202,524) | (8,164,387) | (10,812,039) | | Cost of goods sold | | (1,027,389) | (1,450,391) | (1,882,693) | | T...

## L02 (lookup) — verified=FALSE

**Q:** How much revenue did Grab's deliveries segment generate in FY2025?

**gold_answer:** $1,800 million (up from $1,493 million in FY2024)

- evidence on **grab-2025**, claimed page(s) `88|89|97|98|F-54`, snippet: `Deliveries ... 1,800 ... 1,493`
  - on claimed page ✅
  - p.88 [table] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Revenue by segment
    > ...) | Year Ended December 31, 2025 | Year Ended December 31, 2024 | |---|---|---| | Revenue | 3,370 | 2,797 | | Deliveries | 1,800 | 1,493 | | Mobility | 1,219 | 1,047 | | Financial services | 347 | 253 | | Others | 4 | 4 |
  - p.89 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Revenue by geographical locations
    > Deliveries revenue was $1,800 million in 2025 compared to $1,493 million in 2024. Mobility revenue increased by $172 million to $1,219 million in 2025 from $1,047 million in 2024. Financial services revenue increased to ...
  - p.97 [table] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Deliveries
    > The table below highlights key operating metrics which drive our revenue for the deliveries segment. | (in $ millions, unless otherwise stated) | Year Ended December 31, 2025 | Year Ended December 31, 2024 | 2024-2025 % Change | |---|---|---|---| | Revenue | 1,800 | 1,493 | 21% | | Segment Adjusted E...
  - p.98 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Deliveries
    > Deliveries revenue was $1,800 million in 2025 compared to revenue of $1,493 million in 2024. The increase in revenue for deliveries was primarily driven by an increase in deliveries GMV of 21%, or $2.5 billion, to $14.2 ...
  - p.F-54 [table] Item 18. Financial Statements > i) Revenue streams
    > | (in $ millions) | 2025 $ | 2024 $ | 2023 $ | |---|---|---|---| | Deliveries | 1,800 | 1,493 | 1310 | | Mobility | 1,219 | 1,047 | 871 | | Financial services | 347 | 253 | 177 | | Others | 4 | 4 | 1 | | | 3,370 | 2,797 | 2,359 |

## L03 (lookup) — verified=FALSE

**Q:** How many full-time employees did Grab have as of December 31, 2025?

**gold_answer:** 12,012 full-time employees

- evidence on **grab-2025**, claimed page(s) `117`, snippet: `Total (1) ... 12,012`
  - on claimed page ✅
  - p.117 [table] Item 6. Directors, Senior Management and Employees > D. Employees
    > ...rketing | 785 | | Operations, support and supermarket retail | 6,888 | | Research and development | 2,964 | | Total (1) | 12,012 |

## L04 (lookup) — verified=FALSE

**Q:** Approximately how many employees did Sea have as of December 31, 2025?

**gold_answer:** Approximately 102,700 employees

- evidence on **sea-2025**, claimed page(s) `121`, snippet: `80,700 and 102,700 employees`
  - on claimed page ✅
  - p.121 [text] Item 6. Directors, Senior Management and Employees > D. Employees
    > We had a total of approximately 62,700, 80,700 and 102,700 employees as of December 31, 2023, 2024 and 2025, respectively. The following table indicates the distribution of our employees by function as of December 31, 2025:

## L05 (lookup) — verified=FALSE

**Q:** What was Grab's profit or loss for the year in FY2025?

**gold_answer:** A profit of $200 million (compared with a loss of $158 million in FY2024)

- evidence on **grab-2025**, claimed page(s) `88|92|94|F-6|F-55|F-71`, snippet: `for the year ... 200 ... (158)`
  - on claimed page ✅
  - p.88 [table] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Results of Operations
    > ...(8) | | Profit/ (loss) before income tax | 269 | (95) | | Income tax expense | (69) | (63) | | Profit/ (loss) for the year | 200 | (158) |
  - p.92 [table] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Profit / (loss) for the year
    > ...ed December 31, 2025 | Year Ended December 31, 2024 | 2024-2025 % Change | |---|---|---|---| | Profit/ (loss) for the year | 200 | (158) | NM | | Percentage of revenue | 6% | (6)% | |
  - p.94 [table] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Reconciliation of Non-IFRS Financial Measures
    > ...tated) | Year Ended December 31, 2025 | Year Ended December 31, 2024 (Recast) | |---|---|---| | Profit/(loss) for the year | 200 | (158) | | Income tax expense | 69 | 63 | | Share of (profit)/ loss of equity-accounted investees (net of tax) | (1) | 8 | | Net finance income (including foreign exchange (gain) loss) | (203) | (81) ...
  - p.F-6 [table] Item 18. Financial Statements > (in $ millions, except for per share data)
    > ... before income tax | | 269 | (95) | (466) | | Income tax expense | 17 | (69) | (63) | (19) | | Profit/ (loss) for the year | | 200 | (158) | (485) | | Items that will not be reclassified to profit or loss: | | | | | | Defined benefit plan remeasurements | | * | * | 2 | | Put liabilities at FVOCI – net change in fair value | | 10...
  - p.F-55 [table] Item 18. Financial Statements > i) Basic earnings/ (loss) per share
    > ...ng table sets forth the computation of basic earnings/ (loss) per share attributable to ordinary shareholders for the years ended December 31, 2025, 2024 and 2023 (in $ millions, except share amounts which are reflected in thousands, and per share amounts): | | 2025 $ | 2024 $ | 2023 $ | |---|---|---|---| | Basic earnings/ (loss...
  - p.F-71 [table] Item 18. Financial Statements > ii) Information about reportable segments
    > ... 60 | | Share of profit/ (loss) of equity-accounted investees (net of tax) | 1 | (8) | (7) | | Profit/ (loss) for the year | 200 | (158) | (485) |

## L06 (lookup) — verified=FALSE

**Q:** What were Sea's cash and cash equivalents as of December 31, 2025?

**gold_answer:** US$4,158,920 thousand (about US$4.2 billion)

- evidence on **sea-2025**, claimed page(s) `F-7`, snippet: `Cash and cash equivalents ... 2,405,153 ... 4,158,920`
  - on claimed page ✅
  - p.F-7 [table] Item 18. Financial Statements > CONSOLIDATED BALANCE SHEETS
    > As of December 31, | | Note | 2024 $ | 2025 $ | |---|---|---|---| | ASSETS | | | | | Current assets | | | | | Cash and cash equivalents | | 2,405,153 | 4,158,920 | | Restricted cash (including restricted cash of the Consolidated VIEs that can only be used to settle the obligations of those Consolidated VIEs of $43,127 and $111,6...

## L07 (lookup) — verified=FALSE

**Q:** What was Sea's net income in FY2025?

**gold_answer:** US$1,610,894 thousand (about US$1.6 billion)

- evidence on **sea-2025**, claimed page(s) `99|F-11|F-13|F-14`, snippet: `Net income ... 447,827 ... 1,610,894`
  - on claimed page ✅
  - p.99 [table] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Results of Operations
    > ...) | (2.8) | | Share of results of equity investees | (7,032) | (0.1) | (9,788) | (0.1) | (18,884) | (0.1) | | Net income | 162,682 | 1.2 | 447,827 | 2.7 | 1,610,894 | 7.0 |
  - p.F-11 [table] Item 18. Financial Statements > CONSOLIDATED STATEMENTS OF OPERATIONS
    > ...62,680) | (321,168) | (651,081) | | Share of results of equity investees | | (7,032) | (9,788) | (18,884) | | Net income | | 162,682 | 447,827 | 1,610,894 | | Net income attributable to non-controlling interests | | (11,956) | (3,506) | (32,745) | | Net income attributable to Sea Limited’s ordinary shareholders | | 150,726 | 444...
  - p.F-13 [table] Item 18. Financial Statements > CONSOLIDATED STATEMENTS OF COMPREHENSIVE INCOME
    > Year ended December 31, | | 2023 $ | 2024 $ | 2025 $ | |---|---|---|---| | Net income | 162,682 | 447,827 | 1,610,894 | | Other comprehensive (loss) income, net of tax | | | | | Change in foreign currency translation adjustment | (695) | (85,548) | 170,852 | | Available-for-sale investments: | ...
  - p.F-14 [table] Item 18. Financial Statements > CONSOLIDATED STATEMENTS OF CASH FLOWS
    > ...ecember 31, | | 2023 $ | 2024 $ | 2025 $ | |---|---|---|---| | Cash flows from operating activities | | | | | Net income | 162,682 | 447,827 | 1,610,894 | | Adjustments to reconcile net income to net cash generated from operating activities: | | | | | Amortization of debt issuance costs of convertible notes | 6,034 | 5,075 | 4,0...

## L08 (lookup) — verified=FALSE

**Q:** How much revenue did Grab earn in Malaysia in FY2025?

**gold_answer:** $1,039 million (up from $816 million in FY2024)

- evidence on **grab-2025**, claimed page(s) `42|54|89|F-54`, snippet: `Malaysia ... 1,039 ... 816`
  - on claimed page ✅
  - p.42 [text] Item 3. Key Information > D. Risk Factors > Risks Relating to Our Corporate Structure and Doing Business in Southeast Asia
    > ...ast Asian region, where substantially all of our assets and operations are located. Our revenue in Indonesia, Malaysia, Philippines, Singapore, Thailand, Vietnam and the rest of Southeast Asia was $715 million, $1,039 million, $316 million, $727 million, $288 million, $255 million and $30 million in the year ended December 31, 2...
  - p.54 [text] Item 4. Information on the Company > B. Business Overview > Southeast Asia’s leading superapp
    > ...ing year-over-year growth rates of 20% from 2024 to 2025 and 19% from 2023 to 2024. Our revenue in Indonesia, Malaysia, Philippines, Singapore, Thailand, Vietnam and the rest of Southeast Asia was $715 million, $1,039 million, $316 million, $727 million, $288 million, $255 million and $30 million in the year ended December 31, 2...
  - p.89 [table] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Revenue by geographical locations
    > ... | 2024-2025 % Change | |---|---|---|---| | Revenue | 3,370 | 2,797 | 20% | | Indonesia | 715 | 643 | 11% | | Malaysia | 1,039 | 816 | 27% | | Philippines | 316 | 265 | 19% | | Singapore | 727 | 578 | 26% | | Thailand | 288 | 252 | 14% | | Vietnam | 255 | 228 | 12% | | Rest of Southeast Asia | 30 | 15 | 100% |
  - p.F-54 [table] Item 18. Financial Statements > ii) Geographic information
    > | (in $ millions) | 2025 $ | 2024 $ | 2023 $ | |---|---|---|---| | Indonesia | 715 | 643 | 605 | | Malaysia | 1,039 | 816 | 673 | | Philippines | 316 | 265 | 200 | | Singapore | 727 | 578 | 480 | | Thailand | 288 | 252 | 205 | | Vietnam | 255 | 228 | 185 | | Rest of Southeast Asia | 30 | 15 | 11 | | | 3,370 | 2,797 | ...

## L09 (lookup) — verified=FALSE

**Q:** What was Grab's mobility GMV in FY2025?

**gold_answer:** $7.9 billion (up from $6.6 billion in FY2024)

- evidence on **grab-2025**, claimed page(s) `98`, snippet: `mobility GMV increasing to $7.9 billion`
  - on claimed page ✅
  - p.98 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Mobility
    > ...ng revenue was primarily driven by stronger demand and platform engagement with our product initiatives, with mobility GMV increasing to $7.9 billion in 2025 compared to $6.6 billion in 2024. Our incentives increased by $111 million (comprised of increases of $108 million in partner incentives and increases of $3 million in cons...

## L10 (lookup) — verified=FALSE

**Q:** How large a share repurchase program did Grab's board authorize in February 2026?

**gold_answer:** Up to $500 million of Class A Ordinary Shares, with no fixed end date

- evidence on **grab-2025**, claimed page(s) `49|99|135|F-73`, snippet: `repurchase up to $500 million`
  - on claimed page ✅
  - p.49 [text] Item 3. Key Information > D. Risk Factors > Risks Relating to the Company’s Securities
    > In February 2026, our board of directors authorized a share repurchase program, under which we may repurchase up to $500 million worth of our Class A Ordinary Shares. The share repurchase program does not have a fixed end date and does not obligate us to repurchase any specific dollar amount or to acquire any specific...
  - p.99 [text] Item 5. Operating and Financial Review and Prospects > B. Liquidity and Capital Resources
    > ... 2024. In February 2026, we announced the authorization of a new share repurchase program, under which we may repurchase up to $500 million worth of our outstanding Class A ordinary shares. See “Item 16E. Purchases of Equity Securities by the Issuer and Affiliated Purchasers” for more details about this program. We have funded, ...
  - p.135 [text] Item 16E. Purchases of Equity Securities by the Issuer and Affiliated Purchasers
    > In February 2024, our board of directors has authorized a share repurchase program, under which we may repurchase up to $500 million worth of our outstanding Class A ordinary shares. The table below summarizes our repurchases in 2024 and 2025 under this program. The repurchase in June 2025 was made in connection and concu...
  - p.F-73 [text] Item 18. Financial Statements > 29. Subsequent events
    > ...February 2026, the Group announced the authorization of a share repurchase program, under which the Group may repurchase up to $500 million of the outstanding Class A ordinary shares.

## N01 (narrative) — verified=FALSE

**Q:** What drove the growth of Sea's e-commerce (Shopee) service revenue in FY2025?

**gold_answer:** Mainly GMV growth (GMV grew 26.8% to US$127.4 billion), and secondarily a higher monetization rate on GMV

- evidence on **sea-2025**, claimed page(s) `100`, snippet: `mainly due to the growth of GMV, as GMV grew 26.8%`
  - on claimed page ✅
  - p.100 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Revenue
    > ...-commerce service revenue increased by 33.9% from US$10.9 billion in 2024 to US$14.5 billion in 2025. This is mainly due to the growth of GMV, as GMV grew 26.8% from US$100.5 billion in 2024 to US$127.4 billion in 2025, and secondarily attributable to an increase in the rate of monetization on the GMV, as e-commerce service reve...

## N02 (narrative) — verified=FALSE

**Q:** Why did Sea's digital financial services (Monee) revenue increase in FY2025?

**gold_answer:** Growth of its credit business: lending increased and loans receivable grew from US$4.2 billion to US$8.0 billion

- evidence on **sea-2025**, claimed page(s) `100`, snippet: `loans receivable grew from US$4.2 billion`
  - on claimed page ✅
  - p.100 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Revenue
    > ...lion in 2025. This is mainly due to growth of our credit business as our lending activities increased and our loans receivable grew from US$4.2 billion as at December 31, 2024 to US$8.0 billion as at December 31, 2025. Growth of our loans receivable was mainly driven by a few factors including growth of our e-commerce platform, ...

## N03 (narrative) — verified=FALSE

**Q:** What explains the increase in Sea's digital entertainment (Garena) revenue in FY2025?

**gold_answer:** A larger active user base and deeper paying-user penetration (average Game QAUs rose 5.7% to 657.7 million)

- evidence on **sea-2025**, claimed page(s) `100`, snippet: `average Game QAUs increased by 5.7%`
  - on claimed page ✅
  - p.100 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Revenue
    > ...was primarily due to the increase in our active user base as well as the deepened paying user penetration, as average Game QAUs increased by 5.7% from 622.3 million in 2024 to 657.7 million in 2025, while average Game QPUs increased by 23.9% from 50.5 million in 2024 to 62.6 million in 2025.

## N04 (narrative) — verified=FALSE

**Q:** What drove the growth in Grab's deliveries revenue in FY2025?

**gold_answer:** Deliveries GMV grew 21% to $14.2 billion on higher consumer demand and product innovation, plus $161 million more from its supermarket business

- evidence on **grab-2025**, claimed page(s) `98`, snippet: `increase in deliveries GMV of 21%`
  - on claimed page ✅
  - p.98 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Deliveries
    > ...pared to revenue of $1,493 million in 2024. The increase in revenue for deliveries was primarily driven by an increase in deliveries GMV of 21%, or $2.5 billion, to $14.2 billion in 2025 compared to $11.7 billion in 2024, mainly due to increased consumer demand and platform engagement with technology-led product innovations. The...

## N05 (narrative) — verified=FALSE

**Q:** Why did Grab's financial services revenue grow in FY2025?

**gold_answer:** Mainly $81 million of growth in its lending businesses, plus $10 million more interest income in its digital banking business

- evidence on **grab-2025**, claimed page(s) `99`, snippet: `$81 million growth in our lending businesses`
  - on claimed page ✅
  - p.99 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Financial Services
    > ...enue increased to $347 million in 2025, compared to $253 million in 2024. The increase was primarily due to a $81 million growth in our lending businesses through our ecosystem partners and users, and a $10 million growth in interest income from securities and treasury bills placement in our digital banking business. Additionall...

## N06 (narrative) — verified=FALSE

**Q:** What risk does Grab's FY2025 annual report describe around the status of its driver-partners?

**gold_answer:** Being required to reclassify driver-partners as employees, provide more benefits, or face unionization, with adverse business, financial, tax and legal consequences

- evidence on **grab-2025**, claimed page(s) `9|19`, snippet: `reclassify our driver-partners as employees`
  - on claimed page ✅
  - p.9 [text] Item 3. Key Information > D. Risk Factors > Risks Relating to Our Business and Industry
    > •If we are required to reclassify our driver-partners as employees, if we are required to provide additional benefits, welfare and protection for our driver-partners, or if our driver-partners unionize, there may be adverse business, financial...
  - p.19 [text] Item 3. Key Information > D. Risk Factors > Risks Relating to Our Business and Industry
    > If we are required to reclassify our driver-partners as employees, if we are required to provide additional benefits, welfare and protection for our driver-partners, or if our driver-partners unionize, there may be adverse business, financial...

## N07 (narrative) — verified=FALSE

**Q:** Which regulatory change in Indonesia does Grab's FY2025 report say could cap its commissions?

**gold_answer:** A draft decree would lower the commission cap to a flat 10% and treat driver-partners as quasi-employees needing insurance and pension contributions

- evidence on **grab-2025**, claimed page(s) `16`, snippet: `flat 10% commission cap`
  - on claimed page ✅
  - p.16 [text] Item 3. Key Information > D. Risk Factors > Risks Relating to Our Business and Industry
    > ...ng fee cap under Ministry of Transportation (“MOT”) Decree No. 667 of 2022, as amended) would be lowered to a flat 10% commission cap. Furthermore, the draft decree seeks to reclassify driver-partners as quasi-employees, requiring us to fund accident and death insurance and contribute to health, old-age, and pension premiums. As...

## N08 (narrative) — verified=FALSE

**Q:** According to Sea's FY2025 annual report, what happened to Free Fire in India?

**gold_answer:** Since early 2022 Free Fire has been unavailable in the Google Play Store and iOS App Store in India because of government actions, and it remains unavailable

- evidence on **sea-2025**, claimed page(s) `10`, snippet: `Free Fire was made unavailable in the Google Play Store`
  - on claimed page ✅
  - p.10 [text] Item 3. Key Information > D. Risk Factors > Risks Applicable Across Multiple Businesses
    > ...ncerns, or due to some misunderstanding. For example, due to unanticipated government actions, in early 2022, Free Fire was made unavailable in the Google Play Store and iOS App Store in India, and currently remains unavailable. Users generally need to access the internet and app stores to access, download or use our services an...

## N09 (narrative) — verified=FALSE

**Q:** What is Grab's dividend policy, according to its FY2025 annual report?

**gold_answer:** It has never declared or paid a cash dividend and intends to retain future earnings, with no dividends expected in the foreseeable future

- evidence on **grab-2025**, claimed page(s) `123`, snippet: `never declared or paid any cash dividend`
  - on claimed page ✅
  - p.123 [text] Item 8. Financial Information > A. Consolidated Statements and Other Financial Information > Dividend Policy
    > We have never declared or paid any cash dividend on our Class A Ordinary Shares. We currently intend to retain any future earnings and do not expect to pay any dividends in the foreseeable future. Any further determination to pa...

## N10 (narrative) — verified=FALSE

**Q:** Why did Sea's e-commerce cost of revenue increase in FY2024?

**gold_answer:** Mainly higher logistics costs as order volume grew 33.0% from 8.2 billion to 10.9 billion orders

- evidence on **sea-2024**, claimed page(s) `97`, snippet: `increase in logistics costs as orders volume grew 33.0%`
  - on claimed page ✅
  - p.97 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Cost of Revenue
    > ...ased by 38.6% from US$5.2 billion in 2023 to US$7.2 billion in 2024. The increase was primarily driven by the increase in logistics costs as orders volume grew 33.0% from 8.2 billion in 2023 to 10.9 billion in 2024.

## C01 (comparison) — verified=FALSE

**Q:** Whose total revenue grew faster in FY2025, Sea's or Grab's?

**gold_answer:** Sea's: 36.4% (US$16.8 billion to US$22.9 billion) vs about 20% for Grab ($2,797 million to $3,370 million)

- evidence on **sea-2025**, claimed page(s) `100`, snippet: `total revenue increased by 36.4%`
  - on claimed page ✅
  - p.100 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Revenue
    > Our total revenue increased by 36.4% from US$16.8 billion in 2024 to US$22.9 billion in 2025.
- evidence on **grab-2025**, claimed page(s) `89`, snippet: `revenue increased by $573 million to $3,370 million`
  - on claimed page ✅
  - p.89 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Revenue by geographical locations
    > Our revenue increased by $573 million to $3,370 million in 2025 from $2,797 million in 2024.

## C02 (comparison) — verified=FALSE

**Q:** Which company had more employees at the end of 2025, Sea or Grab, and by roughly how much?

**gold_answer:** Sea, with about 102,700 employees vs Grab's 12,012 full-time employees (about 8.5 times as many)

- evidence on **sea-2025**, claimed page(s) `121`, snippet: `80,700 and 102,700 employees`
  - on claimed page ✅
  - p.121 [text] Item 6. Directors, Senior Management and Employees > D. Employees
    > We had a total of approximately 62,700, 80,700 and 102,700 employees as of December 31, 2023, 2024 and 2025, respectively. The following table indicates the distribution of our employees by function as of December 31, 2025:
- evidence on **grab-2025**, claimed page(s) `117`, snippet: `Total (1) ... 12,012`
  - on claimed page ✅
  - p.117 [table] Item 6. Directors, Senior Management and Employees > D. Employees
    > ...rketing | 785 | | Operations, support and supermarket retail | 6,888 | | Research and development | 2,964 | | Total (1) | 12,012 |

## C03 (comparison) — verified=FALSE

**Q:** Which company has had the same auditor for longer, according to their FY2025 reports: Sea or Grab?

**gold_answer:** Sea: Ernst & Young LLP has audited it since 2010, while KPMG LLP has audited Grab since 2015

- evidence on **sea-2025**, claimed page(s) `F-4`, snippet: `auditor since 2010`
  - on claimed page ✅
  - p.F-4 [text] Item 18. Financial Statements > Critical Audit Matters (continued)
    > We have served as the Company’s auditor since 2010.
- evidence on **grab-2025**, claimed page(s) `F-3`, snippet: `auditor since 2015`
  - on claimed page ✅
  - p.F-3 [text] Item 18. Financial Statements > Critical Audit Matter
    > We have served as the Company’s auditor since 2015.

## C04 (comparison) — verified=FALSE

**Q:** In FY2025, whose financial services revenue grew faster: Sea's Monee or Grab's financial services segment?

**gold_answer:** Sea's Monee: up 60.1% (US$2.4 billion to US$3.8 billion) vs about 37% for Grab ($253 million to $347 million)

- evidence on **sea-2025**, claimed page(s) `100`, snippet: `digital financial services revenue increased by 60.1%`
  - on claimed page ✅
  - p.100 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Revenue
    > ● Digital Financial Services (Monee): Our digital financial services revenue increased by 60.1% from US$2.4 billion in 2024 to US$3.8 billion in 2025. This is mainly due to growth of our credit business as our lending activities increased and our loans receivabl...
- evidence on **grab-2025**, claimed page(s) `89|99`, snippet: `Financial services revenue increased to $347 million`
  - on claimed page ✅
  - p.89 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Revenue by geographical locations
    > ...on in 2024. Mobility revenue increased by $172 million to $1,219 million in 2025 from $1,047 million in 2024. Financial services revenue increased to $347 million in 2025 from $253 million in 2024. Others revenue remained flat at $4 million in 2025 and 2024.
  - p.99 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Financial Services
    > Financial services revenue increased to $347 million in 2025, compared to $253 million in 2024. The increase was primarily due to a $81 million growth in our lending businesses through our ecosystem partners and users, a...

## C05 (comparison) — verified=FALSE

**Q:** In FY2025, which grew faster: Shopee's GMV or Grab's deliveries GMV?

**gold_answer:** Shopee's GMV: up 26.8% to US$127.4 billion vs 21% for Grab's deliveries GMV (to $14.2 billion)

- evidence on **sea-2025**, claimed page(s) `100`, snippet: `GMV grew 26.8% from US$100.5 billion`
  - on claimed page ✅
  - p.100 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Revenue
    > ...by 33.9% from US$10.9 billion in 2024 to US$14.5 billion in 2025. This is mainly due to the growth of GMV, as GMV grew 26.8% from US$100.5 billion in 2024 to US$127.4 billion in 2025, and secondarily attributable to an increase in the rate of monetization on the GMV, as e-commerce service revenue over GMV improved from 10.8% in ...
- evidence on **grab-2025**, claimed page(s) `98`, snippet: `increase in deliveries GMV of 21%`
  - on claimed page ✅
  - p.98 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Deliveries
    > ...pared to revenue of $1,493 million in 2024. The increase in revenue for deliveries was primarily driven by an increase in deliveries GMV of 21%, or $2.5 billion, to $14.2 billion in 2025 compared to $11.7 billion in 2024, mainly due to increased consumer demand and platform engagement with technology-led product innovations. The...

## C06 (comparison) — verified=FALSE

**Q:** Did Sea's total revenue grow faster in FY2025 or in FY2024?

**gold_answer:** FY2025: 36.4% vs 28.8% in FY2024

- evidence on **sea-2025**, claimed page(s) `100`, snippet: `total revenue increased by 36.4%`
  - on claimed page ✅
  - p.100 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Revenue
    > Our total revenue increased by 36.4% from US$16.8 billion in 2024 to US$22.9 billion in 2025.
- evidence on **sea-2024**, claimed page(s) `97`, snippet: `total revenue increased by 28.8%`
  - on claimed page ✅
  - p.97 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Revenue
    > Our total revenue increased by 28.8% from US$13.1 billion in 2023 to US$16.8 billion in 2024.

## C07 (comparison) — verified=FALSE

**Q:** How did Grab's full-time headcount change between the end of 2024 and the end of 2025?

**gold_answer:** It rose by 745, from 11,267 to 12,012 full-time employees (about 6.6%)

- evidence on **grab-2024**, claimed page(s) `161`, snippet: `Total (1) ... 11,267`
  - on claimed page ✅
  - p.161 [table] Item 6. Directors, Senior Management and Employees > D. Employees
    > ...rketing | 853 | | Operations, support and supermarket retail | 6,055 | | Research and development | 2,934 | | Total (1) | 11,267 |
- evidence on **grab-2025**, claimed page(s) `117`, snippet: `Total (1) ... 12,012`
  - on claimed page ✅
  - p.117 [table] Item 6. Directors, Senior Management and Employees > D. Employees
    > ...rketing | 785 | | Operations, support and supermarket retail | 6,888 | | Research and development | 2,964 | | Total (1) | 12,012 |

## C08 (comparison) — verified=FALSE

**Q:** Did Grab's deliveries GMV grow faster in FY2025 or in FY2024?

**gold_answer:** FY2025: 21% (to $14.2 billion) vs 13% in FY2024 (to $11.7 billion)

- evidence on **grab-2025**, claimed page(s) `98`, snippet: `increase in deliveries GMV of 21%`
  - on claimed page ✅
  - p.98 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Deliveries
    > ...pared to revenue of $1,493 million in 2024. The increase in revenue for deliveries was primarily driven by an increase in deliveries GMV of 21%, or $2.5 billion, to $14.2 billion in 2025 compared to $11.7 billion in 2024, mainly due to increased consumer demand and platform engagement with technology-led product innovations. The...
- evidence on **grab-2024**, claimed page(s) `129`, snippet: `increase in deliveries GMV of 13%`
  - on claimed page ✅
  - p.129 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Revenue by geographical locations
    > ...024 compared to $1,310 million in 2023. The increase in revenue for deliveries was primarily driven by (i) an increase in deliveries GMV of 13%, or $1.4 billion, to $11.7 billion in 2024 compared to $10.4 billion in 2023, due to increased consumer demand and platform engagement with technology-led product innovations; (ii) an in...

## C09 (comparison) — verified=FALSE

**Q:** Compare Shopee's GMV growth in FY2024 with Grab's deliveries GMV growth in FY2025.

**gold_answer:** Shopee's GMV grew 28.0% in FY2024 (to US$100.5 billion), faster than the 21% growth of Grab's deliveries GMV in FY2025 (to $14.2 billion)

- evidence on **sea-2024**, claimed page(s) `97`, snippet: `GMV grew 28.0% from US$78.5 billion`
  - on claimed page ✅
  - p.97 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Revenue
    > ... by 37.8% from US$7.9 billion in 2023 to US$10.9 billion in 2024. This is mainly due to the growth of GMV, as GMV grew 28.0% from US$78.5 billion in 2023 to US$100.5 billion in 2024. Average order value on Shopee decreased slightly to approximately US$9 in 2024, as compared to approximately US$10 in 2023, while our orders volume...
- evidence on **grab-2025**, claimed page(s) `98`, snippet: `increase in deliveries GMV of 21%`
  - on claimed page ✅
  - p.98 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Deliveries
    > ...pared to revenue of $1,493 million in 2024. The increase in revenue for deliveries was primarily driven by an increase in deliveries GMV of 21%, or $2.5 billion, to $14.2 billion in 2025 compared to $11.7 billion in 2024, mainly due to increased consumer demand and platform engagement with technology-led product innovations. The...

## C10 (comparison) — verified=FALSE

**Q:** In each of FY2024 and FY2025, which company grew its revenue faster, Sea or Grab?

**gold_answer:** Sea both years: 28.8% vs 19% for Grab in FY2024, and 36.4% vs 20% in FY2025

- evidence on **sea-2025**, claimed page(s) `100`, snippet: `total revenue increased by 36.4%`
  - on claimed page ✅
  - p.100 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Revenue
    > Our total revenue increased by 36.4% from US$16.8 billion in 2024 to US$22.9 billion in 2025.
- evidence on **sea-2024**, claimed page(s) `97`, snippet: `total revenue increased by 28.8%`
  - on claimed page ✅
  - p.97 [text] Item 5. Operating and Financial Review and Prospects > A. Operating Results > Revenue
    > Our total revenue increased by 28.8% from US$13.1 billion in 2023 to US$16.8 billion in 2024.
- evidence on **grab-2025**, claimed page(s) `54`, snippet: `growth rates of 20% from 2024 to 2025`
  - on claimed page ✅
  - p.54 [text] Item 4. Information on the Company > B. Business Overview > Southeast Asia’s leading superapp
    > ... million, $2,797 million and $2,359 million in 2025, 2024 and 2023, respectively, representing year-over-year growth rates of 20% from 2024 to 2025 and 19% from 2023 to 2024. Our revenue in Indonesia, Malaysia, Philippines, Singapore, Thailand, Vietnam and the rest of Southeast Asia was $715 million, $1,039 million, $316 million...
- evidence on **grab-2024**, claimed page(s) `64`, snippet: `growth rates of 19% from 2023 to 2024`
  - on claimed page ✅
  - p.64 [text] Item 4. Information on the Company > B. Business Overview > Southeast Asia’s leading superapp
    > ... million, $2,359 million and $1,433 million in 2024, 2023 and 2022, respectively, representing year-over-year growth rates of 19% from 2023 to 2024 and 65% from 2022 to 2023. Our revenue in Indonesia, Malaysia, Philippines, Singapore, Thailand, Vietnam and the rest of Southeast Asia was $643 million, $816 million, $265 million, ...
