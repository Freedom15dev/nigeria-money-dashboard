"""My savings: "What is my money worth today?" """

import calendar

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import (HELP, OPTION_COLORS, data_up_to, footer, load_meta, load_panel, naira, pct,
                        show_chart, style_figure, under_the_hood)
from money_math import MATTRESS, OPTIONS, InputProblem, savings_journey

panel = load_panel()
meta = load_meta()
latest = pd.Timestamp(meta["latest_month"])
first = panel.dropna(subset=["savingsDeposit"])["month"].min()

OPTION_HELP = {
    "Savings account": "CBN average savings rate, with interest added every month (rate ÷ 12).",
    "12-month fixed deposit": "CBN average 12-month deposit rate, locked for a year, then rolled over at the rate then.",
    "Treasury bills": "CBN 91-day Treasury bill rate, locked for 3 months, then rolled over at the rate then.",
    "Dollars": "Changed to dollars at the start month's official rate, kept as cash dollars (no interest), "
               "changed back at the latest official rate.",
}
SHORT = {"Savings account": "a savings account", "12-month fixed deposit": "12-month fixed deposits",
         "Treasury bills": "Treasury bills", "Dollars": "dollars", MATTRESS: "cash under the mattress"}

st.title("What is my money worth today?")
data_up_to(meta)

# ----------------------------------------------------------------------------- inputs
with st.container(border=True):
    amount = st.number_input("Amount saved (₦)", min_value=0, value=100_000, step=10_000, format="%d")
    st.caption(f"= {naira(amount)}")
    c1, c2 = st.columns(2)
    month_names = list(calendar.month_name)[1:]
    start_month_name = c1.selectbox("Start month", month_names, index=0)
    years = list(range(first.year, latest.year + 1))
    start_year = c2.selectbox("Start year", years, index=0)
    chosen = st.multiselect("Where was it kept?", OPTIONS, default=OPTIONS,
                            help="Cash under the mattress is always shown, as the baseline.")
    with st.expander("How each option is worked out"):
        for o in OPTIONS:
            st.markdown(f"- **{o}**: {OPTION_HELP[o]}")
        st.markdown(f"- **{MATTRESS}**: cash kept at home, earning nothing.")

start = pd.Timestamp(year=start_year, month=month_names.index(start_month_name) + 1, day=1)

try:
    journey = savings_journey(panel, amount, start)
except InputProblem as problem:
    st.info(f"👉 {problem}")
    footer()
    st.stop()

shown = [MATTRESS] + chosen
s = journey.summary.loc[shown]
start_label, end_label = f"{journey.start:%B %Y}", f"{journey.end:%B %Y}"

# ----------------------------------------------------------------------------- the sentence
lead = chosen[0] if chosen else MATTRESS
row = s.loc[lead]
st.markdown(
    f'<p class="mm-sentence">{naira(amount)} kept in {SHORT[lead]} since {start_label} is now '
    f'<b>{naira(row["naira_today"])}</b>. In today\'s prices, that buys what <b>{naira(row["buys_what_then"])}</b> '
    f'bought then.</p>',
    unsafe_allow_html=True,
)
st.caption(f"Prices in {end_label} are {journey.price_multiple:,.1f} times what they were in {start_label}, "
           f"so you would need {naira(s.iloc[0]['start_in_todays_prices'])} today to buy what "
           f"{naira(amount)} bought then.")

if not chosen:
    st.info("Pick at least one place in the box above to compare it with cash under the mattress.")

# ----------------------------------------------------------------------------- results
st.subheader(f"From {start_label} to {end_label}")
order = s.sort_values("naira_today", ascending=False).index
for i in range(0, len(order), 2):
    cols = st.columns(2)
    for col, option in zip(cols, order[i:i + 2]):
        r = s.loc[option]
        with col.container(border=True):
            st.markdown(f"<span style='color:{OPTION_COLORS[option]};font-weight:700'>● {option}</span>",
                        unsafe_allow_html=True)
            st.markdown(f'<p class="mm-big">{naira(r["naira_today"])}</p>'
                        f'<p class="mm-small">in naira today</p>', unsafe_allow_html=True)
            word = "gained" if r["real_change_pct"] >= 0 else "lost"
            colour = "#1E7F4F" if r["real_change_pct"] >= 0 else "#B3261E"
            st.markdown(
                f'<p class="mm-small">Buys what {naira(r["buys_what_then"])} bought in {journey.start:%b %Y}</p>'
                f'<p style="color:{colour};font-weight:600;margin:0">{word} {pct(abs(r["real_change_pct"]), 1)} '
                f'of its buying power</p>',
                unsafe_allow_html=True,
            )
if "Dollars" in chosen:
    st.caption(f"Dollars: {naira(amount)} bought ${journey.usd_bought:,.2f} at the official rate in {start_label}.")

# ----------------------------------------------------------------------------- chart
st.subheader("Buying power over time")
measure = st.radio(
    "Show values in",
    [f"{start_label} money", "today's prices"],
    horizontal=True,
    help=HELP["todays_prices"],
)
in_start_money = measure.endswith("money")
values = journey.start_money if in_start_money else journey.todays_prices
break_even = amount if in_start_money else s.iloc[0]["start_in_todays_prices"]

fig = go.Figure()
for option in shown:
    fig.add_trace(go.Scatter(
        x=values.index, y=values[option], name=option, mode="lines",
        line=dict(color=OPTION_COLORS[option], width=2.5 if option != MATTRESS else 2),
        hovertemplate="%{y:,.0f}",
    ))
fig.add_hline(y=break_even, line_dash="dash", line_color="#0F1E33", line_width=1,
              annotation_text=f"Break-even: {naira(break_even)}", annotation_position="top right",
              annotation_font_color="#4A5568")
fig.update_yaxes(tickprefix="₦", tickformat=",.0f", rangemode="tozero")
style_figure(fig, y_title=f"Buying power ({'in ' + start_label + ' naira' if in_start_money else 'in today’s prices'})")
show_chart(fig)
st.caption("Above the dashed line, the money buys more than it did at the start. Below it, it buys less.")

# ----------------------------------------------------------------------------- caveats
st.caption(
    "Rates are CBN averages across banks; your own bank and account will differ. Taxes and fees are not "
    "included, so real savers did a little worse than shown. Dollars use the official CBN rate, not the "
    "street rate, which many savers couldn't get before 2023. This is not financial advice."
)

under_the_hood(
    meta,
    ["revised_2025_inflation", "june_2025_repeat", "rebasing_2025", "tbill_zeros", "exchange_rates"],
    extra_md=(
        "**How the price index works.** Each month's yearly inflation rate is turned into a monthly step "
        "(12% a year ≈ 0.95% a month), and the steps are multiplied together. This is an approximation: it "
        "reacts a few months late when inflation changes fast, so start-to-end results are solid and "
        "values in between are rough. Same method as the "
        "[savings article](https://www.linkedin.com/pulse/i-followed-100000-20-years-heres-what-happened-nigerian-freedom-oboh-o090f).\n\n"
        "**How each option grows.** Interest earned in a month uses the rate at the start of that month. "
        "A fixed deposit's and a Treasury bill's interest is spread evenly over its term, so the line is "
        "smooth but lands on exactly what the bank would pay at each rollover.\n\n"
        "**Known data fixes:**"
    ),
)
footer()
