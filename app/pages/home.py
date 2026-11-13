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
st.html(
    f'<section class="mm mm-hero" aria-label="This month in one sentence"><div class="main">'
    f'<p class="kicker">Your money, this month</p>'
    f'<p class="statement">Prices are rising <b>{pct(now["inflation"])}</b> a year. A savings account pays '
    f'<b>{pct(now["savingsDeposit"])}</b>. Money in a savings account is {direction} about '
    f'<span class="warm">{abs(real):.1f}%</span> of its value each year.</p></div>'
    f'<a class="mm-cta" href="/savings">Check your savings <span aria-hidden="true">→</span></a></section>'
)


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


d_infl = now["inflation"] - then["inflation"]
d_fx = (now["usd_ngn"] / then["usd_ngn"] - 1) * 100
d_sav = now["savingsDeposit"] - then["savingsDeposit"]
d_mpr = now["policy_rate"] - then["policy_rate"]
d_prime = now["primeLending"] - then["primeLending"]
d_max = now["maxLending"] - then["maxLending"]
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
        change(d_sav, "pts", "up", "savings pay more" if d_sav > 0 else "savings pay less"), HELP["savings"]),
    kpi("Real savings rate", pct(real), real_change, HELP["real"], value_colour=BAD if real < 0 else GOOD),
    kpi("Policy rate (MPR)", pct(now["policy_rate"]),
        change(d_mpr, "pts", None, "the CBN has cut rates" if d_mpr < 0 else "the CBN has raised rates"),
        HELP["mpr"]),
    kpi("Bank lending: best borrowers", pct(now["primeLending"]),
        change(d_prime, "pts", "down", "prime lending rate"), HELP["prime"]),
    kpi("Bank lending: riskier borrowers", pct(now["maxLending"]),
        change(d_max, "pts", "down", "maximum lending rate"), HELP["max"]),
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

# ----------------------------------------------------------------------------- explore
section_head("Explore")
st.html(
    '<div class="mm mm-cards">'
    '<a class="mm-card mm-explore" href="/savings"><span class="t">My savings</span>'
    '<span class="d">What is money you saved in a past year worth today?</span></a>'
    '<div class="mm-card mm-explore"><span class="t">Prices</span>'
    '<span class="d">Inflation since 2003, and where it may head next.</span><span class="soon">Coming soon</span></div>'
    '<div class="mm-card mm-explore"><span class="t">The naira</span>'
    '<span class="d">20 years of the dollar rate, and the outlook to 2030.</span><span class="soon">Coming soon</span></div>'
    f'<a class="mm-card mm-explore warm" href="{LOAN_CALCULATOR_URL}" target="_blank" rel="noopener">'
    '<span class="t">Borrowing</span><span class="d">Who pays what to borrow. The page is coming soon; '
    'the loan calculator works now: <b>work out your own loan →</b></span></a>'
    '</div>'
)

with st.expander("About Money Matters"):
    st.write(DESCRIPTION)

footer()
