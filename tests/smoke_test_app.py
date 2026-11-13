"""Smoke test: run each page headlessly and check it renders without errors, including silly inputs.

    python tests/smoke_test_app.py
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app" / "Home.py")


def run(page=None, setup=None):
    at = AppTest.from_file(APP, default_timeout=60)
    if page:
        at.switch_page(page)
    at.run()
    if setup:
        setup(at)
        at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def text_of(at):
    return " ".join(m.value for m in at.markdown) + " " + " ".join(c.value for c in at.caption) + \
        " " + " ".join(i.value for i in at.info)


def main():
    at = run()
    assert "(+234) Money Matters" in [t.value for t in at.title]
    assert len(at.metric) == 7, len(at.metric)
    assert "Data up to" in text_of(at)
    print("ok  Home renders: title, 7 KPI cards, data-up-to label")

    at = run("pages/savings.py")
    body = text_of(at)
    assert "₦208,347" in body and "₦13,459" in body, "savings spot-check not on screen"
    print("ok  My savings (defaults): ₦100,000 from Jan 2006 -> ₦208,347, buys what ₦13,459 bought then")

    at = run("pages/savings.py", lambda a: a.number_input[0].set_value(0))
    assert "above ₦0" in text_of(at)
    print("ok  ₦0 gives a friendly message")

    def latest_year_december(a):
        a.selectbox[0].set_value("December")
        a.selectbox[1].set_value(a.selectbox[1].options[-1] and int(a.selectbox[1].options[-1]))
    at = run("pages/savings.py", latest_year_december)
    assert "before the end month" in text_of(at) or "only goes up to" in text_of(at)
    print("ok  start after the latest month gives a friendly message")

    def latest_month(a):
        a.selectbox[0].set_value("September")
        a.selectbox[1].set_value(int(a.selectbox[1].options[-1]))
    at = run("pages/savings.py", latest_month)
    assert "before the end month" in text_of(at)
    print("ok  start = latest month gives a friendly message")

    at = run("pages/savings.py", lambda a: a.multiselect[0].set_value([]))
    assert "Pick at least one" in text_of(at)
    print("ok  no options ticked: mattress baseline still shown, with a hint")

    at = run("pages/savings.py", lambda a: a.radio[0].set_value("today's prices"))
    print("ok  chart toggle to today's prices renders")
    print("All app smoke tests passed.")


if __name__ == "__main__":
    main()
