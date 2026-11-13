"""The naira: official ₦/$ history with the jump months, the backtest-adjusted outlook to 2030 and the
four scenarios. Same design as Home and My savings. Every number comes from data/processed/."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import (BLUE, GREY, HELP, NAVY, ORANGE, brand_header, e, footer, forecast_tracker, info_box,
                        legend, load_csv,
                        load_meta, load_panel, naira, naira_log_axis, page_intro, section_head, show_chart, style_figure,
                        under_the_hood)

panel = load_panel()
meta = load_meta()
outlook = load_csv("naira_outlook.csv")
scenarios = load_csv("naira_scenarios.csv")
notes = meta["models"]["naira"]
latest = pd.Timestamp(meta["latest_month"])
year_ago = latest - pd.DateOffset(years=1)
fx = panel.set_index("month")["usd_ngn"]
today, then = fx[latest], fx[year_ago]

JUMP = 0.05  # a jump month: the naira lost more than 5% in one month (naira-scenarios, Phase 4)
PERIODS = {"Since 2003": None, "Since 2016": 2016, "Last 5 years": -5, "Last 2 years": -2}
SCENARIO_NAMES = list(notes["scenarios"])
# 1, 2 and 4 years after the last month of data the outlook was made with (Sep 2027/2028/2030 for Sep 2026 data)
KEY_MONTHS = [outlook["month"].min() + pd.DateOffset(months=m - 1) for m in (12, 24, 48)]


def ten(x):
    """Ranges are shown to the nearest ₦10, as in the article: the precision is not real."""
    return naira(round(x, -1))


st.session_state.setdefault("fx_scale", "Normal")
st.session_state.setdefault("fx_period", "Since 2003")
st.session_state.setdefault("scenario", "History repeats")

brand_header("The naira", meta)
page_intro("The naira", "How much is the naira worth?",
           "The official dollar rate since 2003, how it fell (mostly in sudden jumps), and a range for 2030.", meta)

# ----------------------------------------------------------------------------- history facts
since06 = fx.loc["2006-01-01":]
returns = np.log(since06).diff().dropna()
is_jump = returns > np.log(1 + JUMP)
total_fall = returns.sum()
jump_share = returns[is_jump].sum() / total_fall if total_fall > 0 else np.nan
lost_since_06 = (1 - since06.iloc[0] / today) * 100
yoy = (today / then - 1) * 100

# ----------------------------------------------------------------------------- the answer (navy hero)
badge = (f'<span class="mm-pill good">The naira is {abs(yoy):.1f}% stronger than a year ago</span>' if yoy < 0 else
         f'<span class="mm-pill bad">The naira is {abs(yoy):.1f}% weaker than a year ago</span>')
st.html(
    f'<section class="mm mm-hero" aria-label="The naira this month"><div class="main">'
    f'<p class="soft">Official CBN rate, monthly average</p>'
    f'<div class="figs">'
    f'<div class="fig"><span class="lbl">One dollar in {latest:%B %Y}</span><span class="num">{naira(today, 2)}</span></div>'
    f'<span class="arrow" aria-hidden="true">←</span>'
    f'<div class="fig"><span class="lbl">In January 2006</span><span class="num warm">{naira(since06.iloc[0], 2)}</span></div>'
    f'</div>{badge}</div>'
    f'<div class="side"><p>Since January 2006 the naira has lost <b>{lost_since_06:.0f}%</b> of its value against the dollar.</p>'
    f'<p>Just <b>{int(is_jump.sum())} jump months since {since06.index[0]:%B %Y}</b> (a fall of more than 5% in one '
    f'month) account for about '
    f'<b>{jump_share * 100:.0f}%</b> of that fall. The rest of the time it barely moved.</p></div></section>'
)

# ----------------------------------------------------------------------------- history chart
with st.container(key="panel-inputs"):
    c1, c2 = st.columns(2)
    with c1:
        scale = st.pills("Scale", ["Normal", "Log"], key="fx_scale", help=HELP["log"]) or "Normal"
    with c2:
        period = st.pills("Period", list(PERIODS), key="fx_period") or "Since 2003"

p = PERIODS[period]
start = (fx.index.min() if p is None else pd.Timestamp(year=p, month=1, day=1) if p > 0
         else latest - pd.DateOffset(years=-p))
view = fx.loc[start:]
all_returns = np.log(fx).diff()
jumps = view[(all_returns.loc[view.index] > np.log(1 + JUMP))]
pct_move = (fx / fx.shift(1) - 1) * 100

with st.container(key="panel-history"):
    st.html(f'<div class="mm"><h2>Naira per US dollar, {view.index.min():%b %Y} to {latest:%b %Y}</h2>'
            f'<p style="font-size:14px;color:#4A5568;margin-top:4px">Up means the naira got weaker. '
            f'Orange dots: months the naira lost more than 5%.</p></div>')
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=view.index, y=view, name="Official rate", mode="lines",
                             line=dict(color=BLUE, width=2.5), hovertemplate="₦%{y:,.2f}"))
    fig.add_trace(go.Scatter(x=jumps.index, y=jumps, name="Jump month", mode="markers",
                             marker=dict(color=ORANGE, size=9, line=dict(color="#FFFFFF", width=1.5)),
                             customdata=pct_move.loc[jumps.index], hovertemplate="jump: +%{customdata:.1f}%"))
    if scale == "Log":
        naira_log_axis(fig, view.min(), view.max())
    else:
        fig.update_yaxes(tickprefix="₦", tickformat=",.0f", rangemode="tozero")
    style_figure(fig, height=340)
    show_chart(fig)
    legend([("Official rate (monthly average)", BLUE, False),
            (f"{len(jumps)} jump months since {view.index.min():%B %Y}", ORANGE, False)])

# ----------------------------------------------------------------------------- outlook
section_head(f"Where could the naira be by {KEY_MONTHS[-1]:%Y}?", "A range, not a prediction")
by_month = outlook.set_index("month")
cards = []
for month in KEY_MONTHS:
    r = by_month.loc[month]
    cards.append(
        f'<article class="mm-card mm-range"><span class="when">{month:%B %Y}</span>'
        f'<p class="num">{ten(r["low80"])} – {ten(r["high80"])}</p>'
        f'<p class="sub">4 in 5 chance (80% range)</p>'
        f'<p class="sub">Even odds: {ten(r["low50"])} – {ten(r["high50"])} (50% range)</p></article>')
st.html(f'<div class="mm mm-cards">{"".join(cards)}</div>')

with st.container(key="panel-outlook"):
    st.html(f'<div class="mm"><h2>The outlook to {KEY_MONTHS[-1]:%B %Y}</h2>'
            f'<p style="font-size:14px;color:#4A5568;margin-top:4px">Dark band: 50% range. Light band: 80% range. '
            f'Log scale, so equal steps are equal % changes.</p></div>')
    hist = fx.loc["2016-01-01":]
    x_join = [latest] + list(outlook["month"])

    def band(lo, hi, colour, name):
        return go.Scatter(x=x_join + x_join[::-1], y=[today] + list(outlook[hi]) + list(outlook[lo])[::-1] + [today],
                          fill="toself", fillcolor=colour, line=dict(width=0), hoverinfo="skip", name=name)

    fig = go.Figure()
    fig.add_trace(band("low80", "high80", "rgba(42,111,219,0.14)", "80% range"))
    fig.add_trace(band("low50", "high50", "rgba(42,111,219,0.30)", "50% range"))
    fig.add_trace(go.Scatter(x=hist.index, y=hist, name="Actual", mode="lines", line=dict(color=NAVY, width=2.5),
                             hovertemplate="₦%{y:,.0f}"))
    fig.add_trace(go.Scatter(x=x_join, y=[today] + list(outlook["median"]), name="Middle of the simulations",
                             mode="lines", line=dict(color=BLUE, width=2), hovertemplate="middle ₦%{y:,.0f}"))
    for col, label in [("low80", "80% low"), ("high80", "80% high")]:
        fig.add_trace(go.Scatter(x=outlook["month"], y=outlook[col], mode="lines", line=dict(width=0), name=label,
                                 hovertemplate=f"{label} ₦%{{y:,.0f}}"))
    fig.add_trace(go.Scatter(x=x_join, y=[today] * len(x_join), name="No change", mode="lines",
                             line=dict(color=GREY, width=1.5, dash="dash"), hoverinfo="skip"))
    naira_log_axis(fig, hist.min(), outlook["high80"].max())
    style_figure(fig, height=360)
    show_chart(fig)
    legend([("Actual", NAVY, False), ("Middle of the simulations", BLUE, False), ("50% range", "#94B7EC", False),
            ("80% range", "#C9DAF5", False), (f"No change ({naira(today)})", GREY, True)])
    st.caption("The middle line is there for orientation only; the band is the message. "
               "Official rate only, not the parallel (street) market. Ranges are not predictions.")

# ----------------------------------------------------------------------------- scenarios
section_head("Four 'what if' stories", f"Each story's 80% range for {KEY_MONTHS[-1]:%B %Y}")
choice = st.pills("Scenario", SCENARIO_NAMES, key="scenario", label_visibility="collapsed",
                  help=HELP["scenario"]) or "History repeats"
end = scenarios[scenarios["month"] == scenarios["month"].max()].set_index("scenario")
s = end.loc[choice]
story = notes["scenarios"][choice]
st.html(
    f'<div class="mm mm-cards"><article class="mm-card lead" style="flex:2 1 320px">'
    f'<span class="when" style="font-size:13px;font-weight:700;color:#2A6FDB">IF: {e(choice.upper())}</span>'
    f'<p style="font-size:16px;line-height:1.5">{e(story["story"])}</p>'
    f'<p class="sub">What changes in the model: {e(story["change"])}</p></article>'
    f'<article class="mm-card mm-range" style="flex:1 1 220px"><span class="when">THEN, BY {KEY_MONTHS[-1]:%b %Y}</span>'
    f'<p class="num">{ten(s["low80"])} – {ten(s["high80"])}</p>'
    f'<p class="sub">80% range within this story; middle about {ten(s["median"])}.</p></article></div>'
)

with st.container(key="panel-scenarios"):
    order = SCENARIO_NAMES[::-1]
    overall = by_month.loc[KEY_MONTHS[-1]]
    fig = go.Figure()
    fig.add_vrect(x0=overall["low80"], x1=overall["high80"], fillcolor=BLUE, opacity=0.08, line_width=0)
    for name in order:
        r = end.loc[name]
        picked = name == choice
        fig.add_trace(go.Scatter(x=[r["low80"], r["high80"]], y=[name, name], mode="lines",
                                 line=dict(color=ORANGE if picked else "#A9C5F0", width=14),
                                 hovertemplate=f"{name}: ₦%{{x:,.0f}}<extra></extra>"))
        fig.add_trace(go.Scatter(x=[r["median"]], y=[name], mode="markers",
                                 marker=dict(color=NAVY, size=10, line=dict(color="#FFFFFF", width=2)),
                                 hovertemplate=f"{name} middle: ₦%{{x:,.0f}}<extra></extra>"))
    fig.add_vline(x=today, line_dash="dash", line_color=GREY, line_width=1.5)
    naira_log_axis(fig, min(end["low80"].min(), today), max(end["high80"].max(), overall["high80"]), axis="x", sparse=True)
    fig.update_xaxes(showgrid=True, gridcolor="#EEF0F3")
    style_figure(fig, height=260)
    fig.update_layout(hovermode="closest", margin=dict(l=4, r=8, t=8, b=4))
    show_chart(fig)
    legend([("Selected story: 80% range", ORANGE, False), ("Other stories", "#A9C5F0", False),
            ("Overall 80% range (adjusted)", "#DCE6F6", False), (f"Today ({naira(today)})", GREY, True)])
    st.caption("Story ranges are not adjusted for past misses; the shaded band is the overall, adjusted range.")

# ----------------------------------------------------------------------------- forecast tracker
section_head("How are the forecasts doing?", "Old forecasts are kept exactly as made")
forecast_tracker("naira", "outlook", fx, "naira", NAVY, "track-naira", history_months=24, prefer_rerun=True)

# ----------------------------------------------------------------------------- what this means
k_last = by_month.loc[KEY_MONTHS[-1]]
widest = end["high80"].idxmax()
calmest = end["high80"].idxmin()
info_box("What this means", e(
    f"The naira is {abs(yoy):.1f}% {'stronger' if yoy < 0 else 'weaker'} than a year ago, but over 20 years it has "
    f"lost {lost_since_06:.0f}% of its value against the dollar, and almost all of that came in {int(is_jump.sum())} "
    f"sudden jump months since {since06.index[0]:%B %Y} rather than a steady slide. Nobody can say when the next jump comes, so the outlook is a "
    f"range: by {KEY_MONTHS[-1]:%B %Y}, a 4 in 5 chance of between {ten(k_last['low80'])} and {ten(k_last['high80'])} "
    f"per dollar. It leans upward because the naira's history is mostly falls; the bottom allows it to strengthen as "
    f"much as it has since the 2023 float. Of the four stories, '{calmest}' gives the lowest top "
    f"({ten(end.loc[calmest, 'high80'])}) and '{widest}' the highest ({ten(end.loc[widest, 'high80'])})."
))

# ----------------------------------------------------------------------------- under the hood
m80 = ", ".join(f"{int(k) // 12} yr +{(np.exp(v) - 1) * 100:.0f}%" for k, v in notes["margins_top80"].items())
falls = ", ".join(f"{k} months {v * 100:.0f}%" for k, v in notes["biggest_float_fall"].items())
under_the_hood(
    meta, ["exchange_rates", "us_cpi_oct_2025"],
    extra_md=(
        "**The outlook** is ported unchanged from the "
        "[naira article](https://www.linkedin.com/pulse/how-much-worse-can-naira-get-i-tried-find-out-freedom-oboh-ibxaf). "
        f"A *jump model* simulates {notes['paths']:,} possible futures, {notes['horizon_months']} months each. Every "
        f"simulated month is either a jump (chance {notes['jump_chance'] * 100:.1f}% a month: {notes['jumps']} of the "
        f"last {notes['months']} months fell more than 5%), drawn from the naira's real past jumps, or a normal month, "
        f"drawn from its real normal months. Random seed {notes['seed']}, so every run gives the same answer.\n\n"
        "**Honesty correction.** Tested on past start dates "
        f"({notes['backtest_starts']}), the model's ranges were too narrow, always on the top side. So the top of the "
        f"80% range is raised by how far past outcomes overshot ({m80}), and the bottom may repeat the biggest "
        f"strengthening seen since the June 2023 float ({falls}).\n\n"
        "**The stories** reuse the same model with one or two switches changed (shown on each story). The policy "
        "reversal catch-up uses the gap between Nigerian and US inflation over the last 12 months "
        f"(a {notes['policy_reversal_catch_up'] * 100:.0f}% devaluation after 2 years), the idea behind *purchasing "
        f"power parity*. {HELP['ppp']}\n\n"
        "**Self-check:** each monthly run re-runs the model on data to September 2026 and must reproduce the "
        "article's published ranges to the nearest ₦10, or the update is stopped.\n\n**Data notes:**"
    ),
)
footer()
