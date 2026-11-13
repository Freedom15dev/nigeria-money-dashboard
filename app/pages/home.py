"""Home: (+234) Money Matters, "Your money, this month". Layout: design/Home.dc.html."""

import pandas as pd
import streamlit as st

from components import (BAD, DESCRIPTION, GOOD, HELP, LOAN_CALCULATOR_URL, NAVY, SUPPORTING_LINE, TAGLINE,
                        brand_header, e, footer, load_meta, load_panel, naira, page_intro, pct, section_head)

panel = load_panel().set_index("month")
meta = load_meta()
latest = pd.Timestamp(meta["latest_month"])
year_ago = latest - pd.DateOffset(years=1)
now, then = panel.loc[latest], panel.loc[year_ago]

brand_header("Home", meta)
page_intro(SUPPORTING_LINE.rstrip("."), TAGLINE,
           "Inflation, the naira, interest rates, savings and borrowing in one place, explained in plain "
           "words and updated every month.", meta)

# ----------------------------------------------------------------------------- the sentence (navy hero)
real = now["real_savings_rate"]
direction = "losing" if real < 0 else "gaining"
# The navy card is a Streamlit container so the button can be a real st.page_link (see brand_header).
with st.container(key="hero-home", horizontal=True, vertical_alignment="center"):
    st.html(
        f'<section class="mm mm-hero bare" aria-label="This month in one sentence"><div class="main">'
        f'<p class="kicker">Your money, this month</p>'
        f'<p class="statement">Prices are rising <b>{pct(now["inflation"])}</b> a year. A savings account pays '
        f'<b>{pct(now["savingsDeposit"])}</b>. Money in a savings account is {direction} about '
        f'<span class="warm">{abs(real):.1f}%</span> of its value each year.</p></div></section>'
    )
    with st.container(key="cta", width="content"):
        st.page_link("pages/savings.py", label="Check your savings →")


# ----------------------------------------------------------------------------- key numbers
def arrow(x):
    return "↑" if x > 0 else "↓" if x < 0 else "→"


def change(x, unit, good_when, words):
    """Coloured change plus a plain-words note. good_when: 'up', 'down' or None (neutral)."""
    if abs(x) < 0.005:
        return f'<b style="color:{NAVY}">no change</b> · {e(words)}'
    colour = NAVY if good_when is None else GOOD if (x > 0) == (good_when == "up") else BAD
    amount = f"{abs(x):.2f} pts" if unit == "pts" else f"{abs(x):.1f}%"
    return f'<b style="color:{colour}">{arrow(x)} {amount}</b> · {e(words)}'


def kpi(title, value, change_html, help_text, value_colour=NAVY):
    return (f'<article class="mm-card mm-kpi"><h3>{e(title)}<span class="mm-tip" title="{e(help_text)}" '
            f'aria-label="{e(help_text)}">ⓘ</span></h3>'
            f'<p class="num" style="color:{value_colour}">{value}</p><p class="chg">{change_html}</p></article>')


estimated = []  # rates whose year-ago figure was a feed glitch (see clean.fix_one_month_spikes)


def rate_change(col):
    """Change in a rate over 12 months. If the year-ago figure was removed as a one-month glitch,
    compare with the chart value (the straight line between its neighbours) and say so."""
    old = then[col]
    if pd.isna(old) and pd.notna(then.get(f"{col}_chart")):
        old = then[f"{col}_chart"]
        estimated.append(col)
    return now[col] - old


def note(col, words):
    return f"{words} (vs an estimated {year_ago:%b %Y})" if col in estimated else words


d_infl = now["inflation"] - then["inflation"]
d_fx = (now["usd_ngn"] / then["usd_ngn"] - 1) * 100
d_sav = rate_change("savingsDeposit")
d_mpr = rate_change("policy_rate")
d_prime = rate_change("primeLending")
d_max = rate_change("maxLending")
real_then = then["real_savings_rate"]

if real < 0 and real_then < 0:
    real_words = "still losing, but less" if real > real_then else "losing more than a year ago"
elif real < 0:
    real_words = "now losing value"
elif real_then < 0:
    real_words = "now beating prices"
else:
    real_words = "still beating prices"
real_change = f'<b style="color:{NAVY}">was {pct(real_then)}</b> · {e(real_words)}'

cards = [
    kpi("Inflation", pct(now["inflation"]),
        change(d_infl, "pts", "down", "prices rising more slowly" if d_infl < 0 else "prices rising faster"),
        HELP["inflation"]),
    kpi("₦ per $1 (official)", naira(now["usd_ngn"], 2),
        change(d_fx, "%", "down", "the naira is stronger" if d_fx < 0 else "the naira is weaker"), HELP["usd"]),
    kpi("Savings account rate", pct(now["savingsDeposit"]),
        change(d_sav, "pts", "up", note("savingsDeposit", "savings pay more" if d_sav > 0 else "savings pay less")),
        HELP["savings"]),
    kpi("Real savings rate", pct(real), real_change, HELP["real"], value_colour=BAD if real < 0 else GOOD),
    kpi("Policy rate (MPR)", pct(now["policy_rate"]),
        change(d_mpr, "pts", None, note("policy_rate", "the CBN has cut rates" if d_mpr < 0 else "the CBN has raised rates")),
        HELP["mpr"]),
    kpi("Bank lending: best borrowers", pct(now["primeLending"]),
        change(d_prime, "pts", "down", note("primeLending", "prime lending rate")), HELP["prime"]),
    kpi("Bank lending: riskier borrowers", pct(now["maxLending"]),
        change(d_max, "pts", "down", note("maxLending", "maximum lending rate")), HELP["max"]),
]
section_head("The key numbers", f"{latest:%B %Y}, compared with {year_ago:%B %Y}")
st.html(f'<div class="mm mm-cards">{"".join(cards)}</div>')

with st.expander("What these terms mean"):
    for term, key in [("Inflation", "inflation"), ("₦ per $1 (official)", "usd"), ("Savings account rate", "savings"),
                      ("Real savings rate", "real"), ("Policy rate (MPR)", "mpr"),
                      ("Bank lending: best borrowers (prime rate)", "prime"),
                      ("Bank lending: riskier borrowers (maximum rate)", "max")]:
        st.markdown(f"**{term}.** {HELP[key]}")
    st.caption("Green means better for an ordinary saver or borrower, red means worse. "
               "Rates are CBN averages; real banks differ.")
    if estimated:
        st.markdown(f"**Estimated year-ago figures.** {meta['trap_notes']['rate_spikes']} The change on "
                    f"those cards compares with that straight-line value for {year_ago:%B %Y}.")

# ----------------------------------------------------------------------------- explore
section_head("Explore")
with st.container(key="explore", horizontal=True):
    with st.container(key="explore-savings"):
        st.html('<div class="mm" style="display:flex;flex-direction:column;gap:8px">'
                '<span style="font-size:18px;font-weight:700">My savings</span>'
                '<span style="font-size:14px;line-height:1.5;color:#4A5568">What is money you saved in a past '
                'year worth today?</span></div>')
        st.page_link("pages/savings.py", label="Work out my savings →")
    st.html('<div class="mm mm-card mm-explore"><span class="t">Prices</span>'
            '<span class="d">Inflation since 2003, and where it may head next.</span>'
            '<span class="soon">Coming soon</span></div>')
    st.html('<div class="mm mm-card mm-explore"><span class="t">The naira</span>'
            '<span class="d">20 years of the dollar rate, and the outlook to 2030.</span>'
            '<span class="soon">Coming soon</span></div>')
    st.html(f'<a class="mm mm-card mm-explore warm" href="{LOAN_CALCULATOR_URL}" target="_blank" rel="noopener">'
            '<span class="t">Borrowing</span><span class="d">Who pays what to borrow. The page is coming soon; '
            'the loan calculator works now: <b>work out your own loan →</b></span></a>')

with st.expander("About Money Matters"):
    st.write(DESCRIPTION)

footer()
