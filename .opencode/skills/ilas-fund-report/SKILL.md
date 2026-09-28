---
name: ilas-fund-report
description: >-
  Use when the user asks for a reallocation report, model portfolio, or asset
  allocation for an ILAS plan. Triggers on "reallocation", "model portfolio",
  "asset allocation", "age-based allocation", "what should I buy/sell",
  "rebalance", "fund ranking", "top funds", "best allocation for [plan name]",
  "HTML report", "age tabs".
  DO NOT use for data extraction — that's ilAS-data-extract.
  DO NOT use for macro research — that's macro-research.
---

# ILAS Fund Reallocation Report — Top-Down Analysis

## Overview

Produce a reallocation report for an ILAS plan using a strict **top-down** methodology. This skill is the **analysis layer** only — it assumes enriched fund data (with NAV, returns, vol, Sharpe, TER, region, sector, type) has already been extracted. If it hasn't, stop and invoke `ilAS-data-extract` first.

**Critical rule #1 (METHODOLOGY ORDER): You MUST follow top-down in this exact order: Macro → Regional → Sector → Funds → Portfolio. Do NOT reverse this order. If you find yourself picking funds first and then justifying with macro, STOP — you're doing it wrong.**

**Critical rule #2 (AGE-STRATIFIED): Always produce three age-stratified portfolios (Senior 60+, Mid-40s, Young 20-30s). One-size-fits-all is unacceptable.**

**Critical rule #3 (FEE AWARENESS): All return comparisons must be gross-of-TER (standardised). Net-of-TER shown alongside. Never compare funds on net returns alone — TER differences create misleading rankings.**

**Critical rule #4 (DATA GATE — HARD STOP): You MUST NOT generate any report output (MD, HTML, or partial) if the coverage gate (≥90%) is not met. The prerequisites section above contains mandatory checks. If coverage < 90%, your ONLY action is to invoke `ilAS-data-extract` to fix the data. Generating a report with incomplete data is a critical failure — it produces misleading recommendations that could cost the user money.**

**Critical rule #5 (HTML CONTRACT): Write `report.json` then copy `template.html` + `report.js` from this skill. The page fetch()es JSON. MUST match `html-report-contract.md`. Chat MUST NOT paste HTML. Serve the directory (LAN/tailnet) and put Markdown in chat.**

**Critical rule #6 (CLEAN WORKSPACE): Each run starts empty.** Delete prior extract/report artifacts (`en.txt`, `zh.txt`, `*.json` fund dumps, `index.html`, `funds.js`, old CSVs) before fetching. Do not reuse last-run JSON. Keep only scripts/templates. See `RUN.md`.

## Parameter Extraction

| Parameter | Type | Required | Default |
|-----------|------|----------|---------|
| `plan_name` | String | Yes | — |
| `data_csv_path` | String | Yes | — |
| `macro_json_path` | String | No | Auto-detect from `/tmp/opencode/macro_context.json` |
| `currency` | String | No | USD |
| `age_profile` | String | No | "all" (produce all three) |

## Prerequisites — HARD GATES, NO EXCEPTIONS

Before running this skill, verify ALL of the following. If ANY check fails, STOP and do NOT proceed.

### Gate 1: CSV exists and has required columns

Check that the enriched CSV exists and contains these columns: `code`, `name`, `region`, `sector`, `type`, `nav`, `ret_1y`, `ret_3y`, `ret_5y`, `vol_annual`, `sharpe_1y`, `sharpe_3y`, `sharpe_5y`, `ter`, `ter_source`

If the CSV is missing → invoke `ilAS-data-extract`
If columns are missing → the CSV is incomplete, invoke `ilAS-data-extract`

### Gate 2: Coverage ≥ 90% (MANDATORY — DO NOT SKIP)

Read the CSV and compute:

```python
import csv
with open(csv_path) as f:
    reader = csv.DictReader(f)
    rows = list(reader)
total = len(rows)
complete = sum(1 for r in rows if all([
    r.get('ret_1y', '') not in ('', 'N/A', 'nan', 'None'),
    r.get('ret_3y', '') not in ('', 'N/A', 'nan', 'None'),
    r.get('ret_5y', '') not in ('', 'N/A', 'nan', 'None'),
    r.get('ter', '') not in ('', 'N/A', 'nan', 'None'),
    r.get('region', '') not in ('', 'N/A', 'nan', 'None'),
    r.get('sector', '') not in ('', 'N/A', 'nan', 'None'),
    r.get('type', '') not in ('', 'N/A', 'nan', 'None'),
]))
coverage = complete / total * 100 if total > 0 else 0
```

**If coverage < 90%:**
1. Print the coverage report showing exactly which funds are missing data
2. Print: "COVERAGE GATE FAILED: {coverage:.1f}% < 90%. Cannot generate report. Invoke ilAS-data-extract to complete data extraction."
3. **STOP. Do NOT generate a report. Do NOT write partial output. Do NOT ask the user if they want to proceed anyway.**
4. The ONLY acceptable action is to invoke `ilAS-data-extract` to fix the data.

### Gate 3: Macro context exists

Check that `/tmp/opencode/macro_context.json` exists and is valid JSON.

If missing → invoke `macro-research`

### Gate 4: TER coverage ≥ 90%

Compute TER coverage separately:
```python
ter_coverage = sum(1 for r in rows if r.get('ter', '') not in ('', 'N/A', 'nan', 'None')) / total * 100
```

If ter_coverage < 90% → invoke `ilAS-data-extract` (Phase 1.x)

### Summary of gates

| Gate | Check | Fail action |
|------|-------|-------------|
| 1 | CSV exists + has columns | Invoke `ilAS-data-extract` |
| 2 | Coverage ≥ 90% | Invoke `ilAS-data-extract` |
| 3 | Macro JSON exists | Invoke `macro-research` |
| 4 | TER coverage ≥ 90% | Invoke `ilAS-data-extract` |

**You MUST NOT bypass these gates. There is no "proceed anyway" option. The skills exist to enforce quality.**

## Workflow: Top-Down in Order

### Phase 1: Macro → Map to ILAS Universe

Read the macro context JSON. Identify the 3 most investable asset classes / regions / sectors based on the macro picture. This is your **macro thesis** — it drives ALL downstream decisions.

For each macro theme, map to concrete fund categories:
```
Macro Theme → ILAS Category Mapping
─────────────────────────────────────
Fed cutting, USD weak → EM equities, DM ex-US, gold
BOJ hiking, TSE reform → Japan equities
AI capex supercycle → Tech/semiconductor sector
Gold structural bid → Gold/precious metals
China stimulus → China/HK equities
GLP-1 disruption → Healthcare sector
```

**Hard rule: At this point, NO individual fund names have been mentioned. This is purely thematic.**

### Phase 2: Regional Views

Using the enriched CSV, filter funds by `region` column. For each region:
- Compute average 1Y/3Y/5Y returns (gross-of-TER)
- Compute average Sharpe ratio
- Identify top quartile funds
- Map back to macro thesis: which regions are overweight vs underweight

Regional categories:
- North America
- Europe (developed)
- Japan
- Asia Pacific (ex-Japan)
- Greater China
- Emerging Markets (broad)
- Global

Output a regional summary table:

| Region | # Funds | Avg 1Y | Avg 3Y | Avg 5Y | Avg Sharpe | Macro Tilt |
|--------|---------|--------|--------|--------|------------|------------|
| ... | ... | ... | ... | ... | ... | OW/UW/Neutral |

### Phase 3: Sector Views

Using the enriched CSV, filter funds by `sector` column. For each sector:
- Same analysis as regional
- Map to macro thesis
- Note concentration risks (e.g., tech-heavy)

Sector categories:
- Technology / AI
- Healthcare
- Financials
- Energy / Resources
- Consumer
- Real Estate
- Industrials
- Utilities
- Broad / Multi-sector

### Phase 4: Fund Selection (Top Quartile, by Region + Sector)

Only NOW do individual fund names appear. For each macro-overweight region+sector combination:
- Rank funds by Sharpe ratio (gross-of-TER)
- Apply tiering: Tier 1 (top quartile), Tier 2 (second quartile), Tier 3 (below median)
- Check sizing: **at most 10 holdings**, **each ≥ 10%**, no fund house >30%
- Verify liquidity: prefer funds with 5Y track record
- Flag any fund with TER >2% (high-cost warning)

Fund selection criteria (in priority order):
1. Gross-of-TER Sharpe ratio (1Y, confirmed by 3Y)
2. Consistency: 3Y return > median for its category
3. TER: lower is better, all else equal
4. Track record: prefer 5Y history
5. Diversification: **max 10 holdings**, **min 10% per holding**, max 30% per fund house

### Phase 5: Age-Stratified Portfolio Construction

Build three model portfolios. Each must be:
- Fully invested (100% allocation)
- **At most 10 funds; every weight ≥ 10%** — these are **caps/floors, not a target**. Pick the smallest set that expresses the macro thesis. Filling 10 names forces 10×10% equal weight and **washes out conviction**. Prefer 6–8 names with 10–20% weights. State why that count, not “because the max is 10”.
- House-constrained (no single fund house >30%)
- Risk-appropriate for the age group
- A 5% / 8% “sleeve” is invalid — raise it to ≥10% or drop the name
- Do **not** add funds just to reach 10
- Shortlist and age portfolios use the **same investable set**. Unusable names are deleted from the shortlist, not footnoted.
- Do **not** give >10% to a name you have flagged as Sharpe/vol biased (short wrapper history). Drop it or keep at the 10% floor with the flag in the reason.
- Calendar-year worst return is **not** max drawdown. If you cannot compute MDD from daily/monthly NAV, write “MDD unavailable”.

#### Senior (60+)
- 60% income / defensive (bonds, high-dividend equity, multi-asset)
- 30% global / quality equity
- 10% alternatives (gold, infrastructure)
- No cash sleeve under 10% — omit cash or size it at 10% and drop another name

#### Mid-career (40s)
- 35% global equity (broad market)
- 25% regional equity (OW per macro thesis)
- 20% income (bonds, dividend equity)
- 15% growth (sector bets: tech, healthcare)
- 5% alternatives (gold, EM)

#### Young (20-30s)
- 40% growth equity (tech, AI, sector bets)
- 30% regional equity (EM, Japan, OW per macro)
- 20% global equity (broad market)
- 10% alternatives (gold, commodities)

For each portfolio, output:

| Fund Code | Fund Name | House | Region | Sector | Allocation | Tier | Rationale |
|-----------|-----------|-------|--------|--------|------------|------|-----------|
| ... | ... | ... | ... | ... | x% | T1 | ... |

## Anti-Patterns (METHODOLOGY VIOLATIONS)

These are **fatal errors** that invalidate the analysis:

1. **Picking funds first, then justifying with macro** — you MUST go top-down (Macro → Regional → Sector → Funds)
2. **Only one portfolio** — you MUST produce three age-stratified portfolios
3. **Comparing net returns across funds with different TERs** — use gross-of-TER Sharpe ratios
4. **Ignoring sizing** — more than 10 names, or any line &lt; 10% (including 5% cash)
5. **Using only 1Y data** — 1Y Sharpe confirmed by 3Y consistency
6. **No macro thesis** — every allocation must trace back to a macro theme
7. **Single fund house dominance** — diversify across managers

## Output Format

### Markdown Report Structure

```
# [Plan Name] Reallocation Report — [Date]

## Methodology Flow
Macro → Regional → Sector → Funds → Portfolio

## 1. Macro Context
[From macro-research JSON]

## 2. Regional Views
[Table + analysis]

## 3. Sector Views
[Table + analysis]

## 4. Fund Selection
[Top quartile funds by region+sector]

## 5. Model Portfolios

### 5.1 Senior (60+)
[Table + rationale]

### 5.2 Mid-career (40s)
[Table + rationale]

### 5.3 Young (20-30s)
[Table + rationale]

## 6. Key Risks & Watchlist
[Risks to the macro thesis]

## 7. Cost Summary
[TER-weighted cost per portfolio]

## Data Coverage Report
[From ilAS-data-extract output]

## COI Reminder
All underlying-fund returns are gross of cost-of-insurance (~1.5–2.5% p.a.
drag depending on age and plan). This is NOT included in the fund returns
shown above and WILL reduce your actual portfolio return.
```

### HTML Report

**REQUIRED SUB-SPEC:** Follow `html-report-contract.md` exactly. The HTML is incomplete if any required section is missing.

A rates dump is not macro analysis. A 20-fund shortlist is not the universe table. A comma-separated weight list is not an age tab. A one-word "T1" is not a pick reason.

Save as `[plan_name]_report_[date].html`. Do not paste HTML into chat.

### Completeness Checklist (HTML)

- [ ] Macro section has sourced rates **and** a written thesis + ILAS implications
- [ ] `#universe` table lists **every** fund with 1Y / 3Y / 5Y, sortable, inside `<details>`
- [ ] Every selected fund has a `reason` sentence tied to a named macro theme
- [ ] Age **tabs** (60+ / 40s / 20–30s), each showing an allocation **table** (not a sentence)
- [ ] Chat has Markdown only; HTML served on LAN/tailnet

## Data Coverage Report

Include the coverage report from `ilAS-data-extract` output:

```
## Data Coverage Report
| Status | Funds | % |
|--------|:-----:|:--:|
| Complete (returns + TER + region/sector) | n | x% |
| Partial (missing some fields) | n | x% |
| Missing (no data) | n | x% |
COVERAGE: x% — GATE ≥ 90%: PASS/FAIL
```

## COI Reminder (Always Include)

> All underlying-fund returns are gross of cost-of-insurance (~1.5–2.5% p.a.
> drag depending on age and plan). This is NOT included in the fund returns
> shown above and WILL reduce your actual portfolio return. For a 40-year-old,
> expect ~1.8% p.a. COI drag; for a 60-year-old, expect ~2.5% p.a.

## Completeness Checklist

- [ ] Macro context loaded (Phase 1 complete)?
- [ ] Regional views computed (Phase 2)?
- [ ] Sector views computed (Phase 3)?
- [ ] Fund selection done top-down (Phase 4)?
- [ ] Three age-stratified portfolios constructed (Phase 5)?
- [ ] Sizing: ≤10 holdings, each ≥10%, house ≤30%?
- [ ] All returns standardised to gross-of-TER?
- [ ] COI reminder included?
- [ ] Data coverage report included?
- [ ] Markdown + HTML both generated?
- [ ] HTML matches html-report-contract.md (macro thesis, full universe table, pick reasons, age tabs)?

## Out of Scope

- Fund data extraction (→ `ilAS-data-extract`)
- Macro research (→ `macro-research`)
- Tax / estate / insurance structuring
- Single-fund analysis without top-down context
- Performance backtesting
