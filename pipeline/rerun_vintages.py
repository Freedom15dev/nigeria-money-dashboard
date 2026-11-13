"""A second September 2026 naira vintage: the published model re-run, monthly, so tracking can start in
October 2026 instead of waiting for September 2027.

The published vintage (naira_2026-09.csv) holds only the three dates the article printed and is left as it is.
This file (naira_2026-09-rerun.csv) re-runs the SAME model (models.naira_outlook: jump model, 5,000 paths,
seed 42, the same calibration) on the SAME data (to September 2026), and keeps every month to September 2030
with its 50% and 80% ranges. Before saving it must reproduce every published naira number (to the nearest
₦10, as printed); otherwise nothing is saved.

`python pipeline/rerun_vintages.py` writes it once. It never overwrites an existing vintage.
"""

import pandas as pd

import build
import models
from published_vintages import NAIRA_OUTLOOK, NAIRA_SCENARIOS
from vintages import save_vintage

VINTAGE = "2026-09-rerun"
SOURCE = "model re-run (not published)"
DATA_TO = pd.Timestamp("2026-09-01")


def rerun_table():
    raw = build.load_all_raw()
    panel, _, _ = build.build_panel(raw)
    panel = panel[panel["month"] <= DATA_TO]
    rates, ng, us = models.naira_inputs(build.parse_all(raw), panel)
    outlook, scenarios, _ = models.naira_outlook(rates, ng, us)

    # It must reproduce the published numbers before it may be saved.
    o = outlook.set_index("month")
    for month, *published in NAIRA_OUTLOOK:
        row = o.loc[pd.Timestamp(f"{month}-01")]
        ours = [round(row[c], -1) for c in ["low80", "low50", "median", "high50", "high80"]]
        if ours != published:
            raise ValueError(f"Re-run does not reproduce the published outlook for {month}: {ours} vs {published}")
    last = scenarios[scenarios["month"] == scenarios["month"].max()].set_index("scenario")
    for name, published in NAIRA_SCENARIOS.items():
        ours = tuple(round(last.loc[name, c], -1) for c in ["low80", "median", "high80"])
        if ours != published:
            raise ValueError(f"Re-run does not reproduce the published scenario {name}: {ours} vs {published}")

    table = pd.concat([outlook.drop(columns=["model_high80"]).assign(series="outlook"),
                       scenarios.rename(columns={"scenario": "series"})], ignore_index=True)
    return table[["series", "month", "low80", "low50", "median", "high50", "high80"]].round(6)


if __name__ == "__main__":
    table = rerun_table()
    print("Re-run reproduces all published naira numbers (outlook and scenarios).")
    print(save_vintage("naira", VINTAGE, table, SOURCE,
                       "models.naira_outlook re-run on data to Sep 2026 (seed 42); reproduces the published "
                       "ranges and adds every month to Sep 2030"))
