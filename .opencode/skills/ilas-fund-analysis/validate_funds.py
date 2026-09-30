#!/usr/bin/env python3
"""Mechanical contract check for an ilAS-data-extract enriched CSV.

Usage:
    python3 validate_funds.py funds.csv [--rf 4.0] [--json plan_harvest.json]

Exit 0 = contract satisfied. Exit 1 = at least one violation.

This exists to catch the specific defects that produced real bad data in a live
run, all of which are mechanically detectable and therefore must never again be
caught by an agent's memory:

  D1  `y3`/`y5 == 0.0` is a MISSING-DATA SENTINEL, not a 0% return.
      Treating it as 0% ranks every recently-launched share class catastrophic.
  D2  A wrapper/policy fee is not an OCF. Providers expose the plan-level
      investment-choice fee next to the fund and it looks like a fee field.
      Substituting it for `ter` silently invents the single number the whole
      downstream comparison depends on.
  D3  A Sharpe's numerator and denominator must come from the same fund and the
      same window, and the vol actually used must be published. Otherwise the
      published Sharpe cannot be recomputed from the published columns.
  D4  The plan platform name is not a fund house. A provider's fund-list API
      sets `platformName`/`providerName` to the plan sponsor for every row, so
      trusting that field labels all 100+ funds as one house.
  D5  Aggregator pages can be stale snapshots. A source that enumerates a
      universe is not automatically current; assert freshness before trusting it.
  D6  A source's own liveness flag is not a wind-up check. Providers keep
      pricing funds after announcing compulsory redemption.
"""

import argparse
import csv
import json
import os
import sys
from collections import Counter

RF_DEFAULT = 4.0
NA = {"", "N/A", "n/a", "nan", "None", "none", "null", "NULL", "-"}

REQUIRED = [
    "code", "name", "house", "region", "sector", "type", "nav",
    "ret_1y", "ret_3y", "ret_5y", "vol_annual",
    "sharpe_1y", "sharpe_3y", "sharpe_5y",
    "ter", "ter_basis", "ter_source", "data_source",
]
REQUIRED_FOR_CONTRACT = [
    "wrapper_fee_pct",      # D2
    "sharpe_basis_flag",    # D3
    "liveness_checked",     # D6
    "ret_src_3y",           # D1 backfill provenance
    "ret_src_5y",
]
VALID_TER_BASIS = {"OCF", "TER", "ongoing_charges", "unavailable"}
VALID_REGIONS = {
    "North America", "Europe", "Japan", "Asia Pacific ex-Japan",
    "Greater China", "EM", "Emerging Markets", "Global",
}
VALID_RET_SRC = {
    "plan_share_class", "underlying_fund", "insufficient_history",
    "not_covered", "unavailable",
}
# D4: a plan sponsor / platform name is not a fund house.
PLATFORM_NAMES = {
    "manulife", "prudential", "axa", "aviva", "generali", "aia",
    "fubon", "ctf life", "chow tai fook", "YF life", "YF Life",
}


class Check:
    def __init__(self):
        self.fails, self.warns, self.oks = [], [], 0

    def fail(self, code, rule, msg):
        self.fails.append((code, rule, msg))

    def warn(self, code, rule, msg):
        self.warns.append((code, rule, msg))

    def ok(self):
        self.oks += 1

    def req(self, cond, code, rule, msg):
        if cond:
            self.ok()
        else:
            self.fail(code, rule, msg)


def na(v):
    return v is None or str(v).strip() in NA


def fnum(v):
    if na(v):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--rf", type=float, default=RF_DEFAULT)
    ap.add_argument("--json", default=None,
                    help="optional plan_harvest.json, to cross-check raw sentinel values")
    a = ap.parse_args()

    if not os.path.exists(a.csv_path):
        print(f"[FAIL] {a.csv_path} not found")
        return 1
    with open(a.csv_path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("[FAIL] CSV is empty")
        return 1

    c = Check()
    codes = [r.get("code", "") for r in rows]
    print(f"validate_funds.py — {a.csv_path} — {len(rows)} funds, {len(rows[0])} columns\n")

    # ---- R0: contract columns present -----------------------------------
    missing = [k for k in REQUIRED + REQUIRED_FOR_CONTRACT if k not in rows[0]]
    if missing:
        c.fail("(schema)", "R0", (
            f"missing required column(s): {missing}. "
            f"The contract needs {REQUIRED_FOR_CONTRACT} on top of the base schema. "
            f"See SKILL.md 'Output CSV Schema'."
        ))
        report(c)
        return 1

    # ---- D1: 0.0 sentinel ----------------------------------------------
    d1 = 0
    for r in rows:
        for per in ("1y", "3y", "5y"):
            v = fnum(r.get(f"ret_{per}"))
            if v is not None and abs(v) < 1e-9:
                d1 += 1
                flag = (r.get(f"ret_{per}_flag") or "").strip()
                src = (r.get(f"ret_src_{per}") or "").strip()
                ok = bool(flag) and src == "insufficient_history"
                c.req(
                    ok, r["code"], "D1",
                    f"ret_{per} == 0.0 with no explanation. 0.0 is a MISSING-DATA "
                    f"SENTINEL, not a 0% return. Set it null and set "
                    f"ret_{per}_flag + ret_src_{per}=insufficient_history, or backfill "
                    f"from the underlying fund. A real 0%% needs a flag too.",
                )
    if d1:
        print(f"  D1: {d1} unflagged 0.0 return value(s)\n")

    # ---- D1b: backfill provenance declared -----------------------------
    for r in rows:
        for per in ("3y", "5y"):
            src = (r.get(f"ret_src_{per}") or "").strip()
            c.req(
                src in VALID_RET_SRC, r["code"], "D1b",
                f"ret_src_{per}={src!r} is not one of {sorted(VALID_RET_SRC)}. "
                f"Every multi-period return must declare whether it came from the "
                f"plan share class or the underlying fund.",
            )

    # ---- D2: wrapper fee is not an OCF ---------------------------------
    for r in rows:
        w = fnum(r.get("wrapper_fee_pct"))
        t = fnum(r.get("ter"))
        c.req(
            w is not None, r["code"], "D2",
            "wrapper_fee_pct is empty. A provider fund-detail API usually exposes a "
            "plan-level investment-choice fee next to the fund; it is NOT the fund's "
            "OCF. Publish it under its own name so it cannot be mistaken for `ter`.",
        )
        if w is not None and t is not None and abs(w - t) < 1e-9:
            # Equality is a SIGNAL, not proof. Two genuinely different charges can
            # coincide -- an internally managed fund whose all-in plan fee equals the
            # wrapper fee, or a fund whose OCF happens to match. Only a bare
            # field-name source makes it a conflation. Warn, and let the human confirm.
            c.warn(r["code"], "D2",
                   f"ter ({t}) == wrapper_fee_pct ({w}). Verify these are two different "
                   f"charges and not the wrapper fee written into `ter` "
                   f"(ter_basis={r.get('ter_basis')!r}, ter_source={r.get('ter_source','')[:60]!r}). "
                   f"An internally managed fund's all-in plan fee legitimately equals "
                   f"the wrapper fee -- that is not a conflation.")
        basis = (r.get("ter_basis") or "").strip()
        c.req(
            basis in VALID_TER_BASIS, r["code"], "D2b",
            f"ter_basis={basis!r} not in {sorted(VALID_TER_BASIS)}. Record WHICH measure "
            f"this is — OCF excludes transaction costs, TER does not; they are not "
            f"interchangeable.",
        )
        c.req(
            not na(r.get("ter_source")), r["code"], "D2c",
            "ter_source is empty. Every TER needs a named document or endpoint.",
        )
        if not na(r.get("ter")) and re_bad_source(r.get("ter_source", "")):
            c.fail(r["code"], "D2d",
                   f"ter_source={r['ter_source']!r} looks like a plan-level wrapper fee "
                   f"field, not a fund cost document.")

    # ---- D3: Sharpe basis + reproducibility ---------------------------
    d3 = 0
    for r in rows:
        for per in ("3y", "5y"):
            g = fnum(r.get(f"ret_{per}_gross"))
            s = fnum(r.get(f"sharpe_{per}_gross"))
            v = fnum(r.get(f"vol_{per}_used"))
            if v in (None, 0.0):
                v = fnum(r.get("vol_annual"))
            if g is None or s is None or not v:
                continue
            exp = (g - a.rf) / v
            if abs(s - exp) > 0.005:
                d3 += 1
                c.fail(r["code"], "D3",
                       f"sharpe_{per}_gross={s} but (ret_{per}_gross {g} - {a.rf}) / "
                       f"vol {v} = {exp:.4f}. The published Sharpe is not recomputable "
                       f"from the published columns. Publish vol_{per}_used = the vol "
                       f"you actually divided by.")
    if d3:
        print(f"  D3: {d3} Sharpe(s) not recomputable from published columns\n")

    for r in rows:
        flag = (r.get("sharpe_basis_flag") or "").strip()
        c.req(
            bool(flag), r["code"], "D3b",
            "sharpe_basis_flag is empty. State whether each Sharpe's return and vol "
            "come from the same fund and window ('matched', '3y', '5y', '3y+5y').",
        )
        for per in ("3y", "5y"):
            rs = (r.get(f"ret_src_{per}") or "").strip()
            vs = (r.get(f"vol_{per}_source") or "").strip()
            if not (rs and vs) or rs == vs:
                continue
            # If no Sharpe is computed for this horizon there is no mix to disclose.
            # A missing vol is not a basis mismatch -- it means no Sharpe exists,
            # and vol_<N>y_used must never be reused to manufacture one.
            if fnum(r.get(f"sharpe_{per}_gross")) is None:
                continue
            # A mixed pair is legitimate ONLY when no source published the matching
            # vol (plan share class launched after the lookback) -- and then it must
            # be disclosed in sharpe_basis_flag. Silent mixing is the defect.
            c.req(
                per in flag,
                r["code"], "D3c",
                f"{per}: return basis {rs!r} != vol basis {vs!r} but sharpe_basis_flag "
                f"is {flag!r} and does not name {per}. A backfilled underlying-fund "
                f"return should be paired with an underlying-fund vol. If no source "
                f"published one, the mix is allowed but MUST be disclosed by naming "
                f"'{per}' in sharpe_basis_flag.",
            )

    # ---- D4: house is not the platform --------------------------------
    d4 = Counter()
    for r in rows:
        h = (r.get("house") or "").strip()
        c.req(bool(h), r["code"], "D4", "house is empty")
        if h.lower() in PLATFORM_NAMES:
            d4[h] += 1
            c.fail(r["code"], "D4",
                   f"house={h!r} is a plan sponsor/platform name, not a fund manager. "
                   f"Provider fund-list APIs label every row with the plan platform. "
                   f"Derive house from the underlying fund name / share class.")
    if d4:
        print(f"  D4: {sum(d4.values())} row(s) labelled with a platform name: {dict(d4)}\n")

    # ---- D5: source freshness -----------------------------------------
    # A plan/provider page is exactly as capable of being a stale snapshot as an
    # aggregator is -- the frozen-2021 page that produced a 4%-complete dataset was
    # a provider-style fund-price table. Key on the source TYPE, not on brand names.
    STALE_RISK = ("hket", "invest.hket", "aggregator", "fund-price", "fund price",
                  "fundprice", "price page", "fund list", "fundlist", "portal",
                  "comparator", "etnet", "fsmone", "aastocks", "provider table")
    for r in rows:
        ds = (r.get("data_source") or "").lower()
        if any(k in ds for k in STALE_RISK):
            fc = (r.get("freshness_checked") or "").strip()
            c.req(
                bool(fc), r["code"], "D5",
                "data_source names a plan/provider/aggregator fund-price page but "
                "freshness_checked is empty. A stale snapshot still enumerates a full-"
                "looking universe — record the as-of date of the prices it actually "
                "returned.",
            )
    fc_any = sum(1 for r in rows if (r.get("freshness_checked") or "").strip())
    if fc_any == 0 and any("hket" in (r.get("data_source") or "").lower() for r in rows):
        pass  # already reported per-row above

    # ---- D6: liveness cross-check -------------------------------------
    for r in rows:
        c.req(
            not na(r.get("liveness_checked")), r["code"], "D6",
            "liveness_checked is empty. A provider's own suspend/switch flag is not a "
            "wind-up check: funds announced for compulsory redemption keep returning a "
            "live NAV and suspend=N. Record where you confirmed the fund is still "
            "open (house notice / KFS / provider fund list).",
        )

    # ---- R9: taxonomy --------------------------------------------------
    for r in rows:
        reg = (r.get("region") or "").strip()
        c.req(reg in VALID_REGIONS, r["code"], "R9",
              f"region={reg!r} not in {sorted(VALID_REGIONS)}")
        c.req(not na(r.get("type")), r["code"], "R9", "type is empty")

    # ---- optional cross-check vs raw harvest --------------------------
    if a.json and os.path.exists(a.json):
        raw = json.load(open(a.json))
        if isinstance(raw, dict) and "funds" in raw:
            raw = raw["funds"]
        rawmap = {x.get("code"): x for x in raw if isinstance(x, dict)}
        n_sent = 0
        for r in rows:
            h = rawmap.get(r.get("code"))
            if not h:
                continue
            for per, key in (("3y", "y3"), ("5y", "y5")):
                rawv = h.get(f"ret_{per}")
                srcv = h.get(f"ret_src_{per}")
                if rawv is not None and abs(rawv) < 1e-9 and srcv != "insufficient_history":
                    n_sent += 1
                    c.fail(r["code"], "D1",
                           f"raw {key} == 0.0 but ret_src_{per}={srcv!r}. The raw API "
                           f"sentinel was passed through as a real return.")
        if n_sent:
            print(f"  D1 cross-check: {n_sent} raw sentinel(s) passed through\n")

    report(c)
    return 1 if c.fails else 0


# A ter_source that resolves to a real document or endpoint is trustworthy even
# if it also mentions the management fee. Only a bare wrapper-field name with no
# concrete locator is a conflation. Test for the locator, don't blocklist.
_SOURCE_LOCATOR = (
    "http", "op=", ".pdf", "charges.", "ongoing_charge", "tearsheet", "kfs",
    "key facts", "kid", "pr iip", "priip", "brochure", "factsheet", "monthly",
    "p.", "page", "s.f.c", "sfc", "/api", "hksfc", "notice", "annex",
)


def re_bad_source(s):
    """True only when ter_source is a bare plan-level fee field with no locator."""
    s = (s or "").strip().lower()
    if not s or s in ("unavailable", "n/a"):
        return False
    has_locator = any(k in s for k in _SOURCE_LOCATOR)
    mentions_wrapper = any(
        k in s for k in ("managementfee", "management fee", "wrapper", "policy fee",
                         "platform fee")
    )
    # A source that names a wrapper field but also names where to look is fine.
    return mentions_wrapper and not has_locator


def report(c):
    by_rule = Counter(r for _, r, _ in c.fails)
    if c.fails:
        print(f"{'RULE':6} COUNT  MESSAGE")
        for rule, n in sorted(by_rule.items(), key=lambda kv: -kv[1]):
            print(f"{rule:6} {n:5}  (first: {next(m for _, rr, m in c.fails if rr == rule)[:150]})")
        print()
        for w in c.warns[:10]:
            print("[WARN]", w[0], w[1], w[2][:120])
        print(f"\nCONTRACT FAILED: {len(c.fails)} violation(s) across {len(by_rule)} rule(s), "
              f"{len(c.warns)} warning(s).")
        print("D1 0.0 = sentinel | D2 wrapper != OCF | D3 return/vol basis | "
              "D4 platform != house | D5 aggregator freshness | D6 liveness cross-check")
        sys.exit(1)
    print(f"CONTRACT OK: {c.oks} checks passed, {len(c.warns)} warning(s).")


if __name__ == "__main__":
    sys.exit(main())
