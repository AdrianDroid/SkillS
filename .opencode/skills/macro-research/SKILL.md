---
name: macro-research
description: >-
  Use when the user needs current macro context for any financial analysis:
  rates (Fed, ECB, BOJ, PBOC), equity index all-time highs, gold/commodity
  drivers, geopolitical events, growth/inflation trends, market structure shifts.
  Triggers on "current rates", "macro snapshot", "what's driving markets",
  "gold outlook", "Fed funds rate", "BOJ policy", "global macro context".
  Generic — works for any market analysis, not just ILAS.
  Output is a structured JSON snapshot for consumption by other skills.
---

# Macro Research — Structured Context Gathering

## Overview

Produce a structured macro-economic snapshot for financial analysis. This skill is **reusable across any analysis** — ILAS reallocation, equity research, sector analysis, or tactical allocation. It does NOT produce recommendations; it produces **verified facts** for other skills to consume.

**Critical rule: No speculation.** Every statement must have a source URL. If you cannot verify a claim, omit it and note the gap.

## Parameter Extraction

| Parameter | Type | Required | Default |
|-----------|------|----------|---------|
| `themes` | List of strings | No | Rates, equities, commodities, geopolitics |
| `date_range` | String | No | Last 30 days |
| `currency_base` | String | No | USD |

## Workflow

### Phase 1: Rate Environment (authoritative sources)

**Preferred sources** (check in order):

1. **Federal Reserve H.15** — `https://www.federalreserve.gov/releases/h15/`
   - Fed Funds target/effective rate, SOFR, 2Y/10Y/30Y UST yields
   - Date-stamp each reading

2. **ECB** — `https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html`
   - Main refinancing rate, deposit facility rate

3. **BOJ** — `https://www.boj.or.jp/en/mpmdeci/mpr_2025/k250XXX.htm`
   - Overnight call rate target, policy rate

4. **PBOC** — `http://www.pbc.gov.cn/en/3688110/3688172/index.html`
   - LPR 1Y and 5Y

5. **Yields** — `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/all/YYYY?type=daily_treasury_yield_curve&field_tdr_date_value=YYYY&page&_format=csv`

Output for each rate:
```
| Indicator | Value | Date | Source |
|-----------|-------|------|--------|
| Fed Funds Effective | 3.63% | 29 Jul 2026 | Fed H.15 |
| 2Y UST | 4.23% | 29 Jul 2026 | Fed H.15 |
| 10Y UST | 4.68% | 29 Jul 2026 | Fed H.15 |
| BOJ Policy Rate | 0.25-0.50% | 31 Jul 2026 | BOJ |
| ECB Main Refi | 2.15% | 17 Jul 2026 | ECB |
| USD/JPY | 138 | Jul 2026 | — |
| DXY | 96.4 | Jul 2026 | — |
```

### Phase 2: Equity Indices — All-Time Highs and Key Levels

**Sources:**
- Wikipedia: `https://en.wikipedia.org/wiki/List_of_stock_market_indices` + individual index pages for historical ATH tables
- Google Finance / TradingView for current levels
- Bloomberg / Reuters for recent milestones

For each relevant index, record:
- Current level
- All-time high (date + level)
- YTD return
- Whether currently in correction/bear territory (>-10% from ATH)

Cover these by default (adjust based on `themes`):
```
| Index | Current | ATH | ATH Date | Drawdown | YTD |
|-------|---------|-----|----------|----------|-----|
| S&P 500 | ... | ... | ... | ... | ... |
| Nasdaq 100 | ... | ... | ... | ... | ... |
| Nikkei 225 | ... | ... | ... | ... | ... |
| KOSPI | ... | ... | ... | ... | ... |
| NIFTY 50 | ... | ... | ... | ... | ... |
| Hang Seng | ... | ... | ... | ... | ... |
| CSI 300 | ... | ... | ... | ... | ... |
| TOPIX | ... | ... | ... | ... | ... |
| FTSE 100 | ... | ... | ... | ... | ... |
| DAX | ... | ... | ... | ... | ... |
```

### Phase 3: Commodities & Gold

**Sources:**
- **World Gold Council** — `https://www.gold.org/goldhub/data/gold-prices`
- **J.P. Morgan Global Research** — commodity forecasts (search: `J.P. Morgan gold price forecast 2026`)
- **Lazard Asset Management** — annual macro outlook
- **IMF** — `https://www.imf.org/en/Publications/WEO` (growth/inflation forecasts)

For gold specifically:
- Current spot price
- WGC demand-supply analysis
- J.P. Morgan end-of-year forecast
- Central bank purchasing trends (ECB data: `https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_system_reserves/html/index.en.html`)
- Gold as % of global reserves vs Treasuries

Output:
```
| Asset | Value | Source |
|-------|-------|--------|
| Gold (USD/oz) | ... | ... |
| JPM EOY Forecast | $6,000/oz | J.P. Morgan |
| WGC CB Purchases | ... | WGC |
| Silver | ... | ... |
| WTI Crude | ... | ... |
| Copper | ... | ... |
| Iron Ore | ... | ... |
```

### Phase 4: Growth & Inflation

**Sources:**
- IMF World Economic Outlook: `https://www.imf.org/en/Publications/WEO`
- OECD: `https://www.oecd.org/en/topics/sub-issues/economic-outlook-and-growth.html`
- US CPI: `https://www.bls.gov/cpi/`
- US GDP: `https://www.bea.gov/data/gdp/gross-domestic-product`

Record:
- Global GDP growth forecast (current year + next)
- US GDP growth + PCE inflation
- China GDP growth
- Eurozone GDP growth
- Japan GDP growth
- US CPI / PCE latest readings

### Phase 5: Geopolitical & Structural Shifts

**Sources:**
- Council on Foreign Relations: `https://www.cfr.org/global-conflict-tracker`
- IISS: `https://www.iiss.org/`
- Chatham House: `https://www.chathamhouse.org/`

Focus on what moves markets:
- US-China relations (tariffs, tech restrictions, Taiwan)
- Middle East / oil supply risk
- European energy security
- Emerging market stability (Turkey, Argentina, etc.)
- Major elections / policy shifts

### Phase 6: Sector & Structural Themes

**Sources:**
- McKinsey Global Institute: `https://www.mckinsey.com/mgi/overview`
- Deloitte Insights: `https://www2.deloitte.com/us/en/insights.html`
- Pitchbook / CB Insights for VC/PE trends
- Company earnings calls (aggregated commentary)

Identify 2-3 structural themes relevant to the investment universe:
- AI / semiconductor capex cycle
- Energy transition
- GLP-1 / healthcare innovation
- Reshoring / supply chain restructuring
- Demographics (aging populations in DMs)

## Output Format

Return a JSON object with this schema:

```json
{
  "as_of": "YYYY-MM-DD",
  "rates": {
    "us": {"fed_funds_effective": 0.0363, "fed_funds_upper": 0.04, "ust_2y": 0.0423, "ust_10y": 0.0468, "ust_30y": 0.0482, "sofr": 0.0361},
    "eurozone": {"ecb_main_refi": 0.0215, "ecb_deposit": 0.02},
    "japan": {"boj_rate_upper": 0.005, "boj_rate_lower": 0.0025, "usdjpy": 138},
    "china": {"lpr_1y": 0.031, "lpr_5y": 0.036},
    "dxy": 96.4,
    "as_of_dates": {"us": "29 Jul 2026", "eurozone": "17 Jul 2026", "japan": "31 Jul 2026"}
  },
  "equities": {
    "sp500": {"level": 6352.22, "ath": 6352.22, "ath_date": "30 Jul 2026", "ytd_pct": 8.5},
    "nasdaq100": {"level": ..., "ath": ..., "ath_date": ..., "ytd_pct": ...},
    "nikkei225": {"level": ..., "ath": ..., "ath_date": ..., "ytd_pct": ...},
    "kospi": {"level": 3538, "ath": 9114, "ath_date": "22 Jun 2026", "ytd_pct": 32.2},
    "nifty50": {"level": 26029.4, "ath": 26327.7, "ath_date": "2 Jan 2026", "ytd_pct": 2.4},
    "hangseng": {"level": ..., "ath": ..., "ath_date": ..., "ytd_pct": ...},
    "csi300": {"level": ..., "ath": ..., "ath_date": ..., "ytd_pct": ...},
    "ftse100": {"level": ..., "ath": ..., "ath_date": ..., "ytd_pct": ...},
    "dax": {"level": ..., "ath": ..., "ath_date": ..., "ytd_pct": ...}
  },
  "commodities": {
    "gold_spot": {"price_usd_oz": 3324, "ytd_pct": 28.1},
    "gold_forecasts": {"jpm_eoy": "$6,000/oz by end-2026", "wgc_view": "..."},
    "central_banks": {"pct_global_reserves": 0.27, "vs_treasuries": 0.22},
    "silver": ..., "wti_crude": ..., "copper": ..., "iron_ore": ...
  },
  "growth": {
    "global_gdp_2026": 0.033,
    "us_gdp_2026": 0.016, "us_pce_inflation": 0.03,
    "china_gdp_2026": 0.04, "japan_gdp_2026": 0.012, "eurozone_gdp_2026": 0.009,
    "us_cpi_latest": "2.7% Jun 2026"
  },
  "geopol": {
    "us_china_tariffs": "150-530% cumulative on Chinese imports",
    "taiwan_risk": "Medium — PLA incursions continue",
    "middle_east": "Israel-Iran tensions ongoing",
    "other": "..."
  },
  "themes": ["AI capex supercycle", "GLP-1 disruption", "Central bank gold buying"],
  "sources": [
    "https://www.federalreserve.gov/releases/h15/",
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/all/2026?type=daily_treasury_yield_curve",
    "https://en.wikipedia.org/wiki/List_of_S%26P_500_index_milestones",
    "https://www.gold.org/goldhub/data/gold-prices",
    "..."
  ],
  "data_gaps": ["FTSE 100 ATH not verified", "DAX current level not found"]
}
```

## Anti-Patterns

- **Stating a value without a source URL** — every number must be verifiable
- **Mixing up "current" and "forecast"** — clearly label each
- **Ignoring the date** — a rate from Jan 2025 is useless for Jul 2026 analysis
- **Omitting the gap list** — always declare what you could NOT verify
- **Hardcoding** — if you know the answer from training data, verify it anyway; data changes

## Quality Gate

Before returning the JSON:
- [ ] Every field has a source URL in the `sources` array
- [ ] `as_of` date is within the last 7 days
- [ ] `data_gaps` lists anything you couldn't verify
- [ ] No speculative statements (only facts + forecasts with attribution)
- [ ] At least one authoritative source per category (Fed, BOJ, WGC, IMF)

## Out of Scope

- Fund-level analysis (→ `ilas-fund-report`)
- Data extraction from fund portals (→ `ilAS-data-extract`)
- Portfolio construction (→ `ilas-fund-report`)
- Tax / estate / insurance structuring
