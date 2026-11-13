"""The money maths behind (+234) Money Matters: price index, real rates, savings growth.

Every method here is ported from the nigeria-savings-vs-inflation notebook, so the app
reproduces the published article:

- Price index: each month's year-on-year inflation becomes a monthly step
  (1 + yoy)^(1/12), and the steps are multiplied together (chained).
- Real rate (Fisher): (1 + rate) / (1 + inflation) - 1.
- Savings growth, for ₦1 saved at the start month:
    Under the mattress      no growth
    Savings account         rate / 12 added every month (monthly compounding)
    12-month fixed deposit  rate locked for 12 months, then rolled over at the rate then;
                            each year's interest is spread evenly over its 12 months
    Treasury bills          the CBN rate is the 91-day bill: locked for 3 months, then rolled
                            over; a quarter-year's interest is spread over 3 months
    Dollars                 bought at the start month's official rate, held without interest
  Interest earned during a month uses the rate in force at the start of that month
  (the previous month's figure). No tax, no fees.

Run `python src/money_math.py` to run the self-check.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

MATTRESS = "Under the mattress"
SAVINGS = "Savings account"
FIXED = "12-month fixed deposit"
TBILL = "Treasury bills"
DOLLARS = "Dollars"
OPTIONS = [SAVINGS, FIXED, TBILL, DOLLARS]  # the user can choose these
ALL_OPTIONS = [MATTRESS] + OPTIONS          # the mattress is always shown as the baseline

# Published in the savings article (₦100,000 from Jan 2006 to Sep 2026):
# (naira in Sep 2026, buying power in Jan 2006 naira)
ARTICLE_RESULTS = {
    MATTRESS: (100_000, 6_460),
    SAVINGS: (208_347, 13_459),
    FIXED: (582_785, 37_648),
    TBILL: (617_455, 39_887),
    DOLLARS: (1_032_535, 66_701),
}
ARTICLE_START, ARTICLE_END = pd.Timestamp("2006-01-01"), pd.Timestamp("2026-09-01")


# =========================================================================== building blocks
def price_index_from_yoy(yoy, base_position=-1):
    """Chained price index from year-on-year inflation (%), equal to 100 at `base_position`.

    The first month is the starting point (its own step is ignored). Rebasing only rescales,
    so the ratio between any two months doesn't depend on the base.
    """
    yoy = pd.Series(yoy, dtype=float).reset_index(drop=True)
    if yoy.isna().any():
        raise ValueError("Inflation has gaps; the price index needs every month.")
    step = (1 + yoy / 100) ** (1 / 12)
    step.iloc[0] = 1.0
    level = step.cumprod()
    return (100 * level / level.iloc[base_position]).to_numpy()


def real_rate(nominal, inflation):
    """Fisher real rate, % per year: (1 + rate) / (1 + inflation) - 1."""
    return ((1 + np.asarray(nominal, float) / 100) / (1 + np.asarray(inflation, float) / 100) - 1) * 100


def locked_rate(rate, term_months):
    """The rate fixed at the most recent rollover; rollovers every `term_months` from the first month."""
    months_since_start = pd.Series(np.arange(len(rate)), index=rate.index)
    return rate.where(months_since_start % term_months == 0).ffill()


def growth_path(window):
    """How ₦1 saved in the first month of `window` grows in each option, month by month (naira).

    `window` needs columns savingsDeposit, twelveMonthsDeposit, treasuryBill (all % per year)
    and usd_ngn, one row per month, oldest first.
    """
    # The two missing T-bill months (Dec 2017, Dec 2018) carry the previous month's rate,
    # because a saver's balance has to grow (or not) every month.
    tbill = window["treasuryBill"].ffill()

    steps = pd.DataFrame(index=window.index)
    steps[MATTRESS] = 1.0
    steps[SAVINGS] = 1 + window["savingsDeposit"].shift(1) / 100 / 12
    steps[FIXED] = (1 + locked_rate(window["twelveMonthsDeposit"], 12).shift(1) / 100) ** (1 / 12)
    steps[TBILL] = (1 + locked_rate(tbill, 3).shift(1) / 100 / 4) ** (1 / 3)
    steps.iloc[0] = 1.0  # the start month: no growth yet
    path = steps.cumprod()
    path[DOLLARS] = window["usd_ngn"] / window["usd_ngn"].iloc[0]
    return path


# =========================================================================== the calculator
@dataclass
class Journey:
    start: pd.Timestamp
    end: pd.Timestamp
    amount: float
    naira: pd.DataFrame          # value in naira, month by month, per option
    start_money: pd.DataFrame    # buying power in start-month naira
    todays_prices: pd.DataFrame  # buying power in latest-month naira
    summary: pd.DataFrame        # one row per option
    price_multiple: float        # how many times prices rose from start to end
    usd_bought: float            # dollars bought at the start


class InputProblem(ValueError):
    """A friendly message for a silly input (shown to the user, not a crash)."""


def savings_journey(panel, amount, start_month, end_month=None):
    """Follow `amount` naira from `start_month` to `end_month` (default: the latest month)."""
    if amount is None or not np.isfinite(amount) or amount <= 0:
        raise InputProblem("Enter an amount above ₦0 to see what it would be worth.")
    df = panel.set_index("month").sort_index()
    rates = df.dropna(subset=["savingsDeposit", "twelveMonthsDeposit", "usd_ngn"])
    first, latest = rates.index.min(), rates.index.max()
    start = pd.Timestamp(start_month)
    end = pd.Timestamp(end_month) if end_month is not None else latest
    if start < first:
        raise InputProblem(f"Interest rate data starts in {first:%B %Y}. Pick a start from then on.")
    if end > latest:
        raise InputProblem(f"Data only goes up to {latest:%B %Y}.")
    if start >= end:
        raise InputProblem("The start month has to be before the end month. Pick an earlier start.")

    window = df.loc[start:end]
    naira = amount * growth_path(window)
    index = window["price_index"]
    start_money = naira.mul(index.iloc[0] / index, axis=0)
    todays_prices = naira.mul(index.iloc[-1] / index, axis=0)
    years = (len(window) - 1) / 12

    end_naira = naira.iloc[-1]
    end_real = start_money.iloc[-1]
    summary = pd.DataFrame({
        "naira_today": end_naira,
        "buys_what_then": end_real,                      # in start-month naira
        "start_in_todays_prices": amount * index.iloc[-1] / index.iloc[0],
        "real_change_pct": (end_real / amount - 1) * 100,
        "real_per_year_pct": ((end_real / amount) ** (1 / years) - 1) * 100,
    })
    return Journey(start, end, float(amount), naira, start_money, todays_prices, summary,
                   float(index.iloc[-1] / index.iloc[0]), float(amount / window["usd_ngn"].iloc[0]))


def article_check(panel, tolerance=2.0):
    """Reproduce the savings article on `panel`. Returns rows of (option, expected, got, ok)."""
    j = savings_journey(panel, 100_000, ARTICLE_START, ARTICLE_END)
    rows = []
    for option, (naira, real) in ARTICLE_RESULTS.items():
        got_naira, got_real = j.summary.loc[option, "naira_today"], j.summary.loc[option, "buys_what_then"]
        ok = abs(got_naira - naira) <= tolerance and abs(got_real - real) <= tolerance
        rows.append((option, naira, round(got_naira), real, round(got_real), ok))
    return rows


# =========================================================================== self-check
def _close(a, b, tol=1e-9):
    return abs(a - b) <= tol * max(1.0, abs(b))


def _self_check():
    print("money_math self-check")

    # 1. Price index: 12% a year, every month -> exactly 12% after 12 months.
    idx = price_index_from_yoy([12.0] * 13, base_position=0)
    assert _close(idx[12] / idx[0], 1.12), idx
    # Rebasing changes the level, not the ratios.
    a = price_index_from_yoy([10, 20, 30, 15], base_position=0)
    b = price_index_from_yoy([10, 20, 30, 15], base_position=-1)
    assert _close(a[3] / a[1], b[3] / b[1]) and _close(b[-1], 100)
    print("  ok  price index: 12% a year compounds to exactly 12%; base doesn't change ratios")

    # 2. Fisher real rate: 5% interest, 15% inflation -> -8.70%.
    assert _close(float(real_rate(5, 15)), (1.05 / 1.15 - 1) * 100)
    print("  ok  real rate: 5% interest with 15% inflation = -8.70%")

    # 3. Toy saver: 13 months, flat rates, so every option has a hand-worked answer.
    months = pd.date_range("2020-01-01", periods=13, freq="MS")
    toy = pd.DataFrame({
        "month": months,
        "savingsDeposit": 12.0, "twelveMonthsDeposit": 10.0, "treasuryBill": 8.0,
        "usd_ngn": [400.0] * 12 + [600.0], "inflation": 0.0,
    })
    toy["price_index"] = 100.0
    j = savings_journey(toy, 1_000, "2020-01-01")
    s = j.summary["naira_today"]
    assert _close(s[MATTRESS], 1_000)
    assert _close(s[SAVINGS], 1_000 * 1.01 ** 12)            # 1% a month for 12 months
    assert _close(s[FIXED], 1_000 * 1.10)                     # one full year at 10%
    assert _close(s[TBILL], 1_000 * 1.02 ** 4)                # four 91-day bills at 2% each
    assert _close(s[DOLLARS], 1_500)                          # $2.50 bought at 400, sold at 600
    assert _close(j.usd_bought, 2.5)
    print("  ok  toy saver: savings 1%/month, FD 10%/year, T-bill 2%/quarter, dollars 400->600")

    # 4. Rollover: a fixed deposit locks January's rate even when the rate changes in February.
    toy2 = toy.copy()
    toy2.loc[1:, "twelveMonthsDeposit"] = 50.0
    assert _close(savings_journey(toy2, 1_000, "2020-01-01").summary.loc[FIXED, "naira_today"], 1_100)
    print("  ok  fixed deposit keeps its locked rate until the rollover")

    # 5. Silly inputs give friendly messages, not crashes.
    for amount, start, end in [(0, "2020-01-01", None), (-5, "2020-01-01", None),
                               (1_000, "2021-01-01", None), (1_000, "2020-06-01", "2020-03-01"),
                               (1_000, "2019-01-01", None)]:
        try:
            savings_journey(toy, amount, start, end)
        except InputProblem:
            pass
        else:
            raise AssertionError(f"no friendly message for amount={amount}, start={start}, end={end}")
    print("  ok  silly inputs (₦0, negative, start after end, before the data) give friendly messages")

    # 6. Reproduce the savings article on the real data, if the pipeline has run.
    panel_path = Path(__file__).resolve().parents[1] / "data" / "processed" / "panel.csv"
    if panel_path.exists():
        panel = pd.read_csv(panel_path, parse_dates=["month"])
        rows = article_check(panel)
        for option, n_exp, n_got, r_exp, r_got, ok in rows:
            print(f"  {'ok ' if ok else 'BAD'} article {option:<24} naira ₦{n_got:>9,} (article ₦{n_exp:>9,})"
                  f"  in Jan 2006 naira ₦{r_got:>7,} (article ₦{r_exp:>7,})")
        assert all(r[-1] for r in rows), "The savings article is not reproduced."
    else:
        print("  --  article check skipped: run python pipeline/run_all.py first")

    print("All money_math checks passed.")


if __name__ == "__main__":
    _self_check()
