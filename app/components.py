"""Shared pieces for every page: data loading, formatting, KPI cards, chart style, footer.

The app only ever reads data/processed/. It never calls the CBN.
"""

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
sys.path.insert(0, str(ROOT / "src"))

APP_NAME = "(+234) Money Matters"
TAGLINE = "Understand what the economy is doing to your money."
SUPPORTING_LINE = "Nigeria's economy, through the numbers."
DESCRIPTION = (
    "Money Matters is a data-driven platform that helps Nigerians understand how the economy affects "
    "their everyday finances. It brings together key economic indicators such as inflation, exchange "
    "rates, interest rates, savings and borrowing into one interactive dashboard. Users can explore "
    "historical trends, understand how the value of their money has changed over time, compare "
    "financial scenarios, and see what the numbers mean for their personal and business decisions. "
    "The platform brings together data from multiple research projects into one place, with regular "
    "monthly updates."
)
LOAN_CALCULATOR_URL = "https://naija-loan-cost.streamlit.app/"
GITHUB_URL = "https://github.com/Freedom15dev"
ARTICLES = {
    "Inflation": "https://www.linkedin.com/pulse/i-analysed-23-years-nigerian-inflation-data-heres-what-freedom-oboh-vumkf",
    "Savings": "https://www.linkedin.com/pulse/i-followed-100000-20-years-heres-what-happened-nigerian-freedom-oboh-o090f",
    "The naira": "https://www.linkedin.com/pulse/how-much-worse-can-naira-get-i-tried-find-out-freedom-oboh-ibxaf",
    "Borrowing": "https://www.linkedin.com/pulse/who-gets-borrow-nigeria-i-followed-two-borrowers-find-freedom-oboh-q6mof",
}

NAVY, BLUE, ORANGE, GREY, GRID = "#0F1E33", "#2A6FDB", "#D9822B", "#8A94A6", "#E3E6EB"
OPTION_COLORS = {
    "Under the mattress": GREY,
    "Savings account": BLUE,
    "12-month fixed deposit": NAVY,
    "Treasury bills": "#2E9E6B",
    "Dollars": ORANGE,
}

# Plain-words help for every term (shown on hover of the ⓘ next to a label).
HELP = {
    "inflation": "How much prices are higher than 12 months ago (year-on-year headline inflation, NBS via the CBN).",
    "usd": "The official CBN rate: how many naira one US dollar costs, averaged over the month. Not the street (parallel) rate.",
    "mpr": "The Monetary Policy Rate: the CBN's main interest rate. When it goes up, borrowing usually gets dearer and deposits pay a bit more.",
    "prime": "The prime lending rate: the average rate banks charge their best, lowest-risk customers (usually big companies).",
    "max": "The maximum lending rate: the average rate banks charge their riskiest borrowers. Small businesses and individuals often pay this or more.",
    "savings": "The average interest a bank savings account pays in a year, before tax (CBN average across banks).",
    "real": "The real rate is the interest rate after inflation. Below zero means money in the account buys less each year, even though the balance grows.",
    "todays_prices": "'Today's prices' means the prices of the latest month in the data. We use a price index built from the inflation figures.",
}


# --------------------------------------------------------------------------- data
@st.cache_data(show_spinner=False)
def load_panel():
    return pd.read_csv(PROCESSED / "panel.csv", parse_dates=["month"])


@st.cache_data(show_spinner=False)
def load_meta():
    return json.loads((PROCESSED / "meta.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- formatting
def naira(x, decimals=0):
    if pd.isna(x):
        return "–"
    sign = "−" if x < 0 else ""
    return f"{sign}₦{abs(x):,.{decimals}f}"


def pct(x, decimals=2, signed=False):
    if pd.isna(x):
        return "–"
    text = f"{abs(x):.{decimals}f}%"
    if signed:
        return ("+" if x > 0 else "−" if x < 0 else "") + text
    return ("−" if x < 0 else "") + text


def points(x, decimals=2):
    """A change in a rate, in percentage points, for st.metric deltas.

    Uses a plain hyphen for minus: st.metric reads the sign from it to pick the arrow and colour.
    """
    if pd.isna(x):
        return None
    return f"{x:+.{decimals}f} pts"


def pct_delta(x, decimals=1):
    """A % change for st.metric deltas (plain hyphen for minus, see points)."""
    return None if pd.isna(x) else f"{x:+.{decimals}f}%"


# --------------------------------------------------------------------------- page pieces
def base_css():
    st.markdown(
        """
        <style>
        .block-container {padding-top: 2rem; padding-bottom: 2rem;}
        [data-testid="stMetricValue"] {font-size: 1.6rem;}
        [data-testid="stMetricLabel"] p {font-size: 0.9rem;}
        .mm-sentence {font-size: 1.15rem; line-height: 1.6; color: #0F1E33;}
        .mm-big {font-size: 1.5rem; font-weight: 700; color: #0F1E33; margin: 0;}
        .mm-small {color: #4A5568; font-size: 0.9rem; margin: 0;}
        @media (max-width: 640px) {
            .block-container {padding-left: 1rem; padding-right: 1rem;}
            h1 {font-size: 1.8rem !important;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def data_up_to(meta):
    st.caption(f"📅 Data up to **{meta['latest_month_label']}** · Central Bank of Nigeria")


def footer():
    st.divider()
    st.caption(
        "Educational, not financial advice. Data: Central Bank of Nigeria (and US BLS via FRED for the "
        "naira page). Built by Freedom Oboh with Python and Streamlit."
    )
    article_links = " · ".join(f"[{name}]({url})" for name, url in ARTICLES.items())
    st.caption(f"[GitHub]({GITHUB_URL}) · Articles on LinkedIn: {article_links}")


def under_the_hood(meta, keys, extra_md=None):
    with st.expander("Under the hood: how these numbers are made"):
        if extra_md:
            st.markdown(extra_md)
        for key in keys:
            st.markdown(f"- {meta['trap_notes'][key]}")
        st.caption(f"Data pulled from the CBN on {min(meta['pulled_at_utc'].values())[:10]}.")


# --------------------------------------------------------------------------- charts
def style_figure(fig, y_title="", height=420):
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=8, r=8, t=40, b=8),
        font=dict(color=NAVY, size=13),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, title=None),
        hovermode="x unified",
        yaxis_title=y_title,
        xaxis_title=None,
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


def show_chart(fig):
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "responsive": True})


def empty_figure():
    return go.Figure()
