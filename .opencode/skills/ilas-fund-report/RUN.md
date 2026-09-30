# ILAS report run notes

## Plan identity

### Manulife ARI

- **Alpha Regular Investor (ARI)** shares Manulife `fundslist` **productId=3** (also 11, 15) with Matrix / Alpha.
- Codes are **U**** (MIL wrappers). **D**** codes are a different product (MIP2, productId=21). Do not mix.
- Direct `manulife.com.hk` is often Akamai 403; JSON via `r.jina.ai/https://…`.

### CTF Life Oscar

- Product dropdown value **`OSCAR`**. Closed to new applications. Fund list is the **shared** Cheers Plus / Legend / Legend 2 / We Shine table (`tr[data-prod*=OSCAR]`).
- Codes: **F**** accumulation; **T**** cash-dist (Legend/Legend 2). Filter Oscar via `data-prod`, not “all products”.
- Playwright on `ctflife.com.hk` hits **Alibaba Cloud ESA slider**. webfetch/curl HTML still works.
- **FE Precision Plus** (from `getPricePDF(citicode)` in fund-price HTML):
  `https://datafeeds.feprecisionplus.com/api/funddata/CTFLife/5331e260-6d43-295c-cd1c-dea0faa31e7c?Languages=en-gb&rangename=Range&citicodes=CP70,OK05`
  Returns ISIN + KFS + factsheet URLs. Batch ~25 citicodes.
- Trailing 1/3/5Y + OCF: FT.com `…/tearsheet/performance?s={ISIN}:{CCY}` (`rawFundPerformance`, headers 5y/3y/1y) and summary `Ongoing charge`. HK-domiciled ISINs often miss FT → KFS/factsheet; **annualise cumulative 3Y/5Y**.
- POST `/api/PerformanceData` needs `fund_code` (Server Error without sibling fields). Do not wait on it.
- Oscar Product Guide/KFS **not public** (SFC empty OD). Do **not** copy Legend 2 / We Shine policy fees. Bid-offer 0% is in the shared Investment Guide (Jul 2026 p.7).
- Scratch: `/tmp/opencode/oscar/`. Keep `template.html` `build.py`. Wipe `funds.js` `index.html` `rows.min.json` before rebuild.

## Fees (do not invent OCF)

- Policy fees if the user supplies them (ARI example: Initial Account **3.6%**, Accumulative Account **1.2%**). Label as user-supplied until the offering doc is parsed.
- **No placeholder OCF** (never 1.7% / 1.5–2%). Add OCF only from a named tearsheet ISIN.
- Hurdle for names without OCF = policy fee only, plus “actual cost higher”.

## Watchlist (`picks`) vs portfolios (`ages`) — different objects

| | `picks` | `ages.tabs` |
|---|---|---|
| Count | **exactly 20** = 10 growth + 10 income | 6–10 per band |
| Sizing | **none apply** | ≥10% each, sum 100%, house ≤30% |
| Role | the menu you select *from* | what the client holds |

The 20 is a fixed shape (`report.schema.json` pins each leg to 10; `report.js` renders 增長型 10 / 收益／防禦 10). The thesis picks **which** 20, never **how many**. A 6–8 watchlist is a failure, not restraint — portfolio sizing never applies to it.

Watchlist entries that are unusable (biased Sharpe/vol, no 5Y when 5Y is claimed, cash below the policy-fee hurdle) are **omitted and replaced from the universe**, never left as a "不納入組合" row. Replacement only makes sense because the list is longer than any one portfolio consumes.

## Sizing — applies to `ages.tabs` ONLY

- Max 10 holdings, min 10% each, weights sum to 100%, house ≤30%. Caps, not a quota.
- Pick 6–8 names so weights can be 10–20%. Filling 10 forces equal 10%.
- Do not apply these to `picks`.

## Validate before serving

```bash
python3 validate_report.py report.json --csv /path/to/ari_enriched.csv
```

Enforces 10+10 picks, pick reasons that name a theme, the ≥10%/sum-100%/house-≤30% portfolio rules, watchlist-is-superset-of-portfolios, universe vs `meta.fund_count`, and Sharpe recomputability from the published vol. **Exit 1 = do not serve.** Add the `vol_3y_used` / `vol_5y_used` columns to the CSV so the Sharpe check has a real denominator.

## Workspace (every run)

Scratch dir example: `/tmp/opencode/ari/`

**Delete before fetch:**

- `en.txt` `zh.txt` `en.json` `zh.json`
- `rows.min.json` `funds.js` `index.html`

**Keep:** `template.html` `build.py`

Then fetch APIs → rebuild rows → build HTML → serve. Last-run files must not leak into this run.

## Pipeline (any ILAS)

Execution tree is in each skill's Execution section (`divide-and-conquer`). This list is dependency order, not permission to do every step inline.

1. Discover (web + XHR first) → `source_map.json`
2. Extract → `funds.json` (gate ≥90%)
3. Macro → `macro_context.json`
4. Analyse → `report.json` (**picks exactly 10+10**; ages 6–10, ≥10%, sum 100%, house ≤30%)
5. **`python3 validate_report.py report.json --csv …` — must exit 0**
6. Copy `template.html` + `report.js` from this skill; `index.html` fetches `report.json`
7. Serve the directory; Markdown + URL in chat

Do not inject `@@GROWTH@@` into HTML. Swap JSON = new plan.

## HTML

Serve the **directory** on LAN/tailnet (needs `report.json` beside `index.html`). Markdown + URL in chat only. Contract: `html-report-contract.md`.
