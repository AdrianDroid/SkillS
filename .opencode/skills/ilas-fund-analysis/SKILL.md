---
name: ilAS-data-extract
description: >-
  Use when the user wants to extract fund data (NAV, returns, TER, volatility,
  Sharpe ratios) from an ILAS (Investment-Linked Assurance Scheme) plan's fund
  price page. Triggers on "get fund list", "extract NAVs", "find TERs", "scrape
  the ARI fund prices", "data for [plan name]", "fund returns for [plan name]".
  Output is an enriched CSV with returns, vol, Sharpe, TER, region, sector, type.
  DO NOT use for analysis, allocation, or reporting — that's ilas-fund-report.
  DO NOT use for macro research — that's macro-research.
---

# ILAS Fund Data Extraction — Enriched CSV Production

## Overview

Extract complete fund data from an ILAS plan's fund price page. Produce an enriched CSV ready for `ilas-fund-report`. Do not ask the user for direction mid-extraction. First action is the execution tree below — not a search.

**Critical rule #1 (COVERAGE GATE — HARD STOP): the run is NOT complete until ≥90% of funds have COMPLETE data (1Y + 3Y + 5Y returns + TER + region/sector/type all populated).** Recompute the metric after EVERY pass. Below 90% → keep working the source layers; do NOT write the final output. Still short after L1–L6 → produce a coverage report naming the missing funds and the sources tried, and tell the user: "Coverage is X%. I cannot proceed with report generation. Here are the missing funds and the sources I tried."

**Critical rule #2: an output where >5% of performance/cost fields are N/A is USELESS. Exhaust all data-mining approaches before accepting an empty field.**

**Critical rule #3 (TER as hard gate): TER/OCF is mandatory for every fund. ≥90% TER coverage required. <90% → stop and ask the user for factsheets, KFS, fund detail pages. <70% → halt.**

**Critical rule #4 (REPORT GATE): you MUST NOT invoke `ilas-fund-report` or generate any report if coverage <90% or if `validate_funds.py` does not exit 0. Fix the data first.**

**Critical rule #5 (EXECUTION TREE): no search, navigate, fetch, or scrape until the tree in Execution is written in the chat. Parent coordinates; the parent does not do leaf work.**

## Execution — REQUIRED SUB-SKILL

**REQUIRED SUB-SKILL:** divide-and-conquer. Load it before any data tool call.

**Violating the letter of this section is violating the spirit of this section.**

Autonomous means do not ask the user. It does not mean the parent scrapes.

```
WAVE 1 (one unit): discover plan → source_map.json + fund-universe table. Done-when: saturation checklist met.
WAVE 2 (parallel, one task per fund house): that house's L1 XHR/API only. Done-when: 1/3/5Y+TER or a documented block with the HTTP/error.
WAVE 3 (after WAVE 2, parallel, incomplete houses only): one task per failed house or per aggregator (L2–L6). Done-when: fields filled or every layer tried and recorded.
INTEGRATE (parent only): coverage + TER gates, merge enriched CSV, then `python3 validate_funds.py funds.csv`. **Exit 0 is required before the CSV is handed to `ilas-fund-report`.** Parent does not search, scrape, or parse fund pages.
```

Leaf prompt is self-contained: use Playwright/XHR or the named fallback layer; if you have no browser tools, return `blocked` — do not invent numbers. `subagent_type`: `general`. All WAVE 2 `task` calls go in one message.

Human forbade sub-agents: still write this tree. Run waves yourself in dependency order. Units stay separate. Do not collapse houses into one pass.

Extract-only: do not invoke `macro-research` or `ilas-fund-report`. If the user asked for a report, `macro-research` is a sibling of WAVE 2, not a step after the CSV.

| Excuse | Reality |
|---|---|
| Skill says start with web search | That search is WAVE 1's leaf. Tree first, then dispatch WAVE 1. |
| User is waiting / don't over-engineer / deadline | That is why WAVE 2 houses run at once. |
| No sub-agents | Still write the tree. Run waves yourself. Do not merge units. |
| I already know productId / jina / the API | That is the WAVE 1 brief. It does not skip the tree or Stage 1 rediscovery. |
| Execute autonomously means I scrape | Autonomous = don't ask the user. Parent integrates. |
| Sub-agents can't run Playwright, so I will | Dispatch anyway. Prompt requires browser tools. `blocked` returns; parent does not scrape that leaf. |
| I'll just do this one house; I have the context | One house is still a leaf. |

## Parameter Extraction

| Parameter | Type | Required | Default |
|-----------|------|----------|---------|
| `ilas_plan_name` | String | Yes | — |
| `target_funds` | List | No | All available funds |
| `risk_tolerance` | String | No | `Moderate` |
| `time_horizon` | String | No | `7+ yrs` |
| `currency_preference` | String | No | `USD` / `HKD` |

## Stage 1 — Discover the plan (any ILAS)

**This stage is WAVE 1's leaf.** If the execution tree is not already in the chat, stop and write it. The parent does not run this search.

Do **not** start from a hardcoded adapter (Manulife `productId`, CTF `OSCAR`, …). Those are examples Stage 1 should **rediscover**.

1. Web search EN + 中文: `"[plan]" ILAS`, `"[plan]" 投資相連保險`, fund price / 投資選擇 / KFS PDF.
2. Open the official fund-price (and info) page. **Preferred:** Playwright intercept XHR/fetch (`application/json`) → replay the API for the full universe.
3. If no JSON / blocked (Akamai, ESA slider, 403): HTML tables, jina, offering PDFs, FE/citicode, FT by ISIN, aggregators. XHR is one path, **not the only path**.
4. Write `source_map.json` (schema in `ilas-fund-report/schemas/source_map.schema.json`): `plan`, `provider`, `product_code`, `pages[]`, `apis[]`, `docs[]`, `blockers[]`.
5. Then extract into `funds.json`. Coverage ≥90% or stop.

## Core Principle: API-First Data Extraction

**Prefer JSON APIs over HTML.** Launch headless, intercept ALL XHR/fetch responses filtering for `application/json` / `application/javascript`, identify the endpoints serving fund list, fund detail and fund fees, then replay them directly with `webfetch` and parse exact values. This is orders of magnitude faster and more reliable than HTML scraping: one endpoint often serves every fund, JSON is machine-readable, APIs change less often than layouts, and a house can be batch-queried in a single script.

## Phase 1: Fund Universe Identification — FIND EVERY FUND IN THE PLAN

**CRITICAL RULE:** find ALL funds available in this specific plan. ILAS universes range from ~30 to 150+ funds. Do NOT assume a number — exhaust every method until no new fund can be discovered.

### 1A: Identify the Plan

Determine: **Provider** (Manulife, Generali, AXA, Aviva, Prudential, …), **plan name** (exact English and Chinese), **product/plan code** if available, and **plan type** (regular premium, single premium, lump sum). Search `"[Plan Name]" "[Provider]" ILAS"` and `"[Plan Name]" 投資相連保險"` — HK providers often market ILAS plans under different Chinese names.

### 1B: Discover the Fund Universe — Use ALL Methods

For each search method, track which funds it discovers. Stop when multiple methods return the same set (saturation).

| Method | What to Search | What to Expect |
|--------|---------------|----------------|
| **Provider fund price page** | The provider's fund price / fund choice page for ILAS, in both the English and Chinese plan name | Full fund list with NAV prices |
| **Investment Choice Brochure PDF** | `"[Plan Name]" investment choice brochure PDF`, `"[Plan Name]" 投資選擇` | Official fund list with all fund names |
| **Plan brochure / product sheet** | `"[Plan Name]" brochure PDF`, `"[Plan Name]" product sheet` | Full plan description with fund list |
| **Fund change announcements** | `"[Provider]" ILAS fund change announcement`, `"[Provider]" 基金變更` | Specific fund additions/deletions; also the wind-up evidence for D6 |
| **SFC authorized fund list** | `apps.sfc.hk/productlistWeb/searchProduct/ILAS.do` — find the plan code | Plan registration info, possibly the fund list |
| **API/XHR interception** | Playwright on the provider's fund page, intercepting JSON fund-list APIs | Full fund universe in one API call |
| **Aggregator / comparison sites** | `"[Plan Name]" fund list`, `"[Plan Name]" fund choices` | Curated fund lists — verify freshness first (D5) |
| **Web search — EN + 中文** | `"[Plan Name]" fund ILAS`; for HK plans also `"[Plan Chinese Name]" 基金` | Fund options, Chinese forum discussions |
| **Fund house search** | For each house mentioned in any result: `"[Fund House]" "[Plan Name]"` | Additional funds from that house |

### 1C: Identify Fund Houses in This Plan

From the funds discovered, compile the list of fund houses this specific plan offers. For each fund discovered, record which house manages it. If you find a fund house in any search result that hasn't been checked yet, search for more funds from that house in this plan.

#### Deriving the house (D4)

**The plan platform is not a fund house.** A provider's fund-list API labels **every** row with the plan sponsor — `platformName` was the plan name for all 108 rows of a real run (verified Sep 2026). Trusting that field labels the entire universe as one house.

- Derive `house` from the **underlying fund name / share class**, never from `platformName` / `providerName`.
- An internally managed line with no underlying is labelled `INTERNAL — <sponsor>` so it can never be confused with a rival asset manager. Four internally-managed lines were written as `house="Manulife"`, indistinguishable from Manulife Investment Management.

### 1D: Fund Universe Completeness Check

- **[ ] No new funds discovered after trying 3+ methods?** (saturation reached)
- **[ ] Provider's official fund page/PDF consulted?**
- **[ ] At least one PDF/factsheet source checked?**
- **[ ] If HK plan: Chinese name searched?**
- **[ ] SFC product list checked?**
- **[ ] All fund houses mentioned in search results individually searched?**

**If you have any evidence that more funds exist (e.g., a fund house appears in the plan's brochure but none of their funds are in your list), continue searching. Do NOT proceed until you've exhausted all discovery methods.**

Create a fund list table with: Fund Name | Fund House | ISIN | Asset Class | Currency | Morningstar ID (if found) | Source (which method found this fund).

### 1E: Liveness and wind-up (D6)

**A provider's own liveness flag is not a wind-up check.** Two funds announced for **compulsory redemption and termination on 2026-10-30** (Manulife IM HK notice dated 2026-08-17, Trust Deed cl. 28.3(b), sub-scale plus underlying-fee inflation) while the plan API still returned `fundSuspendInd = "N"` and a live NAV for both (verified Sep 2026).

- Check house notices, KFS/prospectus, and provider fund lists for compulsory redemption, termination, or merger. Do not rely on the plan API's `fundSuspendInd` / switch / availability flag.
- Record where you confirmed the fund is still open, in `liveness_checked`.
- **Record both directions.** A separate run found a false positive of the opposite kind: a fund flagged suspended at the wrapper with no closure notice anywhere, a live factsheet, and continuous pricing. `liveness_checked` must say what you checked and what you concluded, not just "OK".

### Phase 1.x: TER/OCF Capture — MANDATORY, BEFORE RETURNS EXTRACTION

**TER/OCF is the #1 hardest field to extract and the #1 field that breaks cross-fund comparison. Capture it early and verify it.**

For each fund house, extract TER/OCF (Ongoing Charges Figure / Total Expense Ratio) using these layers in order:

| Layer | Source | Method | Expected TER Fields |
|-------|--------|--------|---------------------|
| **T1** | Fund house website | XHR interception on fund detail page | OCF, TER. A management fee belongs in `wrapper_fee_pct`, not `ter` |
| **T2** | Fund factsheet PDF | Download + extract from "Fund Expense" or "Charges" section | OCF, TER, total cost |
| **T3** | HK aggregators | FSMOne, ETNet fund detail pages. HKET only after the D5 freshness check | OCF |
| **T4** | Morningstar HK | `morningstar.hk` fund page → "费用" tab | TER, transaction fee |
| **T5** | FT.com | `markets.ft.com/data/funds/tearsheet/summary?s=[ISIN]:USD` | OCF |
| **T6** | Plan documents | Investment Choice Brochure PDF, fund change announcements | TER for internal funds |
| **T7** | User-provided | Ask user to upload factsheet PDFs or KFS (Key Features Statement) | All fees |

**TER extraction rules:**
- Prefer OCF over TER if both available, and record which measure you used in `ter_basis`. They are **not interchangeable**: OCF excludes transaction costs, TER does not.
- **A management fee is not a partial TER.** Record it in `wrapper_fee_pct`, never in `ter` — see the wrapper-fee trap below.
- Record the source for each TER value in `ter_source`, naming a real document or endpoint
- If TER is genuinely unavailable after T1-T6, set `ter = NULL`, `ter_basis = "unavailable"`, `ter_source = "unavailable"` — do NOT guess
- Internal funds (e.g., Manulife Select series): check the plan's Investment Choice Brochure PDF (T6) first

#### The wrapper-fee trap (D2)

A provider's fund-detail API returns `details.managementFee` as a string like `"0.0175 per annum"` on **every** investment choice. It is the plan sponsor's investment-management fee on the choice, not the fund's ongoing charge. Substituting it for `ter` invents the single number the whole downstream comparison rests on.

- Write it to `wrapper_fee_pct`. **Never** write it to `ter`.
- **Conflation signature — the mechanical check:** `ter == wrapper_fee_pct`, or a `ter_source` that resolves to a bare fee-field name with no document/endpoint locator. Both fail `validate_funds.py` (rules D2, D2d).
- A `ter_source` that names a real document or endpoint passes even when it also mentions the management fee.
- **Genuine exception — state it so the rule is not over-applied:** an internally managed fund may have *only* an all-in plan fee. The Manulife ARI brochure p.59 discloses 1.70% p.a. and states it already includes the underlying managers' fees. That is a legitimate all-in cost, not an OCF — record it as all-in and label it, never as `ter` with basis `OCF`.

**TER quality gate after extraction:**
```
TER coverage = # funds with TER populated / total_funds × 100
```
- ≥ 90% → proceed
- 70-89% → continue to T7 (ask user for factsheets)
- < 70% → halt. TER data is insufficient for fair analysis.

### Phase 1.y: MyBrowser MCP Fallback — When Headless Fails

**If Playwright headless is blocked on the primary source (Akamai 403, Cloudflare, `ERR_NETWORK_CHANGED`), use MyBrowser MCP.**

1. Detect failure: HTTP 403, `ERR_NETWORK_CHANGED`, "Just a moment...", `ERR_ABORTED`
2. Prompt the user: *"Headless scraping is blocked on [site]. Please enable MyBrowser MCP (browser extension) so I can capture data directly from your browser. Once enabled I'll continue."*
3. Once enabled: `mybrowser_browser_navigate` → `mybrowser_browser_snapshot` to confirm load → `mybrowser_browser_network` (start_capture → navigate → get_log) to intercept XHR → `mybrowser_browser_extract` / `mybrowser_browser_evaluate` for structured capture.

**MyBrowser MCP is the LAST RESORT before asking the user for manual data entry.** Try all other layers (T1-T6, L2-L6) first.

## Phase 2: Per-Fund-House Playwright XHR Interception (PRIMARY — MANDATORY)

**This phase is WAVE 2.** One house per `task`, all houses in one message. The parent does not run the Playwright script.

**CRITICAL RULE:** For EVERY fund house in the plan, you MUST write and execute a Playwright XHR interception script on their HK fund page. Save each script to `/tmp/opencode/`. Do NOT skip this step. Do NOT fall back to web search. Only after XHR interception fails on a site may you use fallback sources.

### Procedure for Each Fund House

1. Navigate to the house's HK fund price/performance page (URLs below)
2. Intercept ALL XHR/fetch responses, filter for JSON
3. Replay the discovered API for ALL funds from this house
4. Parse JSON for trailing returns, OCF, NAV, ratings
5. Save the script to `/tmp/opencode/xhr_[house].js` and captured JSON to `/tmp/opencode/xhr_[house]_capture.json`

### Playwright Template — Use This for Every Fund House

```javascript
const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    viewport: { width: 1920, height: 1080 }, locale: 'en-US'
  });
  const page = await context.newPage();
  const captured = [];
  page.on('response', async (r) => {
    if (!(r.headers()['content-type'] || '').includes('json')) return;
    try { captured.push({ url: r.url(), status: r.status(), data: await r.json() }); } catch (e) {}
  });
  await page.goto('TARGET_URL', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(5000);
  fs.writeFileSync('/tmp/opencode/xhr_captures.json', JSON.stringify(captured, null, 2));
  console.log(`Captured ${captured.length} XHR responses`);
  await browser.close();
})();
```

### Concrete Fund House Targets — see `house-access.md`

**Do not trust a "blocked" verdict without re-testing.** The table this replaced marked 13 of 16 houses "blocked"; a live run (verified Sep 2026) reached **16 of 24**. Nearly every "block" was a typo'd/legacy domain, a wrong URL path, **bundled Chromium crashing** (which reports as `ERR_NETWORK_CHANGED` / `ERR_ABORTED`, *not* bot detection), or a consent gate a real browser clicks past.

**Order of attack, every house, every run:**

1. Use the corrected URL in **`house-access.md`** — it has the working targets, the live API endpoints, and the share-class traps that produce wrong numbers rather than mere blocks.
2. `chromium.launch({ channel: 'chrome', headless: false })` under `xvfb-run` + `navigator.webdriver` override. Bundled Chromium is the most common false negative.
3. Bare domain 404s? Try the **global root** (`.com` vs `.com.hk`).
4. Click through consent/disclaimer gates. `page.request.get()` inherits the 403; **in-page `window.fetch()` under real Chrome returns 200**.

Houses confirmed reachable Sep 2026: AllianzGI, Franklin Templeton, JPMorgan, Fidelity, Manulife HK, Manulife IM, Ninety One, Schroders, Invesco, Amundi, BNP Paribas AM, AllianceBernstein, Value Partners, Barings, T. Rowe Price, First Sentier, Janus Henderson, Hang Seng IM, PIMCO, Capital Group, ChinaAMC. Confirmed hard: UBS (Akamai 403 behind a role gate — use issuer KIDs via `api.fundinfo.com`), Pictet (404 + hCaptcha), BlackRock (path + T&C gate).

### Real-World API Discovery Notes (verified Sep 2026)

#### AllianzGI HK — reachable, but no returns and no OCF
```
API (multi-fund): GET /en-HK/api/funddata/multi/funds/{sitecoreId}/{datasourceId}
  -> ~412 funds, ~687KB
  Real fields: FundName, Isin, BaseCurrency, Nav, NavDate, CALENDAR_YEAR_<YEAR>
  NO TrailingReturn* fields. NO OCF. NO Morningstar. NO SRRI.
  YEAR_INTERVAL_1/3/5_MONTH_ULTIMO  = 1/3/5 MONTHS, not years
  Values are HTML-wrapped: '<span class="up--color">34.90 %</span>' -> regex-strip
  OCF/TER: fund DETAIL page (server-side rendered, has "Total Expense Ratio"),
           or the per-fund factsheet under /documents/{guid}/{ISIN}
```
**How to use**: Navigate once, capture the GET response, parse it for the ISINs needed. The max 3Y-equivalent figure in the payload observed was 29.85% p.a. — that field is 36 months, not 3 years. Never use it to validate a plan's 3Y/5Y returns without an ISIN match.

#### Franklin Templeton HK — GraphQL API Fully Working
```
Target: https://www.franklintempleton.com.hk/en-hk/our-funds/price-and-performance/mutual-funds
- Must first accept role selector ("Individual Investor") + welcome dialog ("Accept") + cookie consent ("Ok")

API: POST /api/pds/price-and-performance (GraphQL)
  op=FundOverviewSummary -> ONGOING_CHARGE_RATIO = THE OCF (as-of dated)
  op=IntlCorePpss        -> charges.prfrmncefee / fundadminfee / annchrg / expratnet
                            annchrg = MANAGEMENT CHARGE, not the OCF
                            Proof of the distinction: one fund had OCF 1.37%, annchrg 1.05%, expratnet 1.39%
  op=IntlIndentifiers    -> ISIN, Bloomberg ticker, share class codes (199KB)
  op=CommonPerformance   -> no trailing returns for FT funds (only YTD on the live site)
  op=IntlRatings         -> Morningstar Overall Rating, MS Rating 3/5/10Y, MS Category (142KB)
  op=CalendarYearMonthly -> calendar year returns monthly
  op=CalendarYearQuarterly -> calendar year returns quarterly
```
**How to use**: the page fires these automatically; capture the bodies. `FundOverviewSummary` + `IntlRatings` + `IntlIndentifiers` give the OCF, Morningstar stars, and ISIN. `charges.annchrg` is the manager's charge — writing it to `ter` is defect D2.

#### Symptom → most likely cause (verified Sep 2026)

**Read this before concluding anything about bot protection.** The previous version of this
table listed SSL expiry, 404-behind-headless and network intercepts as site properties.
Every one of those was wrong: they were artefacts of a headless-Chromium build, a typo'd
TLD, or a wrong path. None of these seven houses actually blocks a real browser.

| Symptom | What it usually actually is | Verified example |
|---------|----------------------------|------------------|
| `ERR_NETWORK_CHANGED`, `ERR_ABORTED` | **Bundled Chromium failing on a GPU-sandbox host.** Not a block. Use `channel: 'chrome'` | JPMorgan, Schroders, Janus, Manulife IM — all reachable |
| `SSL EXPIRED` / `ERR_CERT_*` | The **wrong host**. Try the global root | AB: `.com` root valid. Value Partners: `vp.com.hk` dead, `valuepartners-group.com` valid |
| `ERR_NAME_NOT_RESOLVED` | A **typo'd or legacy TLD** | `bnpparibas-am.com.hk` has zero DNS records; `.com` works |
| 404 on every fund URL | **A guessed path**, or a wrong share-class slug | JPMorgan `/products/` is a 304-byte stub; PIMCO `eg-usd-…` does not exist, `e-usd-…` does |
| 403 on `page.request.get()` | **That call bypasses the browser stack.** In-page `window.fetch()` returns 200 | Fidelity International |
| 403 everywhere | Genuine edge protection, or a **role/cookie gate after a 200** | Manulife HK (Akamai — beat by replaying real-Chrome cookies through curl); UBS (Akamai — no way through, use issuer KIDs) |
| A consent/splash gate | A **button disabled until you scroll the disclaimer** | Invesco's Confirm; BlackRock's T&C modal |

**Escalation order when genuinely blocked:** L2 aggregators (freshness-checked) → L3 stealth (real Chrome, mobile emulation, curl cookie replay, API-host probe) → L4 Wayback → L5 plan documents → L6 external tearsheets. But exhaust §"Concrete Fund House Targets" **first** — the cheap causes above resolve most cases.

### Special Case: CTF Life (Chow Tai Fook)

Playwright on `ctflife.com.hk` is often blocked by **Alibaba Cloud ESA slider**. Fund-price HTML is still fetchable (curl/webfetch). Vue `GET /api/PerformanceData` is not the path; POST with `fund_code` 500s.

**CTF Life extraction procedure:**
1. Parse the fund-price **HTML table**: `data-prod` (Oscar=`OSCAR`), `data-comp`, `data-cat`, code, `getPricePDF('CITICODE')`, NAV.
2. Filter the plan with `OSCAR` in `data-prod` (shared list with Cheers Plus / Legend / We Shine). Drop Legend-only T-codes.
3. Batch FE Precision Plus for ISIN + KFS + factsheet:
   `https://datafeeds.feprecisionplus.com/api/funddata/CTFLife/5331e260-6d43-295c-cd1c-dea0faa31e7c?Languages=en-gb&rangename=Range&citicodes=`
4. FT.com by `{ISIN}:{CCY}` for trailing returns (`data-mod-config` rawFundPerformance) and ongoing charge. HK ISINs often 404 on FT → KFS OCF + factsheet cumulative 1/3/5Y (**annualise** 3Y/5Y).
5. **Do NOT generate a report with only current prices — that is 0% coverage**

Oscar (~180 F-codes) houses: BlackRock, abrdn, Allianz, Schroder, Barings, BNP, Fidelity, JPMorgan, Invesco, FT, Ninety One, PIMCO, T. Rowe, Value Partners, Wellington, others.

### After Discovery: Replay APIs Directly

Once you find an endpoint pattern for a fund house, batch-extract data for ALL their funds in one script: `fetch` the discovered URL per fund ID, `res.json()`, then read the exact field (`data.performance.oneYearReturn`, etc.). Save the script and its output per house.

### Mandatory Checklist Per Fund House

- [ ] Script written, saved to `/tmp/opencode/xhr_[house].js`, and executed?
- [ ] XHR responses captured; JSON API found and replayed for the whole house?
- [ ] If no JSON API, HTML parsing attempted on the fund page?
- [ ] Extracted 1/3/5Y returns, rating, OCF, risk rating?
- [ ] Results saved to the house's output file?

## Phase 2B: Fallback Source Layers (escalate until coverage ≥ 90%)

**Rule: After EVERY layer, recompute the coverage metric (Phase 3). Below 90% → move to the next layer. Do NOT stop after one pass.**

| Layer | Method | Targets | When to Use |
|-------|--------|---------|-------------|
| **L1** | Fund house XHR interception + API replay | Per-house HK sites (Phase 2) | Always first |
| **L2** | HK aggregator portals — XHR intercept + API replay | HKET invest.hket.com, ETNet fund.etnet.com.hk, FSMOne fsmone.com.hk, AASTOCKS aastocks.com.hk | L1 failed or partial |
| **L3** | Stealth re-attempt on blocked houses | Every house that failed L1/L2 (see stealth template) | Any house marked "blocked" |
| **L4** | Wayback Machine for dead/SSL-expired sites | web.archive.org snapshots of fund pages + factsheet PDFs | Sites with SSL expired / DNS dead / 404 |
| **L5** | Plan's own documents | Investment Choice Brochure PDF, plan fact sheet, fund change announcements | Internal funds + remaining gaps |
| **L6** | External tearsheets (per fund) | Morningstar, FT.com, Yahoo, Endowus, PDF factsheets, fundinfo.com | Last resort, per missing fund |

### Layer L2: HK Aggregator Portals (HIGH VALUE — do not skip)

Aggregator fund price pages cover many fund houses in one site, are rarely bot-blocked, and are JSON-API-backed. **The source that enumerated the fund universe will usually have a performance API too** — but verify it is current first.

Targets: `invest.hket.com`, `fund.etnet.com.hk`, `fsmone.com.hk`, `aastocks.com.hk/en/funds/`.

**Freshness check (D5, before trusting a fund-price page).** `invest.hket.com` returned a **frozen 2021-03-26 snapshot** — 95 rows, every price stamped 26/03/21, zero ISINs, and delisted funds still listed (verified Sep 2026). A prior run took its whole universe and fund count from that page and produced a dataset that self-reported 4% complete. **This applies to plan and provider fund-price pages too, not just third-party aggregators** — a provider table is equally capable of being stale.

- Assert the as-of date of what the aggregator *actually returns* (price dates, "as of" header, API field), not the date of the page you requested.
- Sanity-check the count against a second source. A stale snapshot still enumerates a full-looking universe — **a plausible fund count is not evidence of currency**.
- Never accept a prior run's fund count as gospel. Re-derive saturation every run, and record the verified as-of date in `freshness_checked` on every aggregator-sourced row.

Procedure: write a Playwright XHR interception script per aggregator (save to `/tmp/opencode/xhr_aggregator_*.js`), search for each missing fund, capture the JSON API, replay it for all missing funds. Batch by aggregator, not per fund.

### Layer L3: Stealth Re-Attempt on Blocked Houses

**"Blocked" ≠ "exhausted".** For every house that failed L1, re-attempt with these techniques in order, then replay the API with curl using the session cookies:

1. **Real Chrome channel + webdriver override** (defeats basic Akamai/Cloudflare headless detection):
```javascript
const browser = await chromium.launch({
  channel: 'chrome',                 // real Chrome, not bundled Chromium
  headless: false,                    // headed; on a server use `xvfb-run node script.js`
  args: ['--disable-blink-features=AutomationControlled']
});
const context = await browser.newContext({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36', locale: 'en-US', timezoneId: 'Asia/Hong_Kong' });
await context.addInitScript(() => {
  Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
  window.chrome = window.chrome || { runtime: {} };
});
```
2. **Mobile device emulation** — many Akamai configs exempt mobile traffic: `browser.newContext({ ...devices['iPhone 13'] })`
3. **Cookie/session replay via curl**: export `context.cookies()`, then `curl -H 'User-Agent: ...' -H 'Accept: application/json' -b 'cookies.txt' -H 'Referer: <the page>' <API URL>` — API hosts are often less protected than HTML pages.
4. **Bypass path via API host**: even when HTML is 403, probe the API endpoint host directly (e.g., `api.fidelity.com.hk`, `prices.manulifeim.com.hk`) — check DNS and common API paths.
5. Only if ALL of 1–4 fail for a house may you drop L1 for that house and go to L2/L4 for its funds.

### Layer L4: Wayback Machine (dead / SSL-expired / DNS-failed sites)

For sites like AB HK, Value Partners HK, BNP Paribas AM HK:

- Page snapshots: `web.archive.org/web/2024*/{original-url}` — pick the newest
- PDF factsheets: `web.archive.org/web/{timestamp}if_/{factsheet-url}.pdf` — `if_` returns the raw original file
- Fund data pages render server-side, so cached HTML still holds the performance tables
- Search by fund name: `web.archive.org/web/*/vp.com.hk/*`

### Layer L5: Plan's Own Documents (internal funds)

**Internal funds are NOT "no public data" until the plan's own documents have been checked.** The operator publishes OCF and fund details for internal funds in the Investment Choice Brochure / 投資選擇手冊 PDF, the plan fact sheet / product brochure, fund change announcements, and the provider's public ILAS platform pages. Search `"[Plan Name]" investment choice brochure PDF`, `"[Plan Name]" 投資選擇手冊`, `"[Provider]" ILAS fund change announcement`.

### Layer L6: Per-Fund External Sources (in order, only for funds still missing data)

**Source A — Fund Manager Pages: Direct HTML Scrape.**

If XHR found no API, read the HTML fund page directly for each fund from this house. The house's fund-detail URL shape is listed in the fund-house table above (Phase 2); the recurring patterns are:

- **BlackRock**: `https://www.blackrock.com/hk/en/products/[PRODUCT_ID]` — SSR HTML with performance tables
- **Fidelity**: `https://www.fidelity.com.hk/en/funds/[FUND-NAME]` — factsheet performance
- **Manulife IM**: `https://www.manulifeim.com.hk/en/funds/fund-prices.html` (may be 403)
- Anything else: `{fundhouse}.com.hk/{language}/fund-literature/{fund-name}.pdf` for the factsheet

**Source B — Morningstar HK.**

`https://www.morningstar.hk/hk/report/fund/performance.aspx?t=0P0000XXXX` — star rating, trailing returns, category, OCF. Search: `site:morningstar.hk "[Fund Name]" "[Fund House]"`.

**Source C — FT.com (by ISIN).**

`https://markets.ft.com/data/funds/tearsheet/summary?s=[ISIN]:USD` and `.../performance?s=[ISIN]:USD` — exact trailing returns (1/3/5yr), quartile ranking, OCF, fund size, launch date.

**Source D — Yahoo Finance (by Morningstar ID).**

`https://finance.yahoo.com/quote/0P0000XXXX/` — YTD, 1/3/5yr returns, Morningstar Risk Rating, expense ratio.

**Source E — Endowus / Aggregators.**

`https://endowus.com/en-hk/investment-funds-list/[fund-name]-[ISIN]`; search `endowus.com "[Fund Name]" performance`.

**Source F — PDF Factsheets.**

Search `"[Fund Name]" factsheet PDF Hong Kong"` or `api.fundinfo.com "[Fund Name]"`; `https://api.fundinfo.com/document/[HASH]/MR_en_en_[ISIN]_YES_[DATE].pdf?apiKey=[KEY]`


## Phase 3: Coverage Gate — MANDATORY, NEVER SKIP

After every extraction pass (Phase 2 → L1/L2/L3/L4/L5/L6), compute:

```
complete   = # funds with ALL of [1Y return, 3Y return, 5Y return, TER, region, sector, type] populated
coverage % = complete / total_funds × 100
```

**GATE: `coverage % ≥ 90%` is REQUIRED before producing the final output.** A row nulled for an `insufficient_history` sentinel (D1) counts as **incomplete**: nulling is the honest reading, not a coverage regression to be excused, and clearing the gate now requires backfilling.

| Coverage | Action |
|----------|--------|
| ≥ 90% | Proceed to analysis and report |
| 70–89% | NOT DONE — continue to the next source layer (L2 → L3 → L4 → L5 → L6), targeting ONLY the missing funds. Recompute after each layer. |
| < 70% | CRITICAL FAILURE of extraction — go back and redo Phase 2 from scratch with stealth techniques (L3) on ALL houses before touching L6 |

**Loop until one of:** coverage ≥ 90%, OR every missing fund has a documented exclusion reason naming WHICH sources were tried and WHY they failed (L2, L3, L4, L5 must each have been attempted for that fund — one source failing is never a valid exclusion).

**Include this report in the output:**

```
## Data Coverage Report
| Status | Funds | % |
| Complete (1/3/5Y + TER + region/sector/type) | n | x% |
| Partial / Missing | n | x% |
COVERAGE: x% — GATE ≥ 90%: PASS/FAIL

## TER Coverage Report
| TER populated | n | x% |   | TER unavailable | n | x% |
TER GATE ≥ 90%: PASS/FAIL
```

## Data Extraction Rules

- **No `~` (approximate) values.** Extract exact percentages (e.g., `5.37`, not `~5.4%`).
- Use most recent data available; note the date.
- Use trailing annualised returns (1yr, 3yr, 5yr) — never calendar-year or YTD figures in a `ret_Ny` field.
- **TER standardisation**: Record TER in the output. The analysis layer (`ilas-fund-report`) will standardise all returns to gross-of-TER for fair comparison. Your job is to extract the TER accurately.

## Sentinels, nulls, and backfill provenance (D1)

`0.0` is a **missing-data sentinel**, not a 0% return. 32 of 108 fund-periods in a real run returned `y3`/`y5 == 0.0`; all 32 belonged to a share class whose NAV history started *after* the lookback date. Published as-is, every recently-launched class is ranked catastrophic.

- When a trailing-return field is exactly `0.0`, compare the class's NAV-tracking-start / launch date with the lookback date. A real 0% is possible and still needs a flag; `0.0` is never silently publishable.
- **Class too young:** `ret_3y = null`, `ret_3y_flag = "insufficient_history"`, `ret_src_3y = "insufficient_history"`.
- **Underlying fund exists:** backfill its trailing 3Y/5Y by ISIN, set `ret_src_3y = "underlying_fund"`, and state the basis — net of that fund's own OCF, **not** net of the plan wrapper.
- **Never** interpolate, and **never** back-extrapolate a 3Y/5Y from the 1Y.
- `ret_src_*` must be one of `plan_share_class` | `underlying_fund` | `insufficient_history` | `not_covered` | `unavailable`. Every multi-period return declares its provenance (D1b).

**Gate interaction:** a nulled sentinel counts as an **incomplete** row for the ≥90% coverage gate. Nulling is not a coverage regression to be excused — it is the honest reading, and clearing the gate now requires backfilling.

## Volatility, Sharpe, and basis matching (D3)

A Sharpe's numerator and denominator must be the same fund **and** the same window. A house-sourced vol overrode the plan vol, so three funds published a Sharpe that divided an underlying-fund return by a plan-share-class vol, or the reverse. In all 108 rows the published Sharpe could not be recomputed from the published columns; one fund was overstated by 67% (vol 10.63 used vs 17.77 published).

- Compute the return and the vol for a given horizon **from the same price-history series over the same window**. A cumulative return field sourced separately from the vol is not a matched pair.
- If a return is backfilled from the underlying fund, its vol must be the underlying fund's for the same window.
- If no house vol is published for that window, use the plan vol **and** flag the mix in `sharpe_basis_flag` — never silently mix.
- **Hard requirement:** the published Sharpe must be recomputable from the published columns — `sharpe_Ny = (ret_Ny_gross − rf) / vol_Ny_used`. Publish the vol you actually divided by.
- `vol_annual` is the **trailing-3Y** vol, not a 1Y figure.

## Output CSV Schema

The output must be an enriched CSV with these columns. `validate_funds.py` fails the run (exit 1) on any violation of R0, D1, D1b, D2, D2b, D2c, D2d, D3, D3b, D3c, D4, D5, D6, R9.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `code` | String | Yes | Fund code (e.g., UIG01) |
| `name` | String | Yes | Fund full name |
| `house` | String | Yes | Fund house, derived from the underlying fund — never the platform name (D4). `INTERNAL — <sponsor>` for internal lines |
| `region` | String | Yes | Geographic region (North America, Europe, Japan, Asia Pacific ex-Japan, Greater China, EM, Global) |
| `sector` | String | Yes | Sector focus (Technology, Healthcare, Financials, etc. or "Broad" if multi-sector) |
| `type` | String | Yes | Asset class (Equity, Bond, Multi-Asset, Money Market, etc.) |
| `nav` | Float | Yes | Latest NAV |
| `ret_1y` | Float | Yes | 1-year annualised return (%) |
| `ret_3y` | Float | Yes | 3-year annualised return (%). Null if sentinel (D1) |
| `ret_5y` | Float | Yes | 5-year annualised return (%). Null if sentinel (D1) |
| `ret_1y_flag` / `ret_3y_flag` / `ret_5y_flag` | String | No | Sentinel explanation, e.g. `insufficient_history`. Required wherever a value is `0.0` (D1) |
| `ret_src_1y` / `ret_src_3y` / `ret_src_5y` | String | Yes | `plan_share_class` \| `underlying_fund` \| `insufficient_history` \| `not_covered` \| `unavailable` (D1b) |
| `ret_1y_gross` / `ret_3y_gross` / `ret_5y_gross` | Float | No | **Gross-of-TER** return = `ret_Ny + ter`. This is the standardised comparison basis, not the money invested returned — two funds with different OCFs are compared on this, never on `ret_Ny` (D2) |
| `vol_annual` | Float | Yes | Annualised volatility (%) — **trailing 3Y**, not 1Y |
| `vol_3y_used` / `vol_5y_used` | Float | No | The vol actually used in the Sharpe for that horizon (D3) |
| `vol_3y_source` / `vol_5y_source` | String | No | `plan_share_class` (the plan's exact share class) \| `house_underlying_fund` (the fund, representative or other class) \| `published_standard_deviation` (issuer-published SD, window read from the document) \| `computed_daily_nav_series` / `computed_monthly_nav_series` (derived, method + window in `vol_method`/`vol_window`) \| `short_window` \| `unavailable`. Should equal `ret_src_*` (**D3c**) |
| `sharpe_1y` / `sharpe_3y` / `sharpe_5y` | Float | Yes | Realised Sharpe on the **net** return, risk-free = 4% p.a. USD: `(ret_Ny − rf) / vol` |
| `sharpe_1y_gross` / `sharpe_3y_gross` / `sharpe_5y_gross` | Float | No | Sharpe on the **gross-of-TER** return: `(ret_Ny_gross − rf) / vol_Ny_used`. This is what the analysis layer ranks on. Note the numerator is cost-stripped while the denominator is not, so it is a comparison index, not a realised risk-adjusted return (D3) |
| `sharpe_basis_flag` | String | Yes | `matched` \| `3y` \| `5y` \| `3y+5y` — whether each Sharpe's return and vol share one fund and window (D3b) |
| `ter` | Float | No | Total Expense Ratio / OCF (%) — NULL if unavailable. **Never** the wrapper fee (D2) |
| `ter_basis` | String | Yes | `OCF` \| `TER` \| `ongoing_charges` \| `unavailable` (D2b) |
| `ter_source` | String | Yes | Named document or endpoint (e.g., "factsheet.pdf p.2", "op=FundOverviewSummary"), or `unavailable` (D2c/D2d) |
| `wrapper_fee_pct` | Float | Yes | Plan sponsor's investment-management fee on the choice. Published under its own name so it cannot be mistaken for `ter` (D2) |
| `freshness_checked` | String | No | As-of date verified on aggregator-sourced rows, else `not-applicable` (D5) |
| `liveness_checked` | String | Yes | Where you confirmed the fund is still open (house notice / KFS / fund list) and what you concluded (D6) |
| `data_source` | String | Yes | Which method found this fund's data |

`validate_funds.py` ships alongside this SKILL.md. Run it before handing the CSV on:

```bash
python3 validate_funds.py funds.csv --rf 4.0 --json plan_harvest.json   # exit 0 = contract satisfied
```

It enforces the rules by id: **R0** required columns · **R9** `region` from the fixed taxonomy and a non-empty `type` · **D1**/`D1b` sentinel and backfill provenance · **D2**/`D2b`/`D2c`/`D2d` wrapper-fee separation, `ter_basis`, named source · **D3**/`D3b`/`D3c` Sharpe recomputability and basis disclosure · **D4** house is not the platform · **D5** aggregator freshness · **D6** liveness cross-check. Warnings are advisory (a `ter` that coincidentally equals the wrapper fee is one); failures block the run.

## N/A Enforcement

You may only mark a field N/A **after** attempting ALL of these in order:
1. **Playwright XHR interception** on the fund manager's HK site (write and run the script)
2. **Replay discovered APIs** to batch-extract data
3. **Layer L2** — HK aggregator portals (HKET / ETNet / FSMOne / AASTOCKS), freshness-checked
4. **Layer L3** — stealth re-attempt on blocked houses
5. **Layer L4** — Wayback Machine for dead/SSL-expired sites
6. **Layer L5** — plan's own documents (brochure / investment choice PDF) for internal funds
7. **Layer L6** — Fund Manager Pages → Morningstar HK → FT.com by ISIN → Yahoo Finance → Endowus/aggregators → PDF factsheets
- **Coverage gate: <90% of funds COMPLETE (1/3/5Y + TER + region/sector) → go back and mine more data (Phase 3)**
- N/A is acceptable only after documenting WHICH sources were tried and WHY they failed, for that specific fund
- A N/A TER additionally requires T1-T7 (Phase 1.x) attempted and each layer documented
- **You may NOT skip a house's XHR interception because "it might be blocked" — prove it fails, with L3**
- **You may NOT accept "internal fund, no public data" before L5**
- **You may NOT stop the run below 90% coverage — the output is not final until the gate passes**

## Completeness Checklist

**UNIVERSE COMPLETENESS (Phase 1):**
- [ ] Provider's official fund page/source found?
- [ ] Investment Choice Brochure or equivalent PDF consulted?
- [ ] Fund change announcements checked?
- [ ] If HK plan: Chinese name searched?
- [ ] SFC product list checked?
- [ ] Saturation reached? (multiple methods return the same fund set)
- [ ] Every fund house mentioned in any result individually searched?
- [ ] Every fund's liveness checked against house notices / KFS, not the API's suspend flag (Phase 1E, D6)?
- [ ] Every aggregator-sourced price verified for as-of date freshness (D5)?

**DATA COMPLETENESS (Phase 2 + 3):**
- [ ] Playwright XHR interception script written and saved for EVERY fund house?
- [ ] Each script executed and captured XHR responses?
- [ ] Discovered JSON APIs replayed for batch data extraction?
- [ ] **TER/OCF extracted for every fund (Phase 1.x complete)?**
- [ ] **Region/sector/type classified for every fund?**
- [ ] **L2 aggregator portals (HKET/ETNet/FSMOne/AASTOCKS) attempted for all missing funds?**
- [ ] **L3 stealth re-attempt (real Chrome + webdriver override + curl replay) done for ALL blocked houses?**
- [ ] **L4 Wayback Machine attempted for SSL-expired/DNS-dead sites?**
- [ ] **L5 plan documents (brochure/投資選擇) attempted for internal funds?**
- [ ] **Coverage gate computed and ≥ 90%? (Phase 3 report included in output)**
- [ ] **TER coverage gate computed and ≥ 90%?**
- [ ] Each fund has TER extracted (not N/A)?
- [ ] All returns are exact percentages (no `~` approximations)?
- [ ] Morningstar ratings populated for each fund?
- [ ] FT.com (Layer L6) attempted for every fund with known ISIN?
- [ ] Yahoo Finance (Layer L6) attempted for every fund?

**CONTRACT COMPLIANCE (`validate_funds.py` — exit 0 required before `ilas-fund-report`):**
- [ ] `wrapper_fee_pct` populated on every row, and never equal to `ter` (D2)?
- [ ] `ter_basis` and `ter_source` populated, with a real document/endpoint locator (D2b, D2c, D2d)?
- [ ] No unflagged `0.0` in `ret_1y/3y/5y` — every sentinel nulled or backfilled (D1)?
- [ ] `ret_src_1y/3y/5y` declared on every row (D1b)?
- [ ] Every 3Y/5Y Sharpe recomputable as `(ret_Ny_gross − rf) / vol_Ny_used`, with `vol_Ny_source` equal to `ret_src_Ny` (D3, D3b, D3c)?
- [ ] `house` is a fund manager or `INTERNAL — <sponsor>`, never a platform name (D4)?
- [ ] `freshness_checked` populated wherever `data_source` cites an aggregator (D5)?
- [ ] `liveness_checked` populated on every row, with what was checked and concluded (D6)?
- [ ] `python3 validate_funds.py funds.csv` exits 0?

## Mandatory Disclaimer

> *This analysis evaluates fund performance and risk metrics for informational purposes and does not constitute personalized financial or investment advice.*

## Common Mistakes

- **Skipping Playwright XHR interception and going straight to web search** — the #1 error. XHR is MANDATORY for every house. Write the script, run it, capture the JSON.
- **Stopping the run below 90% coverage** — the single biggest failure mode. L2 (aggregators), L3 (stealth), L4 (Wayback), L5 (plan docs) exist for the funds L1 missed. Recompute after each layer.
- **Accepting "blocked" as final** — Akamai/Cloudflare 403 does not mean no data. Real Chrome, webdriver override, mobile emulation, curl cookie replay and API-host probing recover many houses.
- **Trusting an aggregator because it enumerated a full-looking universe** — a frozen snapshot returns a complete-looking list with stale prices. Assert the as-of date of what it returns, cross-check the count, record `freshness_checked` (D5).
- **Publishing a `0.0` 3Y/5Y as a return** — `0.0` is a missing-data sentinel. Null it, flag it, or backfill from the underlying fund; treating it as 0% ranks every young share class catastrophic (D1).
- **Substituting the plan's investment-management fee for the OCF** — `details.managementFee` appears on every investment choice and is the sponsor's fee, not the fund's ongoing charge. It goes in `wrapper_fee_pct` (D2).
- **Mixing bases inside one Sharpe** — a plan-share-class vol against an underlying-fund return (or the reverse) is not a Sharpe. Match fund and window, publish the vol you divided by (D3).
- **Labelling `house` from `platformName`** — the plan sponsor is the platform, not the manager. Derive it from the underlying fund; internal lines get `INTERNAL — <sponsor>` (D4).
- **Treating the API's suspend flag as a liveness check** — funds announced for compulsory redemption keep returning a live NAV and `suspend=N`. Check house notices and the KFS (D6).
- **Marking internal funds "no public data"** without checking the plan's own brochure/投資選擇手冊 (L5).
- **Not using Wayback Machine** for SSL-expired / DNS-dead / 404 sites — cached pages and PDFs still contain the data.
- **Doing house leaves in the parent** — dispatch is required. A `blocked` return is a failed leaf, not permission for the parent to scrape it.
- **Dispatching text-only agents without saying so in the prompt** — XHR needs a browser; without one the leaf returns `blocked`.
- **Scraping HTML instead of finding the JSON API** — always check XHR first
- **Hardcoding fund counts or fund houses** — every ILAS plan is different. Discover, don't assume.
- **Comparing returns without standardising for TER** — two funds with the same 1Y return but different TERs have different investor outcomes.
- **Accepting "TER not available" without trying T1-T7** — TER is the hardest field and the most important for fair comparison.
- **Outputting N/A before attempting all layers; listing fund names without data; asking the user for direction; skipping fund manager pages; not trying FT.com/Endowus/PDF factsheets; using `~` approximations; processing funds one at a time instead of batch-by-house; not documenting which source yielded each fund's data; accepting >5% N/A or <90% coverage.**

## Red Flags — The Run Is NOT Complete, Keep Searching

- "Most funds have data, a few N/A is fine" — the gate is 90%, not "most"
- "That site is blocked" — blocked ≠ exhausted; L3 stealth + L4 Wayback untried
- "Internal fund, no public data" — L5 plan documents untried
- "I already tried Morningstar" — one tearsheet failing ≠ all sources exhausted
- "Coverage is high enough" — compute the metric; below 90% means continue
- "I'll write the output and note the gaps" — below 90%, the output is not final
- "This fund is terminated/merged" — still record it with last-known data + source
- "XHR failed, going to web search" — go to L2/L3/L4 first, web search is L6 territory
- "TER is hard to find" — TER is the #1 field for fair comparison; exhaust T1-T7
- "This 3Y return is 0.0" — that is a sentinel, not a return. Null and flag, or backfill (D1)
- "The page shows a 1.75% fee, so that's the TER" — that is the wrapper fee (D2)
- "The Sharpe is roughly right" — it must be recomputable from the published columns (D3)
- "The API says the fund is active" — that is not a wind-up check (D6)
- "The aggregator lists 130 funds, so the universe is 130" — a stale snapshot lists a full universe too (D5)
- A search, navigate, or fetch before the tree is in the chat — stop, write the tree, dispatch the current wave
- "Don't over-engineer / user is waiting / no sub-agents" — still write the tree; forbidden spawn means run waves yourself, units stay separate
- "I'll scrape this house myself, I have the context" — that house is a leaf
- "The validator is a formality, I'll run it at the end" — it is the gate; exit 0 before the CSV moves on

**All of these mean: keep mining. The gate is 90%. And if the tree was skipped: stop, write the tree, dispatch the current wave.**

## Out of Scope

This skill handles **data extraction only**. Analysis, ranking, model portfolios, reallocation recommendations, cross-plan comparison → `ilas-fund-report`. Macro context → `macro-research`.

## Companion Skills

After extracting data, invoke the analysis pipeline:
1. `macro-research` — gather structured macro context (rates, indices, gold, geopol)
2. `ilas-fund-report` — top-down analysis, age-stratified portfolios, MD + HTML output
