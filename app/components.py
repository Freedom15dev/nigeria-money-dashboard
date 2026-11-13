"""Shared pieces for every page: data loading, formatting, the house CSS, the brand header,
cards, badges, chart style and the footer. Layout follows the mockups in design/.

The app only ever reads data/processed/. It never calls the CBN.
"""

import html
import json
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
# MM_PROCESSED_DIR is for testing only (e.g. a simulated future month); the app normally reads data/processed/.
PROCESSED = Path(os.environ.get("MM_PROCESSED_DIR", ROOT / "data" / "processed"))
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
NAV_PAGES = {"Home": "views/home.py", "My savings": "views/savings.py",
             "Prices": "views/prices.py", "The naira": "views/naira.py", "Borrowing": None}

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
    "food": "Food inflation: how much food prices are higher than 12 months ago.",
    "core": "Core inflation: price rises leaving out farm produce and energy, which jump around the most. It shows the steadier, underlying trend.",
    "range": "A range, not a prediction. An 80% range should contain the real figure about 4 times in 5, and a 50% range about half the time. The real figure can still land outside it.",
    "log": "On a log scale each step up the axis is the same % change, so ₦100 → ₦200 looks as big as ₦1,000 → ₦2,000. It shows the early years clearly.",
    "jump": "A jump month: the naira lost more than 5% of its value against the dollar in a single month.",
    "ppp": "Purchasing power parity (PPP): the idea that, over the years, a currency weakens by about the gap between its inflation and the other country's inflation.",
    "scenario": "A scenario is an 'if → then' story, not a forecast: if this happens, the rate would likely end up around here.",
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
[class*="st-key-explore-"] {background: #FFFFFF; border: 1px solid #E3E6EB; border-top: 4px solid #2A6FDB;
  border-radius: 14px; padding: 22px; gap: 8px !important;}
[class*="st-key-explore-"] [data-testid="stPageLink-NavLink"] {padding: 0; background: none !important;}
[class*="st-key-explore-"] [data-testid="stPageLink-NavLink"] p {color: #2A6FDB !important; font-weight: 600 !important; font-size: 14px;}

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
[class*="st-key-panel-"] {background: #FFFFFF; border: 1px solid #E3E6EB !important;
  border-radius: 16px; padding: 28px;}
[class*="st-key-panel-"] h2 {font-family: 'Space Grotesk', Arial, sans-serif; font-size: 22px; font-weight: 700; margin: 0; padding: 0;}
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

/* pills: unselected white with grey border. Pick-several pills (multi) turn navy with a tick;
   pick-one pills (single) turn light blue, like the mockup's quick amounts. */
[data-testid="stButtonGroup"] button[data-variant="pills"] {border-radius: 999px !important; height: 40px;
  padding: 0 16px; background: #FFFFFF !important; border: 1px solid #CBD2DC !important;}
[data-testid="stButtonGroup"] button[data-variant="pills"] p {font-size: 14px; color: #0F1E33 !important;}
[data-testid="stButtonGroup"] button[data-selected="true"] {background: #0F1E33 !important; border-color: #0F1E33 !important;}
[data-testid="stButtonGroup"] button[data-selected="true"] p {color: #FFFFFF !important; font-weight: 600;}
[data-testid="stButtonGroup"] button[data-selected="true"] p::before {content: "✓ ";}
[data-testid="stButtonGroup"] button[aria-checked="true"] {background: #EAF1FC !important; border-color: #2A6FDB !important;}
[data-testid="stButtonGroup"] button[aria-checked="true"] p {color: #1B4FA8 !important; font-weight: 600;}
.st-key-quick button[data-variant="pills"] {height: 36px; padding: 0 14px;}
/* forecast tracker: checked months */
.mm-table {width: 100%; border-collapse: collapse; background: #FFFFFF; border: 1px solid #E3E6EB; border-radius: 12px;
  font-size: 14px; overflow: hidden;}
.mm-table th {text-align: left; font-weight: 600; color: #4A5568; background: #F5F6F8; padding: 10px 12px;}
.mm-table td {padding: 10px 12px; border-top: 1px solid #EEF0F3; white-space: nowrap;}
/* range cards (Prices and The naira) */
.mm-range .num {font-size: 24px;}
.mm-range .when {font-size: 13px; font-weight: 700; color: #2A6FDB; letter-spacing: 0.5px;}
.mm-note {background: #FFFFFF; border: 1px solid #E3E6EB; border-left: 4px solid #D9822B; border-radius: 12px;
  padding: 18px 22px; display: flex; flex-direction: column; gap: 8px;}
.mm-note h3 {margin: 0; padding: 0; font-family: Inter, Arial, sans-serif; font-size: 16px; font-weight: 700; color: #0F1E33;}
.mm-note p {font-size: 14px; line-height: 1.6; color: #2D3A4F;}

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
  [class*="st-key-panel-"] {padding: 18px; border-radius: 14px;}
  [class*="st-key-panel-"] h2 {font-size: 18px;}
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


def change_text(x, unit, good_when, words):
    """A coloured 12-month change plus a plain-words note, for key-number cards.
    unit: 'pts' (percentage points) or '%'. good_when: 'up', 'down' or None (neutral, navy)."""
    if pd.isna(x) or abs(x) < 0.005:
        return f'<b style="color:{NAVY}">no change</b> · {e(words)}'
    colour = NAVY if good_when is None else GOOD if (x > 0) == (good_when == "up") else BAD
    amount = f"{abs(x):.2f} pts" if unit == "pts" else f"{abs(x):.1f}%"
    return f'<b style="color:{colour}">{"↑" if x > 0 else "↓"} {amount}</b> · {e(words)}'


def kpi_card(title, value, change_html, help_text, value_colour=NAVY):
    """One key-number card (HTML); put several in <div class="mm mm-cards">."""
    return (f'<article class="mm-card mm-kpi"><h3>{e(title)}<span class="mm-tip" title="{e(help_text)}" '
            f'aria-label="{e(help_text)}">ⓘ</span></h3>'
            f'<p class="num" style="color:{value_colour}">{value}</p><p class="chg">{change_html}</p></article>')


def load_csv(name, dates=("month",)):
    return _load_csv(name, tuple(dates))


@st.cache_data(show_spinner=False)
def _load_csv(name, dates):
    return pd.read_csv(PROCESSED / name, parse_dates=list(dates))


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


NICE_NAIRA = [100, 150, 200, 300, 500, 700, 1000, 1500, 2000, 3000, 5000, 7000, 10000, 15000, 20000]


def naira_log_axis(fig, low, high, axis="y", sparse=False):
    """A log-scale ₦ axis with a few round labels instead of Plotly's crowded minor ticks.
    sparse=True keeps only 1-2-3-5 steps, for short axes on phones."""
    nice = [t for t in NICE_NAIRA if not sparse or str(t)[0] in "1235" and t not in (150, 1500, 15000)]
    ticks = [t for t in nice if low * 0.9 <= t <= high * 1.1]
    update = fig.update_yaxes if axis == "y" else fig.update_xaxes
    update(type="log", tickvals=ticks, ticktext=[f"₦{t:,}" for t in ticks], tickangle=0, minor=dict(showgrid=False))
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


# --------------------------------------------------------------------------- forecast tracker
def _vintage_label(vintage, source):
    month = pd.Timestamp(f"{vintage}-01")
    return f"{month:%b %Y}" + (" (as published)" if source == "published" else "")


def forecast_tracker(model, series, actual, unit, colour, key, history_months=12):
    """'How are the forecasts doing?': each saved forecast, frozen exactly as made, with the actual
    line drawn over it, a plain-words scorecard and every checked month (hits and misses alike).

    model 'inflation' or 'naira'; series 'headline'/'food'/'outlook'; actual: pd.Series by month;
    unit 'points' or 'naira'.
    """
    import plotly.graph_objects as go

    vint = load_csv("forecast_vintages.csv")
    vint = vint[(vint["model"] == model) & (vint["series"] == series)]
    cards = load_csv("forecast_scorecard.csv", dates=("last_checked", "next_check"))
    cards = cards[(cards["model"] == model) & (cards["series"] == series)]
    scores = load_csv("forecast_scores.csv")
    scores = scores[(scores["model"] == model) & (scores["series"] == series)] if len(scores) else scores
    if vint.empty:
        st.info("No saved forecasts yet.")
        return

    vint["vintage"] = vint["vintage"].astype(str)
    cards = cards.assign(vintage=cards["vintage"].astype(str))
    options = {_vintage_label(v, s): v for v, s in vint.groupby("vintage")["source"].first().items()}
    labels = list(options)
    picked = st.pills("Forecast made with data up to", labels, default=labels[0], key=f"{key}_vintage") or labels[0]
    vintage = options[picked]
    v = vint[vint["vintage"] == vintage].sort_values("month")
    card = cards[cards["vintage"] == vintage].iloc[0]
    sc = scores[scores["vintage"].astype(str) == vintage].sort_values("month") if len(scores) else scores
    made = pd.Timestamp(f"{vintage}-01")
    fmt = (lambda x: f"{x:.1f}%") if unit == "points" else (lambda x: naira(x))

    # ---- scorecard in words
    n = int(card["checked"])
    if n == 0:
        when = pd.Timestamp(card["next_check"])
        sparse = len(v) < 6
        words = (f"This forecast was made with data up to {made:%B %Y}. Nothing to check yet: the first check is in "
                 f"<b>{when:%B %Y}</b>, when that month's figure is published.")
        if sparse:
            words += (f" Only {len(v)} dates were published for it ({', '.join(f'{m:%b %Y}' for m in v['month'])}), "
                      "so that is the first month it can be scored.")
    else:
        miss_avg = (f"{card['mean_abs_error']:.1f} points" if unit == "points"
                    else f"{card['mean_abs_error_pct']:.1f}%")
        naive_avg = (f"{card['mean_abs_naive_error']:.1f} points" if unit == "points"
                     else f"{(sc['naive_error'].abs() / sc['actual'] * 100).mean():.1f}%")
        words = (f"Since {made:%B %Y}: <b>{int(card['inside80'])} of {n}</b> month{'s' if n != 1 else ''} inside the "
                 f"80% range")
        if card["checked50"] > 0:
            words += f", <b>{int(card['inside50'])} of {int(card['checked50'])}</b> inside the 50% range"
        words += (f". Average miss: <b>{miss_avg}</b> (the 'no change' guess missed by {naive_avg}). ")
        if card["above80"] or card["below80"]:
            outside = [f"{m:%b %Y} ({fmt(a)}, {'above' if a > hi else 'below'} the range {fmt(lo)} to {fmt(hi)})"
                       for m, a, lo, hi in zip(sc["month"], sc["actual"], sc["low80"], sc["high80"])
                       if not lo <= a <= hi]
            words += f"<b>Missed the 80% range:</b> {'; '.join(outside)}. "
        else:
            words += "No month has fallen outside the 80% range so far. "
        if n < 6:
            words += (f"That is only {n} month{'s' if n != 1 else ''}, far too early to judge: an honest 80% range "
                      "should still miss about 1 month in 5, so it needs a year or more of checks.")
        if pd.notna(card["next_check"]):
            words += f" Next check: {pd.Timestamp(card['next_check']):%B %Y}."
    st.html(f'<section class="mm mm-note" style="border-left-color:#2A6FDB"><h3>Scorecard</h3><p>{words}</p>'
            f'<p style="color:#4A5568">The forecast is shown exactly as it was saved in {made:%B %Y}; '
            f'old forecasts are never redrawn or edited.</p></section>')

    # ---- chart: the frozen forecast with the actual line over it
    with st.container(key=f"panel-{key}"):
        start = made - pd.DateOffset(months=history_months)
        a = actual.loc[start:]
        fig = go.Figure()
        band80, band50 = "rgba(42,111,219,0.14)", "rgba(42,111,219,0.30)"
        if len(v) >= 6:  # a monthly forecast: draw its bands
            x = list(v["month"])
            fig.add_trace(go.Scatter(x=x + x[::-1], y=list(v["high80"]) + list(v["low80"])[::-1], fill="toself",
                                     fillcolor=band80, line=dict(width=0), hoverinfo="skip", name="80% range"))
            if v["low50"].notna().all():
                fig.add_trace(go.Scatter(x=x + x[::-1], y=list(v["high50"]) + list(v["low50"])[::-1], fill="toself",
                                         fillcolor=band50, line=dict(width=0), hoverinfo="skip", name="50% range"))
            fig.add_trace(go.Scatter(x=x, y=v["central"], mode="lines", name="Forecast",
                                     line=dict(color=BLUE, width=2, dash="dash"),
                                     hovertemplate="forecast " + ("%{y:.1f}%" if unit == "points" else "₦%{y:,.0f}")))
        else:  # only a few published dates: draw each range as a bar, never join the dots
            for _, r in v.iterrows():
                fig.add_trace(go.Scatter(x=[r["month"], r["month"]], y=[r["low80"], r["high80"]], mode="lines",
                                         line=dict(color="#A9C5F0", width=16), hoverinfo="skip"))
                if pd.notna(r["low50"]):
                    fig.add_trace(go.Scatter(x=[r["month"], r["month"]], y=[r["low50"], r["high50"]], mode="lines",
                                             line=dict(color="#5E8FDE", width=16), hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=v["month"], y=v["central"], mode="markers", name="Forecast",
                                     marker=dict(color=NAVY, size=9, line=dict(color="#FFFFFF", width=2)),
                                     hovertemplate="middle ₦%{y:,.0f}"))
        fig.add_trace(go.Scatter(x=a.index, y=a, mode="lines", name="Actual", line=dict(color=colour, width=2.5),
                                 hovertemplate="actual " + ("%{y:.2f}%" if unit == "points" else "₦%{y:,.2f}")))
        if len(sc):
            outside = sc[(sc["actual"] < sc["low80"]) | (sc["actual"] > sc["high80"])]
            fig.add_trace(go.Scatter(x=outside["month"], y=outside["actual"], mode="markers", name="Outside 80%",
                                     marker=dict(color=BAD, size=10, symbol="x"), hoverinfo="skip"))
        fig.add_vline(x=made, line_color=GREY, line_width=1, line_dash="dot")
        fig.add_annotation(x=made, y=1, yref="paper", text=f"Forecast made ({made:%b %Y})", showarrow=False,
                           xanchor="left", yanchor="top", xshift=4, font=dict(size=12, color=MUTED))
        if unit == "naira":
            naira_log_axis(fig, min(a.min(), v["low80"].min()), v["high80"].max())
        else:
            fig.update_yaxes(ticksuffix="%", rangemode="tozero")
        style_figure(fig, height=320)
        show_chart(fig)
        items = [("Actual", colour, False), ("Forecast", BLUE if len(v) >= 6 else NAVY, len(v) >= 6),
                 ("80% range", "#C9DAF5", False)]
        if v["low50"].notna().any():
            items.append(("50% range", "#94B7EC", False))
        if len(sc):
            items.append(("Outside the 80% range (×)", BAD, False))
        legend(items)

    # ---- every checked month, hits and misses alike
    if len(sc):
        rows = "".join(
            f'<tr><td>{m:%b %Y}</td><td>{fmt(f)}</td><td>{fmt(lo)} to {fmt(hi)}</td><td><b>{fmt(act)}</b></td>'
            + ('<td style="color:#1D6B44">✓ inside</td>' if lo <= act <= hi else
               f'<td style="color:#9B1C1C"><b>✗ {"above" if act > hi else "below"}</b></td>') + '</tr>'
            for m, f, lo, hi, act in zip(sc["month"], sc["forecast"], sc["low80"], sc["high80"], sc["actual"]))
        st.html('<div class="mm" style="overflow-x:auto"><table class="mm-table"><thead><tr><th>Month</th>'
                '<th>Forecast</th><th>80% range</th><th>Actual</th><th>Result</th></tr></thead>'
                f'<tbody>{rows}</tbody></table></div>')
