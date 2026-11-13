"""Build the monthly panel the app reads: one row per month, Jan 2003 to the latest month.

Steps:
1. parse every raw feed into monthly numbers (clean.parse_*)
2. apply the trap fixes (clean.fix_*), collecting a log line for each
3. join everything on month
4. add the price index (method from nigeria-savings-vs-inflation) and the real savings rate

The latest month is the last month that has inflation, the savings rate AND the exchange
rate, so the dashboard never shows a month with half its numbers missing.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import clean  # noqa: E402
from money_math import price_index_from_yoy, real_rate  # noqa: E402

PANEL_START = pd.Timestamp("2003-01-01")  # inflation starts here; interest rates start Jan 2006


def parse_all(raw):
    """The feeds as published, turned into numbers. No fixes. Used by validate.py too."""
    usd_monthly, _ = clean.usd_monthly_average(clean.parse_usd_daily(raw["exchange_rates"]))
    return {
        "inflation": clean.parse_inflation(raw["inflation"]),
        "money_market": clean.parse_money_market(raw["money_market"]),
        "credit": clean.parse_credit(raw["money_credit"]),
        "usd": usd_monthly,
        "crude": clean.crude_monthly_average(clean.parse_crude_daily(raw["crude"])),
        "us": clean.parse_us_cpi(raw["us_cpi"])[0],
    }


def load_all_raw():
    """Every raw source: the CBN feeds plus the FRED US CPI file."""
    from fetch import FEEDS, load_raw, load_us_cpi_text
    raw = {name: load_raw(name) for name in FEEDS}
    raw["us_cpi"] = load_us_cpi_text()
    return raw


def find_latest_month(infl, mm, usd):
    have = (
        set(infl.dropna(subset=["inflation"])["month"])
        & set(mm.dropna(subset=["savingsDeposit"])["month"])
        & set(usd["month"])
    )
    if not have:
        raise ValueError("No month has inflation, the savings rate and the exchange rate together.")
    return max(have)


def build_panel(raw):
    """Return (panel, log_lines, latest_month)."""
    parsed = parse_all(raw)
    log = []

    infl, line = clean.fix_june_2025_inflation(parsed["inflation"]); log.append(line)
    infl, line = clean.keep_revised_2025_inflation(infl); log.append(line)

    mm, line = clean.fix_policy_rate(parsed["money_market"]); log.append(line)
    mm, line = clean.fix_tbill_zeros(mm); log.append(line)
    mm, line, spike_gaps = clean.fix_one_month_spikes(mm); log.append(line)

    _, line = clean.usd_monthly_average(clean.parse_usd_daily(raw["exchange_rates"])); log.append(line)
    usd = parsed["usd"]

    latest = find_latest_month(infl, mm, usd)
    months = pd.date_range(PANEL_START, latest, freq="MS")

    credit, line = clean.note_negative_government_credit(parsed["credit"]); log.append(line)
    credit, line = clean.fill_credit_for_charts(credit, months); log.append(line)
    _, line = clean.parse_us_cpi(raw["us_cpi"]); log.append(line)

    panel = (
        pd.DataFrame({"month": months})
        .merge(infl, on="month", how="left")
        .merge(mm, on="month", how="left")
        .merge(usd, on="month", how="left")
        .merge(parsed["crude"], on="month", how="left")
        .merge(credit, on="month", how="left")
        .merge(parsed["us"], on="month", how="left")
    )
    panel["usd_days"] = panel["usd_days"].astype("Int64")
    panel["crude_days"] = panel["crude_days"].astype("Int64")

    # Price index, chained from year-on-year inflation; base = the latest month (= 100),
    # so "today's prices" always means the latest data month.
    panel["price_index"] = price_index_from_yoy(panel["inflation"], base_position=-1)

    # Real savings rate (Fisher): what a savings account pays after inflation, % per year.
    panel["real_savings_rate"] = real_rate(panel["savingsDeposit"], panel["inflation"])

    # Borrowing (definitions from nigeria-credit-squeeze): the gap between what risky and prime
    # borrowers pay, lending rates after inflation (Fisher), and government's share of credit.
    panel["lending_gap"] = panel["maxLending"] - panel["primeLending"]
    panel["real_prime"] = real_rate(panel["primeLending"], panel["inflation"])
    panel["real_max"] = real_rate(panel["maxLending"], panel["inflation"])
    panel["gov_share"] = panel["creditToGovernment"] / panel["netDomesticCredit"] * 100

    panel["june_2025_interpolated"] = panel["month"].eq("2025-06-01") & ("June repeated May" in log[0])
    panel["tbill_missing"] = panel["treasuryBill"].isna() & panel["month"].ge("2006-01-01")
    panel = clean.add_rate_chart_columns(panel)
    # Chart-only versions (gaps such as prime Sep 2025 and credit Mar 2026 drawn as straight lines)
    panel["lending_gap_chart"] = panel["maxLending_chart"] - panel["primeLending_chart"]
    panel["real_prime_chart"] = real_rate(panel["primeLending_chart"], panel["inflation"])
    panel["real_max_chart"] = real_rate(panel["maxLending_chart"], panel["inflation"])
    # As in nigeria-credit-squeeze: the share only means something while government is a net
    # BORROWER. While its credit was negative (2006-2014, a net lender) the "share" swings wildly
    # (e.g. 990% in Jan 2007, when net domestic credit was near zero), so charts shade those months.
    panel["gov_net_lender"] = panel["creditToGovernment"] < 0
    panel["gov_share_chart"] = (panel["creditToGovernment_chart"] / panel["netDomesticCredit_chart"] * 100).where(
        panel["creditToGovernment_chart"] > 0)

    # Gaps made on purpose by the fixes, so validate.py accepts exactly these and nothing else.
    panel.attrs["fixed_gaps"] = set(spike_gaps)
    return panel, log, latest


def to_float_rounded(panel):
    """Round for a tidy CSV without losing precision that matters (rates are 2 dp, ₦/$ to 4 dp)."""
    out = panel.copy()
    for col in out.columns:
        if out[col].dtype == float:
            out[col] = out[col].round(6)
    return out


if __name__ == "__main__":
    panel, log, latest = build_panel(load_all_raw())
    print("\n".join(log))
    print(f"Panel: {len(panel)} months, latest {latest:%B %Y}")
    print(panel.tail(3).T)
