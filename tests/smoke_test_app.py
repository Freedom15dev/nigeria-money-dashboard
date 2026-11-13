"""Smoke test: run every page headlessly and check it renders without errors, shows the right numbers,
and handles silly inputs.

The expected numbers are computed from data/processed/ (not typed in), so the test still holds after each
monthly update. Whether the models reproduce the published articles is checked in pipeline/validate.py.

    python tests/smoke_test_app.py
"""

import json
import sys
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "app" / "Home.py")
PROCESSED = ROOT / "data" / "processed"
sys.path.insert(0, str(ROOT / "src"))
from money_math import SAVINGS, savings_journey  # noqa: E402
import loan_offers  # noqa: E402

PANEL = pd.read_csv(PROCESSED / "panel.csv", parse_dates=["month"])
META = json.loads((PROCESSED / "meta.json").read_text(encoding="utf-8"))
FORECAST = pd.read_csv(PROCESSED / "forecast.csv", parse_dates=["month"])
OUTLOOK = pd.read_csv(PROCESSED / "naira_outlook.csv", parse_dates=["month"])
SCEN = pd.read_csv(PROCESSED / "naira_scenarios.csv", parse_dates=["month"])
CARDS = pd.read_csv(PROCESSED / "forecast_scorecard.csv", parse_dates=["next_check"])
LATEST = pd.Timestamp(META["latest_month"])
NOW = PANEL.set_index("month").loc[LATEST]


def run(page=None, state=None, setup=None):
    at = AppTest.from_file(APP, default_timeout=60)
    if page:
        at.switch_page(page)
    for key, value in (state or {}).items():
        at.session_state[key] = value
    at.run()
    if setup:
        setup(at)
        at.run()
    assert not at.exception, [x.value for x in at.exception]
    return at


def everything(at):
    """All text on the page: HTML blocks, markdown, captions and info boxes."""
    parts = [x.proto.body for x in at.get("html")]
    parts += [x.value for x in at.markdown] + [x.value for x in at.caption] + [x.value for x in at.info]
    return " ".join(parts)


def means(text):
    return text.split("What this means</h2><p>")[1].split("</p>")[0]


def naira(x):
    return f"₦{x:,.0f}"


def ten(x):
    return f"₦{round(x, -1):,.0f}"


def pct(x):
    return f"{x:.2f}%"


def main():
    print(f"Data up to {META['latest_month_label']}")

    # ---------------------------------------------------------------- Home
    text = everything(run())
    assert "Understand what the economy is doing to your money." in text
    assert text.count('class="mm-card mm-kpi"') == 7, text.count('class="mm-card mm-kpi"')
    assert f"Data up to <b>{META['latest_month_label']}</b>" in text
    assert pct(NOW["inflation"]) in text and pct(NOW["savingsDeposit"]) in text
    print("ok  Home renders: header, hero sentence, 7 key numbers, data-up-to label")

    # ---------------------------------------------------------------- My savings
    j = savings_journey(PANEL, 100_000, "2006-01-01").summary.loc[SAVINGS]
    text = everything(run("views/savings.py"))
    assert naira(j["naira_today"]) in text and naira(j["buys_what_then"]) in text, "savings result not on screen"
    assert f"Lost {abs(j['real_change_pct']):.1f}% of its value" in text
    print(f"ok  My savings (defaults): savings account {naira(j['naira_today'])}, buys what "
          f"{naira(j['buys_what_then'])} bought, badge in words")
    print("    What this means:", means(text))

    at = run("views/savings.py", setup=lambda a: a.text_input(key="amount").set_value("0"))
    assert "above ₦0" in everything(at)
    at = run("views/savings.py", setup=lambda a: a.text_input(key="amount").set_value("abc"))
    assert "Type the amount in naira" in everything(at)
    print("ok  ₦0 and 'abc' give friendly messages")

    at = run("views/savings.py", setup=lambda a: a.text_input(key="amount").set_value("1m"))
    assert at.session_state["amount"] == "1,000,000" and at.session_state["quick"] == "₦1m"
    j1m = savings_journey(PANEL, 1_000_000, "2006-01-01").summary.loc[SAVINGS]
    assert naira(j1m["naira_today"]) in everything(at)
    print("ok  typing '1m' becomes 1,000,000, selects the ₦1m quick pick, results scale")

    at = run("views/savings.py", state={"start_month": "December", "start_year": LATEST.year})
    assert "Data only goes up to" in everything(at) or "before the end month" in everything(at)
    at = run("views/savings.py", state={"start_month": f"{LATEST:%B}", "start_year": LATEST.year})
    assert "before the end month" in everything(at)
    print("ok  start after or equal to the latest month gives a friendly message")

    at = run("views/savings.py", state={"kept": []})
    assert "Pick where the money was kept" in everything(at)
    print("ok  nothing ticked: mattress baseline still shown, with a hint")

    # ---------------------------------------------------------------- Prices
    text = everything(run("views/prices.py"))
    head = FORECAST[FORECAST["measure"] == "headline"].iloc[-1]
    rng = f"{head['low80']:.1f}% to {head['high80']:.1f}%"
    assert "How fast are prices rising?" in text and pct(NOW["inflation"]) in text and pct(NOW["food_inflation"]) in text
    assert rng in text, f"headline forecast range {rng} not on screen"
    assert "The January 2025 rebasing" in text
    print(f"ok  Prices renders: hero, key numbers, chart, 2025 note, forecast range {rng} for {head['month']:%b %Y}")
    print("    What this means:", means(text))
    food = FORECAST[FORECAST["measure"] == "food"].iloc[-1]
    at = run("views/prices.py", state={"infl_measures": [], "infl_period": "Since 2003", "fc_measure": "Food"})
    assert f"{food['low80']:.1f}% to {food['high80']:.1f}%" in everything(at)
    print("ok  Prices with no measure ticked falls back to headline; food forecast range shown")

    # ---------------------------------------------------------------- The naira
    text = everything(run("views/naira.py"))
    assert "How much is the naira worth?" in text and f"₦{NOW['usd_ngn']:,.2f}" in text
    start = OUTLOOK["month"].min()
    for m in (12, 24, 48):
        r = OUTLOOK.set_index("month").loc[start + pd.DateOffset(months=m - 1)]
        assert f"{ten(r['low80'])} – {ten(r['high80'])}" in text, f"outlook range for +{m} months not on screen"
    print("ok  The naira renders: hero, history, outlook ranges at 1, 2 and 4 years")
    print("    What this means:", means(text))
    end = SCEN[SCEN["month"] == SCEN["month"].max()].set_index("scenario")
    for name, r in end.iterrows():
        at = run("views/naira.py", state={"scenario": name, "fx_scale": "Log", "fx_period": "Last 2 years"})
        assert f"{ten(r['low80'])} – {ten(r['high80'])}" in everything(at), f"{name} range not on screen"
    print("ok  all four scenarios show their ranges; log scale and short period render")

    # ---------------------------------------------------------------- Borrowing
    at = run("views/borrowing.py")
    text = everything(at)
    assert "What does it cost to borrow?" in text
    assert pct(NOW["primeLending"]) in text and pct(NOW["maxLending"]) in text
    loan_links = [x for x in at.get("page_link") if "Work out your own loan" in x.proto.label]
    assert len(loan_links) == 2 and all(x.proto.page == "loan" for x in loan_links), \
        [(x.proto.label, x.proto.page) for x in at.get("page_link")]
    assert "naija-loan-cost.streamlit.app" not in text
    print("ok  Borrowing renders: prime and maximum rates, three charts, two in-app links to My loan")
    at = run()
    assert any(x.proto.page == "loan" for x in at.get("page_link") if "your own loan" in x.proto.label)
    print("ok  Home has a My loan card that opens the page inside the app")
    print("    What this means:", means(text))
    at = run("views/borrowing.py", state={"borrow_period": "Last 2 years"})
    print("ok  Borrowing with a short period renders")

    # ---------------------------------------------------------------- My loan (spot-checks from the old calculator)
    bank = loan_offers.bank_rates(PANEL)
    text = everything(run("views/loan.py"))  # opens on Tunde: ₦100,000, 8.25% a month, 1 month
    assert "What will this loan really cost me?" in text
    assert "₦108,250" in text, "Tunde's total (₦108,250) not on screen"
    tunde_bank_max = f"₦{100_000 * (1 + bank['max_month'] / 100):,.0f}"  # ₦102,718 at the Sep 2026 maximum rate
    assert tunde_bank_max in text, f"Tunde at the bank maximum rate ({tunde_bank_max}) not on screen"
    assert f"Bank rates: CBN averages, <b>{bank['month']}</b>" in text
    assert "Advertised loan app rates, checked Apr–Nov 2026" in text
    for lender in loan_offers.load_offers()["lender"]:
        assert lender.split(" ")[0] not in text, f"lender name {lender} on screen"
    print(f"ok  My loan (Tunde): total ₦108,250; at the {bank['month']} bank maximum rate {tunde_bank_max}; "
          f"labels shown; no lender names")
    if bank["month"] == "September 2026":
        assert tunde_bank_max == "₦102,718"
        print("ok  ₦102,718 at the Sep 2026 bank maximum rate, as in the old calculator")

    amaka = {"loan_preset": "Amaka: ₦500k, 6 months", "loan_amount": "500,000", "loan_rate": 8.25,
             "loan_rate_unit": "per month", "loan_length": 6, "loan_length_unit": "months",
             "loan_method": "Not sure, show me both", "loan_purpose": "Business"}
    text = everything(run("views/loan.py", state=amaka))
    assert "₦653,876" in text and "₦747,500" in text, "Amaka: reducing ₦653,876 vs flat ₦747,500 not on screen"
    print("ok  My loan (Amaka): reducing balance ₦653,876 vs flat ₦747,500")

    text = everything(run("views/loan.py", state={"loan_days_late": 90, "loan_penalty": "Rollover interest",
                                                  "loan_rollover": 1.0}))
    assert "₦205,675" in text, "90 days late at 1% a day on ₦108,250 (₦205,675) not on screen"
    print("ok  My loan late payment: 90 days at 1% a day on ₦108,250 -> ₦205,675")

    text = everything(run("views/loan.py", state={**amaka, "loan_length": 24}))
    assert "only bank rates are shown" in text and "Loan app:" not in text
    print("ok  My loan: a 24-month loan is compared with bank rates only")

    for state, message in [({"loan_amount": "0"}, "above ₦0"), ({"loan_amount": "abc"}, "Type the amount in naira"),
                           ({"loan_rate": 150.0}, "at most 100% a month"),
                           ({"loan_length": 400, "loan_length_unit": "days"}, "enter the length in months"),
                           ({"loan_length": 0}, "at least 1 day or 1 month")]:
        assert message in everything(run("views/loan.py", state=state)), message
    print("ok  My loan: ₦0, 'abc', 150% a month, 400 days and 0 months give friendly messages")

    # ---------------------------------------------------------------- forecast trackers
    text = everything(run("views/prices.py"))
    assert "How are the forecasts doing?" in text and "never redrawn" in text
    first = CARDS[(CARDS["model"] == "inflation") & (CARDS["series"] == "headline")].iloc[0]
    if first["checked"] == 0:
        assert f"<b>{first['next_check']:%B %Y}</b>" in text
    else:
        assert f"{int(first['inside80'])} of {int(first['checked'])}</b>" in text
    print("ok  Prices tracker shows the earliest vintage's scorecard")
    text = everything(run("views/naira.py"))
    assert "How are the forecasts doing?" in text and "never redrawn" in text
    rerun = CARDS[(CARDS["model"] == "naira") & (CARDS["source"] == "model re-run (not published)")]
    if len(rerun):  # the page opens on the re-run of the published model, clearly labelled
        assert "This is a re-run of the published model, not the published forecast itself." in text
        r = rerun.iloc[0]
        if r["checked"] == 0:
            assert f"<b>{r['next_check']:%B %Y}</b>" in text, "re-run's first check not on screen"
    assert "jump months since January 2006" in text and "jump months since January 2003" in text
    print("ok  Naira tracker opens on the labelled re-run; jump-month counts name their periods")

    for s in META.get("rate_spikes", []):  # Borrowing: one line per glitch behind a card, not the full note
        if s["month"] == f"{LATEST - pd.DateOffset(years=1):%Y-%m}" and s["column"] == "primeLending":
            text = everything(run("views/borrowing.py"))
            line = f"prime rate estimated: the CBN figure ({s['value']:.2f}%) was a one-month glitch."
            assert line in text, line
            assert "Our rule: a month more than 5 points" not in " ".join(c.value for c in run("views/borrowing.py").caption)
            print(f"ok  Borrowing shows the one-line glitch note: '... {line}'")
    print("All app smoke tests passed.")


if __name__ == "__main__":
    main()
