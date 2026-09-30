# HTML report contract (ilas-fund-report)

The HTML file is the deliverable. Chat gets Markdown + the serve URL only.

## Delivery

- Content lives in **`report.json`** (schema: `schemas/report.schema.json`).
- Copy `template.html` → `index.html` and `report.js` into the run dir. The page **`fetch('report.json')`**. Do not hardcode plan copy in HTML.
- Serve the directory (`python3 -m http.server` on tailnet/LAN). `file://` will fail (no fetch).
- Do **not** paste the HTML into chat.
- **Wipe last-run artifacts** before fetch (see `RUN.md`). Keep `template.html` / `report.js` in this skill directory.

## Required sections (this order)

1. **Header** — plan name, as-of date, fund count, disclaimer.
2. **`#macro`** — not a rates-only table.
   - Sourced table: policy rates, 2Y/10Y, curve, major equity index, any commodity used in the thesis.
   - **Thesis paragraph** (growth / defensive / balanced) with *why*.
   - **ILAS implications** (what to overweight / underweight and why).
   - **`#fees`**: policy fee stack only from sourced numbers (initial vs accumulation). **Do not invent a typical OCF** (no 1.5–2% placeholder). Add OCF to the hurdle **only** for funds with a verified tearsheet. For the rest, hurdle = policy fee, and write “underlying OCF unknown, actual cost higher”.
   - Sharpe: state rf used (static vs trailing). Flag wrappers with &lt;5 calendar years as **vol/Sharpe biased**.
   - Currency: hedge vs unhedged when known; else `unknown`.
   - Drawdown: do **not** treat calendar-year worst as max drawdown. Intra-year/cross-year troughs are deeper. If no daily NAV, say MDD is unavailable.
   - Do **not** overweight a fund whose Sharpe you have already labelled biased. Drop it or cap at the 10% floor with the bias in the reason cell.
3. **`#universe`** — `<details>` (collapsible; default open).
   - Table of **ALL** funds in the plan (not a shortlist).
   - Columns at least: `code`, `name`, `house`, `type`, `nav`, `ret_1y`, `ret_3y`, `ret_5y`, `vol` or Sharpe if present, `ter`.
   - Header click sorts (vanilla JS, no CDN). Numeric columns sort numerically. `N/A` sorts last.
## The two objects — `picks` is NOT a portfolio

| | `picks` — watchlist | `ages.tabs` — portfolios |
|---|---|---|
| Count | **exactly 10 growth + 10 income = 20** | 6–10 per tab |
| Sizing rules | **none apply** | every weight ≥10%, ≤10 rows, house ≤30% |
| Purpose | the candidate set a client selects *from* | what the client holds |

`report.schema.json` pins `picks.growth` and `picks.income` to `minItems: 10, maxItems: 10`, and `report.js` renders the hardcoded headings 增長型 10 / 收益／防禦 10. The 20 is a fixed shape. Do not shrink it to 6–8 and do not apply §5's sizing rules to it.

4. **`#picks`** — **exactly 10 growth + 10 income.**
   - Each row includes a **`reason`** cell: 1–2 sentences, names the macro theme, why this fund vs peers.
   - "T1" / "high Sharpe" alone is not a reason.
   - Unusable names (biased Sharpe, no 5Y when 5Y is claimed, cash below policy-fee hurdle) are **omitted and replaced from the universe** — never kept with a "不納入組合" footnote. A "replace" step is only meaningful if the list holds more names than any one portfolio consumes.
   - The 20 must be a **strict superset** of every code appearing in `ages.tabs`. Portfolios then size 6–10 of them.
5. **`#ages`** — tab UI, three tabs: `60+`, `40s`, `20–30s`.
   - Only one tab panel visible at a time.
   - Each panel is a **table**: code, name, house, weight %, 1Y, 3Y, 5Y, reason.
     - Weights sum to 100%. No comma-separated allocation sentences.
     - **Max 10 rows. Every weight ≥ 10%.** Caps/floors, not a quota.
     - Pick **as few names as the thesis needs** (typically 6–8). Filling 10 forces equal 10% and is forbidden unless you can justify *each* tenth name.
   - Under the tabs: one line on **why this count** (e.g. "7 names so Japan/AI can be 15–20%").
6. **`#appendix`** — `<details>` (collapsed by default). Title: 附錄／來源.
   - Coverage + COI one-liners at the top of the appendix.
   - **Every URL used in the run** (APIs, product pages, PDFs, FT/Morningstar tearsheets, Fed/ECB, Wikipedia). Grouped lists, full `https://` hrefs, clickable.
   - Plan-level **fund price** page + **factsheet/KFS/brochure** links when known.

## Forbidden substitutes

| Excuse | Reality |
|--------|---------|
| "Macro table is enough" | Need thesis + ILAS implications |
| "Shortlist is the table" | Universe table of every fund is mandatory |
| "The watchlist should stay small" | `picks` is exactly 10 + 10. Portfolio sizing is §5, not §4 |
| "6–8 names is disciplined" | For a portfolio, yes. For `picks`, it is a shape failure |
| "Logic / T1 is the reason" | Reason must cite a macro theme |
| "Three headings = age tabs" | Need tab buttons + one visible panel + tables |
| "I'll paste HTML in chat" | Serve the file; Markdown in chat |
| "Tiny 5% cash sleeve is fine" | Min weight 10%; max 10 names **per portfolio** |
| "Unusable but listed with a footnote" | Omit + replace; footnotes ≠ exclusion |
| "I'll eyeball the counts" | Run `validate_report.py` — it checks 10+10 and every §5 rule |

## Minimal tab + sort behaviour

- Tabs: buttons toggle `.active` on panels; others `hidden`.
- Sort: click `<th data-sort="num|str">`; toggle asc/desc; rewrite `tbody`.
