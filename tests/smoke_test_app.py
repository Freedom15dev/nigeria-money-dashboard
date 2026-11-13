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
    print("All app smoke tests passed.")


if __name__ == "__main__":
    main()
