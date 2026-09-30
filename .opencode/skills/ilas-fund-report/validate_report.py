#!/usr/bin/env python3
"""Mechanical contract check for an ilas-fund-report `report.json`.

Usage:  python3 validate_report.py [path/to/report.json] [--csv path/to/ari_enriched.csv]

Exit 0 = contract satisfied. Exit 1 = at least one violation (printed to stdout).
Run it in INTEGRATE, before writing/serving the report.

This exists because the two artifacts are easy to conflate:
`picks` is the 20-name WATCHLIST (10 growth + 10 income, no sizing rules) and
`ages.tabs` are the PORTFOLIOS (<=10 names, every weight >=10%, house <=30%).
The 20 is a fixed shape; the portfolio rules never apply to it.
"""

import argparse
import csv
import json
import os
import sys

RF_PCT = 4.0
PICK_COUNT = 10           # per leg -- pinned by report.schema.json minItems/maxItems
MIN_REASON_CHARS = 25     # below this a "reason" is a metric, not a rationale
MAX_PORTFOLIO_NAMES = 10
MIN_WEIGHT_PCT = 10.0
MAX_HOUSE_PCT = 30.0

# Never selectable: fail the data gate, or wound up / suspended.
HARD_EXCLUDE = {
    "UGZ01": "share class launched 2023-01-31, no 5Y record",
    "UHI01": "share class launched 2025-07-11, no 3Y/5Y record",
    "USG01": "compulsory redemption + termination 2026-10-30",
    "UAM01": "compulsory redemption + termination 2026-10-30",
}


class Check:
    def __init__(self):
        self.fails, self.warns, self.oks = [], [], 0

    def fail(self, where, msg):
        self.fails.append(f"[FAIL] {where}: {msg}")

    def warn(self, where, msg):
        self.warns.append(f"[WARN] {where}: {msg}")

    def ok(self, msg=""):
        self.oks += 1

    def req(self, cond, where, msg):
        if cond:
            self.ok()
        else:
            self.fail(where, msg)


def load_house_map(csv_path):
    """code -> house, from the enriched CSV. Needed for the 30% house cap."""
    if not csv_path or not os.path.exists(csv_path):
        return {}
    with open(csv_path, newline="") as f:
        return {r["code"]: (r.get("house") or "").strip() for r in csv.DictReader(f) if r.get("code")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report", nargs="?", default="report.json")
    ap.add_argument("--csv", default=None, help="ari_enriched.csv, for the house-cap check")
    a = ap.parse_args()

    if not os.path.exists(a.report):
        print(f"[FAIL] {a.report} not found")
        return 1
    with open(a.report) as f:
        d = json.load(f)
    c = Check()

    # ---- top-level shape -------------------------------------------------
    for k in ("meta", "macro", "fees", "universe", "picks", "ages", "appendix"):
        c.req(k in d, "top-level", f"missing required key '{k}'")
    if c.fails:
        report(c)
        return 1

    # ---- 1. picks = the 20-name WATCHLIST -------------------------------
    picks = d.get("picks") or {}
    growth, income = picks.get("growth") or [], picks.get("income") or []
    for leg, arr in (("growth", growth), ("income", income)):
        c.req(
            len(arr) == PICK_COUNT,
            f"picks.{leg}",
            f"expected exactly {PICK_COUNT} names, got {len(arr)}. "
            f"picks is the 20-name watchlist, NOT a portfolio: portfolio sizing "
            f"(<=10 names, >=10% each, house <=30%) does not apply here.",
        )
    total = len(growth) + len(income)
    c.req(
        total == PICK_COUNT * 2,
        "picks",
        f"expected {PICK_COUNT * 2} picks total, got {total}",
    )

    codes = [p.get("code") for p in growth + income]
    c.req(all(codes), "picks", "a pick has no 'code'")
    c.req(len(set(codes)) == len(codes), "picks", "duplicate codes in picks")

    for leg, arr in (("growth", growth), ("income", income)):
        for p in arr:
            r = (p.get("reason") or "").strip()
            code = p.get("code", "?")
            c.req(
                len(r) >= MIN_REASON_CHARS,
                f"picks.{leg}[{code}]",
                f"reason is {len(r)} chars -- too thin to be a rationale. "
                f"It must name a macro theme and why this fund over alternatives.",
            )
            if code in HARD_EXCLUDE:
                c.fail(f"picks.{leg}[{code}]", f"excluded fund in watchlist: {HARD_EXCLUDE[code]}")

    # ---- 2. portfolios: the sizing rules live ONLY here ------------------
    tabs = ((d.get("ages") or {}).get("tabs") or {})
    for band in ("60+", "40s", "20-30s"):
        c.req(band in tabs, "ages.tabs", f"missing tab '{band}'")
    c.req(bool((d.get("ages") or {}).get("why_count", "").strip()), "ages", "why_count is empty")

    house_of = load_house_map(a.csv)
    used_codes = set()
    for band in ("60+", "40s", "20-30s"):
        rows = tabs.get(band) or []
        where = f"ages.tabs['{band}']"
        if not rows:
            c.fail(where, "no rows")
            continue
        c.req(
            len(rows) <= MAX_PORTFOLIO_NAMES,
            where,
            f"{len(rows)} names exceeds the {MAX_PORTFOLIO_NAMES}-name portfolio cap",
        )
        weights = []
        for r in rows:
            code = r.get("code", "?")
            used_codes.add(code)
            w = r.get("weight")
            try:
                w = float(w)
            except (TypeError, ValueError):
                c.fail(where, f"[{code}] weight is not numeric: {w!r}")
                continue
            weights.append((code, w))
            c.req(
                w >= MIN_WEIGHT_PCT,
                where,
                f"[{code}] weight {w}% is below the {MIN_WEIGHT_PCT}% floor -- "
                f"raise it or drop the name",
            )
            if code in HARD_EXCLUDE:
                c.fail(where, f"[{code}] excluded fund in portfolio: {HARD_EXCLUDE[code]}")
            c.req(
                len((r.get("reason") or "").strip()) >= MIN_REASON_CHARS,
                where,
                f"[{code}] reason is too thin",
            )
        if weights:
            tot = sum(w for _, w in weights)
            c.req(
                abs(tot - 100.0) < 1e-6,
                where,
                f"weights sum to {tot:g}%, must be exactly 100%",
            )
        if house_of:
            per_house = {}
            for code, w in weights:
                hh = house_of.get(code)
                if hh:
                    per_house[hh] = per_house.get(hh, 0.0) + w
            for hh, pct in per_house.items():
                c.req(
                    pct <= MAX_HOUSE_PCT + 1e-9,
                    where,
                    f"house '{hh}' is {pct:g}%, over the {MAX_HOUSE_PCT:g}% cap",
                )
        else:
            c.warn(where, "house cap not checked (no --csv)")

    # ---- 3. the watchlist must be a strict superset of the portfolios ---
    if codes:
        missing = sorted(used_codes - set(codes))
        c.req(
            not missing,
            "picks vs ages",
            f"portfolio uses codes absent from the 20-name watchlist: {missing}. "
            f"The watchlist is the menu; portfolios draw from it.",
        )

    # ---- 4. universe is the FULL plan, not the shortlist ----------------
    uni = d.get("universe") or []
    fc = ((d.get("meta") or {}).get("fund_count"))
    c.req(len(uni) > 0, "universe", "empty universe table")
    if isinstance(fc, int):
        c.req(
            len(uni) == fc,
            "universe",
            f"universe has {len(uni)} rows but meta.fund_count says {fc}",
        )
    picked = set(codes)
    c.req(
        len(picked - {u.get("code") for u in uni}) == 0,
        "universe",
        "a pick is not present in the universe table",
    )

    # ---- 5. Sharpe reproducibility -------------------------------------
    # A published Sharpe must be recomputable from the published vol. Fall back to
    # vol_annual when the more precise vol_<N>y_used column is absent, otherwise
    # this check silently skips every row.
    n_checked = n_flagged = n_fallback = 0
    for u in uni:
        for per in ("3y", "5y"):
            g = u.get(f"ret_{per}_gross")
            s = u.get(f"sharpe_{per}_gross")
            v = u.get(f"vol_{per}_used")
            if v in (None, ""):
                v = u.get("vol_annual")
                if v not in (None, "") and u.get(f"ret_{per}_gross") is not None:
                    n_fallback += 1
            if g is None or not v or s is None:
                continue
            n_checked += 1
            if abs(s - (g - RF_PCT) / v) > 0.005:
                n_flagged += 1
                c.fail(
                    f"universe[{u.get('code')}]",
                    f"sharpe_{per}_gross={s} but (gross {g} - {RF_PCT}) / "
                    f"vol {v} = {(g - RF_PCT) / v:.4f}. Return and vol must come "
                    f"from the same fund and the same window. Publish vol_{per}_used.",
                )
    if n_fallback:
        c.warn(
            "universe",
            f"{n_fallback} rows lack vol_3y_used/vol_5y_used; Sharpe check fell back "
            f"to vol_annual, which is the trailing-3Y vol",
        )
    if n_flagged:
        c.warn("universe", f"{n_flagged}/{n_checked} Sharpes not reproducible from published vol")
    elif n_checked:
        c.ok()
    else:
        c.warn("universe", "no gross returns/vol published -- Sharpe check could not run")

    report(c)
    return 1 if c.fails else 0


def report(c):
    for w in c.warns:
        print(w)
    if c.fails:
        for f in c.fails:
            print(f)
        print(f"\nCONTRACT FAILED: {len(c.fails)} violation(s), {c.warns.__len__()} warning(s).")
        print("picks = 20-name WATCHLIST (10 growth + 10 income, no sizing rules).")
        print("ages.tabs = PORTFOLIOS (<=10 names, each >=10%, weights=100%, house <=30%).")
        sys.exit(1)
    print(f"CONTRACT OK: {c.oks} checks passed, {len(c.warns)} warning(s).")
    if c.warns:
        print("  (warnings are advisory -- house cap needs --csv to verify)")


if __name__ == "__main__":
    sys.exit(main())
