"""Home: (+234) Money Matters, "Your money, this month"."""

import pandas as pd
import streamlit as st

from components import (APP_NAME, DESCRIPTION, HELP, LOAN_CALCULATOR_URL, SUPPORTING_LINE, TAGLINE,
                        data_up_to, footer, load_meta, load_panel, naira, pct, pct_delta, points)

panel = load_panel().set_index("month")
meta = load_meta()
latest = pd.Timestamp(meta["latest_month"])
year_ago = latest - pd.DateOffset(years=1)
now, then = panel.loc[latest], panel.loc[year_ago]

st.title(APP_NAME)
st.markdown(f"#### {TAGLINE}")
st.caption(SUPPORTING_LINE)
data_up_to(meta)

with st.expander("About Money Matters"):
    st.write(DESCRIPTION)

st.subheader("Your money, this month")

# ----------------------------------------------------------------------------- the sentence
real = now["real_savings_rate"]
direction = "losing" if real < 0 else "gaining"
st.markdown(
    f'<p class="mm-sentence">Prices are rising <b>{pct(now["inflation"])}</b> a year. '
    f'A savings account pays <b>{pct(now["savingsDeposit"])}</b>. Money in a savings account is '
    f'<b>{direction} about {abs(real):.1f}%</b> of its value each year.</p>',
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------- KPI cards
st.caption(f"Each card shows the change since {year_ago:%B %Y}.")
fx_change = (now["usd_ngn"] / then["usd_ngn"] - 1) * 100
cards = [
    ("Inflation", pct(now["inflation"]), points(now["inflation"] - then["inflation"]), "inverse", HELP["inflation"]),
    ("₦ per $1 (official)", naira(now["usd_ngn"], 2), pct_delta(fx_change), "inverse", HELP["usd"]),
    ("Policy rate (MPR)", pct(now["policy_rate"]), points(now["policy_rate"] - then["policy_rate"]), "off", HELP["mpr"]),
    ("Prime lending rate", pct(now["primeLending"]), points(now["primeLending"] - then["primeLending"]), "inverse", HELP["prime"]),
    ("Maximum lending rate", pct(now["maxLending"]), points(now["maxLending"] - then["maxLending"]), "inverse", HELP["max"]),
    ("Savings account rate", pct(now["savingsDeposit"]), points(now["savingsDeposit"] - then["savingsDeposit"]), "normal", HELP["savings"]),
    ("Real savings rate", pct(real), points(real - then["real_savings_rate"]), "normal", HELP["real"]),
]
for row_start in range(0, len(cards), 2):
    cols = st.columns(2)
    for col, (label, value, delta, colour, help_text) in zip(cols, cards[row_start:row_start + 2]):
        col.metric(label, value, delta, delta_color=colour, help=help_text, border=True)

st.caption(
    "Green means better for an ordinary saver or borrower, red means worse. "
    "For the dollar rate, up means the naira got weaker. Rates are CBN averages; real banks differ."
)

# ----------------------------------------------------------------------------- where next
st.subheader("Explore")
c1, c2 = st.columns(2)
with c1.container(border=True):
    st.markdown("**💰 My savings**")
    st.caption("What is money you saved years ago worth today? Compare a savings account, fixed deposit, "
               "Treasury bills and dollars.")
    st.page_link("pages/savings.py", label="Work out my savings →")
with c2.container(border=True):
    st.markdown("**🧮 Loan calculator**")
    st.caption("What will a loan really cost you? Compare banks, microfinance and loan apps.")
    st.link_button("Work out your own loan →", LOAN_CALCULATOR_URL)

with st.container(border=True):
    st.markdown("**Coming soon**")
    st.caption("📈 Prices: inflation since 2003 and where it may go next · 💱 The naira: its history and "
               "a range for 2030 · 🏦 Borrowing: who pays what to borrow")

footer()
