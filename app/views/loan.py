"""My loan: "What will this loan really cost me?"

Ported from the loan calculator in nigeria-credit-squeeze (app/loan_calculator.py). The maths is unchanged and
lives in src/loan_math.py; app tiers and bank rates come from src/loan_offers.py. This page only collects inputs
and shows results, in the Money Matters design. Bank rates come from data/processed/ (they update monthly);
loan app rates are the hand-collected snapshot from the credit article.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import (BLUE, GREY, NAVY, ORANGE, ARTICLES, brand_header, e, footer, info_box, legend, load_panel,
                        load_meta, naira, page_intro, parse_naira, section_head, show_chart, style_figure)
import loan_math  # noqa: E402  (src/ is on the path via components)
import loan_offers  # noqa: E402

REPO_URL = "https://github.com/Freedom15dev/nigeria-money-dashboard"

# Limits from the old app
MAX_AMOUNT = 1_000_000_000      # ₦1 billion: anything above is almost certainly a typo
MAX_MONTHLY_RATE = 100.0
MAX_DAYS, MAX_MONTHS = 365, 60
LONGEST_APP_DAYS = 365          # longer loans are compared with bank rates only

METHODS = ["Reducing balance", "Flat", "Not sure, show me both"]
PRESETS = {
    "Tunde: ₦100k, 1 month": dict(loan_amount="100,000", loan_rate=8.25, loan_rate_unit="per month", loan_length=1,
                                  loan_length_unit="months", loan_method=METHODS[2], loan_purpose="Personal"),
    "Amaka: ₦500k, 6 months": dict(loan_amount="500,000", loan_rate=8.25, loan_rate_unit="per month", loan_length=6,
                                   loan_length_unit="months", loan_method=METHODS[2], loan_purpose="Business"),
}
DEFAULT_PRESET = "Tunde: ₦100k, 1 month"
PENALTIES = {
    "Daily late fee": "A fee of a small % of the amount due, added every day you're late.",
    "Rollover interest": "Interest of a % per day on the amount due, added every day you're late (simple, not compounded).",
    "Monthly rollover at your loan's rate": "Every 30 days late, the whole amount due becomes a new one-month loan at your rate.",
}


def lpct(v):
    """A rate to at most 2 decimal places, without trailing zeros (8.25%, 99%)."""
    return f"{v:,.2f}".rstrip("0").rstrip(".") + "%"


def length_text(n, unit):
    n = int(n)
    return f"{n} {unit[:-1] if n == 1 else unit}"


# ----------------------------------------------------------------------------- state and presets
for key, value in PRESETS[DEFAULT_PRESET].items():
    st.session_state.setdefault(key, value)
st.session_state.setdefault("loan_preset", DEFAULT_PRESET)
st.session_state.setdefault("loan_days_late", 30)
st.session_state.setdefault("loan_penalty", "Rollover interest")
st.session_state.setdefault("loan_late_fee", 0.0333)
st.session_state.setdefault("loan_rollover", 1.0)


def apply_preset():
    name = st.session_state.loan_preset
    if name:
        for key, value in PRESETS[name].items():
            st.session_state[key] = value


def matching_preset():
    for name, values in PRESETS.items():
        if all(parse_naira(st.session_state[k]) == parse_naira(v) if k == "loan_amount" else st.session_state[k] == v
               for k, v in values.items()):
            return name
    return None


def on_edit():
    """Any change: tidy the amount, and keep the example highlighted only while the inputs still match it."""
    value = parse_naira(st.session_state.loan_amount)
    if value is not None:
        st.session_state.loan_amount = f"{value:,.0f}"
    st.session_state.loan_preset = matching_preset()


# ----------------------------------------------------------------------------- page top + inputs
meta = load_meta()
brand_header("My loan", meta)
page_intro("My loan", "What will this loan really cost me?",
           "Type in a loan, or try an example from the credit article, and see the total in naira, how it compares "
           "with banks and loan apps, and what happens if you pay late.", meta)

with st.container(key="panel-inputs"):
    st.pills("Try an example", list(PRESETS), key="loan_preset", on_change=apply_preset,
             help="Tunde borrows ₦100,000 for a month for personal use; Amaka borrows ₦500,000 for 6 months for her shop.")
    st.text_input("Amount you want to borrow", key="loan_amount", on_change=on_edit,
                  help="Type an amount in naira, for example 100,000 or 100k.")
    left, right = st.columns(2, gap="medium")
    with left:
        st.number_input("Interest rate (%)", step=0.25, format="%.2f", key="loan_rate", on_change=on_edit,
                        help="Loan apps usually quote per month, banks per year.")
        st.pills("The rate is", ["per month", "per year"], key="loan_rate_unit", on_change=on_edit,
                 label_visibility="collapsed")
    with right:
        st.number_input("Loan length", step=1, key="loan_length", on_change=on_edit)
        st.pills("Length in", ["days", "months"], key="loan_length_unit", on_change=on_edit,
                 label_visibility="collapsed")
    st.pills("What's the loan for?", ["Personal", "Business"], key="loan_purpose", on_change=on_edit,
             help="Used only to pick which loan app products to compare you with.")
    st.pills("How is interest charged?", METHODS, key="loan_method", on_change=on_edit,
             help=("Reducing balance: you pay interest only on what you still owe, so it shrinks as you repay. "
                   "Flat: you pay interest on the full amount every month, even after you've repaid part of it."))

ss = st.session_state
inp = dict(amount=parse_naira(ss.loan_amount), rate=ss.loan_rate, rate_unit=ss.loan_rate_unit or "per month",
           length=ss.loan_length, length_unit=ss.loan_length_unit or "months",
           method=ss.loan_method or METHODS[2], purpose=ss.loan_purpose or "Personal")


# ----------------------------------------------------------------------------- friendly checks (old app's rules)
def validate(inp):
    problems = []
    if inp["amount"] is None:
        problems.append("Type the amount in naira, for example 100,000.")
    elif inp["amount"] <= 0:
        problems.append("Please enter an amount above ₦0.")
    elif inp["amount"] > MAX_AMOUNT:
        problems.append(f"That's more than {naira(MAX_AMOUNT)}. Please check the amount for an extra zero.")
    if inp["rate"] is None or inp["rate"] < 0:
        problems.append("The interest rate can't be negative.")
    elif (inp["rate"] / 12 if inp["rate_unit"] == "per year" else inp["rate"]) > MAX_MONTHLY_RATE:
        problems.append("Please enter a rate of at most 100% a month (1,200% a year).")
    if inp["length"] is None or inp["length"] < 1:
        problems.append("The loan length must be at least 1 day or 1 month.")
    elif inp["length_unit"] == "days" and inp["length"] > MAX_DAYS:
        problems.append(f"For loans longer than {MAX_DAYS} days, please enter the length in months.")
    elif inp["length_unit"] == "months" and inp["length"] > MAX_MONTHS:
        problems.append(f"Please enter a length of at most {MAX_MONTHS} months (5 years).")
    return problems


problems = validate(inp)
if problems:
    for p in problems:
        st.info(f"👉 {p}")
    footer()
    st.stop()


# ----------------------------------------------------------------------------- the maths (all from loan_math)
def describe_loan(inp):
    monthly = loan_math.annual_to_monthly(inp["rate"]) if inp["rate_unit"] == "per year" else inp["rate"]
    in_days = inp["length_unit"] == "days"
    months = inp["length"] / 30 if in_days else int(inp["length"])  # days ÷ 30
    one_payment = in_days or months == 1  # repaid in one go at the end
    P = inp["amount"]
    if one_payment:
        total = loan_math.flat_total(P, monthly, months)  # one repayment: flat = reducing
        totals = {"Reducing balance": total, "Flat": total}
        instalments = {}
    else:
        totals = {m: loan_math.repayment(P, monthly, months, "reducing" if m == "Reducing balance" else "flat")
                  for m in ["Reducing balance", "Flat"]}
        instalments = {"Reducing balance": loan_math.reducing_payment(P, monthly, months),
                       "Flat": totals["Flat"] / months}
    shown = "Reducing balance" if inp["method"] != "Flat" else "Flat"
    return dict(inp=inp, P=P, monthly=monthly, months=months, one_payment=one_payment, totals=totals,
                instalments=instalments, shown=shown, simple_year=loan_math.simple_annual(monthly),
                effective_year=loan_math.effective_annual(monthly))


def total_at(loan, monthly_rate):
    """What the same amount and length would cost at another monthly rate, charged the same way."""
    if loan["one_payment"]:
        return loan_math.flat_total(loan["P"], monthly_rate, loan["months"])
    method = "flat" if loan["shown"] == "Flat" else "reducing"
    return loan_math.repayment(loan["P"], monthly_rate, loan["months"], method)


loan = describe_loan(inp)
P, total = loan["P"], loan["totals"][loan["shown"]]
length = length_text(inp["length"], inp["length_unit"])
when = "after " + length if loan["one_payment"] else "over " + length
both = inp["method"] == METHODS[2]

# ----------------------------------------------------------------------------- the answer (navy hero)
if loan["one_payment"]:
    pill = '<span class="mm-pill flat">One repayment at the end</span>'
else:
    pill = (f'<span class="mm-pill flat">Monthly instalment: {naira(loan["instalments"][loan["shown"]])}'
            f'{" (reducing balance)" if both else ""}</span>')
side = (f'<p>That\'s <b>{lpct(loan["simple_year"])}</b> a year (simple: the monthly rate × 12), or about '
        f'<b>{lpct(round(loan["effective_year"]))}</b> a year if the interest compounded (effective).</p>')
if both:
    red, flat = loan["totals"]["Reducing balance"], loan["totals"]["Flat"]
    side += ("<p>Repaid in one go, flat and reducing balance give the same total.</p>" if loan["one_payment"] else
             f'<p>Shown on reducing balance, the cheaper way. <b>Flat interest would cost {naira(flat - red)} more</b> '
             f'({naira(flat)}). Ask your lender which one they use.</p>')
st.html(
    f'<section class="mm mm-hero" aria-label="The answer"><div class="main">'
    f'<p class="soft">You borrow <b>{naira(P)}</b> {when} at <b>{lpct(inp["rate"])} {inp["rate_unit"]}</b></p>'
    f'<div class="figs">'
    f'<div class="fig"><span class="lbl">Total you\'ll repay</span><span class="num">{naira(total)}</span></div>'
    f'<div class="fig"><span class="lbl">Total interest</span><span class="num warm">{naira(total - P)}</span></div>'
    f'</div>{pill}</div><div class="side">{side}</div></section>'
)

# ----------------------------------------------------------------------------- month-by-month breakdown
section_head("Month by month", "Where each payment goes")
if loan["one_payment"]:
    st.html(f'<section class="mm mm-note"><p>This loan is repaid in one go: <b>{naira(total)}</b> {when}. '
            f'There is no month-by-month schedule. (A length in days, or 1 month, is treated as one repayment at '
            f'the end.)</p></section>')
else:
    months = loan["months"]
    sched = {m: pd.DataFrame(loan_math.schedule(P, loan["monthly"], months, key))
             for m, key in [("Reducing balance", "reducing"), ("Flat", "flat")]}
    with st.container(key="panel-breakdown"):
        st.html('<div class="mm"><h2>Interest paid each month</h2><p style="font-size:14px;color:#4A5568;'
                'margin-top:4px">Flat interest stays the same every month because it is charged on the full amount '
                'you borrowed. Reducing-balance interest shrinks as you pay the loan down.</p></div>')
        fig = go.Figure()
        for name, colour in [("Reducing balance", BLUE), ("Flat", ORANGE)]:
            df = sched[name]
            fig.add_trace(go.Scatter(x=df["month"], y=df["interest"], name=name, mode="lines+markers",
                                     line=dict(color=colour, width=3),
                                     hovertemplate=f"{name}, month %{{x}}: ₦%{{y:,.0f}} interest<extra></extra>"))
        fig.update_xaxes(title="Month", tickmode="linear", dtick=1 if months <= 12 else 6)
        fig.update_yaxes(tickprefix="₦", tickformat=",.0f", rangemode="tozero")
        style_figure(fig, height=280)
        fig.update_layout(hovermode="closest")
        show_chart(fig)
        legend([("Reducing balance", BLUE, False), ("Flat", ORANGE, False)])
    with st.expander("See every month: payment, interest and what's left"):
        cols = st.columns(2)
        for col, (name, df) in zip(cols, sched.items()):
            rows = "".join(f"<tr><td>{int(r.month)}</td><td>{naira(r.payment)}</td><td>{naira(r.interest)}</td>"
                           f"<td>{naira(r.balance)}</td></tr>" for r in df.itertuples())
            col.html(f'<div class="mm" style="overflow-x:auto"><p style="font-weight:700;margin-bottom:6px">{name}</p>'
                     f'<table class="mm-table"><thead><tr><th>Month</th><th>Payment</th><th>Interest</th>'
                     f'<th>Left to repay</th></tr></thead><tbody>{rows}</tbody></table></div>')

# ----------------------------------------------------------------------------- bank vs app comparison
bank = loan_offers.bank_rates(load_panel())
offers = loan_offers.load_offers()
days = inp["length"] if inp["length_unit"] == "days" else inp["length"] * 30
products = loan_offers.products_for(offers, days, business=inp["purpose"] == "Business")
rows = [("Bank: prime rate", bank["prime_month"], BLUE), ("Bank: maximum rate", bank["max_month"], BLUE),
        ("Your loan", loan["monthly"], ORANGE)]
bank_only = days > LONGEST_APP_DAYS or products.empty  # no app in the data advertises loans over a year
t = None
if not bank_only:
    t = loan_offers.tiers(products)
    rows += [(loan_offers.TIER_LABELS[k], t[k], GREY) for k in ["start", "mid", "high"] if t[k] == t[k]]  # skip NaN
rows.sort(key=lambda r: total_at(loan, r[1]))
labels = [f"{name} · {lpct(rate)} a month" for name, rate, _ in rows]
totals = [total_at(loan, rate) for _, rate, _ in rows]

section_head("How does it compare?", f"Total repaid on {naira(P)} for {length}")
with st.container(key="panel-compare"):
    st.html(f'<div class="mm"><p style="font-size:14px;color:#4A5568">Bank rates: CBN averages, '
            f'<b>{bank["month"]}</b>' + ("" if bank_only else f' · {loan_offers.APP_RATES_LABEL}') + '</p></div>')
    y = list(range(len(rows)))
    fig = go.Figure(go.Bar(
        x=totals, y=y, orientation="h", width=0.45, marker_color=[c for _, _, c in rows],
        text=[naira(v) for v in totals], textposition="outside", cliponaxis=False,
        textfont=dict(color=NAVY, size=13), customdata=labels,
        hovertemplate="%{customdata}<br>Total repaid: %{text}<extra></extra>"))
    for yi, lab, (name, _, _) in zip(y, labels, rows):  # each label just above its bar, so bars use the full width
        fig.add_annotation(x=0, y=yi - 0.42, text=f"<b>{lab}</b>" if name == "Your loan" else lab, showarrow=False,
                           xanchor="left", yanchor="bottom", font=dict(size=12, color=NAVY))
    style_figure(fig, height=68 * len(rows) + 30)
    fig.update_layout(bargap=0.5, hovermode="closest", margin=dict(l=0, r=0, t=10, b=0),
                      xaxis=dict(visible=False, range=[0, max(totals) * 1.38]),
                      yaxis=dict(visible=False, autorange="reversed", range=[len(rows) - 0.5, -0.9]))
    show_chart(fig)
    how = "one repayment at the end" if loan["one_payment"] else loan["shown"].lower()
    if bank_only:
        st.caption(f"No loan app in this data advertises loans this long, so only bank rates are shown. Bank rates: "
                   f"CBN averages, {bank['month']}. Your actual offer depends on you. All bars: {how}.")
    else:
        st.caption(f"Bank rates: CBN averages, {bank['month']}, updated monthly. {loan_offers.APP_RATES_LABEL}: "
                   f"{len(products)} app products in the credit article's data that offer this loan length "
                   f"({inp['purpose'].lower()} loans), as tiers; no lender is named. Your actual offer depends on "
                   f"you. All bars: {how}.")

bank_max_total = total_at(loan, bank["max_month"])
gap = total - bank_max_total
line = (f"At {lpct(loan['monthly'])} a month, {naira(P)} {when} costs {naira(total)} in total. "
        f"At the banks' average maximum rate ({lpct(bank['max_year'])} a year in {bank['month']}) it would cost "
        f"{naira(bank_max_total)}, {naira(abs(gap))} {'less' if gap > 0 else 'more'}.")
if t is not None:
    start_total, high_total = total_at(loan, t["start"]), total_at(loan, t["high"])
    line += (f" A typical starting loan app rate ({lpct(t['start'])} a month) would cost {naira(start_total)}; the "
             f"highest advertised app rate ({lpct(t['high'])} a month) {naira(high_total)}.")
line += (" Small borrowers rarely get the bank prime rate, which is for the banks' best customers. The real danger "
         "is the highest advertised rates and what happens after the due date.")
info_box("What this means", e(line))

# ----------------------------------------------------------------------------- late payment
section_head("What if you pay late?", "Penalties can cost more than the interest")
due = total if loan["one_payment"] else loan["instalments"][loan["shown"]]
st.html(f'<p class="mm" style="font-size:16px">' + (f"On the due date you owe <b>{naira(due)}</b>. If you can't pay it:"
        if loan["one_payment"] else f"Each month you owe an instalment of <b>{naira(due)}</b>. If you miss one:") + "</p>")
with st.container(key="panel-late"):
    kind = st.pills("Penalty type", list(PENALTIES), key="loan_penalty",
                    help=" ".join(f"{k}: {v}" for k, v in PENALTIES.items())) or "Rollover interest"
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        days_late = st.slider("Days late", 0, 90, key="loan_days_late")
    with c2:
        if kind == "Daily late fee":
            rate = st.number_input("Late fee (% of the amount due, per day)", min_value=0.0, max_value=10.0,
                                   step=0.01, format="%.4f", key="loan_late_fee")
            owed = lambda d: loan_math.daily_charge_total(due, rate, d)  # noqa: E731
        elif kind == "Rollover interest":
            rate = st.number_input("Rollover interest (% per day)", min_value=0.0, max_value=10.0, step=0.1,
                                   format="%.2f", key="loan_rollover")
            owed = lambda d: loan_math.daily_charge_total(due, rate, d)  # noqa: E731
        else:
            st.caption("Every 30 days late, one more month of interest at your loan's rate is added.")
            owed = lambda d: loan_math.monthly_rollover_total(due, loan["monthly"], d)  # noqa: E731
        st.caption(PENALTIES[kind])
    now = owed(days_late)
    st.html(f'<div class="mm mm-cards">'
            f'<article class="mm-card"><span class="sub">You\'d owe after {days_late} days</span>'
            f'<p class="num">{naira(now)}</p></article>'
            f'<article class="mm-card"><span class="sub">Extra because you were late</span>'
            f'<p class="num" style="color:#9B1C1C">{naira(now - due)}</p></article></div>')
    d_axis = list(range(0, 91))
    fig = go.Figure(go.Scatter(x=d_axis, y=[owed(d) for d in d_axis], mode="lines",
                               line=dict(color=ORANGE, width=3, shape="hv" if kind.startswith("Monthly") else "linear"),
                               hovertemplate="Day %{x}: ₦%{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=[days_late], y=[now], mode="markers", marker=dict(color=NAVY, size=11),
                             hoverinfo="skip"))
    fig.update_xaxes(title="Days late", range=[0, 92], tickvals=[0, 30, 60, 90])
    fig.update_yaxes(tickprefix="₦", tickformat=",.0f")
    style_figure(fig, height=260)
    fig.update_layout(hovermode="closest")
    show_chart(fig)
    st.caption("Example penalty terms based on what lenders publish. Check your own lender's terms. The chart starts "
               "at the amount due, so small changes look bigger than they are.")

# ----------------------------------------------------------------------------- before you borrow
section_head("Before you borrow")
st.html(
    '<section class="mm mm-note"><p>1. <b>Turn the rate into a yearly one.</b> 10% a month sounds smaller than 32% '
    'a year, but it\'s 120% a year.</p>'
    '<p>2. <b>Ask for the total in naira.</b> "How much will I repay altogether, and when?"</p>'
    '<p>3. <b>Borrow for the length you need.</b> A longer loan multiplies a monthly rate; a shorter one you can\'t '
    'repay leads to penalties.</p>'
    '<p>4. <b>Read what happens after the due date.</b> Late fees and rollovers can cost more than the interest.</p>'
    '<p>5. <b>Check the lender is on the FCCPC approved list</b> of digital lenders '
    '(<a href="https://fccpc.gov.ng/approvals-of-dmls/" target="_blank" rel="noopener">fccpc.gov.ng</a>).</p>'
    '</section>'
)
with st.expander("How this works"):
    st.markdown(
        "- **Days and months.** A length in days is turned into months as days ÷ 30. A loan entered in days, or for "
        "1 month, is treated as **one repayment at the end**, so flat and reducing give the same total. Loans of 2 "
        "months or more are repaid in **equal monthly instalments**.\n"
        "- **Yearly rates.** Simple = monthly rate × 12 (how an APR is usually quoted). Effective = (1 + monthly "
        "rate)¹² − 1, what the rate adds up to if interest is charged on interest.\n"
        "- **Reducing balance** charges interest only on what you still owe. **Flat** charges it on the full amount "
        "every month.\n"
        f"- **Bank rates:** CBN average prime and maximum lending rates for {bank['month']}, from the same monthly "
        "data as the rest of Money Matters, so they update each month. They are shown for loans of any length.\n"
        f"- **Loan app rates:** {loan_offers.APP_RATES_LABEL.lower()}, from the app products in the "
        f"[credit article]({ARTICLES['Borrowing']})'s data whose advertised loan length covers yours (payroll loans "
        "left out; business loans only for business borrowers). They are summed up as a typical starting rate "
        "(median of minimums), typical mid rate (median of range mid-points) and the highest advertised rate. They "
        "are a snapshot and do not update. No lender is named or recommended. Loans longer than 12 months are "
        "compared with bank rates only, because no app in the data advertises loans that long.\n"
        "- **Late payment.** Daily charges are simple interest on the amount due, not compounded. A monthly rollover "
        "adds one month of interest at your rate for every full 30 days late.\n"
        f"- The maths is in [src/loan_math.py]({REPO_URL}/blob/main/src/loan_math.py), checked by hand. This "
        "calculator stores nothing and asks for no personal details."
    )
footer()
