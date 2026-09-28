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

Extract complete fund data from an ILAS plan's fund price page. Produce an enriched CSV ready for analysis by `ilas-fund-report`. Execute autonomously from start to finish — do NOT ask the user for direction mid-extraction.

**Critical rule #1 (COVERAGE GATE — HARD STOP): The run is NOT complete until ≥90% of funds have COMPLETE data (1Y + 3Y + 5Y returns + TER + region/sector/type all populated). Compute the coverage metric after EVERY extraction pass. Below 90% → keep searching through the source layers. Do NOT write the final output below 90%. If you cannot reach 90% after exhausting ALL layers (L1-L6), you MUST produce a coverage report showing exactly which funds are missing and why, and tell the user: "Coverage is X%. I cannot proceed with report generation. Here are the missing funds and the sources I tried."**

**Critical rule #2: An output where >5% of performance/cost fields are N/A is USELESS. You must exhaust all data mining approaches before accepting empty fields. Missing data means you did not complete the work.**

**Critical rule #3 (TER as Hard Gate): TER/OCF is mandatory for every fund. ≥90% TER coverage required before producing output. <90% → stop and ask the user for TER sources (factsheets, KFS, fund detail pages). <70% → halt. TER standardisation is the foundation of fair cross-fund comparison.**

**Critical rule #4 (REPORT GATE): You MUST NOT invoke `ilas-fund-report` or generate any report if coverage <90%. The report skill will reject your CSV. Do not waste time building a report that will be thrown away. Fix the data first.**

## Parameter Extraction

| Parameter | Type | Required | Default |
|-----------|------|----------|---------|
| `ilas_plan_name` | String | Yes | — |
| `target_funds` | List | No | All available funds |
| `risk_tolerance` | String | No | `Moderate` |
| `time_horizon` | String | No | `7+ yrs` |
| `currency_preference` | String | No | `USD` / `HKD` |

## Stage 1 — Discover the plan (any ILAS)

Do **not** start from a hardcoded adapter (Manulife `productId`, CTF `OSCAR`, …). Those are examples Stage 1 should **rediscover**.

1. Web search EN+中: `"[plan]" ILAS`, `"[plan]" 投資相連保險`, fund price / 投資選擇 / KFS PDF.
2. Open the official fund-price (and info) page. **Preferred:** Playwright intercept XHR/fetch (`application/json`) → replay the API for the full universe.
3. If no JSON / blocked (Akamai, ESA slider, 403): HTML tables, jina, offering PDFs, FE/citicode, FT by ISIN, aggregators. XHR is one path, **not the only path**.
4. Write `source_map.json` (schema in `ilas-fund-report/schemas/source_map.schema.json`): `plan`, `provider`, `product_code`, `pages[]`, `apis[]`, `docs[]`, `blockers[]`.
5. Then extract into `funds.json`. Coverage ≥90% or stop.

## Core Principle: API-First Data Extraction

**Prefer JSON APIs over HTML.** The primary extraction method is XHR JSON interception via Playwright:

1. Launch headless browser on the target page
2. Intercept ALL XHR/fetch responses, filtering for `application/json` and `application/javascript`
3. Identify API endpoints returning: fund list, fund detail (NAV, returns), fund fees
4. Replay these APIs directly with `webfetch` to get structured JSON data
5. Parse the JSON to extract exact numeric values

This approach is orders of magnitude faster and more reliable than HTML scraping:
- One API endpoint often serves data for ALL funds
- JSON is machine-readable with exact numbers
- APIs change less frequently than HTML layouts
- You can batch-query all funds from one house in a single script

## Phase 1: Fund Universe Identification — FIND EVERY FUND IN THE PLAN

**CRITICAL RULE:** You MUST find ALL funds available in this specific plan. Different ILAS plans offer vastly different fund universes — some have 30 funds, others 150+. Do NOT assume a number. Your job is to exhaust every search method until no new funds can be discovered.

### 1A: Identify the Plan

Start by determining what plan you're dealing with:

- **Provider** (Manulife, Generali, AXA, Aviva, Prudential, etc.)
- **Plan name** (exact English and Chinese name if applicable)
- **Product code / plan code** (if available from SFC or provider site)
- **Plan type** (regular premium, single premium, lump sum)

Search: `"[Plan Name]" "[Provider]" ILAS`, `"[Plan Name]" 投資相連保險`.

For HK plans, also search the Chinese name: providers often market ILAS plans with different Chinese names.

### 1B: Discover the Fund Universe — Use ALL Methods

For each search method, track which funds it discovers. Stop when multiple methods return the same set (saturation).

| Method | What to Search | What to Expect |
|--------|---------------|----------------|
| **Provider fund price page** | Navigate the provider's fund price / fund choice page for ILAS. Use both English and Chinese plan name. | Full fund list with NAV prices |
| **Investment Choice Brochure PDF** | `"[Plan Name]" investment choice brochure PDF`, `"[Plan Name]" 投資選擇` | Official fund list PDF with all fund names |
| **Plan brochure / product brochure PDF** | `"[Plan Name]" brochure PDF`, `"[Plan Name]" product sheet` | Full plan description with fund list |
| **Fund change announcements** | `"[Provider]" ILAS fund change announcement`, `"[Provider]" 基金變更` | Lists specific fund additions/deletions |
| **SFC authorized fund list** | Check `apps.sfc.hk/productlistWeb/searchProduct/ILAS.do`. Find the plan code and see if underlying funds are listed. | Plan registration info, possibly fund list |
| **API/XHR interception** | Navigate to the provider's fund page with Playwright, intercept XHR for JSON fund list APIs | Full fund universe in one API call |
| **Aggregator / comparison sites** | `"[Plan Name]" fund list`, `"[Plan Name]" fund choices` | Curated fund lists from financial portals |
| **Web search — English** | `"[Plan Name]" "fund" "ILAS"` | Various pages mentioning fund options |
| **Web search — Chinese (for HK plans)** | `"[Plan Chinese Name]" 基金` | Chinese financial forum discussions listing fund choices |
| **Fund house search** | For each fund house mentioned in any search result, search: `"[Fund House]" "[Plan Name]"` | Additional funds from that house |

### 1C: Identify Fund Houses in This Plan

From the funds discovered, compile the list of fund houses this specific plan offers. For each fund discovered, record which house manages it. If you find a fund house in any search result that hasn't been checked yet, search for more funds from that house in this plan.

### 1D: Fund Universe Completeness Check

- **[ ] No new funds discovered after trying 3+ methods?** (saturation reached)
- **[ ] Provider's official fund page/PDF consulted?**
- **[ ] At least one PDF/factsheet source checked?**
- **[ ] If HK plan: Chinese name searched?**
- **[ ] SFC product list checked?**
- **[ ] All fund houses mentioned in search results individually searched?**

**If you have any evidence that more funds exist (e.g., a fund house appears in the plan's brochure but none of their funds are in your list), continue searching. Do NOT proceed until you've exhausted all discovery methods.**

Create a fund list table with: Fund Name | Fund House | ISIN | Asset Class | Currency | Morningstar ID (if found) | Source (which method found this fund).

### Phase 1.x: TER/OCF Capture — MANDATORY, BEFORE RETURNS EXTRACTION

**TER/OCF is the #1 hardest field to extract and the #1 field that breaks cross-fund comparison. Capture it early and verify it.**

For each fund house, extract TER/OCF (Ongoing Charges Figure / Total Expense Ratio) using these layers in order:

| Layer | Source | Method | Expected TER Fields |
|-------|--------|--------|---------------------|
| **T1** | Fund house website | XHR interception on fund detail page | OCF, TER, management fee, admin fee |
| **T2** | Fund factsheet PDF | Download + extract from "Fund Expense" or "Charges" section | OCF, TER, total cost |
| **T3** | HK aggregators | FSMOne, HKET, ETNet fund detail pages | OCF |
| **T4** | Morningstar HK | `morningstar.hk` fund page → "费用" tab | TER, transaction fee |
| **T5** | FT.com | `markets.ft.com/data/funds/tearsheet/summary?s=[ISIN]:USD` | OCF |
| **T6** | Plan documents | Investment Choice Brochure PDF, fund change announcements | TER for internal funds |
| **T7** | User-provided | Ask user to upload factsheet PDFs or KFS (Key Features Statement) | All fees |

**TER extraction rules:**
- Prefer OCF (Ongoing Charges Figure) over TER if both available — OCF excludes transaction costs
- If only "management fee" available, note it as a partial TER and flag in output
- Record the source for each TER value in `ter_source` column
- If TER is genuinely unavailable after T1-T6, set `ter = NULL` and `ter_source = "unavailable"` — do NOT guess
- Internal funds (e.g., Manulife Select series): check the plan's Investment Choice Brochure PDF (T6) first

**TER quality gate after extraction:**
```
TER coverage = # funds with TER populated / total_funds × 100
```
- ≥ 90% → proceed
- 70-89% → continue to T7 (ask user for factsheets)
- < 70% → halt. TER data is insufficient for fair analysis.

### Phase 1.y: MyBrowser MCP Fallback — When Headless Fails

**If Playwright headless mode is blocked (Akamai 403, Cloudflare, ERR_NETWORK_CHANGED) on the primary data source (e.g., Manulife HK fund price page), use MyBrowser MCP as a fallback.**

Procedure:
1. Detect headless failure: HTTP 403, ERR_NETWORK_CHANGED, "Just a moment...", or ERR_ABORTED
2. Prompt the user:
   ```
   Headless scraping is blocked on [site]. Please enable MyBrowser MCP
   (browser extension) to continue extraction. Once enabled, I'll use the
   browser MCP tools to navigate and capture data directly from your browser.
   ```
3. Once user confirms MyBrowser is enabled:
   - Use `mybrowser_browser_navigate` to the target URL
   - Use `mybrowser_browser_snapshot` to verify page loaded
   - Use `mybrowser_browser_network` (start_capture → navigate → get_log) to intercept XHR
   - Use `mybrowser_browser_extract` for structured data extraction
   - Use `mybrowser_browser_evaluate` for JavaScript-based data capture

**MyBrowser MCP is the LAST RESORT before asking the user for manual data entry.** Try all other layers (T1-T6, L2-L6) before invoking this.

## Phase 2: Per-Fund-House Playwright XHR Interception (PRIMARY — MANDATORY)

## Phase 2: Per-Fund-House Playwright XHR Interception (PRIMARY — MANDATORY)

**CRITICAL RULE:** For EVERY fund house in the plan, you MUST write and execute a Playwright XHR interception script on their HK fund page. Save each script to `/tmp/opencode/`. Do NOT skip this step. Do NOT fall back to web search. Only after XHR interception fails on a site may you use fallback sources.

### Procedure for Each Fund House

1. Navigate to the fund house's HK fund price/performance page (URLs below)
2. Intercept ALL XHR/fetch responses, filter for JSON
3. Identify the API that returns fund performance data
4. Replay that API directly with `fetch` or `webfetch` for ALL funds from this house
5. Parse JSON results to extract: trailing returns, OCF, NAV, ratings
6. **Save the script to `/tmp/opencode/xhr_[house].js`** and save captured JSON to `/tmp/opencode/xhr_[house]_capture.json`

### Playwright Template — Use This for Every Fund House

```javascript
const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    viewport: { width: 1920, height: 1080 },
    locale: 'en-US'
  });
  const page = await context.newPage();

  const capturedData = [];
  page.on('response', async (response) => {
    const url = response.url();
    const contentType = response.headers()['content-type'] || '';
    const status = response.status();
    if (contentType.includes('json') || contentType.includes('application/json')) {
      try {
        const json = await response.json();
        capturedData.push({ url, status, data: json });
      } catch (e) {}
    }
  });

  await page.goto('TARGET_URL', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(5000);

  // Save captures
  fs.writeFileSync('/tmp/opencode/xhr_captures.json', JSON.stringify(capturedData, null, 2));
  console.log(`Captured ${capturedData.length} XHR responses`);

  // Print summary
  capturedData.forEach((r, i) => {
    const dataStr = r.data ? JSON.stringify(r.data).substring(0, 200) : 'no data';
    console.log(`[${i}] ${response.url}`);
    console.log(`    Status: ${r.status}, Data: ${dataStr}`);
  });

  await browser.close();
})();
```

### Concrete Fund House Targets — Navigate HERE for XHR Interception

For each house that appears in your fund universe, navigate to its HK fund page and capture XHR. **Do NOT skip any house.**

| Fund House | Playwright Target URL | Actual Result | API Found |
|------------|----------------------|---------------|-----------|
| **AllianzGI HK** | `https://hk.allianzgi.com/en-hk/retail/products-solutions/retail-funds/` | ✅ Loaded | `GET /en-HK/api/funddata/multi/funds/{guid}/{guid}` → 412 funds with exact trailing returns, NAV, calendar years |
| **Franklin Templeton HK** | `https://www.franklintempleton.com.hk/en-hk/our-funds/price-and-performance/mutual-funds` | ✅ Loaded (needs Individual Investor + Accept + cookie consent) | GraphQL `POST /api/pds/price-and-performance` with operations: IntlCorePpss (core), IntlIndentifiers (ISINs), CommonPerformance, IntlRatings (M★), CalendarYearMonthly |
| **Fidelity HK** | `https://www.fidelity.com.hk/en/funds/fund-price-and-performance/` | 🚫 **HTTP 403** — Akamai bot protection, all URLs blocked | N/A — use PDF factsheets |
| **JPMorgan HK** | `https://am.jpmorgan.com/hk/en/asset-management/per/products/` | 🚫 **ERR_ABORTED** — network security intercept | N/A — use PDF factsheets |
| **BlackRock HK** | `https://www.blackrock.com/hk/en/products/` | 🚫 **Redirected** — CrowdStrike Source Defense blocking | N/A — use Morningstar |
| **Manulife IM** | `https://www.manulifeim.com.hk/en/funds/fund-prices.html` | 🚫 **HTTP 403** — Akamai all pages/APIs | N/A — no public access |
| **Manulife HK** | `https://www.manulife.com.hk/` | 🚫 **HTTP 403** — Akamai on all pages | N/A — no public access |
| **Schroders HK** | `https://www.schroders.com/en-hk/hk/individual/fund-centre/` | 🚫 **ERR_NETWORK_CHANGED** — intermittent failure | N/A — use Morningstar |
| **Ninety One HK** | `https://ninetyone.com/hong-kong/en` | 🚫 **Cloudflare 403** — "Just a moment..." | N/A — use FT.com |
| **Invesco HK** | `https://www.invesco.com.hk/en/home` | 🚫 **404** — all fund URLs not found | N/A — use Morningstar |
| **PIMCO HK** | `https://www.pimco.com/hk/en/investments/mutual-funds` | 🚫 **404** — fund pages broken under headless | N/A — use Yahoo Finance |
| **Janus Henderson HK** | `https://www.janushenderson.com/` | 🚫 **ERR_NETWORK_CHANGED** — intermittent failure | N/A — use Morningstar |
| **AB/AllianceBernstein HK** | `https://www.alliancebernstein.com.hk/` | 🚫 **SSL EXPIRED** — ERR_CERT_DATE_INVALID | N/A — use PDF factsheets |
| **Value Partners HK** | `https://www.vp.com.hk/en/` | 🚫 **SSL EXPIRED** — ERR_CERT_AUTHORITY_INVALID | N/A — use PDF factsheets |
| **BNP Paribas AM HK** | `https://www.bnpparibas-am.com.hk/en-hk/` | 🚫 **DNS FAILURE** — ERR_NAME_NOT_RESOLVED | N/A — no access |
| **Amundi HK** | `https://www.amundi.com.hk/en_retail` | ⚠️ Forces redirect to Chinese (zh_retail) | Partial |
| **Nikko AM → Amova AM** | `https://www.nikkoam.com.hk/en/home` | ⚠️ Redirected to hk.amova-am.com (rebranded) | Partial — needs role selector + disclaimer accept |

### Real-World API Discovery Notes (Verified Jul 2026)

#### AllianzGI HK — Fully Working
```
Target: https://hk.allianzgi.com/en-hk/retail/products-solutions/retail-funds
API (fund list):  POST /api/sitecore/searchservice/fundlist
   Body: IsAutosuggest=true&Region=ap&Language=en-HK&SalesChannel=hk_retail_financial_advisor
API (multi-fund): GET /en-HK/api/funddata/multi/funds/{sitecoreId}/{datasourceId}
   → Returns 412 funds with exact: FundName, ISIN, BaseCurrency, NAV, NavDate,
     YTD, TrailingReturn1Year, TrailingReturn3Year, TrailingReturn5Year,
     SinceInception, CY2022, CY2021, CY2020, CY2019, CY2018
   → NOTE: No OCF, no Morningstar rating, no SRRI in this API
   → OCF/SRRI data must come from fund detail page or factsheet PDF
```
**How to use**: Navigate once, capture the GET `/api/funddata/multi/funds/` response. The response is ~687KB. Parse it for the specific fund ISINs needed.

#### Franklin Templeton HK — GraphQL API Fully Working
```
Target: https://www.franklintempleton.com.hk/en-hk/our-funds/price-and-performance/mutual-funds
- Must first accept role selector ("Individual Investor") + welcome dialog ("Accept") + cookie consent ("Ok")
- Then navigate to the mutual funds page

API: POST /api/pds/price-and-performance (GraphQL)
Operations available:
  op=Labels&id=0          → Field name translations
  op=IntlCorePpss&id=2    → Core fund data: fundid, fundname, basecurrcode,
                             assetclass, fundcatg, invmangr, aum, shareclass[]
                             fields: shclname, shclcurr, prmryshclind, perfincdt,
                             nav { navdate, navvalue, navchngpct, ytdtotretatnav },
                             charges { prfrmncefee, fundadminfee, annchrg, expratnet }
  op=IntlIndentifiers&id=3 → ISIN, Bloomberg ticker, share class codes (199KB response)
  op=CommonPerformance&id=4 → Trailing returns (month_end, quarter_end) but only for AllianzGI funds
  op=IntlRatings&id=5      → Morningstar Overall Rating, MS Rating 3/5/10Y, MS Category (142KB)
  op=CalendarYearMonthly&id=6 → Calendar year returns monthly
  op=CalendarYearQuarterly&id=7 → Calendar year returns quarterly
```
**How to use**: Navigate to mutual funds page, the page fires all these APIs automatically. Capture the response bodies. `IntlCorePpss` + `IntlRatings` + `IntlIndentifiers` together give NAV, OCF, Morningstar stars, and ISIN for all 62 HK mutual funds.

#### Common Bot Protection Patterns
| Pattern | Sites Affected | What Happens |
|---------|---------------|--------------|
| **Akamai CDN** | Manulife HK, Manulife IM, Fidelity HK | HTTP 403 on ALL pages/APIs, even headless Playwright |
| **Cloudflare** | Ninety One HK | "Just a moment..." challenge, 403 block |
| **CrowdStrike Source Defense** | BlackRock HK | Page loads but content is blocked/replaced, 27+ console errors |
| **Network security intercept** | JPMorgan HK | ERR_ABORTED before any page content loads |
| **SSL certificate expired** | AB HK, Value Partners HK | ERR_CERT_DATE_INVALID / ERR_CERT_AUTHORITY_INVALID |
| **404 behind headless** | Invesco HK, PIMCO HK | All fund-related URLs return 404 under Playwright |
| **ERR_NETWORK_CHANGED** | Schroders HK, Janus Henderson HK | Intermittent failures in headless mode |

**Strategy when blocked**: Do NOT stop at the first 403. Escalate through Phase 2B layers: L2 aggregators → L3 stealth re-attempt (real Chrome + webdriver override + curl cookie replay + API-host probe) → L4 Wayback Machine → L5 plan documents → L6 external tearsheets (Morningstar/Primerate/FT.com by ISIN, PDF factsheets at `{fundhouse}.com.hk/{language}/fund-literature/{fund-name}.pdf`).

### Special Case: CTF Life (Chow Tai Fook)

Playwright on `ctflife.com.hk` is often blocked by **Alibaba Cloud ESA slider**. Fund-price HTML is still fetchable (curl/webfetch). Vue `GET /api/PerformanceData` is not the path; POST with `fund_code` 500s.

**CTF Life extraction procedure:**
1. Parse fund-price **HTML table**: `data-prod` (Oscar=`OSCAR`), `data-comp`, `data-cat`, code, `getPricePDF('CITICODE')`, NAV.
2. Filter the plan with `OSCAR` in `data-prod` (shared list with Cheers Plus / Legend / We Shine). Drop Legend-only T-codes.
3. Batch FE Precision Plus for ISIN + KFS + factsheet:
   `https://datafeeds.feprecisionplus.com/api/funddata/CTFLife/5331e260-6d43-295c-cd1c-dea0faa31e7c?Languages=en-gb&rangename=Range&citicodes=`
4. FT.com by `{ISIN}:{CCY}` for trailing returns (`data-mod-config` rawFundPerformance) and Ongoing charge. HK ISINs often 404 on FT → KFS OCF + factsheet cumulative 1/3/5Y (**annualise** 3Y/5Y).
5. **Do NOT generate a report with only current prices — that is 0% coverage and is unacceptable**

Oscar (~180 F-codes) houses: BlackRock, abrdn, Allianz, Schroder, Barings, BNP, Fidelity, JPMorgan, Invesco, FT, Ninety One, PIMCO, T. Rowe, Value Partners, Wellington, others.

### After Discovery: Replay APIs Directly

Once you find the API endpoint pattern for a fund house, use it to batch-extract data for ALL their funds at once:

```javascript
// Example: after finding a Morningstar API endpoint
const fundIds = ['F00000XXXX', ...]; // from XHR capture
const results = [];
for (const id of fundIds) {
  const res = await fetch(`https://asiaapi.morningstar.com/ODSHelperWS/default.aspx?ClientId=chiefsec&DocType=FS&Id=${id}&LanguageId=EN&MarketId=CU$$$$$$HKG`);
  const data = await res.json();
  results.push({ id, data });
}
// Extract: 1Y return = data.performance.oneYearReturn, etc.
```

### Mandatory Checklist Per Fund House

For EACH fund house, verify these before moving on:

- [ ] Playwright script written and saved to `/tmp/opencode/xhr_[house].js`?
- [ ] Script executed and captured XHR responses?
- [ ] Found JSON API with performance data? If yes, replayed it.
- [ ] If no JSON API found, attempted HTML parsing of the fund page?
- [ ] Extracted: 1/3/5Y trailing returns, Morningstar rating, OCF, risk rating?
- [ ] Saved results to fund house output file?

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

Aggregator fund price pages cover ALL fund houses in one site, are rarely bot-blocked, and are JSON-API-backed. **The source that enumerated the fund universe will almost always also have performance data APIs.**

- **HKET fund price page** `invest.hket.com` — proven (Jul 2026): enumerated full 130-fund ILAS universe. Intercept XHR on the fund price/search pages for the performance API.
- **ETNet fund centre** `fund.etnet.com.hk` — fund screener with full data
- **FSMOne HK** `fsmone.com.hk` — full fund database, price + performance + OCF
- **AASTOCKS funds** `aastocks.com.hk/en/funds/` — fund search with returns

Procedure: write a Playwright XHR interception script for each aggregator (save to `/tmp/opencode/xhr_aggregator_*.js`), search for each missing fund, capture the JSON API, replay it for all missing funds. Batch by aggregator, not per fund.

### Layer L3: Stealth Re-Attempt on Blocked Houses

**"Blocked" ≠ "exhausted".** For every house that failed L1, re-attempt with these techniques in order, then replay the API with curl using the session cookies:

1. **Real Chrome channel + webdriver override** (defeats basic Akamai/Cloudflare headless detection):
```javascript
const browser = await chromium.launch({
  channel: 'chrome',                       // real Chrome install, not bundled Chromium
  headless: false,                          // headed; on a server use `xvfb-run node script.js`
  args: ['--disable-blink-features=AutomationControlled']
});
const context = await browser.newContext({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36', locale: 'en-US', timezoneId: 'Asia/Hong_Kong', viewport: { width: 1920, height: 1080 } });
await context.addInitScript(() => {
  Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
  window.chrome = window.chrome || { runtime: {} };
});
```
2. **Mobile device emulation** — many Akamai configs exempt mobile traffic: `browser.newContext({ ...devices['iPhone 13'] })`
3. **Cookie/session replay via curl**: after the browser session, export `context.cookies()`, then replay discovered APIs directly with `curl -H 'User-Agent: ...' -H 'Accept: application/json' -b 'cookies.txt' -H 'Referer: <the page>' <API URL>` — API hosts are often less protected than HTML pages.
4. **Bypass path via API host**: even when HTML is 403, try the API endpoint host directly (e.g., `api.fidelity.com.hk`, `prices.manulifeim.com.hk`) — check DNS and probe common API paths.
5. Only if ALL of 1–4 fail for a house may you drop L1 for that house and go to L2/L4 for its funds.

### Layer L4: Wayback Machine (dead / SSL-expired / DNS-failed sites)

For sites like AB HK (SSL expired), Value Partners HK (SSL expired), BNP Paribas AM HK (DNS dead):

- Page snapshots: `web.archive.org/web/2024*/{original-url}` — pick the newest snapshot
- PDF factsheets: `web.archive.org/web/{timestamp}if_/{factsheet-url}.pdf` — `if_` returns the raw original file
- Fund data pages render server-side; the cached HTML still contains the performance tables
- Search snapshots by fund name: `web.archive.org/web/*/vp.com.hk/*`

### Layer L5: Plan's Own Documents (internal funds)

**Internal funds (e.g., Manulife Select series) are NOT "no public data" until the plan's own documents have been checked.** The plan operator publishes OCF and fund details for internal funds in:

- Investment Choice Brochure / 投資選擇手冊 PDF — search `"[Plan Name]" investment choice brochure PDF`, `"[Plan Name]" 投資選擇手冊`
- Plan fact sheet / product brochure PDF
- Fund change announcements — `"[Provider]" ILAS fund change announcement`
- Provider's ILAS platform login-adjacent public pages (e.g., Manulife's fund price pages for the plan)

### Layer L6: Per-Fund External Sources (in order, only for funds still missing data)

### Source B: Fund Manager Pages — Direct HTML Scrape

If XHR found no API, use Playwright or fetch to read the HTML fund page directly for each fund from this house:

- **BlackRock**: `https://www.blackrock.com/hk/en/products/[PRODUCT_ID]` — SSR HTML with performance tables
- **AllianzGI**: `https://hk.allianzgi.com/en-hk/retail/products-solutions/retail-funds/[FUND-NAME]` — Performance tab HTML
- **PIMCO**: `https://www.pimco.com.hk/en/investments/gis/[FUND-NAME]/inst-usd-accumulation` — factsheet PDFs
- **JPMorgan**: `https://am.jpmorgan.com/hk/en/asset-management/per/products/[FUND-NAME]-ISIN` — performance tables
- **Fidelity**: `https://www.fidelity.com.hk/en/funds/[FUND-NAME]` — factsheet performance
- **Schroders**: `https://www.schroders.com.hk/hk/individual/funds/[FUND-NAME]` — factsheet PDFs
- **Franklin Templeton**: `https://www.franklintempleton.com.hk/en-hk/investor/investments-and-solutions/funds/[FUND-NAME]`
- **Invesco**: `https://www.invesco.com.hk/en/funds/[FUND-NAME]`
- **Manulife IM**: `https://www.manulifeim.com.hk/en/funds/fund-prices.html` (may be 403)
- **Capital Group**: `https://www.capitalgroup.com/individual-investors/hk/en/investments/[FUND-NAME].html`

### Source C: Morningstar HK

Search: `site:morningstar.hk "[Fund Name]" "[Fund House]"`
URL: `https://www.morningstar.hk/hk/report/fund/performance.aspx?t=0P0000XXXX`
Data: Star rating, trailing returns, category, OCF.

### Source D: FT.com (by ISIN)

URL: `https://markets.ft.com/data/funds/tearsheet/summary?s=[ISIN]:USD`
URL (performance): `https://markets.ft.com/data/funds/tearsheet/performance?s=[ISIN]:USD`
Data: Exact trailing returns (5yr, 3yr, 1yr), quartile ranking, OCF, fund size, launch date.

### Source E: Yahoo Finance (by Morningstar ID)

URL: `https://finance.yahoo.com/quote/0P0000XXXX/`
Data: YTD return, 1yr, 3yr, 5yr returns, Morningstar Risk Rating, Expense Ratio.

### Source F: Endowus / Aggregators

URL: `https://endowus.com/en-hk/investment-funds-list/[fund-name]-[ISIN]`
Search: `endowus.com "[Fund Name]" performance`

### Source G: PDF Factsheets

Search: `"[Fund Name]" factsheet PDF Hong Kong` or `api.fundinfo.com "[Fund Name]"`
Fundinfo: `https://api.fundinfo.com/document/[HASH]/MR_en_en_[ISIN]_YES_[DATE].pdf?apiKey=[KEY]`

## Phase 3: Coverage Gate — MANDATORY, NEVER SKIP

After every extraction pass (Phase 2 → L1/L2/L3/L4/L5/L6), compute:

```
complete   = # funds with ALL of [1Y return, 3Y return, 5Y return, TER, region, sector, type] populated
coverage % = complete / total_funds × 100
```

**GATE: `coverage % ≥ 90%` is REQUIRED before producing the final output.**

| Coverage | Action |
|----------|--------|
| ≥ 90% | Proceed to analysis and report |
| 70–89% | NOT DONE — continue to the next source layer (L2 → L3 → L4 → L5 → L6), targeting ONLY the missing funds. Recompute after each layer. |
| < 70% | CRITICAL FAILURE of extraction — go back and redo Phase 2 from scratch with stealth techniques (L3) on ALL houses before touching L6 |

**Loop until one of:**
1. Coverage ≥ 90%, OR
2. Every missing fund has a documented exclusion reason with evidence of WHICH sources were tried and WHY they failed (this requires L2, L3, L4, L5 attempted for that fund — a single source failing is never a valid exclusion)

**Include this report in the output:**

```
## Data Coverage Report
| Status | Funds | % |
|--------|:-----:|:--:|
| Complete (1/3/5Y + TER + region/sector/type) | n | x% |
| Partial (missing some fields) | n | x% |
| Missing (no data) | n | x% |
COVERAGE: x% — GATE ≥ 90%: PASS/FAIL

## TER Coverage Report
| Status | Funds | % |
|--------|:-----:|:--:|
| TER populated | n | x% |
| TER unavailable | n | x% |
TER GATE ≥ 90%: PASS/FAIL
```

## Data Extraction Rules

- **No `~` (approximate) values.** Extract exact percentages (e.g., `5.37`, not `~5.4%`).
- Use most recent data available; note the date.
- For annualised returns, use trailing return figures (1yr, 3yr, 5yr annualised).
- For OCF/TER, use "Ongoing Charges Figure" or "Total Expense Ratio". Prefer OCF if both available.
- **TER standardisation**: Record TER in the output. The analysis layer (`ilas-fund-report`) will standardise all returns to gross-of-TER for fair comparison. Your job is to extract the TER accurately.

## Output CSV Schema

The output must be an enriched CSV with these columns:

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `code` | String | Yes | Fund code (e.g., UIG01) |
| `name` | String | Yes | Fund full name |
| `house` | String | Yes | Fund house (e.g., Manulife IM) |
| `region` | String | Yes | Geographic region (North America, Europe, Japan, Asia Pacific ex-Japan, Greater China, EM, Global) |
| `sector` | String | Yes | Sector focus (Technology, Healthcare, Financials, etc. or "Broad" if multi-sector) |
| `type` | String | Yes | Asset class (Equity, Bond, Multi-Asset, Money Market, etc.) |
| `nav` | Float | Yes | Latest NAV |
| `ret_1y` | Float | Yes | 1-year annualised return (%) |
| `ret_3y` | Float | Yes | 3-year annualised return (%) |
| `ret_5y` | Float | Yes | 5-year annualised return (%) |
| `vol_annual` | Float | Yes | Annualised volatility (%) |
| `sharpe_1y` | Float | Yes | 1-year Sharpe ratio (risk-free = 4% p.a. USD) |
| `sharpe_3y` | Float | Yes | 3-year Sharpe ratio |
| `sharpe_5y` | Float | Yes | 5-year Sharpe ratio |
| `ter` | Float | No | Total Expense Ratio / OCF (%) — NULL if unavailable |
| `ter_source` | String | No | Source of TER value (e.g., "factsheet.pdf", "FSMOne", "unavailable") |
| `data_source` | String | Yes | Which method found this fund's data |

## N/A Enforcement

- You may only mark a field N/A **after** attempting ALL of these in order:
  1. **Playwright XHR interception** on the fund manager's HK site (MANDATORY — write and run the script)
  2. **Replay discovered APIs** to batch-extract data
  3. **Layer L2** — HK aggregator portals (HKET / ETNet / FSMOne / AASTOCKS) XHR interception
  4. **Layer L3** — stealth re-attempt on blocked houses (real Chrome + webdriver override + curl cookie replay)
  5. **Layer L4** — Wayback Machine for dead/SSL-expired sites
  6. **Layer L5** — plan's own documents (brochure / investment choice PDF) for internal funds
  7. **Layer L6** — Morningstar HK → FT.com by ISIN → Yahoo Finance → Endowus/aggregators → PDF factsheets
- **Coverage gate: if <90% of funds have COMPLETE data (1/3/5Y + TER + region/sector), extraction is insufficient — go back and mine more data (Phase 3)**
- N/A only acceptable after documenting WHICH sources were tried and WHY they failed for that specific fund
- A row where TER is N/A is only acceptable after attempting T1-T7 (Phase 1.x) AND documenting each layer
- **You may NOT skip a fund house's XHR interception because "it might be blocked" — you must attempt it and prove it fails (with L3 techniques)**
- **You may NOT accept "internal fund, no public data" for a fund house's internal funds — check the plan's own documents (L5) first**
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

## Mandatory Disclaimer

> *This analysis evaluates fund performance and risk metrics for informational purposes and does not constitute personalized financial or investment advice.*

## Common Mistakes

- **Skipping Playwright XHR interception and going straight to web search** — this is the #1 error. XHR interception is MANDATORY for every fund house. Write the script. Run it. Capture the JSON.
- **Stopping the run below 90% coverage** — the single biggest failure mode. One pass over sources is NOT enough. L2 (aggregators), L3 (stealth), L4 (Wayback), L5 (plan docs) exist precisely for the funds L1 missed. Recompute coverage after each layer and keep going.
- **Accepting "blocked" as final** — Akamai/Cloudflare 403 on the first attempt does not mean no data exists. Stealth techniques (real Chrome, webdriver override, mobile emulation, curl cookie replay, API-host probing) recover many "blocked" houses.
- **Never using the source that found the fund universe for data extraction** — if a portal (e.g., HKET invest.hket.com) enumerated all 130 funds, it has the performance API too. Intercept it.
- **Marking internal funds "no public data"** without checking the plan's own brochure/投資選擇手冊 (L5) — the plan operator publishes OCF for internal funds.
- **Not using Wayback Machine** for SSL-expired / DNS-dead / 404 sites — cached pages and PDFs still contain the data.
- **Dispatching text-only agents/subagents who cannot run Playwright** — XHR interception requires a browser. If you delegate, you must delegate to agents that have Playwright/browser tools.
- **Scraping HTML instead of finding the JSON API via XHR interception** — always check XHR first
- **Stopping early** — once fund discovery plateaus, switch methods. If a fund house appears in the plan but none of their funds are listed, search harder.
- **Assuming the first search result is complete** — it never is. Cross-reference multiple methods.
- **Hardcoding fund counts or fund houses** — every ILAS plan is different. Discover, don't assume.
- **Comparing returns without standardising for TER** — two funds with the same 1Y return but different TERs have different investor outcomes. Always record TER.
- **Accepting "TER not available" without trying T1-T7** — TER is the hardest field but also the most important for fair comparison. Exhaust all layers before giving up.
- **Outputting N/A before attempting all layers**
- **Listing fund names without data**
- **Asking user for direction**
- **Skipping fund manager pages**
- **Not trying FT.com by ISIN (Layer L6)**
- **Not trying Yahoo Finance (Layer L6)**
- **Accepting >5% N/A rate (and never <90% coverage)**
- **Using `~` approximations instead of exact numbers**
- **Processing funds one at a time instead of batch-processing by fund house / aggregator**
- **Not documenting which sources yielded data for each fund**

## Red Flags — The Run Is NOT Complete, Keep Searching

- "Most funds have data, a few N/A is fine" — coverage gate is 90%, not "most"
- "That site is blocked" — blocked ≠ exhausted; L3 stealth + L4 Wayback still untried
- "Internal fund, no public data" — L5 plan documents still untried
- "I already tried Morningstar" — one tearsheet failing ≠ all sources exhausted
- "Coverage is high enough" — compute the metric; below 90% means continue
- "I'll write the output and note the gaps" — below 90%, the output is not final
- "This fund is terminated/merged" — still record it with last-known data + source
- "XHR failed, going to web search" — go to L2/L3/L4 first, web search is L6 territory
- "TER is hard to find" — TER is the #1 field for fair comparison; exhaust T1-T7 before giving up
- "I have the data, no need for TER" — data without TER is incomplete for cross-fund comparison

**All of these mean: keep mining. The gate is 90%.**

## Out of Scope

This skill handles **data extraction only**. It does NOT:
- Analyze or rank funds (→ `ilas-fund-report`)
- Build model portfolios (→ `ilas-fund-report`)
- Research macro context (→ `macro-research`)
- Produce reallocation recommendations (→ `ilas-fund-report`)
- Compare funds across plans (→ `ilas-fund-report`)

## Companion Skills

After extracting data, invoke the analysis pipeline:
1. `macro-research` — gather structured macro context (rates, indices, gold, geopol)
2. `ilas-fund-report` — top-down analysis, age-stratified portfolios, MD + HTML output
