"""Borrowing: what banks charge their best and riskiest borrowers, what that costs after inflation,
and how much of the country's credit goes to government. Same design as the other pages.
Definitions from nigeria-credit-squeeze. Every number comes from data/processed/."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import (BLUE, GREY, HELP, NAVY, ORANGE, brand_header, change_text,
                        e, footer, info_box, kpi_card, legend, load_meta, load_panel, page_intro, pct, section_head,
                        show_chart, style_figure, under_the_hood)

panel = load_panel()
meta = load_meta()
latest = pd.Timestamp(meta["latest_month"])
year_ago = latest - pd.DateOffset(years=1)
p = panel[panel["month"] >= "2006-01-01"].set_index("month")
now, then = p.loc[latest], p.loc[year_ago]
PERIODS = {"Since 2006": None, "Last 10 years": 10, "Last 5 years": 5, "Last 2 years": 2}

st.session_state.setdefault("borrow_period", "Since 2006")

brand_header("Borrowing", meta)
page_intro("Borrowing", "What does it cost to borrow?",
           "What banks charge their best and their riskiest borrowers, what that costs after inflation, and who "
           "gets the country's credit.", meta)

# ----------------------------------------------------------------------------- the answer (navy hero)
# The navy card is a Streamlit container so its button can be a real st.page_link to My loan.
with st.container(key="hero-borrow", horizontal=True, vertical_alignment="center"):
    st.html(
        f'<section class="mm mm-hero bare" aria-label="Borrowing this month"><div class="main">'
        f'<p class="soft">Average bank lending rates, {latest:%B %Y}</p>'
        f'<div class="figs">'
        f'<div class="fig"><span class="lbl">Best borrowers (prime)</span><span class="num">{pct(now["primeLending"])}</span></div>'
        f'<div class="fig"><span class="lbl">Riskier borrowers (maximum)</span><span class="num warm">{pct(now["maxLending"])}</span></div>'
        f'</div><span class="mm-pill flat">A gap of {now["lending_gap"]:.1f} points between them</span></div>'
        f'<div class="side"><p>After inflation ({pct(now["inflation"])}), that is <b>{pct(now["real_prime"], 1)}</b> a year for '
        f'the best borrowers and <b>{pct(now["real_max"], 1)}</b> for riskier ones.</p>'
        f'<p>Small businesses and individuals usually pay the maximum rate or more. Loan apps price by the month.</p>'
        f'</div></section>'
    )
    with st.container(key="cta", width="content"):
        st.page_link("views/loan.py", label="Work out your own loan →")


# ----------------------------------------------------------------------------- key numbers
def then_value(col):
    """Year-ago value; a feed glitch removed by the pipeline is replaced by its straight-line chart value."""
    v = then[col]
    chart = f"{col}_chart"
    if pd.isna(v) and chart in p.columns and pd.notna(then[chart]):
        return then[chart], True
    return v, False


estimated = []
cards = []
for title, col, good_when, words, help_text in [
    ("Prime lending rate", "primeLending", "down", ("cheaper", "dearer"), HELP["prime"]),
    ("Maximum lending rate", "maxLending", "down", ("cheaper", "dearer"), HELP["max"]),
    ("Gap: riskier minus best", "lending_gap", "down", ("narrower", "wider"),
     "How much more the riskiest borrowers pay than the best ones, in percentage points."),
    ("Real prime rate", "real_prime", None, ("lower after inflation", "higher after inflation"), HELP["real"]),
    ("Real maximum rate", "real_max", None, ("lower after inflation", "higher after inflation"), HELP["real"]),
]:
    old, est = then_value(col)
    d = now[col] - old
    note = words[0] if d < 0 else words[1]
    if est:
        note += f" (vs an estimated {year_ago:%b %Y})"
        estimated.append(col)
    value = f"{now[col]:.1f} pts" if col == "lending_gap" else pct(now[col])
    cards.append(kpi_card(title, value, change_text(d, "pts", good_when, note), help_text))

gov_now, gov_then = now["gov_share"], then["gov_share"]
cards.append(kpi_card(
    "Government's share of credit", pct(gov_now, 1),
    change_text(gov_now - gov_then, "pts", "down", "more for government" if gov_now > gov_then else "more for businesses"),
    "Credit to government ÷ all domestic credit from the banking system. The private sector (businesses and "
    "households) gets the rest."))
section_head("The key numbers", f"{latest:%B %Y}, compared with {year_ago:%B %Y}")
st.html(f'<div class="mm mm-cards">{"".join(cards)}</div>')
RATE_NAMES = {"primeLending": "prime rate", "maxLending": "maximum lending rate", "savingsDeposit": "savings rate",
              "treasuryBill": "Treasury bill rate", "policy_rate": "policy rate"}
if estimated:  # one line per feed glitch behind an estimated card; the full explanation is under the hood
    for s in meta.get("rate_spikes", []):
        if s["month"] == f"{year_ago:%Y-%m}":
            st.caption(f"{year_ago:%B %Y} {RATE_NAMES.get(s['column'], s['column'])} estimated: the CBN figure "
                       f"({s['value']:.2f}%) was a one-month glitch.")

# ----------------------------------------------------------------------------- period
with st.container(key="panel-inputs"):
    period = st.pills("Period", list(PERIODS), key="borrow_period") or "Since 2006"
years = PERIODS[period]
view = p if years is None else p.loc[latest - pd.DateOffset(years=years):]

# ----------------------------------------------------------------------------- chart 1: prime vs max
with st.container(key="panel-rates"):
    st.html(f'<div class="mm"><h2>The price of a bank loan, {view.index.min():%b %Y} to {latest:%b %Y}</h2>'
            f'<p style="font-size:14px;color:#4A5568;margin-top:4px">Shaded: the gap between what riskier and the '
            f'best borrowers pay.</p></div>')
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=view.index, y=view["primeLending_chart"], name="Prime", mode="lines",
                             line=dict(color=BLUE, width=2.5), hovertemplate="prime %{y:.2f}%"))
    fig.add_trace(go.Scatter(x=view.index, y=view["maxLending_chart"], name="Maximum", mode="lines",
                             line=dict(color=ORANGE, width=2.5), fill="tonexty", fillcolor="rgba(217,130,43,0.13)",
                             hovertemplate="maximum %{y:.2f}%"))
    fig.add_trace(go.Scatter(x=view.index, y=view["policy_rate_chart"], name="CBN policy rate", mode="lines",
                             line=dict(color=NAVY, width=1.5, dash="dot"), hovertemplate="policy rate %{y:.2f}%"))
    fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    style_figure(fig, height=340)
    show_chart(fig)
    legend([("Maximum lending rate (riskier borrowers)", ORANGE, False), ("Prime lending rate (best borrowers)", BLUE, False),
            ("Gap between them", "#F3D3B3", False), ("CBN policy rate (MPR)", NAVY, True)])
    st.caption("Monthly CBN averages across banks; your own bank will differ. A one-month glitch in the feed "
               "(prime, Sep 2025) is drawn as a straight line.")

# ----------------------------------------------------------------------------- chart 2: real rates
with st.container(key="panel-real"):
    st.html('<div class="mm"><h2>Lending rates after inflation</h2>'
            '<p style="font-size:14px;color:#4A5568;margin-top:4px">Below zero, inflation was eating the loan faster '
            'than interest grew it: cheap for the borrower, a loss for the lender.</p></div>')
    fig = go.Figure()
    fig.add_hrect(y0=min(view["real_prime_chart"].min(), 0) - 2, y1=0, fillcolor=GREY, opacity=0.08, line_width=0)
    fig.add_hline(y=0, line_color=NAVY, line_width=1)
    fig.add_trace(go.Scatter(x=view.index, y=view["real_prime_chart"], name="Real prime", mode="lines",
                             line=dict(color=BLUE, width=2.5), hovertemplate="real prime %{y:.1f}%"))
    fig.add_trace(go.Scatter(x=view.index, y=view["real_max_chart"], name="Real maximum", mode="lines",
                             line=dict(color=ORANGE, width=2.5), hovertemplate="real maximum %{y:.1f}%"))
    fig.update_yaxes(ticksuffix="%")
    style_figure(fig, height=320)
    show_chart(fig)
    legend([("Real maximum rate", ORANGE, False), ("Real prime rate", BLUE, False)])
    neg = int((p["real_prime"] < 0).sum())
    st.caption(f"{HELP['real']} Since January 2006 the real prime rate was below zero in {neg} of "
               f"{int(p['real_prime'].notna().sum())} months.")

# ----------------------------------------------------------------------------- chart 3: government's share
with st.container(key="panel-gov"):
    st.html(f'<div class="mm"><h2>Who gets the credit? Government\'s share, {view.index.min():%b %Y} to {latest:%b %Y}</h2>'
            f'<p style="font-size:14px;color:#4A5568;margin-top:4px">Credit to government ÷ all domestic credit. '
            f'The private sector gets the rest. Grey: years when government was a net lender.</p></div>')
    fig = go.Figure()
    lender = view["gov_net_lender"].fillna(False)
    runs = (lender != lender.shift()).cumsum()
    for _, g in lender[lender].groupby(runs[lender]):
        fig.add_vrect(x0=g.index[0], x1=g.index[-1] + pd.DateOffset(months=1), fillcolor=GREY, opacity=0.15,
                      line_width=0)
    fig.add_trace(go.Scatter(x=view.index, y=view["gov_share_chart"], name="Government's share", mode="lines",
                             line=dict(color=BLUE, width=2.5), connectgaps=False,
                             hovertemplate="government %{y:.1f}%"))
    fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    style_figure(fig, height=320)
    show_chart(fig)
    legend([("Government's share of domestic credit", BLUE, False), ("Government a net lender (share not shown)",
                                                                     "#D5D9E0", False)])
    st.caption(meta["trap_notes"]["credit_to_government_negative"])

# ----------------------------------------------------------------------------- loan calculator
with st.container(key="explore", horizontal=True):
    with st.container(key="explore-borrowing"):
        st.html('<div class="mm" style="display:flex;flex-direction:column;gap:8px">'
                '<span style="font-size:18px;font-weight:700">What will your loan really cost?</span>'
                '<span style="font-size:14px;line-height:1.5;color:#4A5568">My loan compares a bank loan at the '
                'prime and maximum rates with loan app rates, month by month, and shows what you would really '
                'repay, including if you pay late.</span></div>')
        st.page_link("views/loan.py", label="Work out your own loan →")

# ----------------------------------------------------------------------------- what this means
gap_peak_month = p["lending_gap"].idxmax()
real_dir = "positive" if now["real_prime"] > 0 else "negative"
info_box("What this means", e(
    f"In {latest:%B %Y} banks charged their best customers {pct(now['primeLending'])} and their riskiest "
    f"{pct(now['maxLending'])}, a gap of {round(now['lending_gap'], 1)} points (it was {round(p['lending_gap'].iloc[0], 1)} in "
    f"{p.index[0]:%B %Y} and peaked at {round(p['lending_gap'].max(), 1)} in {gap_peak_month:%B %Y}). With prices rising "
    f"{pct(now['inflation'])} a year, the real prime rate is {real_dir} at {pct(now['real_prime'], 1)}, and the real "
    f"maximum rate is {pct(now['real_max'], 1)}: for a small business paying the maximum, borrowing is expensive "
    f"even after inflation. Government takes {pct(gov_now, 1)} of domestic credit, against "
    f"{pct(p['gov_share'].iloc[0], 1)} in {p.index[0]:%B %Y}, leaving less of the banks' lending for businesses "
    f"and households."
))

under_the_hood(
    meta, ["rate_spikes", "policy_rate", "credit_march_2026", "credit_to_government_negative"],
    extra_md=(
        "**Definitions** follow the [credit article](https://www.linkedin.com/pulse/who-gets-borrow-nigeria-i-followed-"
        "two-borrowers-find-freedom-oboh-q6mof). Prime and maximum lending rates are CBN monthly averages across "
        "banks. Real rates use the Fisher formula: (1 + rate) ÷ (1 + inflation) − 1. Government's share is credit "
        "to government ÷ net domestic credit (credit to government plus credit to the private sector).\n\n"
        "**Self-check:** each monthly run recomputes the article's numbers on data to September 2026 and must "
        "match them, or the update is stopped. One known difference is listed in the run log: the article counted "
        "the prime rate's September 2025 glitch.\n\n**Data notes:**"
    ),
)
footer()
