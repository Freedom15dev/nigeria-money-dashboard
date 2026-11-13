"""The forecasts as PUBLISHED in the two earlier projects, saved as the tracker's first vintages.

These numbers are copied exactly as printed (not re-run), with their original rounding:
- nigeria-inflation-forecast, notebook section 9.1 (tables "Headline inflation forecast (%)" and
  "Food inflation forecast (%)"), made with data up to September 2026; summarised in its README.
  Columns: Forecast, Low (80%), High (80%), Naira scenario. No 50% range was published.
- naira-scenarios, notebook section 9c (outlook ranges) and 9e (scenario ranges), made with data up to
  September 2026; the same numbers are in its README. Rounded to ₦10. Only three dates were published.

`python pipeline/published_vintages.py` writes them once. It never overwrites an existing vintage.
"""

import pandas as pd

from vintages import save_vintage

MADE_WITH_DATA_TO = "2026-09"

# (month, forecast, low80, high80, naira scenario)
INFLATION = {
    "headline": [
        ("2026-10", 14.5, 12.6, 16.3, 14.2), ("2026-11", 14.4, 11.5, 17.3, 13.8),
        ("2026-12", 14.4, 10.7, 18.2, 13.6), ("2027-01", 14.4, 10.0, 18.8, 13.3),
        ("2027-02", 14.4, 9.4, 19.4, 13.0), ("2027-03", 14.4, 8.9, 19.9, 12.8),
        ("2027-04", 14.4, 8.4, 20.4, 12.6), ("2027-05", 14.4, 8.0, 20.9, 12.4),
        ("2027-06", 14.4, 7.6, 21.3, 12.2), ("2027-07", 14.4, 7.2, 21.7, 12.1),
        ("2027-08", 14.4, 6.8, 22.0, 11.9), ("2027-09", 14.4, 6.5, 22.4, 11.8),
    ],
    "food": [
        ("2026-10", 19.6, 16.7, 22.4, 19.2), ("2026-11", 19.6, 15.2, 24.0, 18.7),
        ("2026-12", 19.6, 14.0, 25.2, 18.1), ("2027-01", 19.6, 13.0, 26.2, 17.7),
        ("2027-02", 19.6, 12.2, 27.0, 17.3), ("2027-03", 19.6, 11.4, 27.8, 16.9),
        ("2027-04", 19.6, 10.7, 28.5, 16.6), ("2027-05", 19.6, 10.0, 29.1, 16.2),
        ("2027-06", 19.6, 9.4, 29.8, 15.9), ("2027-07", 19.6, 8.9, 30.3, 15.6),
        ("2027-08", 19.6, 8.3, 30.9, 15.3), ("2027-09", 19.6, 7.8, 31.4, 15.1),
    ],
}

# Outlook: (month, low80, low50, median, high50, high80). Scenarios: Sep 2030 (low80, median, high80).
NAIRA_OUTLOOK = [
    ("2027-09", 1130, 1330, 1400, 1670, 2030),
    ("2028-09", 1090, 1390, 1530, 2310, 3390),
    ("2030-09", 1090, 1580, 1880, 4070, 6870),
]
NAIRA_SCENARIOS = {
    "Stable reforms": (1230, 1500, 2010), "History repeats": (1390, 1880, 3000),
    "Oil shock": (2090, 2820, 4500), "Policy reversal": (2060, 2430, 3440),
}


def inflation_table():
    rows = [{"measure": m, "month": f"{month}-01", "forecast": f, "low80": lo, "high80": hi,
             "low50": None, "high50": None, "naira_scenario": s, "naive": None}
            for m, table in INFLATION.items() for month, f, lo, hi, s in table]
    return pd.DataFrame(rows)


def naira_table():
    rows = [{"series": "outlook", "month": f"{m}-01", "low80": a, "low50": b, "median": c, "high50": d, "high80": f}
            for m, a, b, c, d, f in NAIRA_OUTLOOK]
    rows += [{"series": name, "month": "2030-09-01", "low80": lo, "low50": None, "median": mid, "high50": None,
              "high80": hi} for name, (lo, mid, hi) in NAIRA_SCENARIOS.items()]
    table = pd.DataFrame(rows)
    cols = ["low80", "low50", "median", "high50", "high80"]
    table[cols] = table[cols].astype("Int64")  # whole naira, exactly as published (blank where not published)
    return table


def save_published():
    out = []
    out.append(save_vintage("inflation", MADE_WITH_DATA_TO, inflation_table(), source="published",
                            note="nigeria-inflation-forecast, notebook section 9.1 (as published)"))
    out.append(save_vintage("naira", MADE_WITH_DATA_TO, naira_table(), source="published",
                            note="naira-scenarios, notebook sections 9c and 9e (as published)"))
    return out


if __name__ == "__main__":
    for line in save_published():
        print(line)
