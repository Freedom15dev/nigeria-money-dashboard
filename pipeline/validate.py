"""Checks that must pass before anything in data/processed/ is replaced (CLAUDE.md section 4.4).

1. One row per month, no duplicates, no gaps except the known ones.
2. The latest month is the same as, or after, the previous run's latest month.
3. Values in plausible ranges.
4. Months up to Sep 2026 match the reference snapshot from the four earlier projects
   (data/reference/), except known revisions listed in KNOWN_REVISIONS below. Every
   allowed revision is printed in the run log.
5. The savings article is reproduced exactly (money_math.article_check).

validate() returns (errors, log_lines). Any error means: keep the old data, fail the run.
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from money_math import article_check  # noqa: E402

REFERENCE_DIR = ROOT / "data" / "reference"
REFERENCE_END = pd.Timestamp("2026-09-01")

# Gaps we know about and accept: (column, "YYYY-MM").
KNOWN_GAPS = {
    ("treasuryBill", "2017-12"), ("treasuryBill", "2018-12"),
    ("creditToPrivateSector", "2026-03"), ("creditToGovernment", "2026-03"),
    ("netDomesticCredit", "2026-03"), ("moneySupply_M2", "2026-03"),
}

# Accepted differences from the reference snapshot (months up to Sep 2026). Each one is printed
# in the run log. Add an entry only after checking the change by hand, e.g. when the CBN revises
# a figure:  {"project": "...", "column": "savingsDeposit", "month": "2026-09", "reason": "..."}
_FX_TYPO = ("method: this month had a one-day typo in the CBN feed, which naira-scenarios (and this "
            "dashboard) drops; this earlier project kept it")
_FX_DUP = ("method: this month has a day listed twice with two different rates; naira-scenarios (and "
           "this dashboard) averages the two; this earlier project kept only one")
KNOWN_REVISIONS = (
    [{"project": "nigeria-savings-vs-inflation", "column": "usd_ngn", "month": m, "reason": _FX_TYPO}
     for m in ["2007-08", "2008-08"]]
    + [{"project": "nigeria-savings-vs-inflation", "column": "usd_ngn", "month": m, "reason": _FX_DUP}
       for m in ["2022-03", "2023-12", "2024-02", "2024-07"]]
    + [{"project": "nigeria-inflation-forecast", "column": "usd_ngn", "month": m, "reason": _FX_TYPO}
       for m in ["2003-12", "2007-08", "2008-08"]]
    + [{"project": "nigeria-inflation-forecast", "column": "usd_ngn", "month": m, "reason": _FX_DUP}
       for m in ["2023-12", "2024-02", "2024-07"]]
)

RATE_COLUMNS = ["savingsDeposit", "twelveMonthsDeposit", "treasuryBill", "policy_rate",
                "primeLending", "maxLending", "oneMonthDeposit", "threeMonthsDeposit",
                "sixMonthsDeposit"]
INFLATION_COLUMNS = ["inflation", "food_inflation", "core_inflation"]
CREDIT_COLUMNS = ["creditToPrivateSector", "creditToGovernment", "netDomesticCredit", "moneySupply_M2"]


# --------------------------------------------------------------------------- 1. shape and gaps
def check_months(panel):
    errors = []
    if panel["month"].duplicated().any():
        errors.append(f"Duplicate months: {panel.loc[panel['month'].duplicated(), 'month'].dt.strftime('%Y-%m').tolist()}")
    expected = pd.date_range(panel["month"].min(), panel["month"].max(), freq="MS")
    if len(expected) != len(panel) or not (pd.DatetimeIndex(panel["month"]) == expected).all():
        errors.append("Months are not one continuous monthly sequence.")
    return errors


def check_gaps(panel):
    errors = []
    allowed = KNOWN_GAPS | panel.attrs.get("fixed_gaps", set())  # + one-month spikes removed by clean.py
    rules = [(INFLATION_COLUMNS + ["usd_ngn", "price_index"], "2003-01-01"),
             (RATE_COLUMNS, "2006-01-01"), (CREDIT_COLUMNS, "2006-01-01")]
    for columns, start in rules:
        part = panel[panel["month"] >= start]
        for col in columns:
            missing = part.loc[part[col].isna(), "month"]
            unknown = [m for m in missing if (col, f"{m:%Y-%m}") not in allowed]
            if col in CREDIT_COLUMNS:  # credit can be published later: missing latest months are allowed
                last_published = part.loc[part[col].notna(), "month"].max()
                unknown = [m for m in unknown if m < last_published]
            if unknown:
                errors.append(f"Unexpected gap in {col}: {[f'{m:%Y-%m}' for m in unknown]}")
    return errors


# --------------------------------------------------------------------------- 2. no going backwards
def check_not_backwards(latest, previous_meta):
    prev = previous_meta.get("latest_month") if previous_meta else None
    if prev and latest < pd.Timestamp(prev):
        return [f"Latest month went backwards: {latest:%Y-%m} is before the previous run's {prev}."]
    return []


# --------------------------------------------------------------------------- 3. ranges
def check_ranges(panel):
    errors = []
    # Headline: -5% to 60%. Food and core swung harder in 2003-2008 (core was -6.5% in Dec 2007,
    # as published and as in nigeria-inflation-forecast), so their floor is -10%.
    for col, low in [("inflation", -5), ("food_inflation", -10), ("core_inflation", -10)]:
        bad = panel[(panel[col] < low) | (panel[col] > 60)]
        if len(bad):
            errors.append(f"{col} outside {low}% to 60% in {bad['month'].dt.strftime('%Y-%m').tolist()}")
    for col in RATE_COLUMNS + ["interBankCallRate"]:
        bad = panel[(panel[col] <= 0) | (panel[col] > 100)]
        if len(bad):
            errors.append(f"{col} outside 0% to 100% in {bad['month'].dt.strftime('%Y-%m').tolist()}")
    fx = panel.set_index("month")["usd_ngn"]
    if (fx <= 0).any():
        errors.append("₦/$ has zero or negative values.")
    # New months only: history to Sep 2026 is checked against the reference snapshot, and it
    # includes a real jump of more than 50% (Feb 2024, after the January 2024 devaluation).
    jumps = fx.pct_change().abs()
    jumps = jumps[jumps.index > REFERENCE_END]
    if (jumps > 0.5).any():
        errors.append(f"₦/$ moved more than 50% in one month: {jumps[jumps > 0.5].index.strftime('%Y-%m').tolist()}")
    return errors


# --------------------------------------------------------------------------- 4. reference snapshot
def _reference_tables():
    """(name, DataFrame with 'month', {reference column: our column}, tolerance, which parsed table)."""
    sav = pd.read_csv(REFERENCE_DIR / "savings_vs_inflation.csv", parse_dates=["month"])
    macro = pd.read_csv(REFERENCE_DIR / "inflation_forecast_macro.csv", parse_dates=["Date"]).rename(columns={"Date": "month"})
    fx = pd.read_csv(REFERENCE_DIR / "naira_scenarios_fx.csv", parse_dates=["month"])
    cred = pd.read_csv(REFERENCE_DIR / "credit_squeeze_credit.csv", parse_dates=["month"])
    mm_cols = ["savingsDeposit", "oneMonthDeposit", "threeMonthsDeposit", "sixMonthsDeposit",
               "twelveMonthsDeposit", "treasuryBill", "mpr", "mrr", "interBankCallRate",
               "primeLending", "maxLending"]
    return [
        ("nigeria-savings-vs-inflation", sav, {c: c for c in mm_cols}, 1e-9, "money_market"),
        ("nigeria-savings-vs-inflation", sav, {"inflation": "inflation", "food_inflation": "food_inflation"}, 1e-9, "inflation"),
        ("nigeria-savings-vs-inflation", sav, {"usd_ngn": "usd_ngn"}, 1e-6, "usd"),
        ("nigeria-inflation-forecast", macro, {"Headline": "inflation", "Food": "food_inflation",
                                               "Core": "core_inflation"}, 1e-9, "inflation"),
        ("nigeria-inflation-forecast", macro, {"USD_NGN": "usd_ngn"}, 0.0051, "usd"),
        ("naira-scenarios", fx, {"usd_ngn": "usd_ngn", "usd_days": "usd_days"}, 1e-6, "usd"),
        ("nigeria-credit-squeeze", cred, {c: c for c in CREDIT_COLUMNS}, 1e-6, "credit"),
    ]


def compare_with_reference(parsed):
    """Compare the feeds AS PUBLISHED (before our fixes) with the earlier projects, to Sep 2026."""
    differences = []
    for project, ref, columns, tol, table in _reference_tables():
        ours = parsed[table].set_index("month")
        ref = ref[ref["month"] <= REFERENCE_END].set_index("month")
        for ref_col, our_col in columns.items():
            joined = pd.DataFrame({"ref": ref[ref_col]}).join(ours[[our_col]].rename(columns={our_col: "ours"}), how="left")
            both_nan = joined["ref"].isna() & joined["ours"].isna()
            diff = ~both_nan & ~((joined["ref"] - joined["ours"]).abs() <= tol)
            for month, row in joined[diff].iterrows():
                differences.append({"project": project, "column": our_col, "month": f"{month:%Y-%m}",
                                    "reference": row["ref"], "now": row["ours"]})
    return differences


def check_reference(parsed):
    errors, log = [], []
    allowed = {(r["project"], r["column"], r["month"]): r["reason"] for r in KNOWN_REVISIONS}
    diffs = compare_with_reference(parsed)
    for d in diffs:
        line = f"{d['column']} {d['month']}: {d['project']} had {d['reference']:,.4f}, now {d['now']:,.4f}"
        reason = allowed.get((d["project"], d["column"], d["month"]))
        if reason:
            log.append(f"Known difference: {line} ({reason})")
        else:
            errors.append(f"Changed from the reference snapshot: {line}")
    if not errors:
        log.append(f"Reference snapshot: every value up to Sep 2026 matches the four earlier projects, "
                   f"apart from the {len(diffs)} known differences listed above.")
    return errors, log


# --------------------------------------------------------------------------- 5. the article
def check_article(panel):
    if panel["month"].max() < pd.Timestamp("2026-09-01"):
        return ["Panel ends before Sep 2026, so the savings article can't be checked."], []
    rows = article_check(panel)
    errors = [f"Savings article not reproduced for {r[0]}: naira {r[2]:,} vs {r[1]:,}, "
              f"Jan 2006 naira {r[4]:,} vs {r[3]:,}" for r in rows if not r[-1]]
    log = [] if errors else ["Savings article reproduced: all five options match to within ₦2."]
    return errors, log


# --------------------------------------------------------------------------- 6. the models
def check_models(reproduction, forecast, outlook):
    """The ported models must still reproduce the published articles on data to Sep 2026,
    and today's outputs must be well formed (ranges in order, nothing missing)."""
    errors, log = [], []
    bad = reproduction[~reproduction["ok"]]
    for _, r in bad.iterrows():
        errors.append(f"Model no longer reproduces the article: {r['model']} {r['what']}: "
                      f"published {r['published']}, now {r['ours']}")
    if bad.empty:
        checked = reproduction[reproduction["tolerance"] != "info only"]
        log.append(f"Models reproduce the articles on data to Sep 2026: all {len(checked)} published "
                   "numbers match (inflation to 0.1 point, naira to the nearest ₦10).")

    for measure, part in forecast.groupby("measure"):
        if len(part) != 12 or part[["forecast", "low80", "high80"]].isna().any().any():
            errors.append(f"Inflation forecast ({measure}) is not 12 complete months.")
        if not ((part["low80"] <= part["forecast"]) & (part["forecast"] <= part["high80"])).all():
            errors.append(f"Inflation forecast ({measure}): the forecast is outside its own range.")
    cols = ["low80", "low50", "median", "high50", "high80"]
    if outlook[cols].isna().any().any() or (outlook[cols] <= 0).any().any():
        errors.append("Naira outlook has missing or non-positive values.")
    elif not all((outlook[a] <= outlook[b]).all() for a, b in zip(cols, cols[1:])):
        errors.append("Naira outlook ranges are out of order.")
    return errors, log


# --------------------------------------------------------------------------- 7. forecast vintages
def check_vintages():
    """Saved forecasts are frozen: every vintage must match its fingerprint; only new files may be added."""
    import vintages
    errors = vintages.check_unchanged()
    log = [] if errors else [f"Forecast vintages: all {len(vintages.load_manifest())} saved files unchanged."]
    return errors, log


# --------------------------------------------------------------------------- all together
def validate(panel, parsed, latest, previous_meta):
    errors, log = [], []
    errors += check_months(panel)
    errors += check_gaps(panel)
    errors += check_not_backwards(latest, previous_meta)
    errors += check_ranges(panel)
    e, l = check_reference(parsed); errors += e; log += l
    e, l = check_article(panel); errors += e; log += l
    return errors, log
