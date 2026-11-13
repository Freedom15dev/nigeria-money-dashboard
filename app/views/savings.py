"""My savings: "What is your money worth today?" Layout: design/Main.dc.html (desktop) and
design/SavingsPhone.dc.html (phone). All numbers come from data/processed/ via money_math."""

import calendar
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import (NAVY, OPTION_COLORS, brand_header, change_badge, e, footer, info_box, legend,
                        load_meta, load_panel, naira, page_intro, section_head, show_chart, style_figure,
                        under_the_hood)
from money_math import DOLLARS, FIXED, MATTRESS, OPTIONS, SAVINGS, TBILL, InputProblem, savings_journey

panel = load_panel()
meta = load_meta()
latest = pd.Timestamp(meta["latest_month"])
first = panel.dropna(subset=["savingsDeposit"])["month"].min()
by_month = panel.set_index("month")

PRESETS = {"₦50k": 50_000, "₦100k": 100_000, "₦500k": 500_000, "₦1m": 1_000_000}
MONTHS = list(calendar.month_name)[1:]
YEARS = list(range(first.year, latest.year + 1))

KEPT_IN = {SAVINGS: "in a <b>savings account</b>", FIXED: "in a <b>12-month fixed deposit</b>",
           TBILL: "in <b>Treasury bills</b>", DOLLARS: "in <b>dollars</b>", MATTRESS: "<b>under the mattress</b>"}
IN_HAND = {SAVINGS: "In the account today", FIXED: "In the fixed deposit today", TBILL: "In Treasury bills today",
           DOLLARS: "Changed back to naira today", MATTRESS: "In cash today"}
IN_SENTENCE = {SAVINGS: "the savings account", FIXED: "the 12-month fixed deposit", TBILL: "Treasury bills",
               DOLLARS: "dollars", MATTRESS: "cash under the mattress"}
HOW = {
    SAVINGS: "CBN average savings rate, with interest added every month (rate ÷ 12).",
    FIXED: "CBN average 12-month deposit rate, locked for a year, then rolled over at the rate then.",
    TBILL: "CBN 91-day Treasury bill rate, locked for 3 months, then rolled over at the rate then.",
    DOLLARS: "Changed to dollars at the start month's official rate, kept as cash dollars (no interest), "
             "changed back at the latest official rate.",
    MATTRESS: "Cash kept at home, earning nothing. Always shown, as the baseline.",
}


# ----------------------------------------------------------------------------- amount box helpers
def parse_amount(text):
    """'100,000', '₦100000', '100k', '1.5m' -> number. None if it isn't a number."""
    t = str(text).lower().replace("₦", "").replace(",", "").replace(" ", "").replace("naira", "")
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([km]?)", t)
    if not m:
        return None
    return float(m.group(1)) * {"": 1, "k": 1_000, "m": 1_000_000}[m.group(2)]


def matching_preset(value):
    return next((label for label, v in PRESETS.items() if value == v), None)


def on_amount_typed():
    value = parse_amount(st.session_state.amount)
    if value is not None:
        st.session_state.amount = f"{value:,.0f}"
    st.session_state.quick = matching_preset(value)


def on_quick_pick():
    if st.session_state.quick:
        st.session_state.amount = f"{PRESETS[st.session_state.quick]:,}"


st.session_state.setdefault("amount", "100,000")
st.session_state.setdefault("quick", "₦100k")
st.session_state.setdefault("kept", list(OPTIONS))

# ----------------------------------------------------------------------------- intro + inputs
brand_header("My savings", meta)
page_intro("My savings", "What is your money worth today?",
           "See how rising prices changed the value of money you saved, and where it held up best.", meta)

with st.container(key="panel-inputs"):
    left, right = st.columns([2, 2], gap="medium")
    with left:
        st.text_input("Amount saved", key="amount", on_change=on_amount_typed,
                      help="Type an amount in naira, for example 100,000 or 100k.")
        st.pills("Quick amounts", list(PRESETS), key="quick", on_change=on_quick_pick, label_visibility="collapsed")
    with right:
        with st.container(key="dates"):
            c_month, c_year = st.columns([3, 2])
            month_name = c_month.selectbox("Saved from", MONTHS, index=0, key="start_month")
            year = c_year.selectbox("Year", YEARS, index=0, key="start_year")
    chosen = st.pills("Where was it kept? :gray[Pick any to compare. Under the mattress is always shown.]",
                      OPTIONS, selection_mode="multi", key="kept")

amount = parse_amount(st.session_state.amount)
start = pd.Timestamp(year=year, month=MONTHS.index(month_name) + 1, day=1)
chosen = [o for o in OPTIONS if o in (chosen or [])]  # keep a fixed order

try:
    if amount is None:
        raise InputProblem("Type the amount in naira, for example 100,000.")
    journey = savings_journey(panel, amount, start)
except InputProblem as problem:
    st.info(f"👉 {problem}")
    footer()
    st.stop()

shown = chosen + [MATTRESS]
s = journey.summary.loc[shown].sort_values("buys_what_then", ascending=False)
ranked = list(s.index)
lead = chosen[0] if chosen else MATTRESS
start_label, end_label, start_short = f"{journey.start:%B %Y}", f"{journey.end:%B %Y}", f"{journey.start:%b %Y}"
need_today = s.iloc[0]["start_in_todays_prices"]

# ----------------------------------------------------------------------------- the answer (navy hero)
r = s.loc[lead]
st.html(
    f'<section class="mm mm-hero" aria-label="The answer"><div class="main">'
    f'<p class="soft">{naira(amount)} kept {KEPT_IN[lead]} since {start_label}</p>'
    f'<div class="figs">'
    f'<div class="fig"><span class="lbl">{IN_HAND[lead]}</span><span class="num">{naira(r["naira_today"])}</span></div>'
    f'<span class="arrow" aria-hidden="true">→</span>'
    f'<div class="fig"><span class="lbl">What it buys, in {start_label} money</span>'
    f'<span class="num warm">{naira(r["buys_what_then"])}</span></div></div>'
    f'{change_badge(r["real_change_pct"])}</div>'
    f'<div class="side"><p>Prices are <b>{journey.price_multiple:,.2f} times</b> what they were in {start_label}.</p>'
    f'<p>You\'d need <b>{naira(need_today)}</b> today to buy what {naira(amount)} bought then.</p></div>'
    f'</section>'
)


# ----------------------------------------------------------------------------- how each option did
def card_note(option, rank, change_pct):
    if rank == 1:
        return "Beat rising prices." if change_pct > 0 else "Came closest to keeping up with prices."
    if option == SAVINGS:
        a, b = by_month.loc[journey.start, "savingsDeposit"], by_month.loc[journey.end, "savingsDeposit"]
        verb = "fell" if b < a else "rose" if b > a else "stayed"
        return f"The rate {verb} from {a:.1f}% to {b:.1f}% a year." if verb != "stayed" else f"The rate stayed at {a:.1f}% a year."
    if option == FIXED:
        return "Rolled over each year at the rate then."
    if option == TBILL:
        return "91-day bills, rolled over every 3 months."
    if option == DOLLARS:
        a, b = by_month.loc[journey.start, "usd_ngn"], by_month.loc[journey.end, "usd_ngn"]
        verb = "weakened" if b > a else "strengthened"
        return f"The naira {verb} from {naira(a)} to {naira(b)} per $1."
    return "Earned nothing while prices rose."


section_head("How each option did", "Best to worst, by what the money buys now")
cards, rows = [], []
for rank, option in enumerate(ranked, start=1):
    r = s.loc[option]
    is_lead = " lead" if option == lead else ""
    cards.append(
        f'<article class="mm-card{is_lead}"><div class="top"><span class="rank">#{rank}</span>'
        f'{change_badge(r["real_change_pct"], "sm", short=True)}</div>'
        f'<h3>{e(option)}</h3><p class="num">{naira(r["buys_what_then"])}</p>'
        f'<p class="sub">{naira(r["naira_today"])} in naira today</p>'
        f'<p class="sub">{e(card_note(option, rank, r["real_change_pct"]))}</p></article>'
    )
    rows.append(
        f'<div class="row{is_lead}"><span class="rank">{rank}</span>'
        f'<div class="name"><b>{e(option)}</b><span>{naira(r["naira_today"])} in naira</span></div>'
        f'<div class="val"><b>{naira(r["buys_what_then"])}</b>{change_badge(r["real_change_pct"], "xs", short=True)}</div></div>'
    )
st.html(f'<div class="mm mm-cards rank-cards">{"".join(cards)}</div><div class="mm mm-list">{"".join(rows)}</div>')
st.caption(f"Big numbers are what the money buys now, in {start_label} money. "
           + (f"Dollars: {naira(amount)} bought ${journey.usd_bought:,.2f} at the official rate in {start_label}."
              if DOLLARS in chosen else ""))

# ----------------------------------------------------------------------------- chart
with st.container(key="panel-chart"):
    st.html(f'<div class="mm"><h2>Buying power month by month, in {e(start_label)} money</h2>'
            f'<p style="font-size:14px;color:#4A5568;margin-top:4px">Below the dashed line, your money buys less '
            f'than when you saved it.</p></div>')
    values = journey.start_money
    fig = go.Figure()
    for option in reversed(ranked):  # best drawn last, on top
        fig.add_trace(go.Scatter(
            x=values.index, y=values[option], name=option, mode="lines",
            line=dict(color=OPTION_COLORS[option], width=3, dash="dot" if option == MATTRESS else "solid"),
            hovertemplate="₦%{y:,.0f}",
        ))
    fig.add_hline(y=amount, line_dash="dash", line_color=NAVY, line_width=1.5)
    fig.update_yaxes(tickprefix="₦", tickformat="~s")
    style_figure(fig)
    show_chart(fig)
    legend([(o, OPTION_COLORS[o], o == MATTRESS) for o in ranked])
    st.caption(f"Dashed line: the {naira(amount)} you started with.")


# ----------------------------------------------------------------------------- what this means
def what_this_means():
    since = f"Since {start_label}"
    chg = s["real_change_pct"]
    best, worst = ranked[0], ranked[-1]
    years = (journey.end.year - journey.start.year) + (journey.end.month - journey.start.month) / 12
    fx_a, fx_b = by_month.loc[journey.start, "usd_ngn"], by_month.loc[journey.end, "usd_ngn"]

    if not chosen:
        return (f"{since}, cash under the mattress lost {abs(chg[MATTRESS]):.1f}% of its value, because prices "
                f"rose {journey.price_multiple:,.2f} times. Pick where the money was kept, above, to compare.")
    # Say why when dollars are at either end: their naira value only moves with the exchange rate.
    best_why = ", because the naira lost value against the dollar" if best == DOLLARS and fx_b > fx_a else ""
    worst_why = ", because the naira got stronger over this period" if worst == DOLLARS and fx_b < fx_a else ""
    winners = [o for o in ranked if chg[o] > 0]
    if not winners:
        text = (f"{since}, none of these options kept up with prices. {IN_SENTENCE[best].capitalize()} came "
                f"closest, losing {abs(chg[best]):.1f}% in buying power{best_why}. "
                f"{IN_SENTENCE[worst].capitalize()} did worst, losing {abs(chg[worst]):.1f}%{worst_why}.")
    elif len(winners) == 1:
        text = (f"{since}, only {IN_SENTENCE[best]} beat rising prices, gaining {chg[best]:.1f}% in buying "
                f"power{best_why}. {IN_SENTENCE[worst].capitalize()} did worst, losing {abs(chg[worst]):.1f}%{worst_why}.")
    else:
        names = [IN_SENTENCE[o] for o in winners]
        listed = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
        text = (f"{since}, {listed} beat rising prices. {IN_SENTENCE[best].capitalize()} did best, gaining "
                f"{chg[best]:.1f}% in buying power{best_why}. {IN_SENTENCE[worst].capitalize()} did worst, "
                f"losing {abs(chg[worst]):.1f}%{worst_why}.")
    text += (" Over longer periods the picture can change. Try an earlier start year to see." if years < 5
             else " Try a more recent start year to see how the picture changes.")
    return text


info_box("What this means", e(what_this_means()))

# ----------------------------------------------------------------------------- method + caveats
with st.expander("How each option is worked out"):
    for option in [SAVINGS, FIXED, TBILL, DOLLARS, MATTRESS]:
        st.markdown(f"- **{option}**: {HOW[option]}")
    st.markdown(
        "- **What it buys** uses a price index built from CBN inflation figures: the naira value is divided by "
        f"how much prices rose since the start month ({journey.price_multiple:,.2f} times since {start_label}).")
    st.caption(
        "Rates are CBN averages across banks; your own bank and account will differ. Taxes and fees are not "
        "included, so real savers did a little worse than shown. Dollars use the official CBN rate, not the "
        "street rate, which many savers couldn't get before 2023. This is not financial advice.")

under_the_hood(
    meta,
    ["revised_2025_inflation", "june_2025_repeat", "rebasing_2025", "tbill_zeros", "exchange_rates"],
    extra_md=(
        "**How the price index works.** Each month's yearly inflation rate is turned into a monthly step "
        "(12% a year ≈ 0.95% a month), and the steps are multiplied together. This is an approximation: it "
        "reacts a few months late when inflation changes fast, so start-to-end results are solid and values in "
        "between are rough. Same method as the savings article.\n\n"
        "**How each option grows.** Interest earned in a month uses the rate at the start of that month. A fixed "
        "deposit's and a Treasury bill's interest is spread evenly over its term, so the line is smooth but lands "
        "on exactly what the bank would pay at each rollover.\n\n**Known data fixes:**"
    ),
)
footer()
