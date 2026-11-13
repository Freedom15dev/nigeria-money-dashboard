"""Bank rates and loan app price tiers for the "My loan" page.

Ported from nigeria-credit-squeeze (src/loan_offers.py). The tier rule is unchanged; two sources changed:
- bank rates now come from data/processed/panel.csv (the CBN feed, latest month), so they update monthly;
- loan app rates come from data/reference/loan_offers.csv, the hand-collected snapshot from the credit
  article (advertised rates, checked Apr-Nov 2026). They do NOT update.

Tiers, not lender names: callers only ever get the three tier numbers.
Run `python src/loan_offers.py` for the self-check.
"""

import json
from pathlib import Path

import pandas as pd

import loan_math

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "processed" / "panel.csv"
OFFERS = ROOT / "data" / "reference" / "loan_offers.csv"
ARTICLE_NUMBERS = ROOT / "data" / "reference" / "credit_squeeze_numbers.json"

APP_RATES_LABEL = "Advertised loan app rates, checked Apr–Nov 2026"
TIER_LABELS = {"start": "Loan app: typical starting rate", "mid": "Loan app: typical mid rate",
               "high": "Loan app: highest advertised rate"}


def bank_rates(panel=None, month=None):
    """CBN average prime and maximum lending rates, per year and per month, for `month` (default: the latest
    month with both rates). If that month's prime rate was a feed glitch (treated as missing), the latest
    earlier month with both rates is used."""
    p = pd.read_csv(PANEL, parse_dates=["month"]) if panel is None else panel
    p = p.dropna(subset=["primeLending", "maxLending"])
    if month is not None:
        p = p[p["month"] <= pd.Timestamp(month)]
    row = p.sort_values("month").iloc[-1]
    return {
        "month": f"{row['month']:%B %Y}",
        "prime_year": float(row["primeLending"]),
        "max_year": float(row["maxLending"]),
        "prime_month": loan_math.annual_to_monthly(row["primeLending"]),
        "max_month": loan_math.annual_to_monthly(row["maxLending"]),
    }


def load_offers():
    return pd.read_csv(OFFERS)


def products_for(offers, days, business):
    """App products whose advertised tenor covers a loan of `days` days.

    Same rule as the article: payroll loans out; business loans only for business borrowers;
    products that don't publish a tenor stay in.
    """
    keep = offers["product_type"] != "payroll loan"
    if not business:
        keep &= offers["product_type"] != "business loan"
    known = offers["min_tenor_days"].notna() & offers["max_tenor_days"].notna()
    fits = (offers["min_tenor_days"] <= days) & (offers["max_tenor_days"] >= days)
    return offers[keep & (~known | fits)]


def tiers(products):
    """Typical starting rate (median of minimums), typical mid rate (median of range mid-points),
    highest advertised (highest maximum), all in % a month."""
    both = products.dropna(subset=["min_monthly_rate", "max_monthly_rate"])
    return {
        "start": float(products["min_monthly_rate"].median()),
        "mid": float(((both["min_monthly_rate"] + both["max_monthly_rate"]) / 2).median()),
        "high": float(products["max_monthly_rate"].max()),
    }


def _self_check():
    """The rebuilt tiers must match the article's (Tunde: 30 days, personal; Amaka: 180 days, business), and
    the bank rates for September 2026 must be the article's 19.04% and 32.62%."""
    n = json.loads(ARTICLE_NUMBERS.read_text(encoding="utf-8"))
    offers = load_offers()
    for who, days, business in [("tunde", 30, False), ("amaka", 180, True)]:
        t = tiers(products_for(offers, days, business))
        for k in ["start", "mid", "high"]:
            assert round(t[k], 2) == n[f"{who}_rate_{k}"], (who, k, t[k], n[f"{who}_rate_{k}"])
    b = bank_rates(month="2026-09-01")
    assert (b["prime_year"], b["max_year"]) == (n["prime_last"], n["max_last"]) == (19.04, 32.62)
    assert payroll_and_names_rule(offers)


def payroll_and_names_rule(offers):
    """Payroll loans never count; business loans only for business borrowers."""
    personal = products_for(offers, 120, business=False)
    business = products_for(offers, 120, business=True)
    return ("payroll loan" not in set(personal["product_type"]) | set(business["product_type"])
            and "business loan" not in set(personal["product_type"]))


if __name__ == "__main__":
    _self_check()
    print("loan_offers self-check passed: tiers and Sep 2026 bank rates match the article.")
