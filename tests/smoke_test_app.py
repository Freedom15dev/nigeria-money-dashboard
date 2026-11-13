"""Smoke test: run each page headlessly and check it renders without errors, including silly inputs.

    python tests/smoke_test_app.py
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app" / "Home.py")


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


def main():
    at = run()
    text = everything(at)
    assert "Understand what the economy is doing to your money." in text
    assert text.count('class="mm-card mm-kpi"') == 7, text.count('class="mm-card mm-kpi"')
    assert "Data up to <b>September 2026</b>" in text
    assert "14.63%" in text and "5.36%" in text and "8.1%" in text
    print("ok  Home renders: header, hero sentence, 7 key numbers, data-up-to label")

    at = run("pages/savings.py")
    text = everything(at)
    assert "₦208,347" in text and "₦13,459" in text, "savings spot-check not on screen"
    assert "Lost 86.5% of its value" in text
    assert "none of these options kept up with prices" in text
    print("ok  My savings (defaults): savings account ₦208,347, buys what ₦13,459 bought, badge in words")
    print("    What this means:", text.split("What this means</h2><p>")[1].split("</p>")[0])

    at = run("pages/savings.py", state={"start_year": 2025})
    text = everything(at)
    print("    From Jan 2025:", text.split("What this means</h2><p>")[1].split("</p>")[0])

    at = run("pages/savings.py", setup=lambda a: a.text_input(key="amount").set_value("0"))
    assert "above ₦0" in everything(at)
    print("ok  ₦0 gives a friendly message")

    at = run("pages/savings.py", setup=lambda a: a.text_input(key="amount").set_value("abc"))
    assert "Type the amount in naira" in everything(at)
    print("ok  'abc' gives a friendly message")

    at = run("pages/savings.py", setup=lambda a: a.text_input(key="amount").set_value("1m"))
    assert at.session_state["amount"] == "1,000,000" and at.session_state["quick"] == "₦1m"
    assert "₦2,083,4" in everything(at)  # ₦1m in a savings account from Jan 2006 = 10 x ₦208,346.6
    print("ok  typing '1m' becomes 1,000,000, selects the ₦1m quick pick, results scale")

    at = run("pages/savings.py", state={"start_month": "December", "start_year": 2026})
    assert "Data only goes up to" in everything(at) or "before the end month" in everything(at)
    print("ok  start after the latest month gives a friendly message")

    at = run("pages/savings.py", state={"start_month": "September", "start_year": 2026})
    assert "before the end month" in everything(at)
    print("ok  start = latest month gives a friendly message")

    at = run("pages/savings.py", state={"kept": []})
    assert "Pick where the money was kept" in everything(at)
    print("ok  nothing ticked: mattress baseline still shown, with a hint")
    # ---------------------------------------------------------------- Prices
    at = run("pages/prices.py")
    text = everything(at)
    assert "How fast are prices rising?" in text and "14.63%" in text and "19.59%" in text
    assert "6.5% to 22.4%" in text, "Sep 2027 headline range (article: 6.5 to 22.4) not on screen"
    assert "The January 2025 rebasing" in text and "What this means" in text
    print("ok  Prices renders: hero, key numbers, chart, 2025 note, forecast range 6.5% to 22.4% for Sep 2027")
    print("    What this means:", text.split("What this means</h2><p>")[1].split("</p>")[0])
    at = run("pages/prices.py", state={"infl_measures": [], "infl_period": "Since 2003", "fc_measure": "Food"})
    assert "7.8% to 31.4%" in everything(at), "Sep 2027 food range (article: 7.8 to 31.4) not on screen"
    print("ok  Prices with no measure ticked falls back to headline; food forecast range 7.8% to 31.4%")

    # ---------------------------------------------------------------- The naira
    at = run("pages/naira.py")
    text = everything(at)
    assert "How much is the naira worth?" in text and "₦1,326.81" in text
    for rng in ["₦1,130 – ₦2,030", "₦1,090 – ₦3,390", "₦1,090 – ₦6,870"]:
        assert rng in text, f"outlook range {rng} not on screen"
    print("ok  The naira renders: hero, history, outlook ranges match the article (Sep 2027/2028/2030)")
    print("    What this means:", text.split("What this means</h2><p>")[1].split("</p>")[0])
    published = {"Stable reforms": "₦1,230 – ₦2,010", "History repeats": "₦1,390 – ₦3,000",
                 "Oil shock": "₦2,090 – ₦4,500", "Policy reversal": "₦2,060 – ₦3,440"}
    for name, rng in published.items():
        at = run("pages/naira.py", state={"scenario": name, "fx_scale": "Log", "fx_period": "Last 2 years"})
        assert rng in everything(at), f"{name}: {rng} not on screen"
    print("ok  all four scenarios show the article's Sep 2030 ranges; log scale and short period render")
    print("All app smoke tests passed.")


if __name__ == "__main__":
    main()
