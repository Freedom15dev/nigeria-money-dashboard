"""Turn the raw CBN feeds into tidy monthly tables, and fix the known data traps.

Two kinds of function live here:

1. parse_*  : read one raw feed and turn its text into numbers, one row per month,
              oldest first. No fixes yet. validate.py compares these "as published"
              numbers with the reference snapshot from the earlier projects.
2. fix_*    : one function per known trap (CLAUDE.md section 3.2). Each one checks that
              the problem is still there before fixing it, and returns a log line, so
              a silent change in the CBN data can't slip through.

TRAP_NOTES holds the plain-words "Under the hood" note for every trap. build.py copies
them into meta.json, and the app shows them.
"""

import numpy as np
import pandas as pd

RATE_COLUMNS = [
    "savingsDeposit", "oneMonthDeposit", "threeMonthsDeposit", "sixMonthsDeposit",
    "twelveMonthsDeposit", "treasuryBill", "mpr", "mrr", "interBankCallRate",
    "primeLending", "maxLending",
]
CREDIT_COLUMNS = ["creditToPrivateSector", "creditToGovernment", "netDomesticCredit", "moneySupply_M2"]

# Plain-words notes, one per trap, shown in the app under "Under the hood".
TRAP_NOTES = {
    "revised_2025_inflation": (
        "In January 2026 the NBS revised its 2025 inflation figures, raising each month by "
        "about 3 points (the January 2025 rebasing had used the wrong base period). The CBN "
        "feed holds the revised figures and we use them as they are, so 2025 inflation here is "
        "higher than the numbers first reported in the news."
    ),
    "june_2025_repeat": (
        "In the CBN feed, June 2025 inflation is an exact copy of May 2025. We replace June with "
        "the point halfway between May and July."
    ),
    "rebasing_2025": (
        "In January 2025 the NBS rebased the price index (new basket, new base year). That is part "
        "of why inflation fell sharply that month. Our price index is built from the yearly rates, "
        "so it runs straight across the break without restarting."
    ),
    "policy_rate": (
        "The Monetary Policy Rate (MPR) only started in December 2006. Before that the CBN's main "
        "rate was the Minimum Rediscount Rate (MRR), and the feed shows the MPR as 0. We use one "
        "'policy rate' column: the MRR before December 2006 and the MPR after."
    ),
    "tbill_zeros": (
        "The Treasury bill rate shows 0.00% in December 2017 and December 2018, between months of "
        "11-13%. A 0% rate never happened, so we treat both as missing. For the savings calculator "
        "we carry the previous month's rate forward for those two months."
    ),
    "rate_spikes": (
        "A few rates jump for a single month and snap straight back, which is a glitch in the feed, "
        "not history. For example the prime lending rate shows 11.90% in September 2025, between "
        "18.88% in August and 18.89% in October. Our rule: a month more than 5 points away from both "
        "neighbours, while the neighbours agree within 1 point, is treated as missing. Charts draw a "
        "straight line across it; no calculation uses it. (Not applied to the interbank call rate, "
        "which really does swing that much.)"
    ),
    "us_cpi_oct_2025": (
        "US prices come from FRED (series CPIAUCSL, collected by the US Bureau of Labor Statistics). "
        "October 2025 was never published because of a US government shutdown, so we use the point "
        "halfway between September and November."
    ),
    "credit_march_2026": (
        "Credit figures for March 2026 are missing from the CBN feed. Charts draw a straight line "
        "between February and April; no calculation uses the filled value."
    ),
    "credit_to_government_negative": (
        "Credit to government is below zero in many months up to 2014. That is real, not an error: "
        "the government kept more money in the banks than it borrowed, so on balance it was a lender."
    ),
    "exchange_rates": (
        "The CBN publishes the official rate daily. We average each month's days to get one monthly "
        "rate and record how many days went into each average. A few days appear twice; we average "
        "the two. Three days are clear typing errors (for example ₦1,376.80 on 9 December 2003, "
        "when the days around it were about ₦136.80); a day more than 25% away from the 11 trading "
        "days around it is dropped. This is the official rate only, not the parallel (street) market rate."
    ),
}


def _with_month(df):
    df = df.copy()
    df["month"] = pd.to_datetime({"year": df["tyear"].astype(int), "month": df["tmonth"].astype(int), "day": 1})
    return df


def _numeric(series):
    """CBN numbers come as text; blanks become NaN instead of an error."""
    return pd.to_numeric(series, errors="coerce")


def _assert_unique_months(df, feed):
    dups = df["month"].duplicated()
    if dups.any():
        months = df.loc[dups, "month"].dt.strftime("%Y-%m").tolist()
        raise ValueError(f"{feed}: the same month appears twice: {months}")


# =========================================================================== parse
def parse_inflation(records):
    """Monthly year-on-year inflation (%) from Jan 2003: headline, food and core.

    Core = 'all items less farm produce and energy', the same series the
    nigeria-inflation-forecast project used.
    """
    df = _with_month(pd.DataFrame(records))
    out = pd.DataFrame({
        "month": df["month"],
        "inflation": _numeric(df["allItemsYearOn"]),
        "food_inflation": _numeric(df["foodYearOn"]),
        "core_inflation": _numeric(df["allItemsLessFrmProdAndEnergyYearOn"]),
    }).sort_values("month").reset_index(drop=True)
    _assert_unique_months(out, "inflation")
    return out


def parse_money_market(records):
    """Monthly interest rates (% per year) from Jan 2006, exactly as published."""
    df = _with_month(pd.DataFrame(records))
    out = df[["month"]].copy()
    for col in RATE_COLUMNS:
        out[col] = _numeric(df[col])
    out = out.sort_values("month").reset_index(drop=True)
    _assert_unique_months(out, "money_market")
    return out


def parse_credit(records):
    """Monthly money and credit stats (₦ millions, nominal) from Jan 2006.

    The feed mixes yearly rows (tmonth outside 1-12) with monthly ones; only monthly rows are kept.
    """
    df = pd.DataFrame(records)
    df = df[df["tmonth"].astype(int).between(1, 12)]
    df = _with_month(df)
    out = df[["month"]].copy()
    for col in CREDIT_COLUMNS:
        out[col] = _numeric(df[col])
    out = out[out["month"] >= "2006-01-01"].sort_values("month").reset_index(drop=True)
    _assert_unique_months(out, "money_credit")
    return out


def parse_usd_daily(records):
    """Daily official naira per US dollar (CBN central rate)."""
    df = pd.DataFrame(records)
    df["currency"] = df["currency"].str.strip()  # "US DOLLAR" and "US DOLLAR " both appear
    usd = df[df["currency"] == "US DOLLAR"].copy()
    usd["date"] = pd.to_datetime(usd["ratedate"])
    usd["usd_ngn"] = _numeric(usd["centralrate"])
    return usd[["date", "usd_ngn"]].reset_index(drop=True)


def parse_crude_daily(records):
    """Daily crude oil price (US$ per barrel). postDate is day/month/year."""
    df = pd.DataFrame(records)
    out = pd.DataFrame({
        "date": pd.to_datetime(df["postDate"], format="%d/%m/%Y"),
        "crude_usd": _numeric(df["crudeOilPrice"]),
    })
    return out.dropna().sort_values("date").drop_duplicates("date").reset_index(drop=True)


# =========================================================================== fixes
def fix_june_2025_inflation(infl):
    """Trap: June 2025 repeats May 2025. Blank June and interpolate between May and July."""
    df = infl.copy()
    may, june = pd.Timestamp("2025-05-01"), pd.Timestamp("2025-06-01")
    m = df.set_index("month")
    if june not in m.index or may not in m.index:
        return df, "June 2025 fix: skipped (month not in feed)."
    cols = ["inflation", "food_inflation", "core_inflation"]
    if not (m.loc[june, cols] == m.loc[may, cols]).all():
        return df, "June 2025 fix: NOT applied - June no longer repeats May (the CBN may have corrected it)."
    is_june = df["month"] == june
    df.loc[is_june, cols] = np.nan
    df[cols] = df[cols].interpolate()
    vals = df.loc[is_june, "inflation"].iloc[0]
    return df, f"June 2025 fix: June repeated May; interpolated headline to {vals:.2f}%."


def keep_revised_2025_inflation(infl):
    """Trap: the feed holds the NBS January 2026 revision of 2025. Used as is; nothing changes."""
    return infl, "2025 inflation: using the CBN feed's revised figures as published (Jan 2026 NBS revision)."


def fix_policy_rate(mm):
    """Trap: MPR is 0 before Dec 2006. Fake zeros -> NaN; policy_rate = MRR before the MPR existed."""
    df = mm.copy()
    zeros = df["mpr"] == 0
    df.loc[zeros, "mpr"] = np.nan
    df["policy_rate"] = df["mpr"].fillna(df["mrr"])
    df["policy_rate_source"] = np.where(df["mpr"].notna(), "MPR", np.where(df["mrr"].notna(), "MRR", ""))
    return df, f"Policy rate: {int(zeros.sum())} zero MPR months replaced by the MRR."


def fix_tbill_zeros(mm):
    """Trap: T-bill rate 0.00 in Dec 2017 and Dec 2018. Treat as missing."""
    df = mm.copy()
    zeros = df["treasuryBill"] == 0
    months = df.loc[zeros, "month"].dt.strftime("%Y-%m").tolist()
    df.loc[zeros, "treasuryBill"] = np.nan
    # Other zero rates are also impossible; interbank has a few. Mark them missing too.
    df.loc[df["interBankCallRate"] == 0, "interBankCallRate"] = np.nan
    return df, f"T-bill zeros treated as missing: {months}."


# The interbank call rate (the overnight rate between banks) swings hard from month to month for
# real reasons (cash in the banking system gets tight or loose), so the spike rule would remove
# real data there. It isn't used for any number on screen. Excluded by decision, 13 Nov 2026.
SPIKE_EXCLUDED = {"interBankCallRate"}
SPIKE_POINTS, NEIGHBOURS_AGREE = 5.0, 1.0


def fix_one_month_spikes(mm):
    """Trap: a rate that jumps for one month and snaps back (e.g. prime lending Sep 2025: 18.88% ->
    11.90% -> 18.89%) is a glitch in the feed, not history.

    Rule: a month more than 5 points away from BOTH neighbours, while the neighbours agree within
    1 point, is treated as missing. Applied to every rate series except SPIKE_EXCLUDED. Returns
    (frame, log line, list of (column, month)) so validation can accept exactly these gaps.
    """
    df = mm.copy()
    caught = []
    columns = [c for c in RATE_COLUMNS + ["policy_rate"] if c in df.columns and c not in SPIKE_EXCLUDED]
    for col in columns:
        s = df[col]
        prev, nxt = s.shift(1), s.shift(-1)
        hit = ((s - prev).abs() > SPIKE_POINTS) & ((s - nxt).abs() > SPIKE_POINTS) & ((prev - nxt).abs() <= NEIGHBOURS_AGREE)
        for i in df.index[hit]:
            caught.append((col, df.at[i, "month"], prev[i], s[i], nxt[i]))
        df.loc[hit, col] = np.nan
    described = [f"{c} {m:%Y-%m} ({a:.2f} -> {v:.2f} -> {b:.2f})" for c, m, a, v, b in caught]
    line = f"One-month spikes treated as missing: {described if described else 'none'}."
    return df, line, [{"column": c, "month": f"{m:%Y-%m}", "value": round(float(v), 4), "before": round(float(a), 4),
                      "after": round(float(b), 4)} for c, m, a, v, b in caught]


def add_rate_chart_columns(df):
    """<rate>_chart columns: gaps from the fixes above filled with a straight line, for charts only."""
    df = df.copy()
    for col in RATE_COLUMNS + ["policy_rate"]:
        if col in df.columns:
            df[f"{col}_chart"] = df[col].interpolate(limit_area="inside")
    return df


def fill_credit_for_charts(credit, months):
    """Trap: credit data missing for some months (March 2026). Add *_chart columns, interpolated.

    The original columns keep NaN, so no calculation uses a made-up value.
    """
    df = pd.DataFrame({"month": months}).merge(credit, on="month", how="left")
    missing = df.loc[df["creditToPrivateSector"].isna() & (df["month"] >= credit["month"].min())
                     & (df["month"] <= credit["month"].max()), "month"]
    for col in CREDIT_COLUMNS:
        df[f"{col}_chart"] = df[col].interpolate(limit_area="inside")
    return df, f"Credit gaps filled for charts only: {missing.dt.strftime('%Y-%m').tolist()}."


def note_negative_government_credit(credit):
    """Trap: credit to government < 0 in many months to 2014. Real (government was a net lender). Kept."""
    n = int((credit["creditToGovernment"] < 0).sum())
    return credit, f"Credit to government below zero in {n} months: kept as published (net lender)."


def usd_monthly_average(daily):
    """Trap: daily rates -> monthly average, with the number of days in each month's average.

    Ported from naira-scenarios (sections 2c-2e):
    - a day listed twice -> the average of its two rows
    - a one-day typo -> dropped: a day more than 25% away from the median of the 11 trading
      days around it (a real devaluation moves the median too, so it isn't caught)
    """
    duplicates = int(daily["date"].duplicated().sum())
    usd_daily = daily.dropna(subset=["usd_ngn"]).groupby("date")["usd_ngn"].mean().sort_index()

    local_median = usd_daily.rolling(11, center=True, min_periods=3).median()
    is_typo = (usd_daily / local_median - 1).abs() > 0.25
    typos = [f"{d:%Y-%m-%d} (₦{r:,.2f} vs ₦{m:,.2f} nearby)"
             for d, r, m in zip(usd_daily.index[is_typo], usd_daily[is_typo], local_median[is_typo])]
    usd_daily = usd_daily[~is_typo]

    grouped = usd_daily.resample("MS")
    out = pd.DataFrame({"usd_ngn": grouped.mean(), "usd_days": grouped.count()}).reset_index()
    out = out.rename(columns={"date": "month"})
    out = out[out["usd_days"] > 0].reset_index(drop=True)
    return out, (f"Exchange rate: daily -> monthly average; {duplicates} duplicate days averaged; "
                 f"one-day typos removed: {typos}.")


def parse_us_cpi(text):
    """US consumer price index (FRED CPIAUCSL, 1982-84 = 100) and US year-on-year inflation.

    Trap: October 2025 was never published (US government shutdown). One row per month is enforced,
    and that gap is filled halfway between September and November, as in naira-scenarios (2g).
    """
    from io import StringIO
    df = pd.read_csv(StringIO(text), parse_dates=["observation_date"])
    cpi = pd.to_numeric(df["CPIAUCSL"], errors="coerce")  # FRED writes missing values as "."
    cpi.index = df["observation_date"]
    cpi = cpi.asfreq("MS")
    gaps = cpi.index[cpi.isna()].strftime("%Y-%m").tolist()
    cpi = cpi.interpolate(limit_area="inside")
    out = pd.DataFrame({"us_cpi": cpi, "us_inflation": cpi.pct_change(12, fill_method=None) * 100})
    out.index.name = "month"
    return out.reset_index(), f"US CPI (FRED): gaps filled halfway between neighbours: {gaps}."


def crude_monthly_average(daily):
    grouped = daily.set_index("date")["crude_usd"].resample("MS")
    out = pd.DataFrame({"crude_usd": grouped.mean(), "crude_days": grouped.count()}).reset_index()
    return out.rename(columns={"date": "month"})[lambda d: d["crude_days"] > 0].reset_index(drop=True)
