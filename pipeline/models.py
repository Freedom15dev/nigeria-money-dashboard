"""Precomputed models for the Prices and The naira pages (CLAUDE.md §4.3). Run in the pipeline,
never in the app.

1. Inflation forecast: ported from nigeria-inflation-forecast, Phase 9 (the final forecast).
   - Main forecast: ARIMA(1,1,0) with the `Rebased` step dummy (1 from Jan 2025), fitted on every
     month from Jan 2003, 12 months ahead, with an 80% interval. Headline and food.
   - Baseline: naive (the latest value, held flat), the yardstick every model had to beat.
   - Scenario: regression on inflation's last 3 months plus the naira's year-on-year change
     (lags 1 and 3) and a one-month `Rebase_jump` dummy, forecast recursively with the naira's
     change held at its latest value. A "what if the naira's trend continues" line, not the forecast.

2. Naira outlook: ported from naira-scenarios, Phases 7 and 9.
   - Jump model: each simulated month is a jump (chance = share of past months the naira fell
     more than 5%) drawn from real past jumps, or a normal month drawn from real normal months.
     5,000 paths, 48 months, seed 42.
   - Calibration: backtest from every 3rd month (Mar 2010 onward, last start 48 months before the
     latest month) at 12/24/36/48 months ahead; raise the 80% top to the 90th percentile of past
     overshoots and the 50% top to the 75th; never narrow. The 80% bottom may repeat the biggest
     strengthening seen since the June 2023 float (6/12/18/24 months).
   - Four scenarios: stable reforms, history repeats, oil shock, policy reversal.

reproduce() re-runs both on data to Sep 2026 and compares them with the published articles.
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

# =========================================================================== inflation forecast
FORECAST_MONTHS = 12


def inflation_table(panel):
    """The `macro` table of nigeria-inflation-forecast: Headline, Food, USD_NGN, dummies."""
    macro = (panel.set_index("month")[["inflation", "food_inflation", "usd_ngn"]]
             .rename(columns={"inflation": "Headline", "food_inflation": "Food", "usd_ngn": "USD_NGN"})
             .asfreq("MS"))
    macro["Rebased"] = (macro.index >= "2025-01-01").astype(int)       # step: the rebased CPI
    macro["Rebase_jump"] = (macro.index == "2025-01-01").astype(int)   # pulse: the month of the break
    macro["USD_NGN_yoy"] = macro["USD_NGN"].pct_change(12) * 100
    return macro


def _fit_arima(macro, target):
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    model = SARIMAX(macro[target], exog=macro[["Rebased"]], order=(1, 1, 0))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # optimiser chatter; convergence is checked below
        result = model.fit(disp=False)
    if not result.mle_retvals["converged"]:
        raise RuntimeError(f"ARIMA(1,1,0) for {target} did not converge")
    return result


def _make_features(data, target, drivers=(), dummies=()):
    features = pd.DataFrame(index=data.index)
    for lag in [1, 2, 3]:
        features[f"{target}_lag{lag}"] = data[target].shift(lag)
    for driver in drivers:
        for lag in [1, 3]:
            features[f"{driver}_lag{lag}"] = data[driver].shift(lag)
    for dummy in dummies:
        features[dummy] = data[dummy]
    return features


class _OLS:
    """Ordinary least squares with an intercept: the same fit as scikit-learn's LinearRegression."""

    def fit(self, X, y):
        A = np.column_stack([np.ones(len(X)), np.asarray(X, float)])
        coef, *_ = np.linalg.lstsq(A, np.asarray(y, float), rcond=None)
        self.intercept_, self.coef_ = coef[0], coef[1:]
        return self

    def predict(self, X):
        return self.intercept_ + np.asarray(X, float) @ self.coef_


def _naira_scenario(macro, target, drivers=("USD_NGN_yoy",), dummies=("Rebase_jump",)):
    features = _make_features(macro, target, drivers, dummies)
    rows = features.dropna().index
    model = _OLS().fit(features.loc[rows], macro.loc[rows, target])
    history = macro.copy()
    for _ in range(FORECAST_MONTHS):  # recursive: each forecast becomes "last month"
        next_date = history.index[-1] + pd.DateOffset(months=1)
        new_row = history.iloc[[-1]].copy()
        new_row.index = [next_date]
        history = pd.concat([history, new_row])
        next_features = _make_features(history, target, drivers, dummies).iloc[[-1]]
        history.loc[next_date, target] = model.predict(next_features)[0]
    return history[target].iloc[-FORECAST_MONTHS:]


def inflation_forecast(panel):
    """Return (forecast table, model notes). One row per future month and measure."""
    macro = inflation_table(panel)
    last = macro.index[-1]
    future = pd.date_range(last + pd.DateOffset(months=1), periods=FORECAST_MONTHS, freq="MS")
    rows, notes = [], {}
    for target, measure in [("Headline", "headline"), ("Food", "food")]:
        result = _fit_arima(macro, target)
        fc = result.get_forecast(steps=FORECAST_MONTHS, exog=pd.DataFrame({"Rebased": 1}, index=future))
        band = fc.conf_int(alpha=0.2)  # 80% interval
        scenario = _naira_scenario(macro, target)
        for i, month in enumerate(future):
            rows.append({
                "month": month, "measure": measure,
                "forecast": fc.predicted_mean.iloc[i],
                "low80": band.iloc[i, 0], "high80": band.iloc[i, 1],
                "naive": macro.loc[last, target],
                "naira_scenario": scenario.iloc[i],
            })
        notes[measure] = {k: round(float(v), 4) for k, v in result.params.items()}
    notes["naira_yoy_held"] = round(float(macro.loc[last, "USD_NGN_yoy"]), 2)
    return pd.DataFrame(rows), notes


# =========================================================================== naira outlook
SEED = 42
N_PATHS = 5000
HORIZON = 48
JUMP_THRESHOLD = 5                                   # % fall in a month that counts as a jump
JUMP_LOG = np.log(1 + JUMP_THRESHOLD / 100)
CHECK_HORIZONS = [12, 24, 36, 48]
FLOAT_START = pd.Timestamp("2023-06-01")
FLOAT_HORIZONS = [6, 12, 18, 24]
FIRST_BACKTEST_START = pd.Timestamp("2010-03-01")


def simulate_scenario(past, jump_chance=None, freeze_months=0, forced_jump=None,
                      horizon=HORIZON, n_paths=N_PATHS, seed=SEED):
    """The jump model; with no switches set it is exactly naira-scenarios' simulate_jump_model."""
    returns = np.log(past).diff().dropna().to_numpy()
    rng = np.random.default_rng(seed)
    is_jump = returns > JUMP_LOG
    if jump_chance is None:
        jump_chance = is_jump.mean()
    size = (n_paths, horizon)
    jump_happens = rng.random(size) < jump_chance
    simulated = np.where(jump_happens,
                         rng.choice(returns[is_jump], size=size),
                         rng.choice(returns[~is_jump], size=size))
    simulated[:, :freeze_months] = 0
    if forced_jump is not None:
        month, jump_size = forced_jump
        simulated[:, month - 1] += jump_size
    return past.iloc[-1] * np.exp(simulated.cumsum(axis=1))


def _summarise(paths):
    final = paths[:, -1]
    return {"central": np.median(final),
            "low80": np.percentile(final, 10), "high80": np.percentile(final, 90),
            "low50": np.percentile(final, 25), "high50": np.percentile(final, 75)}


def backtest_starts(rates):
    """Every 3rd month from Mar 2010, while a 4-year window still ends inside the data."""
    last_start = rates.index[-1] - pd.DateOffset(months=HORIZON)
    return pd.date_range(FIRST_BACKTEST_START, last_start, freq="3MS")


def calibration_margins(rates):
    starts = backtest_starts(rates)
    margins = {}
    for h in CHECK_HORIZONS:
        rows = []
        for start in starts:
            forecast = _summarise(simulate_scenario(rates.loc[:start], horizon=h))
            rows.append({**forecast, "actual": rates[start + pd.DateOffset(months=h)]})
        bt = pd.DataFrame(rows, index=starts)
        over_80 = np.log(bt["actual"] / bt["high80"])
        over_50 = np.log(bt["actual"] / bt["high50"])
        margins[h] = {"top80": max(0, over_80.quantile(0.90)), "top50": max(0, over_50.quantile(0.75))}
    return pd.DataFrame(margins).T, starts


def inflation_gap_now(rates, ng_inflation, us_inflation):
    """Latest 12-month average monthly log inflation gap (Nigeria minus US), as in naira-scenarios."""
    table = pd.DataFrame({"ng": ng_inflation, "us": us_inflation}).reindex(rates.index)
    gap_all = (np.log(1 + table["ng"] / 100) - np.log(1 + table["us"] / 100)) / 12
    return gap_all.iloc[-12:].mean()


def scenario_settings(gap_now):
    return {
        "Stable reforms": {
            "story": "The float holds, reserves stay healthy and inflation keeps easing.",
            "change": "Jumps become rarer: 2% a month (about one in 4 years) instead of the historical rate.",
            "jump_chance": 0.02, "freeze_months": 0, "forced_jump": None},
        "History repeats": {
            "story": "The next 4 years look like 2002 to today on average.",
            "change": "Nothing changed: the plain jump model, built from the naira's own history.",
            "jump_chance": None, "freeze_months": 0, "forced_jump": None},
        "Oil shock": {
            "story": "Oil prices crash in year 1, and a devaluation the size of 2016 follows.",
            "change": "A forced 50% devaluation in month 12, on top of normal history.",
            "jump_chance": None, "freeze_months": 0, "forced_jump": (12, np.log(1.50))},
        "Policy reversal": {
            "story": "The CBN holds the official rate fixed for 2 years, then devalues to catch up, overshooting.",
            "change": "Rate frozen for 24 months, then a jump in month 25 equal to the inflation gap built up, plus 25%.",
            "jump_chance": None, "freeze_months": 24, "forced_jump": (25, gap_now * 24 + np.log(1.25))},
    }


def naira_outlook(rates, ng_inflation, us_inflation):
    """Return (outlook fan, scenario fans, notes). rates: monthly ₦/$ from Dec 2001 to the latest month."""
    margins, starts = calibration_margins(rates)
    months_ahead = np.arange(1, HORIZON + 1)
    top80 = np.interp(months_ahead, [0] + CHECK_HORIZONS, [0] + margins["top80"].tolist())
    top50 = np.interp(months_ahead, [0] + CHECK_HORIZONS, [0] + margins["top50"].tolist())

    paths = simulate_scenario(rates)
    p10, p25, p50, p75, p90 = np.percentile(paths, [10, 25, 50, 75, 90], axis=0)

    float_log = np.log(rates.loc[FLOAT_START:])
    biggest_fall = [min(0, (float_log.shift(-h) - float_log).min()) for h in FLOAT_HORIZONS]
    fall_by_month = np.interp(months_ahead, [0] + FLOAT_HORIZONS, [0] + biggest_fall)
    float_floor = rates.iloc[-1] * np.exp(fall_by_month)

    future = pd.date_range(rates.index[-1] + pd.DateOffset(months=1), periods=HORIZON, freq="MS")
    outlook = pd.DataFrame({
        "month": future,
        "low80": np.minimum(p10, float_floor),
        "low50": p25,
        "median": p50,
        "high50": p75 * np.exp(top50),
        "high80": p90 * np.exp(top80),
        "model_high80": p90,
    })

    gap_now = inflation_gap_now(rates, ng_inflation, us_inflation)
    settings = scenario_settings(gap_now)
    scen_rows = []
    for name, s in settings.items():
        sp = simulate_scenario(rates, s["jump_chance"], s["freeze_months"], s["forced_jump"])
        q10, q25, q50, q75, q90 = np.percentile(sp, [10, 25, 50, 75, 90], axis=0)
        for i, month in enumerate(future):
            scen_rows.append({"scenario": name, "month": month, "low80": q10[i], "low50": q25[i],
                              "median": q50[i], "high50": q75[i], "high80": q90[i]})

    returns = np.log(rates).diff().dropna()
    notes = {
        "seed": SEED, "paths": N_PATHS, "horizon_months": HORIZON,
        "jump_chance": round(float((returns > JUMP_LOG).mean()), 4),
        "jumps": int((returns > JUMP_LOG).sum()), "months": int(len(returns)),
        "backtest_starts": f"{starts[0]:%b %Y} to {starts[-1]:%b %Y} ({len(starts)} start dates)",
        "margins_top80": {int(k): round(float(v), 3) for k, v in margins["top80"].items()},
        "margins_top50": {int(k): round(float(v), 3) for k, v in margins["top50"].items()},
        "biggest_float_fall": {h: round(float(np.exp(f) - 1), 3) for h, f in zip(FLOAT_HORIZONS, biggest_fall)},
        "inflation_gap_now_monthly_log": round(float(gap_now), 5),
        "policy_reversal_catch_up": round(float(np.exp(gap_now * 24 + np.log(1.25)) - 1), 3),
        "scenarios": {n: {"story": s["story"], "change": s["change"]} for n, s in settings.items()},
    }
    return outlook, pd.DataFrame(scen_rows), notes


def naira_inputs(parsed, panel):
    """Monthly ₦/$ from Dec 2001 to the panel's latest month, plus Nigerian and US inflation."""
    latest = panel["month"].max()
    rates = parsed["usd"].set_index("month")["usd_ngn"].loc[:latest].asfreq("MS")
    ng = panel.set_index("month")["inflation"]  # June 2025 already interpolated, as in naira-scenarios
    us = parsed["us"].set_index("month")["us_inflation"]
    return rates, ng, us


# =========================================================================== reproduce the articles
PUBLISHED = {
    # naira-scenarios 9c: (low80, low50, median, high50, high80), rounded to ₦10
    "naira": {"Sep 2027": (1130, 1330, 1400, 1670, 2030),
              "Sep 2028": (1090, 1390, 1530, 2310, 3390),
              "Sep 2030": (1090, 1580, 1880, 4070, 6870)},
    # naira-scenarios 9e: Sep 2030 (low80, median, high80), rounded to ₦10
    "scenarios": {"Stable reforms": (1230, 1500, 2010), "History repeats": (1390, 1880, 3000),
                  "Oil shock": (2090, 2820, 4500), "Policy reversal": (2060, 2430, 3440)},
    # nigeria-inflation-forecast 9.2: (forecast, low80, high80, naira scenario), rounded to 0.1
    "inflation": {("headline", "Mar 2027"): (14.4, 8.9, 19.9, 12.8),
                  ("headline", "Sep 2027"): (14.4, 6.5, 22.4, 11.8),
                  ("food", "Mar 2027"): (19.6, 11.4, 27.8, 16.9),
                  ("food", "Sep 2027"): (19.6, 7.8, 31.4, 15.1)},
}
REPRODUCE_END = pd.Timestamp("2026-09-01")
REFERENCE_MACRO = Path(__file__).resolve().parents[1] / "data" / "reference" / "inflation_forecast_macro.csv"


def reproduce(panel, parsed):
    """Run both models on data to Sep 2026 and compare with the articles. Returns a DataFrame."""
    p = panel[panel["month"] <= REPRODUCE_END]
    rows = []

    # The naira-scenario regression uses the naira's year-on-year change. The inflation project built
    # its ₦/$ series without dropping the three one-day typos or averaging duplicate days, so to test
    # the METHOD we also run it on that project's own ₦/$ (data/reference). The dashboard itself uses
    # the cleaned series, which moves the scenario by 0.1-0.3 points (shown in the 'dashboard' rows).
    ref_fx = pd.read_csv(REFERENCE_MACRO, parse_dates=["Date"]).set_index("Date")["USD_NGN"]
    p_ref = p.assign(usd_ngn=p["month"].map(ref_fx))
    fc, _ = inflation_forecast(p)
    fc_ref, _ = inflation_forecast(p_ref)
    for f in (fc, fc_ref):
        f["label"] = f["month"].dt.strftime("%b %Y")
    for (measure, label), pub in PUBLISHED["inflation"].items():
        pick = (fc["measure"] == measure) & (fc["label"] == label)
        r, r_ref = fc[pick].iloc[0], fc_ref[pick.values].iloc[0]
        checks = [("forecast", r["forecast"], pub[0]), ("low80", r["low80"], pub[1]),
                  ("high80", r["high80"], pub[2]),
                  ("naira scenario (project's ₦/$)", r_ref["naira_scenario"], pub[3])]
        for name, ours, published in checks:
            rows.append({"model": "Inflation", "what": f"{measure} {label} {name}", "published": published,
                         "ours": round(ours, 2), "difference": round(ours - published, 2),
                         "ok": abs(ours - published) <= 0.05, "tolerance": "rounds to 0.1"})
        rows.append({"model": "Inflation", "what": f"{measure} {label} naira scenario (dashboard ₦/$)",
                     "published": pub[3], "ours": round(r["naira_scenario"], 2),
                     "difference": round(r["naira_scenario"] - pub[3], 2), "ok": True,
                     "tolerance": "info only"})

    rates, ng, us = naira_inputs(parsed, p)
    outlook, scen, _ = naira_outlook(rates, ng, us)
    outlook["label"] = outlook["month"].dt.strftime("%b %Y")
    for label, pub in PUBLISHED["naira"].items():
        r = outlook[outlook["label"] == label].iloc[0]
        for name, published in zip(["low80", "low50", "median", "high50", "high80"], pub):
            ours = r[name]
            rows.append({"model": "Naira outlook", "what": f"{label} {name}", "published": published,
                         "ours": round(ours), "difference": round(ours - published),
                         "ok": round(ours, -1) == published, "tolerance": "rounds to ₦10"})
    last = scen["month"].max()
    for name, pub in PUBLISHED["scenarios"].items():
        r = scen[(scen["scenario"] == name) & (scen["month"] == last)].iloc[0]
        for col, published in zip(["low80", "median", "high80"], pub):
            ours = r[col]
            rows.append({"model": "Naira scenario", "what": f"{name} Sep 2030 {col}", "published": published,
                         "ours": round(ours), "difference": round(ours - published),
                         "ok": round(ours, -1) == published, "tolerance": "rounds to ₦10"})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import build
    raw = build.load_all_raw()
    panel, _, _ = build.build_panel(raw)
    table = reproduce(panel, build.parse_all(raw))
    pd.set_option("display.width", 160)
    print(table.to_string(index=False))
    print("\nAll within tolerance:", bool(table["ok"].all()))
