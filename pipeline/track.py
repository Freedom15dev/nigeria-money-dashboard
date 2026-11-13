"""Forecast tracker: score every saved vintage against the actual figures as they arrive.

For each forecast month that now has an actual figure:
- error = actual minus forecast (inflation in percentage points; naira in ₦ and in %)
- inside the 50% range? inside the 80% range? (blank where that range was not published)
- the naive "no change" yardstick: the actual figure in the vintage month, and its error too

Writes data/processed/forecast_scores.csv (one row per vintage, series and month checked) and
data/processed/forecast_scorecard.csv (one row per vintage and series: the running totals, plus the
next month that can be checked). Old forecasts are read exactly as saved; nothing is redrawn.

Run `python pipeline/track.py` for the self-check.
"""

import numpy as np
import pandas as pd

from vintages import load_vintages


def _months_between(a, b):
    return (b.year - a.year) * 12 + (b.month - a.month)


def _inside(actual, low, high):
    if pd.isna(low) or pd.isna(high):
        return np.nan
    return bool(low <= actual <= high)


def score(vintages, actuals, model, central, unit):
    """vintages: rows with vintage, source, series, month, central/low/high columns.
    actuals: {series: pd.Series indexed by month}. Returns one row per forecast month with an actual."""
    rows = []
    for _, v in vintages.iterrows():
        series_actual = actuals.get(v["series"])
        if series_actual is None or v["month"] not in series_actual.index or pd.isna(series_actual[v["month"]]):
            continue
        made = pd.Timestamp(f"{str(v['vintage'])[:7]}-01")  # e.g. '2026-09' or '2026-09-rerun'
        actual = series_actual[v["month"]]
        naive = series_actual.get(made, np.nan)
        rows.append({
            "model": model, "vintage": v["vintage"], "source": v["source"], "series": v["series"],
            "month": v["month"], "months_ahead": _months_between(made, v["month"]), "unit": unit,
            "actual": actual, "forecast": v[central],
            "low50": v.get("low50"), "high50": v.get("high50"), "low80": v["low80"], "high80": v["high80"],
            "error": actual - v[central],
            "error_pct": (actual / v[central] - 1) * 100 if unit == "naira" else np.nan,
            "inside50": _inside(actual, v.get("low50"), v.get("high50")),
            "inside80": _inside(actual, v["low80"], v["high80"]),
            "naive": naive, "naive_error": actual - naive,
        })
    return pd.DataFrame(rows)


def scorecard(vintages, scores, latest, model):
    """Running totals per vintage and series, including vintages with nothing to check yet."""
    rows = []
    for (vintage, series), part in vintages.groupby(["vintage", "series"]):
        s = scores[(scores["vintage"] == vintage) & (scores["series"] == series)] if len(scores) else scores
        future = part.loc[part["month"] > latest, "month"]
        has50 = s["inside50"].notna() if len(s) else pd.Series(dtype=bool)
        rows.append({
            "model": model, "vintage": vintage, "source": part["source"].iloc[0], "series": series,
            "forecast_months": len(part), "checked": len(s),
            "inside80": int(s["inside80"].sum()) if len(s) else 0,
            "above80": int((s["actual"] > s["high80"]).sum()) if len(s) else 0,
            "below80": int((s["actual"] < s["low80"]).sum()) if len(s) else 0,
            "checked50": int(has50.sum()) if len(s) else 0,
            "inside50": int(s.loc[has50, "inside50"].sum()) if len(s) and has50.any() else 0,
            "mean_abs_error": s["error"].abs().mean() if len(s) else np.nan,
            "mean_error": s["error"].mean() if len(s) else np.nan,
            "mean_abs_error_pct": s["error_pct"].abs().mean() if len(s) else np.nan,
            "mean_abs_naive_error": s["naive_error"].abs().mean() if len(s) else np.nan,
            "last_checked": s["month"].max() if len(s) else pd.NaT,
            "next_check": future.min() if len(future) else pd.NaT,
        })
    return pd.DataFrame(rows)


def all_vintages():
    """Every saved forecast in one long table for the app (the app only reads data/processed/).
    'central' is the forecast for inflation and the middle of the simulations for the naira."""
    parts = []
    infl = load_vintages("inflation")
    if len(infl):
        parts.append(infl.rename(columns={"measure": "series", "forecast": "central"}))
    naira = load_vintages("naira")
    if len(naira):
        parts.append(naira[naira["series"] == "outlook"].rename(columns={"median": "central"}))
    cols = ["model", "vintage", "source", "series", "month", "central", "low50", "high50", "low80", "high80"]
    return pd.concat([p.reindex(columns=cols) for p in parts], ignore_index=True) if parts else pd.DataFrame(columns=cols)


def track(panel):
    """Score both models' vintages against the panel. Returns (scores, scorecard)."""
    latest = panel["month"].max()
    p = panel.set_index("month")
    all_scores, all_cards = [], []

    infl = load_vintages("inflation")
    if len(infl):
        infl = infl.rename(columns={"measure": "series"})
        actuals = {"headline": p["inflation"], "food": p["food_inflation"]}
        sc = score(infl, actuals, "inflation", "forecast", "points")
        all_scores.append(sc)
        all_cards.append(scorecard(infl, sc, latest, "inflation"))

    naira = load_vintages("naira")
    if len(naira):
        outlook = naira[naira["series"] == "outlook"]  # scenarios are "what if" stories, not forecasts
        sc = score(outlook, {"outlook": p["usd_ngn"]}, "naira", "median", "naira")
        all_scores.append(sc)
        all_cards.append(scorecard(outlook, sc, latest, "naira"))

    scores = pd.concat([s for s in all_scores if len(s)], ignore_index=True) if any(len(s) for s in all_scores) \
        else pd.DataFrame(columns=["model", "vintage", "source", "series", "month"])
    cards = pd.concat(all_cards, ignore_index=True) if all_cards else pd.DataFrame()
    return scores, cards


# =========================================================================== self-check
def _self_check():
    print("track self-check")
    months = pd.date_range("2026-10-01", periods=4, freq="MS")
    v = pd.DataFrame({"vintage": "2026-09", "source": "test", "series": "headline", "month": months,
                      "forecast": [10.0, 10.0, 10.0, 10.0], "low80": [8.0] * 4, "high80": [12.0] * 4,
                      "low50": [9.0] * 4, "high50": [11.0] * 4})
    actual = pd.Series([9.5, 10.5, 12.5, 7.0], index=pd.date_range("2026-09-01", periods=4, freq="MS"))
    # Sep 2026 actual 9.5 is the naive value; Oct 10.5 (inside both), Nov 12.5 (above 80%), Dec 7.0 (below 80%)
    s = score(v, {"headline": actual}, "inflation", "forecast", "points")
    assert list(s["month"]) == list(months[:3]), "only months with an actual are scored"
    assert list(s["error"].round(6)) == [0.5, 2.5, -3.0]
    assert list(s["inside80"]) == [True, False, False] and list(s["inside50"]) == [True, False, False]
    assert list(s["naive_error"].round(6)) == [1.0, 3.0, -2.5]
    assert list(s["months_ahead"]) == [1, 2, 3]
    card = scorecard(v, s, pd.Timestamp("2026-12-01"), "inflation").iloc[0]
    assert card["checked"] == 3 and card["inside80"] == 1 and card["above80"] == 1 and card["below80"] == 1
    assert abs(card["mean_abs_error"] - 2.0) < 1e-9 and card["next_check"] == pd.Timestamp("2027-01-01")
    print("  ok  errors, 50%/80% hits, misses above and below, naive yardstick, next check month")

    v2 = v.drop(columns=["low50", "high50"])
    s2 = score(v2, {"headline": actual}, "inflation", "forecast", "points")
    assert s2["inside50"].isna().all() and scorecard(v2, s2, pd.Timestamp("2026-12-01"), "inflation").iloc[0]["checked50"] == 0
    print("  ok  a vintage without a published 50% range is not counted against it")

    empty = score(v, {"headline": actual.loc[:"2026-09-01"]}, "inflation", "forecast", "points")
    card = scorecard(v, empty, pd.Timestamp("2026-09-01"), "inflation").iloc[0]
    assert card["checked"] == 0 and card["next_check"] == pd.Timestamp("2026-10-01")
    print("  ok  no actuals yet: nothing scored, first check = the first forecast month")
    print("All track checks passed.")


if __name__ == "__main__":
    _self_check()
