"""Prices: inflation since 2003, the 12-month forecast as a range, and the 2025 rebasing note.
Same design as Home and My savings. Every number comes from data/processed/."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import (terms_explained, BLUE, GREY, HELP, NAVY, ORANGE, brand_header, e, footer, info_box,
                        kpi_card, change_text, legend, load_csv, load_meta, load_panel, naira, page_intro, pct,
                        forecast_tracker, section_head, show_chart, style_figure, under_the_hood)

panel = load_panel()
meta = load_meta()
forecast = load_csv("forecast.csv")
latest = pd.Timestamp(meta["latest_month"])
year_ago = latest - pd.DateOffset(years=1)
by_month = panel.set_index("month")
now, then = by_month.loc[latest], by_month.loc[year_ago]

MEASURES = {  # label: (column, colour, help)
    "Headline": ("inflation", BLUE, HELP["inflation"]),
    "Food": ("food_inflation", ORANGE, HELP["food"]),
    "Core": ("core_inflation", NAVY, HELP["core"]),
}
PERIODS = {"Since 2003": None, "Last 10 years": 10, "Last 5 years": 5, "Last 2 years": 2}
REBASE = pd.Timestamp("2025-01-01")

st.session_state.setdefault("infl_measures", ["Headline", "Food"])
st.session_state.setdefault("infl_period", "Last 10 years")
st.session_state.setdefault("fc_measure", "Headline")

brand_header("Prices", meta)
page_intro("Prices", "How fast are prices rising?",
           "Inflation since 2003, where it may head over the next year, and what changed in 2025.", meta)

# ----------------------------------------------------------------------------- the answer (navy hero)
cost_now = 1000 * (1 + now["inflation"] / 100)
slower = now["inflation"] < then["inflation"]
st.html(
    f'<section class="mm mm-hero" aria-label="Prices this month"><div class="main">'
    f'<p class="soft">Prices in {latest:%B %Y}, compared with a year earlier</p>'
    f'<div class="figs">'
    f'<div class="fig"><span class="lbl">All prices (headline)</span><span class="num">{pct(now["inflation"])}</span></div>'
    f'<div class="fig"><span class="lbl">Food prices</span><span class="num warm">{pct(now["food_inflation"])}</span></div>'
    f'</div>'
    f'<span class="mm-pill {"good" if slower else "bad"}">'
    f'{"Rising more slowly" if slower else "Rising faster"} than a year ago ({pct(then["inflation"])})</span></div>'
    f'<div class="side"><p>Shopping that cost <b>₦1,000</b> in {year_ago:%B %Y} costs about '
    f'<b>{naira(cost_now)}</b> now.</p>'
    f'<p>Core prices (leaving out farm produce and energy) are rising <b>{pct(now["core_inflation"])}</b> a year.</p>'
    f'</div></section>'
)

# ----------------------------------------------------------------------------- key numbers
cards = []
for label, (col, _, help_text) in MEASURES.items():
    d = now[col] - then[col]
    words = "rising more slowly" if d < 0 else "rising faster"
    cards.append(kpi_card(f"{label} inflation", pct(now[col]), change_text(d, "pts", "down", words), help_text))
section_head("The key numbers", f"{latest:%B %Y}, compared with {year_ago:%B %Y}")
st.html(f'<div class="mm mm-cards">{"".join(cards)}</div>')
terms_explained([("Headline inflation", HELP["inflation"]), ("Food inflation", HELP["food"]),
                 ("Core inflation", HELP["core"]), ("A range", HELP["range"])])

# ----------------------------------------------------------------------------- history chart
with st.container(key="panel-inputs"):
    chosen = st.pills("Show", list(MEASURES), selection_mode="multi", key="infl_measures",
                      help=" ".join(f"{k}: {v[2]}" for k, v in MEASURES.items()))
    period = st.pills("Period", list(PERIODS), key="infl_period")

chosen = [m for m in MEASURES if m in (chosen or [])] or ["Headline"]
years = PERIODS.get(period or "Last 10 years")
start = panel["month"].min() if years is None else latest - pd.DateOffset(years=years)
view = panel[panel["month"] >= start]

with st.container(key="panel-history"):
    st.html(f'<div class="mm"><h2>Inflation, {view["month"].min():%b %Y} to {latest:%b %Y}</h2>'
            f'<p style="font-size:14px;color:#4A5568;margin-top:4px">How much prices were higher than 12 months '
            f'earlier, each month.</p></div>')
    fig = go.Figure()
    for m in chosen:
        col, colour, _ = MEASURES[m]
        fig.add_trace(go.Scatter(x=view["month"], y=view[col], name=m, mode="lines",
                                 line=dict(color=colour, width=2.5), hovertemplate="%{y:.2f}%"))
    if view["month"].min() < REBASE:
        fig.add_vrect(x0=REBASE, x1=latest, fillcolor=GREY, opacity=0.08, line_width=0)
        fig.add_vline(x=REBASE, line_dash="dash", line_color=GREY, line_width=1.2)
        fig.add_annotation(x=REBASE, y=1, yref="paper", text="CPI rebased", showarrow=False,
                           xanchor="left", yanchor="top", xshift=4, font=dict(size=12, color="#4A5568"))
    fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    style_figure(fig, height=340)
    show_chart(fig)
    legend([(m, MEASURES[m][1], False) for m in chosen])
    st.caption("Shaded: after the January 2025 rebasing, figures use the new price basket (see the note below).")

# ----------------------------------------------------------------------------- the 2025 note
st.html(
    f'<section class="mm mm-note"><h3>Two things to know about the 2025 figures</h3>'
    f'<p><b>The January 2025 rebasing.</b> {e(meta["trap_notes"]["rebasing_2025"])}</p>'
    f'<p><b>The January 2026 revision.</b> {e(meta["trap_notes"]["revised_2025_inflation"])}</p></section>'
)

# ----------------------------------------------------------------------------- forecast
section_head("Where inflation may head next", "A range, not a prediction")
fc_label = st.pills("Forecast for", ["Headline", "Food"], key="fc_measure", label_visibility="collapsed") or "Headline"
fc = forecast[forecast["measure"] == fc_label.lower()].reset_index(drop=True)
col, colour, _ = MEASURES[fc_label]
mid, end = fc.iloc[5], fc.iloc[-1]


def range_card(row, title):
    return (f'<article class="mm-card mm-range"><span class="when">{title}</span>'
            f'<p class="num">{row["low80"]:.1f}% to {row["high80"]:.1f}%</p>'
            f'<p class="sub">4 in 5 chance the {fc_label.lower()} rate lands in this range '
            f'(80% range).</p></article>')


st.html(
    '<div class="mm mm-cards">'
    + range_card(mid, f"{mid['month']:%B %Y}") + range_card(end, f"{end['month']:%B %Y}")
    + f'<article class="mm-card mm-range"><span class="when">MIDDLE OF THE RANGE</span>'
      f'<p class="num">About {end["forecast"]:.1f}%</p>'
      f'<p class="sub">Flat, because no model could reliably tell which way inflation will move a year ahead.</p></article>'
    + f'<article class="mm-card mm-range"><span class="when">IF THE NAIRA\'S TREND CONTINUES</span>'
      f'<p class="num">{end["naira_scenario"]:.1f}% by {end["month"]:%b %Y}</p>'
      f'<p class="sub">A "what if", not the forecast: the naira staying {abs(meta["models"]["inflation"]["naira_yoy_held"]):.0f}% '
      f'{"stronger" if meta["models"]["inflation"]["naira_yoy_held"] < 0 else "weaker"} than a year earlier.</p></article>'
    + '</div>'
)

with st.container(key="panel-forecast"):
    st.html(f'<div class="mm"><h2>{fc_label} inflation: the next 12 months</h2>'
            f'<p style="font-size:14px;color:#4A5568;margin-top:4px">The shaded band is the 80% range. '
            f'It widens because the further ahead we look, the less sure anyone can be.</p></div>')
    hist = panel[panel["month"] >= latest - pd.DateOffset(years=2)]
    x_join = [latest] + list(fc["month"])
    last_val = now[col]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_join + x_join[::-1], y=[last_val] + list(fc["high80"]) + list(fc["low80"])[::-1] + [last_val],
                             fill="toself", fillcolor="rgba(42,111,219,0.15)" if fc_label == "Headline" else "rgba(217,130,43,0.15)",
                             line=dict(width=0), hoverinfo="skip", name="80% range"))
    fig.add_trace(go.Scatter(x=hist["month"], y=hist[col], name="Actual", mode="lines",
                             line=dict(color=colour, width=2.5), hovertemplate="%{y:.2f}%"))
    fig.add_trace(go.Scatter(x=x_join, y=[last_val] + list(fc["forecast"]), name="Middle of the range", mode="lines",
                             line=dict(color=colour, width=2.5, dash="dash"), hovertemplate="%{y:.1f}%"))
    fig.add_trace(go.Scatter(x=x_join, y=[last_val] + list(fc["naira_scenario"]), name="If the naira's trend continues",
                             mode="lines", line=dict(color=NAVY, width=2, dash="dot"), hovertemplate="%{y:.1f}%"))
    fig.add_trace(go.Scatter(x=fc["month"], y=fc["low80"], showlegend=False, mode="lines", line=dict(width=0),
                             hovertemplate="low %{y:.1f}%", name="80% low"))
    fig.add_trace(go.Scatter(x=fc["month"], y=fc["high80"], showlegend=False, mode="lines", line=dict(width=0),
                             hovertemplate="high %{y:.1f}%", name="80% high"))
    fig.add_vline(x=latest, line_color=GREY, line_width=1)
    fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    style_figure(fig, height=340)
    show_chart(fig)
    legend([("Actual", colour, False), ("Middle of the range", colour, False),
            ("80% range", "#A9C5F0" if fc_label == "Headline" else "#F3C9A0", False),
            ("If the naira's trend continues", NAVY, True)])
    st.caption(f"Forecast made with data up to {latest:%B %Y}. {HELP['range']}")

# ----------------------------------------------------------------------------- forecast tracker
section_head("How are the forecasts doing?", "Old forecasts are kept exactly as made")
st.session_state.setdefault("track_measure", "Headline")
track_label = st.pills("Check the forecast for", ["Headline", "Food"], key="track_measure",
                       label_visibility="collapsed") or "Headline"
track_col, track_colour, _ = MEASURES[track_label]
forecast_tracker("inflation", track_label.lower(), by_month[track_col], "points", track_colour, "track-infl")

# ----------------------------------------------------------------------------- what this means
h_now, h_then, f_now = now["inflation"], then["inflation"], now["food_inflation"]
head = forecast[forecast["measure"] == "headline"].iloc[-1]
direction = "fallen" if h_now < h_then else "risen"
speed = "rising more slowly" if h_now < h_then else "rising faster"
food_line = (f"Food prices are rising faster than prices overall ({pct(f_now)} against {pct(h_now)}), which hits "
             f"families who spend most of their money on food hardest." if f_now > h_now else
             f"Food prices are rising more slowly than prices overall ({pct(f_now)} against {pct(h_now)}).")
info_box("What this means", e(
    f"Headline inflation has {direction} from {pct(h_then)} to {pct(h_now)} over the past year, so prices are "
    f"{speed}, but they are still rising: ₦1,000 of shopping in {year_ago:%B %Y} costs about {naira(cost_now)} now. "
    f"{food_line} Looking ahead, the middle of the forecast stays at about {head['forecast']:.1f}%, meaning there is no "
    f"reliable signal of which way it will move. The honest answer is the range: by {head['month']:%B %Y}, a 4 in 5 "
    f"chance of between {head['low80']:.1f}% and {head['high80']:.1f}%."
))

# ----------------------------------------------------------------------------- under the hood
m = meta["models"]["inflation"]
under_the_hood(
    meta, ["revised_2025_inflation", "june_2025_repeat", "rebasing_2025"],
    extra_md=(
        "**The forecast** is ported unchanged from the "
        "[inflation forecast project](https://www.linkedin.com/pulse/i-analysed-23-years-nigerian-inflation-data-heres-what-freedom-oboh-vumkf): "
        "an ARIMA(1,1,0) model with a marker for the January 2025 rebasing, fitted on every month since January 2003 "
        "and re-fitted each month when new data arrives. It forecasts the *change* in inflation from its own recent "
        f"changes (this month's fit: momentum {m['headline']['ar.L1']:.2f} for headline, {m['food']['ar.L1']:.2f} for food; "
        f"rebasing step {m['headline']['Rebased']:.2f} and {m['food']['Rebased']:.2f} points). After a month or two the "
        "momentum fades, which is why the middle line goes flat.\n\n"
        "**The yardstick** is the naive forecast: next year = this month. Across 14 years of backtests, no model "
        "reliably beat it 12 months ahead; ARIMA matched it or did slightly better, and was the most consistent. "
        "That is why the range matters more than the line, and the range may even be too narrow in turbulent years.\n\n"
        "**The naira line** is a regression on inflation's last three months and the naira's change from a year "
        "earlier, with the naira's change held at its latest value. It shows what a continuing trend would mean; "
        "it was often wrong when the naira's trend changed, so it is not the main forecast.\n\n"
        "**Self-check:** each monthly run re-runs the model on data to September 2026 and must reproduce the "
        "published article's numbers, or the update is stopped.\n\n**Data notes:**"
    ),
)
footer()
