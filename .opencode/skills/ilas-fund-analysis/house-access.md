# HK Fund House Targets — verified Sep 2026

Reference for the Playwright XHR interception in `ilAS-data-extract` Phase 2.
One house per extraction leaf. Re-verify per run; reachability changes.

**The previous version of this table marked 13 of 16 houses "blocked". A live run
reached 16 of 24.** Almost every "block" was a mundane cause, not bot protection.

## Before writing a house off — in this order

1. Use the **corrected URL below**, not a guess.
2. `chromium.launch({ channel: 'chrome', headless: false })` under `xvfb-run` with a
   `navigator.webdriver` override. **Bundled Chromium is the most common false negative.**
3. If the bare domain 404s, try the **global root** (`.com` vs `.com.hk`) — several HK
   entities have dead or zero-DNS `.com.hk` hosts.
4. Click through consent, role selectors and disclaimer scroll-gates.
   `page.request.get()` bypasses the browser stack and inherits the 403;
   **in-page `window.fetch()` under real Chrome returns 200.**

**`ERR_NETWORK_CHANGED` and `ERR_ABORTED` are NOT bot-detection signals.**
`chrome-headless-shell` fails on a GPU-sandbox host and reports as a network error.
This one artefact produced a false "blocked" verdict for Janus, Schroders, JPMorgan and
Manulife IM.

## Table

| Fund House | Working target (verified Sep 2026) | Result | API / notes |
|------------|-----------------------------------|--------|-------------|
| **AllianzGI HK** | `hk.allianzgi.com/en-hk/retail/products-solutions/retail-funds` | ✅ 412 funds | `POST /api/sitecore/searchservice/fundlist`, then `GET /en-HK/api/funddata/multi/funds/{guid}/{guid}`. **No trailing returns, no OCF in that payload.** OCF on the fund **detail** page or `/documents/{guid}/{ISIN}` |
| **Franklin Templeton HK** | `franklintempleton.com.hk/en-hk/our-funds/price-and-performance/mutual-funds` | ✅ GraphQL | Accept role selector + "Accept" + "Ok" first. **`op=FundOverviewSummary` → `ONGOING_CHARGE_RATIO` is the OCF.** Also IntlCorePpss (NAV, charges), IntlIndentifiers (ISIN), IntlRatings (M★) |
| **J. P. Morgan HK** | `am.jpmorgan.com/hk/en/asset-management/per/products/fund-explorer/retail-funds/distribution` | ✅ | The bare `/products/` path is an **empty 304-byte AEM stub** — that is why it looked dead. Unauthed JSON: `FundsMarketingHandler/fund-explorer` (271 classes → ISINs), `/product-data?cusip={ISIN}` (fees) |
| **Fidelity (Intl) HK** | `fidelity.com.hk/api/ce/fdh/FundList.json?country=hk`; docs `fidelityinternational.com/FILPS/Documents/en/current/mf.en.gb.{ISIN}.pdf` | ✅ **SOLVED** | The missing param is **`country=hk`** (singular). `countries=hk` alone → `missing.request.parameter`; `country=hk` alone → **200, 558 KB, 563 share classes, all with ISIN**. Also works: `?country=hk&language=en`, `?country=hk&channels=ce.private-investor`, and `.jsvar?var=FUND_LIST&country=hk&language=en`. This is a *whole-universe* call, not per-fund. Carries `shareClassFacts.{isin,currencyName,shareType}`, `priceData.nav`, `performance.items.fund.{1y,3y}`, `ratings.risk` — **but NO OCF, NO 5y, NO volatility.** Akamai 403 to curl *and* to a browser-UA curl; needs in-page `window.fetch()` under real Chrome. The **factsheet PDFs need no browser at all — plain curl 200**. The pattern is discoverable from the content engine: any `api/ce/{mod}/{File}.json` wants the `countries`/`country`/`languages`/`channel` quartet |
| **Manulife HK** (plan API) | `www.manulife.com.hk/bin/funds/fundslist?productLine=ilas&overrideLocale=en_HK` | ✅ | **403 to plain curl — beat it by replaying a real-Chrome `ml_cookies.txt` through curl; no browser needed after that.** One endpoint covers the whole universe: returns, NAV, risk, `managementFee` (**the wrapper fee — not OCF, D2**), daily `fundhistory` for vol |
| **Manulife IM** | `manulifeim.com.hk` | ✅ | Akamai-403 to curl; real Chrome + xvfb + webdriver override works. XHR fragment `…/funddetails.details.fid-{classId}.html` → ISIN + `documents.latest[factsheet\|product-key-facts\|prospectus]`. **SFC KFS PDFs carry exact per-class "Ongoing charges"** — the OCF source |
| **Ninety One** | `ninetyone.com/en/hong-kong/funds-literature/funds` | ✅ | Cloudflare present but **200 with real Chrome + webdriver override**. ISIN list at that path; HK KFS PDFs under `/-/media/documents/...`, retrievable via in-page `fetch()` once a CF cookie is held |
| **Schroders** | `schroders.com/en-hk/hk/individual/fund-centre/` | ✅ | Fund centre is at that exact path. `body.nextjs.schrd.eu-central-1.isgdigital.com/.../gfc/fund/search/filter/` (77 funds) + `api.schroders.com/document-store/{NAME}-FMR-UNEN.pdf`. FMR/PKFS carry fees |
| **Invesco HK** | `invesco.com.hk/en/home` | ✅ | Needs a country-splash POST to `/bin/landingpage`; the **Confirm button is disabled until the disclaimer is scrolled**. `dng-api.invesco.com/product/search` (307 HK classes). HK KFS is **per share class** |
| **Amundi HK** | `amundi.com.hk` | ✅ | Force-redirects to `zh_retail` — **use the zh site, same fee data**. `product-services/tip/shares/v2/.../search.json` (`locale=en-HK`, 260 classes) + `dl/doc/{path}` for PDFs |
| **BNP Paribas AM** | `www.bnpparibas-am.com` (**the `.com` root**) | ✅ | `bnpparibas-am.com.hk` has **zero DNS records** — the old "DNS_FAILURE" was a typo'd TLD. Unblocked JSON: `api.bnpparibas-am.com/push/fundsheet/IP_HK-FSE/ENG/HKG/{ISIN}` (fees + factsheet/KFS URLs) |
| **AllianceBernstein** | `alliancebernstein.com` / `.com.hk` (both 200) | ✅ | Fund-finder API `POST /v2/funds/hk/en/investor/fundfinder-performance?frequency=monthly`, body `{}` (800 classes). `expenseRatio` is null at list level — **use the per-ISIN `/fees-and-expenses` endpoint** |
| **Value Partners** | `valuepartners-group.com` | ✅ | **`vp.com.hk` is genuinely dead** (DNS/curl 000) but the group domain is a valid cert, 200. Public doc library is login-gated; the KFS is still exposed at `/ftp/files/reports/vpgb/007_memorandum/eng/vpgb_memorandum_en.pdf` |
| **Barings** | `barings.com` | ✅ | Server-rendered fund pages + factsheet class schedules give ISIN and fees. Watch FT.com: its `IE0000830236` record is internally inconsistent and under-reports OCF by 125bp |
| **T. Rowe Price** | `troweprice.com/financial-intermediary/hk/en/...` | ✅ | The 502 is **path-specific**: the whole `/personal-investor/*` tree returns "Maintenance" on 6/6 retries while `/` returns 200. API needs an `apikey` header published in the page's inline config |
| **First Sentier** | **`firstsentierinvestors.com`** | ✅ via KFS | **`firstsentier.com` is a legacy/typo domain**: mixed DNS (dead Akamai IPs where :443 blackholes while :80 is OPEN) → Chrome picks a dead address and hangs on TLS. That is the old 35/40/45s "timeout". HK statutory KFS PDFs give the OCF directly |
| **Janus Henderson** | `www.janushenderson.com` (root, resolves to 駿利亨德森) | ✅ | **`hk.janushenderson.com` does not resolve.** `ERR_NETWORK_CHANGED` was bundled-Chromium. Plan's A2 USD class is **1.87%** OCF |
| **Hang Seng IM** | **`www.hangsenginvestment.com`** | ✅ | **`hsi.com.hk` is Hang Seng Indexes Company — a different company**, serving an unrelated SPA shell. Two traps: the URL alone does not select the class (`FundClass=A&FundUnit=ACC` silently returns the **AUD-hedged** class), and factsheet OCR dropped a digit from the ISIN |
| **PIMCO** | `pimco.com/hk/en/investments/gis/{FUND}/**e**-usd-accumulation` | ✅ | **Not 404 — the share-class slug was wrong** (`eg-usd-accumulation` does not exist). Its own `fund-detail-api` is genuinely broken (302→404) so the on-page fee tab never loads; use the factsheet or PRIIP KID |
| **UBS** | `ubs.com` + `api.fundinfo.com` | ⚠️ 403 Akamai | Real Chrome gets 200 then hits a role/cookie gate. Fees recovered from **issuer-authored** KIDs/factsheets via `api.fundinfo.com` and Hang Seng's document CDN. Do **not** substitute a sibling base-currency class — hedging cost lives inside the class |
| **Pictet** | `www.pictet.com` (bare → 302 → `/hk/en` 200) | ⚠️ 404 + hCaptcha | `/individual/funds` genuinely 404s and no fund URLs exist in any sitemap. hCaptcha on detail pages — use FT.com + third-party KIDs |
| **BlackRock** | `blackrock.com/hk/en/products/**products-list**` | ⚠️ path + gate | The old 404s rendered BlackRock's **real nav shell** — the paths were guesses, not blocks. A **T&C modal must be accepted**; OCF lives on `/hk/en/products/{id}/{slug}`. Reusable: `GET /hk/en/product-screener/product-screener-v3.1.jsn?dcrPath=/templatedata/config/product-screener-v3/data/en/hk-one/product-screener-backend-config&siteEntryPassthrough=true` (1500 HK products). **A share class matters**: 27 classes on one fund, and an unhedged class is a different ISIN |
| **Capital Group** | `capitalgroup.com/individual-investors/hk/en/investments/{FUND-NAME}.html` | ✅ | Factsheet share-class table is the OCF source |
| **ChinaAMC** | ChinaAMC `/jeecg-boot/fund/tFund/allOptions` | ✅ | HK KFS carries "Ongoing charges over a year" |
| **Nikko AM → Amova** | `hk.amova-am.com` | ⚠️ rebranded | Needs role selector + disclaimer accept |

## Traps that produced wrong numbers, not just blocks

- **Share class decides the ISIN and the fee.** BlackRock: 27 classes on one fund; the
  unhedged A2 USD is a *different* ISIN from the hedged one. Invesco/Schroders KFS are
  per class. Fidelity China High Yield: the plan's own `underlyingFundName` says
  A-MINCOME(G)-USD, but the plan's NAV matches A-ACC-USD. Match on ISIN first, name second.
- **`performance.items.fund` from a fund house is usually CUMULATIVE, not annualised.**
  Fidelity's `3y` matches its own factsheet "Fund cumulative growth" 3yr column
  (America Fund: API 33.26349 vs cumulative 33.3, annualised 10.0). Reading it as
  annualised overstates a 5-year return by ~3x. Check against the factsheet before
  publishing a multi-year figure.
- **A single `0` in a returns field is a gap, not a return.** Fidelity's China Innovation
  A-ACC-HKD is the *only* one of 563 share classes with `1y == "0"` — null it (D1). It was
  a real gap, and the fund's own factsheet was 14 months stale, so neither source could fill it.
- **Same name, different fund.** Allianz carries `Alliance Income and Growth` alongside
  `Balanced Income and Growth`, `Selection Income and Growth` and `Select Income and
  Growth`. A loose substring match pulls a different portfolio entirely — that is where a
  "70% p.a. 3Y" reading came from.
- **FT.com can be wrong.** Its `IE0000830236` record is internally inconsistent (GBP
  price, institutional minimum) and under-reports OCF by 125bp. A same-name class on FT
  is not automatically the class the plan holds.
- **UBS sibling-class substitution.** `LU0086177085` EUR-hedged carries 1.30%; the plan's
  USD-hedged class carries 1.38% because hedging cost sits inside the class.
- **`hsi.com.hk` is Hang Seng Indexes Company**, not Hang Seng Investment Management.
  The open host is `www.hangsenginvestment.com`. Its `FundClass=A&FundUnit=ACC` silently
  returns the AUD-hedged class.
- **`bnpparibas-am.com.hk` has zero DNS records.** Use the `.com` root.
- **`firstsentier.com` is a legacy domain** whose dead IPs blackhole :443 while :80 is
  open, so Chrome hangs on TLS. The live host is `firstsentierinvestors.com`.
