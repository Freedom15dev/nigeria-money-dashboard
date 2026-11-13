"""Shared pieces for every page: data loading, formatting, the house CSS, the brand header,
cards, badges, chart style and the footer. Layout follows the mockups in design/.

The app only ever reads data/processed/. It never calls the CBN.
"""

import html
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
sys.path.insert(0, str(ROOT / "src"))

# --------------------------------------------------------------------------- wording (CLAUDE.md §0)
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
GITHUB_URL = "https://github.com/Freedom15dev/nigeria-money-dashboard"
LINKEDIN_URL = "https://www.linkedin.com/in/freedomoboh"
PORTFOLIO_URL = "https://oboh.com.ng/"
ARTICLES = {
    "Inflation": "https://www.linkedin.com/pulse/i-analysed-23-years-nigerian-inflation-data-heres-what-freedom-oboh-vumkf",
    "Savings": "https://www.linkedin.com/pulse/i-followed-100000-20-years-heres-what-happened-nigerian-freedom-oboh-o090f",
    "The naira": "https://www.linkedin.com/pulse/how-much-worse-can-naira-get-i-tried-find-out-freedom-oboh-ibxaf",
    "Borrowing": "https://www.linkedin.com/pulse/who-gets-borrow-nigeria-i-followed-two-borrowers-find-freedom-oboh-q6mof",
}

# Pages in the header (paths as given to st.Page in Home.py). None = not built yet, shown as "soon".
NAV_PAGES = {"Home": "pages/home.py", "My savings": "pages/savings.py",
             "Prices": None, "The naira": None, "Borrowing": None}

# --------------------------------------------------------------------------- colours (design/)
NAVY, BLUE, ORANGE, ORANGE_LIGHT = "#0F1E33", "#2A6FDB", "#D9822B", "#F0A65E"
PAGE, GREY, GRID, MUTED = "#F5F6F8", "#8A94A6", "#EEF0F3", "#4A5568"
GOOD, BAD = "#1D6B44", "#9B1C1C"
OPTION_COLORS = {
    "Treasury bills": BLUE,
    "12-month fixed deposit": "#7FA9EC",
    "Savings account": NAVY,
    "Under the mattress": GREY,
    "Dollars": ORANGE,
}

# Plain-words help for every term.
HELP = {
    "inflation": "How much prices are higher than 12 months ago (year-on-year headline inflation, NBS via the CBN).",
    "usd": "The official CBN rate: how many naira one US dollar costs, averaged over the month. Not the street (parallel) rate.",
    "mpr": "The Monetary Policy Rate: the CBN's main interest rate. When it goes up, borrowing usually gets dearer and deposits pay a bit more.",
    "prime": "The prime lending rate: the average rate banks charge their best, lowest-risk customers (usually big companies).",
    "max": "The maximum lending rate: the average rate banks charge their riskiest borrowers. Small businesses and individuals often pay this or more.",
    "savings": "The average interest a bank savings account pays in a year, before tax (CBN average across banks).",
    "real": "The real rate is the interest rate after inflation. Below zero means money in the account buys less each year, even though the balance grows.",
}

e = html.escape  # short name for escaping text put into HTML


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
    return f"{'−' if x < 0 else ''}₦{abs(x):,.{decimals}f}"


def pct(x, decimals=2):
    if pd.isna(x):
        return "–"
    return f"{'−' if x < 0 else ''}{abs(x):.{decimals}f}%"


def short_naira(x):
    """₦50k, ₦1.5m: for axis ticks and quick picks."""
    if abs(x) >= 1_000_000:
        return f"₦{x / 1_000_000:,.3g}m"
    if abs(x) >= 1_000:
        return f"₦{x / 1_000:,.3g}k"
    return f"₦{x:,.0f}"


# --------------------------------------------------------------------------- CSS
CSS = """
<style>
/* ---------- page ---------- */
.stApp {background: #F5F6F8;}
[data-testid="stAppViewContainer"], .stMain {overflow-x: hidden;}
[data-testid="stMainBlockContainer"], .block-container {
  max-width: 1120px; padding: 0 24px 0 24px;
}
/* Streamlit's own top bar, toolbar, deploy button and heading link icons: hidden for visitors */
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stAppDeployButton"],
[data-testid="stDecoration"], [data-testid="stHeaderActionElements"] {display: none !important;}
h1 a, h2 a, h3 a {display: none !important;}

.mm, .mm p, .mm span, .mm a, .mm li {font-family: Inter, Arial, sans-serif;}
.mm h1, .mm h2, .mm h3, .mm .num {font-family: 'Space Grotesk', Arial, sans-serif; letter-spacing: 0;}
.mm p {margin: 0;}
.mm a {color: #2A6FDB;} .mm a:hover {color: #1B4FA8;}

/* ---------- brand header (full width; built from st.page_link so it works inside Streamlit Cloud's frame) */
.st-key-mm-topbar {background: #FFFFFF; border-bottom: 1px solid #E3E6EB; box-sizing: border-box;
  width: 100vw !important; max-width: 100vw !important; margin-left: calc(50% - 50vw) !important;
  padding: 14px max(24px, calc((100vw - 1120px) / 2 + 24px)); flex-wrap: nowrap !important; gap: 32px !important;}
.st-key-mm-topbar [data-testid="stPageLink-NavLink"] {text-decoration: none !important; margin: 0;}
.st-key-nav-brand [data-testid="stPageLink-NavLink"] {gap: 10px; padding: 0; background: none !important;}
.st-key-nav-brand [data-testid="stPageLink-NavLink"]::before {content: "+234"; display: inline-flex; align-items: center;
  height: 34px; padding: 0 10px; border-radius: 8px; background: #0F1E33; color: #FFFFFF;
  font-family: 'Space Grotesk', Arial, sans-serif; font-weight: 700; font-size: 14px;}
.st-key-nav-brand p {font-family: 'Space Grotesk', Arial, sans-serif !important; font-weight: 700 !important;
  font-size: 20px !important; color: #0F1E33 !important; white-space: nowrap;}
.st-key-mm-tabs {flex: 1 1 auto !important; gap: 4px !important;}
[class*="st-key-tab-"] [data-testid="stPageLink-NavLink"] {padding: 8px 12px; border-radius: 8px; background: transparent;}
[class*="st-key-tab-"] [data-testid="stPageLink-NavLink"]:hover {background: #F5F6F8;}
[class*="st-key-tab-"] p {font-size: 15px !important; font-weight: 500 !important; color: #4A5568 !important; white-space: nowrap;}
[class*="st-key-tab-"][class*="-active"] [data-testid="stPageLink-NavLink"] {background: #EAF1FC !important;}
[class*="st-key-tab-"][class*="-active"] p {font-weight: 600 !important; color: #0F1E33 !important;}
.mm-soon {display: inline-block; padding: 8px 12px; font-size: 15px; color: #9AA3B2; cursor: default; white-space: nowrap;}
.mm-soon small {font-size: 11px; margin-left: 4px;}
.mm-upto {font-size: 14px; color: #4A5568; white-space: nowrap;}
.mm-upto b {color: #0F1E33;}
.st-key-mm-burger {display: none !important;}
.st-key-mm-burger button {width: 44px; height: 44px; min-height: 44px; padding: 0; border: 1px solid #E3E6EB;
  border-radius: 10px; background: #FFFFFF; justify-content: center;}
.st-key-mm-burger button p {font-size: 22px; line-height: 1;}
.st-key-mm-burger button [data-testid="stIconMaterial"] {display: none;}
[data-testid="stPopoverBody"] [data-testid="stPageLink-NavLink"] p {font-size: 16px; font-weight: 500;}

/* ---------- Home hero and Explore card that hold a st.page_link ---------- */
.st-key-hero-home {background: #0F1E33; border-radius: 20px; padding: 32px 36px; gap: 24px 40px !important;}
.st-key-hero-home .mm-hero.bare {background: none; padding: 0; border-radius: 0;}
.st-key-hero-home > [data-testid="stElementContainer"]:has(.mm-hero) {flex: 1 1 420px !important;}
.st-key-cta [data-testid="stPageLink-NavLink"] {height: 52px; padding: 0 22px; border-radius: 12px;
  background: #F0A65E !important; text-decoration: none !important;}
.st-key-cta [data-testid="stPageLink-NavLink"]:hover {background: #F4B97A !important;}
.st-key-cta p {color: #0F1E33 !important; font-weight: 700 !important; font-size: 16px !important; white-space: nowrap;}
.st-key-explore {gap: 16px !important;}
.st-key-explore > * {flex: 1 1 240px !important; min-width: 0 !important;}
.st-key-explore .mm-card {height: 100%;}
.st-key-explore-savings {background: #FFFFFF; border: 1px solid #E3E6EB; border-top: 4px solid #2A6FDB;
  border-radius: 14px; padding: 22px; gap: 8px !important;}
.st-key-explore-savings [data-testid="stPageLink-NavLink"] {padding: 0; background: none !important;}
.st-key-explore-savings [data-testid="stPageLink-NavLink"] p {color: #2A6FDB !important; font-weight: 600 !important; font-size: 14px;}

/* ---------- page intro ---------- */
.mm-intro {display: flex; flex-direction: column; gap: 12px; max-width: 800px; padding-top: 48px;}
.mm-eyebrow {font-size: 13px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: #B4561A;}
.mm-eyebrow .phone-only {display: none;}
.mm-intro h1 {margin: 0; padding: 0; font-size: 48px; line-height: 1.08; font-weight: 700; color: #0F1E33;}
.mm-lead {font-size: 18px; line-height: 1.55; color: #4A5568;}

/* ---------- section headings ---------- */
.mm-sechead {display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 8px; margin-top: 8px;}
.mm-sechead h2 {margin: 0; padding: 0; font-size: 28px; font-weight: 700; color: #0F1E33;}
.mm-sechead p {font-size: 14px; color: #4A5568;}

/* ---------- navy hero ---------- */
.mm-hero {background: #0F1E33; color: #FFFFFF; border-radius: 20px; padding: 36px; display: flex;
  flex-wrap: wrap; gap: 24px 40px; align-items: center;}
.mm-hero .main {flex: 3 1 420px; display: flex; flex-direction: column; gap: 14px;}
.mm-hero .side {flex: 2 1 260px; display: flex; flex-direction: column; gap: 8px;
  border-top: 1px solid #2B3B55; padding-top: 20px;}
.mm-hero .soft {color: #B8C6DA; font-size: 16px;}
.mm-hero .soft b {color: #FFFFFF;}
.mm-hero .side p {font-size: 15px; line-height: 1.55; color: #D7DFEA;}
.mm-hero .side b {color: #FFFFFF;}
.mm-hero .figs {display: flex; flex-wrap: wrap; align-items: baseline; gap: 12px 20px;}
.mm-hero .fig {display: flex; flex-direction: column; gap: 2px;}
.mm-hero .fig .lbl {font-size: 13px; color: #B8C6DA;}
.mm-hero .fig .num {font-size: 44px; font-weight: 700; color: #FFFFFF; line-height: 1.1;}
.mm-hero .fig .num.warm {color: #F0A65E;}
.mm-hero .arrow {font-size: 32px; color: #F0A65E;}
.mm-hero .kicker {font-size: 13px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: #F0A65E;}
.mm-hero .statement {font-family: 'Space Grotesk', Arial, sans-serif; font-size: 28px; line-height: 1.3; font-weight: 500; color: #FFFFFF;}
.mm-hero .statement .warm {color: #F0A65E; font-weight: 700;}
.mm-cta {flex: 0 0 auto; display: inline-flex; align-items: center; gap: 10px; height: 52px; padding: 0 22px;
  border-radius: 12px; background: #F0A65E; color: #0F1E33 !important; font-weight: 700; font-size: 16px;
  text-decoration: none !important;}
.mm-cta:hover {background: #F4B97A;}

/* ---------- badges ---------- */
.mm-pill {display: inline-flex; align-self: flex-start; align-items: center; gap: 6px; padding: 6px 12px;
  border-radius: 999px; font-size: 15px; font-weight: 700;}
.mm-pill.sm {padding: 3px 9px; font-size: 13px;}
.mm-pill.xs {padding: 2px 8px; font-size: 12px;}
.mm-pill.bad {background: #FDECEA; color: #9B1C1C;}
.mm-pill.good {background: #E3F4EA; color: #1D6B44;}
.mm-pill.flat {background: #EEF0F3; color: #0F1E33;}

/* ---------- cards ---------- */
.mm-cards {display: flex; flex-wrap: wrap; gap: 16px;}
.mm-card {flex: 1 1 190px; background: #FFFFFF; border: 1px solid #E3E6EB; border-radius: 14px; padding: 20px;
  display: flex; flex-direction: column; gap: 10px; box-sizing: border-box;}
.mm-card.lead {border: 2px solid #0F1E33; padding: 19px;}
.mm-card .top {display: flex; justify-content: space-between; align-items: center; gap: 8px;}
.mm-card .rank {font-size: 13px; font-weight: 700; color: #2A6FDB;}
.mm-card h3 {margin: 0; padding: 0; font-family: Inter, Arial, sans-serif; font-size: 17px; font-weight: 700; color: #0F1E33;}
.mm-card .num {font-size: 26px; font-weight: 700; color: #0F1E33;}
.mm-card .sub {font-size: 13px; color: #4A5568; line-height: 1.5;}
.mm-kpi {flex: 1 1 240px; padding: 22px; gap: 8px;}
.mm-kpi h3 {font-size: 14px; font-weight: 600; color: #4A5568;}
.mm-kpi .num {font-size: 34px;}
.mm-kpi .chg {font-size: 14px; color: #4A5568;}
.mm-kpi .chg b {font-weight: 700;}
.mm-tip {display: inline-block; margin-left: 4px; color: #8A94A6; cursor: help; font-weight: 400;}
.mm-explore {flex: 1 1 240px; border-top: 4px solid #2A6FDB; padding: 22px; gap: 8px;
  text-decoration: none !important; color: #0F1E33 !important;}
.mm-explore.warm {border-top-color: #D9822B;}
.mm-explore .t {font-size: 18px; font-weight: 700;}
.mm-explore .d {font-size: 14px; line-height: 1.5; color: #4A5568;}
.mm-explore .soon {font-size: 12px; font-weight: 600; color: #8A94A6; text-transform: uppercase; letter-spacing: 1px;}
a.mm-explore:hover {border-color: #CBD2DC; box-shadow: 0 2px 10px rgba(15,30,51,0.06);}

/* ---------- ranked list (phones) ---------- */
.mm-list {display: none; background: #FFFFFF; border: 1px solid #E3E6EB; border-radius: 14px; flex-direction: column;}
.mm-list .row {display: flex; align-items: center; gap: 12px; padding: 14px 16px; border-bottom: 1px solid #EEF0F3;}
.mm-list .row:last-child {border-bottom: none;}
.mm-list .row.lead {background: #F5F8FD;}
.mm-list .rank {width: 22px; font-size: 13px; font-weight: 700; color: #2A6FDB;}
.mm-list .name {flex: 1 1 auto; display: flex; flex-direction: column; gap: 2px;}
.mm-list .name b {font-size: 15px; font-weight: 600;}
.mm-list .name span {font-size: 12px; color: #4A5568;}
.mm-list .val {display: flex; flex-direction: column; align-items: flex-end; gap: 4px;}
.mm-list .val b {font-size: 16px; font-weight: 700;}

/* ---------- "What this means" ---------- */
.mm-means {background: #FDF3E8; border-radius: 16px; padding: 24px 28px; display: flex; flex-direction: column; gap: 8px;}
.mm-means h2 {margin: 0; padding: 0; font-size: 20px; font-weight: 700; color: #0F1E33;}
.mm-means p {font-size: 16px; line-height: 1.6; color: #2D3A4F;}

/* ---------- white panels made from st.container(key=...) ---------- */
.st-key-panel-inputs, .st-key-panel-chart {background: #FFFFFF; border: 1px solid #E3E6EB !important;
  border-radius: 16px; padding: 28px;}
.st-key-panel-chart h2 {font-family: 'Space Grotesk', Arial, sans-serif; font-size: 22px; font-weight: 700; margin: 0; padding: 0;}
.mm-legend {display: flex; flex-wrap: wrap; gap: 10px 22px; font-size: 14px; margin: 0; padding: 0; list-style: none;}
.mm-legend li {display: flex; align-items: center; gap: 8px; margin: 0;}
.mm-legend .sw {width: 18px; height: 4px; border-radius: 2px;}
.mm-legend .sw.dot {height: 0; border-top: 4px dotted #8A94A6; background: none !important;}

/* ---------- inputs ---------- */
[data-testid="stWidgetLabel"] p {font-size: 14px !important; font-weight: 600 !important; color: #0F1E33;}
.st-key-panel-inputs [data-testid="stTextInputRootElement"],
.st-key-panel-inputs .react-aria-ComboBox > [role="group"] {
  height: 52px; border: 1.5px solid #CBD2DC !important; border-radius: 10px !important; background: #FFFFFF;
  box-sizing: border-box; align-items: center;}
.st-key-panel-inputs .react-aria-ComboBox input {font-size: 16px !important; color: #0F1E33;}
/* the ₦ prefix inside the amount box */
.st-key-amount [data-testid="stTextInputRootElement"] {display: flex; align-items: center;}
.st-key-amount [data-testid="stTextInputRootElement"]::before {content: "₦"; font-size: 20px; font-weight: 600;
  color: #4A5568; padding-left: 16px; flex: 0 0 auto;}
.st-key-amount input {font-size: 20px !important; font-weight: 600 !important; color: #0F1E33; padding-left: 8px !important;}
/* month + year stay side by side, even on phones */
.st-key-dates [data-testid="stHorizontalBlock"] {flex-wrap: nowrap !important; gap: 10px;}
.st-key-dates [data-testid="stColumn"] {min-width: 0 !important;}
.mm-hint {font-weight: 400; color: #4A5568;}

/* pills: unselected white with grey border; selected navy with a tick (the "kept" choices) */
[data-testid="stButtonGroup"] button[data-variant="pills"] {border-radius: 999px !important; height: 40px;
  padding: 0 16px; background: #FFFFFF !important; border: 1px solid #CBD2DC !important;}
[data-testid="stButtonGroup"] button[data-variant="pills"] p {font-size: 14px; color: #0F1E33 !important;}
.st-key-kept button[data-selected="true"] {background: #0F1E33 !important; border-color: #0F1E33 !important;}
.st-key-kept button[data-selected="true"] p {color: #FFFFFF !important; font-weight: 600;}
.st-key-kept button[data-selected="true"] p::before {content: "✓ ";}
.st-key-quick button[data-variant="pills"] {height: 36px; padding: 0 14px;}
.st-key-quick button[aria-checked="true"] {background: #EAF1FC !important; border-color: #2A6FDB !important;}
.st-key-quick button[aria-checked="true"] p {color: #1B4FA8 !important; font-weight: 600;}

/* expanders as white cards */
[data-testid="stExpander"] details {background: #FFFFFF; border: 1px solid #E3E6EB; border-radius: 12px;}
[data-testid="stExpander"] summary p {font-size: 15px; font-weight: 600;}

/* ---------- footer (full width) ---------- */
.mm-footer {border-top: 1px solid #E3E6EB; background: #FFFFFF; margin: 32px calc(50% - 50vw) 0;}
.mm-footer-in {max-width: 1120px; margin: 0 auto; padding: 24px; display: flex; flex-wrap: wrap;
  justify-content: space-between; gap: 12px; font-size: 13px; color: #4A5568; box-sizing: border-box;}
.mm-footer-in p {font-size: 13px; color: #4A5568; line-height: 1.6;}

/* ---------- phones ---------- */
@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"], .block-container {padding: 0 16px;}
  .st-key-mm-topbar {padding: 12px 16px; justify-content: space-between; gap: 12px !important;}
  .st-key-nav-brand [data-testid="stPageLink-NavLink"]::before {height: 30px; padding: 0 8px; font-size: 13px;}
  .st-key-nav-brand p {font-size: 18px !important;}
  .st-key-mm-tabs, .st-key-mm-topbar [data-testid="stElementContainer"]:has(.mm-upto) {display: none !important;}
  .st-key-mm-burger {display: flex !important;}
  .st-key-hero-home {padding: 22px; border-radius: 16px; gap: 16px !important;}
  .mm-intro {padding-top: 24px; gap: 8px;}
  .mm-eyebrow {font-size: 12px; letter-spacing: 1.4px;}
  .mm-eyebrow .phone-only {display: inline;}
  .mm-intro h1 {font-size: 32px; line-height: 1.1;}
  .mm-lead {font-size: 16px;}
  .mm-sechead h2 {font-size: 22px;}
  .mm-hero {padding: 22px; border-radius: 16px; gap: 14px;}
  .mm-hero .main {flex-basis: 100%; gap: 14px;}
  .mm-hero .side {flex-basis: 100%; padding-top: 12px;}
  .mm-hero .soft {font-size: 14px;}
  .mm-hero .figs {flex-direction: column; align-items: flex-start; gap: 14px;}
  .mm-hero .arrow {display: none;}
  .mm-hero .fig .lbl {font-size: 12px;}
  .mm-hero .fig .num {font-size: 34px;}
  .mm-hero .statement {font-size: 21px;}
  .mm-hero .side p {font-size: 14px;}
  .mm-pill {font-size: 14px; padding: 5px 11px;}
  .mm-cards.rank-cards {display: none;}
  .mm-list {display: flex;}
  .mm-kpi .num {font-size: 28px;}
  .st-key-panel-inputs, .st-key-panel-chart {padding: 18px; border-radius: 14px;}
  .st-key-panel-chart h2 {font-size: 18px;}
  .mm-means {padding: 18px; border-radius: 14px;}
  .mm-means h2 {font-size: 18px;}
  .mm-means p {font-size: 15px;}
  [data-testid="stButtonGroup"] button[data-variant="pills"] {height: 38px; padding: 0 12px;}
  [data-testid="stButtonGroup"] button[data-variant="pills"] p {font-size: 13px;}
  .st-key-panel-inputs [data-testid="stTextInputRootElement"] {height: 50px;}
  .st-key-panel-inputs .react-aria-ComboBox > [role="group"] {height: 48px;}
  .mm-footer {margin-top: 24px;}
  .mm-footer-in {padding: 16px; flex-direction: column; gap: 4px;}
  .mm-footer-in p {font-size: 12px;}
}
</style>
"""


def inject_css():
    st.html(CSS)


# --------------------------------------------------------------------------- page pieces
def _slug(name):
    return name.lower().replace(" ", "-")


def brand_header(active, meta):
    """The white top bar: +234 badge and name, page tabs, 'Data up to' on the right.

    Links between pages are st.page_link, not HTML <a> tags: on Streamlit Cloud the app runs
    inside a frame, and a plain link would open the whole site inside that frame. On phones
    the tabs fold into a ☰ menu (st.popover).
    """
    with st.container(key="mm-topbar", horizontal=True, vertical_alignment="center", gap="medium"):
        with st.container(key="nav-brand", width="content"):
            st.page_link(NAV_PAGES["Home"], label="Money Matters", help=None)
        with st.container(key="mm-tabs", horizontal=True, vertical_alignment="center", gap=None):
            for name, page in NAV_PAGES.items():
                if page is None:
                    st.html(f'<span class="mm mm-soon" title="Coming soon">{e(name)}<small>soon</small></span>',
                            width="content")
                else:
                    state = "-active" if name == active else ""
                    with st.container(key=f"tab-{_slug(name)}{state}", width="content"):
                        st.page_link(page, label=name)
        st.html(f'<p class="mm mm-upto">Data up to <b>{e(meta["latest_month_label"])}</b></p>', width="content")
        with st.container(key="mm-burger", width="content"):
            with st.popover("☰", help="Menu"):
                for name, page in NAV_PAGES.items():
                    if page is None:
                        st.html(f'<span class="mm mm-soon">{e(name)}<small>soon</small></span>')
                    else:
                        st.page_link(page, label=name)


def page_intro(eyebrow, title, lead, meta):
    """Orange eyebrow, big Space Grotesk title, grey lead. On phones the eyebrow adds 'Data up to'."""
    short = pd.Timestamp(meta["latest_month"]).strftime("%b %Y")
    lead_html = f'<p class="mm-lead">{lead}</p>' if lead else ""
    st.html(
        f'<section class="mm mm-intro"><p class="mm-eyebrow">{e(eyebrow)}'
        f'<span class="phone-only"> · Data up to {short}</span></p>'
        f'<h1>{e(title)}</h1>{lead_html}</section>'
    )


def section_head(title, note=""):
    st.html(f'<div class="mm mm-sechead"><h2>{e(title)}</h2><p>{e(note)}</p></div>')


def change_badge(change_pct, size="", short=False):
    """A real-terms change in colour AND words: 'Lost 15.9% of its value' / 'Gained 3.2%'.

    short=True gives 'Lost 15.9%' for tight spaces.
    """
    if pd.isna(change_pct):
        return ""
    if abs(change_pct) < 0.05:
        return f'<span class="mm-pill flat {size}">Kept its value</span>'
    if change_pct < 0:
        words = f"Lost {abs(change_pct):.1f}%" + ("" if short else " of its value")
        return f'<span class="mm-pill bad {size}">{words}</span>'
    words = f"Gained {change_pct:.1f}%" + ("" if short else " in value")
    return f'<span class="mm-pill good {size}">{words}</span>'


def info_box(title, text_html):
    """The warm 'What this means' box."""
    st.html(f'<section class="mm mm-means"><h2>{e(title)}</h2><p>{text_html}</p></section>')


def footer():
    articles = " · ".join(f'<a href="{url}" target="_blank" rel="noopener">{e(n)}</a>' for n, url in ARTICLES.items())
    linkedin = f' · <a href="{LINKEDIN_URL}" target="_blank" rel="noopener">LinkedIn</a>' if LINKEDIN_URL else ""
    st.html(
        f'<footer class="mm mm-footer"><div class="mm-footer-in">'
        f'<p>Educational, not financial advice. Data: Central Bank of Nigeria (and US BLS via FRED for the naira page).</p>'
        f'<p>Built by <a href="{PORTFOLIO_URL}" target="_blank" rel="noopener">Freedom Oboh</a> '
        f'with Python and Streamlit · '
        f'<a href="{GITHUB_URL}" target="_blank" rel="noopener">GitHub</a>{linkedin} · Articles: {articles}</p>'
        f'</div></footer>'
    )


def under_the_hood(meta, keys, extra_md=None, title="Under the hood: how these numbers are made"):
    with st.expander(title):
        if extra_md:
            st.markdown(extra_md)
        for key in keys:
            st.markdown(f"- {meta['trap_notes'][key]}")
        st.caption(f"Data pulled from the CBN on {min(meta['pulled_at_utc'].values())[:10]}.")


# --------------------------------------------------------------------------- charts
def style_figure(fig, height=320):
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=4, r=8, t=8, b=4),
        font=dict(family="Inter, Arial, sans-serif", color=NAVY, size=13),
        showlegend=False,
        hovermode="x unified",
        hoverlabel=dict(font=dict(family="Inter, Arial, sans-serif")),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        xaxis_title=None,
        yaxis_title=None,
    )
    fig.update_xaxes(showgrid=False, linecolor="#E3E6EB", tickfont=dict(color=MUTED, size=12))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickfont=dict(color=MUTED, size=12))
    return fig


def show_chart(fig):
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "responsive": True})


def legend(items):
    """items: list of (name, colour, dotted)."""
    lis = "".join(
        f'<li><span class="sw{" dot" if dotted else ""}" style="background:{c}"></span>{e(n)}</li>'
        for n, c, dotted in items
    )
    st.html(f'<ul class="mm mm-legend">{lis}</ul>')
