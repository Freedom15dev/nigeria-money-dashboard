# CLAUDE.md — (+234) Money Matters

**Understand what the economy is doing to your money.**

## 0. Name and wording (use exactly)

- **Name:** (+234) Money Matters
- **Tagline:** Understand what the economy is doing to your money.
- **Supporting line:** Nigeria's economy, through the numbers.
- **Description (README intro and the Home page "About" section):**
  Money Matters is a data-driven platform that helps Nigerians understand how the economy affects
  their everyday finances. It brings together key economic indicators such as inflation, exchange
  rates, interest rates, savings and borrowing into one interactive dashboard. Users can explore
  historical trends, understand how the value of their money has changed over time, compare
  financial scenarios, and see what the numbers mean for their personal and business decisions.
  The platform brings together data from multiple research projects into one place, with regular
  monthly updates.
- **Never describe it as "free"** anywhere: no "free app", "free tool", "free calculator". It isn't
  being sold, so price isn't part of the message. Just describe what it does.
- Page title in the browser tab: "(+234) Money Matters". Home page: name as the title, tagline
  under it, supporting line as a small caption.

Repo: `nigeria-money-dashboard` on GitHub (local folder: `naija-money-dashboard`)
Author: Freedom Oboh (GitHub: Freedom15dev), data analyst and Excel trainer, Lagos
Builds on: `nigeria-inflation-forecast`, `nigeria-savings-vs-inflation`, `naira-scenarios`,
`nigeria-credit-squeeze` (and its live loan calculator, https://naija-loan-cost.streamlit.app/)

---

## 1. Why this exists (read first)

Over four projects I've asked one question from different angles: **what does the economy do to an
ordinary Nigerian's money?**

- Prices: inflation and where it's heading.
- Savings: ₦100,000 kept as cash since January 2006 buys what about ₦6,460 bought then; in a savings
  account it grew to ₦208,347, which still only buys what ₦13,459 bought in 2006.
- The naira: ₦128 to the dollar in 2006, about ₦1,327 in September 2026, mostly in a few sudden jumps.
- Borrowing: small borrowers pay far more than big companies, and loan apps price by the month.

Each project lives in a notebook and an article. People read them once. Money Matters puts them in
one place that people can **use**, and that **stays current**. Every month it pulls the latest CBN
figures by itself.

The voice is mine: plain words, honest about limits, never financial advice. A shop owner should
understand every number; an analyst should respect the code.

My first app (the loan calculator) taught me two things to carry over:
- **Inputs go on the page, not in a sidebar.** Most people arrive on a phone.
- **Numbers come from code, never typed in**, and each module has a self-check.

---

## 2. Pages

A multi-page Streamlit app (`st.navigation`). Every page shows **"Data up to <month year>"** near the top.

### 2.1 Home: (+234) Money Matters, "Your money, this month"
- Top: the name, the tagline, the supporting line (see §0), then a short "About" from the description.
- KPI cards: headline inflation, ₦ per $ (official), MPR, prime lending rate, maximum lending rate,
  savings deposit rate, and the **real savings rate** (savings rate after inflation). Each card shows
  the change from 12 months earlier.
- One plain-words sentence built from the numbers, e.g. *"Prices are rising 14.6% a year. A savings
  account pays 5.4%. Money in a savings account is losing about 8% of its value each year."*
- Short cards linking to each page and to the loan calculator.

### 2.2 My savings: "What is my money worth today?" (launch with this page)
Inputs at the top of the page:
- Amount (₦), default ₦100,000
- Start: month and year (from Jan 2006 to the latest month)
- Where it was kept (multi-select, all four on by default):
  1. **Savings account**: CBN average savings deposit rate, compounded monthly (rate ÷ 12).
  2. **12-month fixed deposit**: CBN 12-month deposit rate, rolled over each year at the rate then.
  3. **Treasury bills**: CBN T-bill rate, which is the 91-day bill: locked for 3 months, then rolled
     over at the rate then (as in `nigeria-savings-vs-inflation`).
  4. **Dollars**: converted to $ at the start month's official rate, held (no interest), converted
     back at the latest rate.
  5. Always shown as the baseline: **Under the mattress**: cash, earning nothing.

Outputs:
- For each option: value today in naira, and **value in today's prices** (deflated with the price
  index), with the % gained or lost in real terms.
- A line chart of real value over time, one line per option, a dashed line at the starting amount.
- A plain-words sentence, e.g. *"₦100,000 kept in a savings account since January 2006 is now
  ₦X. In today's prices, that buys what ₦Y bought then."*
- Caption: rates are CBN averages; real banks and accounts differ; taxes and fees not included.

### 2.3 Prices
- Headline, food and core inflation from 2003, with a date-range control and measure toggles.
- The forecast (precomputed, §4.3): the next 12 months with a range, clearly labelled as a range.
- A note on the January 2025 rebasing and the January 2026 revision.

### 2.4 The naira
- Official ₦/$ history (monthly average), linear/log toggle, the big jump months marked
  (> 5% weaker in a month).
- The 2030 outlook (precomputed, §4.3): 50% and 80% ranges for Sep 2027, Sep 2028 and Sep 2030.
- A scenario selector (stable reforms / history repeats / policy reversal / oil shock) showing each
  scenario's range.
- Caption: official rate only, not the parallel market; ranges are not predictions.

### 2.5 Borrowing
- Prime vs maximum lending rate with the gap shaded; the real lending rate; government's share of
  domestic credit.
- A prominent link to the loan calculator: "Work out your own loan →".

### Footer (every page)
"Educational, not financial advice. Data: Central Bank of Nigeria (and US BLS via FRED for the naira
page). Built by Freedom Oboh with Python and Streamlit." Links to GitHub, LinkedIn and the four
articles. (Ask me for the article links.)

---

## 3. Data

### 3.1 Sources
CBN undocumented JSON APIs (all values are strings; records are newest first):
- `https://www.cbn.gov.ng/api/GetAllInflationRates`: headline, food, core inflation
- `https://www.cbn.gov.ng/api/GetAllExchangeRates`: daily official rates → monthly average USD/NGN
- `https://www.cbn.gov.ng/api/GetAllMoneyMarketIndicators`: MPR, MRR, T-bill, savings and deposit
  rates, prime and maximum lending rates (monthly, Jan 2006 onward)
- `https://www.cbn.gov.ng/api/GetAllMoneyAndCreditStats`: credit to government and private sector, M2
- `https://www.cbn.gov.ng/api/GetAllDailyCrude`: crude price (for context and the forecast if used)
- US CPI: FRED series `CPIAUCSL` (for PPP on the naira page)

The four existing repos already hold this data to Sep 2026. Use them as the **reference snapshot**:
the pipeline's output for Sep 2026 must match them.

### 3.2 Known traps (each needs a fix and an "Under the hood" note)
- The CBN feed holds the NBS's **revised 2025 inflation** (Jan 2026 revision, ~3 points higher than
  first releases). Use the feed as is, and say so.
- **June 2025 inflation repeats May.** Interpolate it.
- **January 2025 CPI rebasing** breaks the series; note it on the Prices page.
- **MPR is 0 for Jan–Nov 2006.** Use the MRR before Dec 2006 as one `policy_rate` column.
- **T-bill 0.00 in Dec 2017 and Dec 2018.** Treat as missing.
- **Credit data: March 2026 missing.** Fill for charts only.
- **Credit to government below zero** for many months to 2014. Keep it (government was a net lender).
- **Exchange rates:** daily → monthly average; record how many days each month had.

### 3.3 Price index
Chained from CBN year-on-year headline inflation, exactly as in `nigeria-savings-vs-inflation`
(read that notebook and reproduce the method). Base = the latest month, so "today's prices" always
means the latest data month.

---

## 4. Pipeline and the monthly update

### 4.1 Layout
```
naija-money-dashboard/
├── CLAUDE.md
├── README.md
├── app/
│   ├── Home.py                 # entry point (st.navigation)
│   ├── pages/                  # savings.py, prices.py, naira.py, borrowing.py
│   └── components.py           # shared KPI cards, chart style, footer, "data up to" label
├── pipeline/
│   ├── fetch.py                # pull every source, save raw with the pull date
│   ├── clean.py                # all the fixes in §3.2, one function each
│   ├── build.py                # monthly panel + price index → data/processed/
│   ├── models.py               # precomputed forecast and naira outlook (§4.3)
│   ├── validate.py             # checks before anything is saved (§4.4)
│   └── run_all.py              # fetch → clean → build → models → validate
├── src/
│   └── money_math.py           # savings growth, deflating, rollovers; with _self_check()
├── data/
│   ├── raw/                    # latest pull per source (overwritten each month, dated in a manifest)
│   └── processed/              # what the app reads: panel.csv, forecast.csv, naira_outlook.csv, meta.json
├── .github/workflows/monthly.yml
├── .streamlit/config.toml
└── requirements.txt
```

### 4.2 The app never calls the CBN
The app only reads `data/processed/`. If the CBN site is down, the app still works.
`meta.json` holds the latest data month, the pull date, and row counts; the app shows "Data up to …"
from it.

### 4.3 Precomputed models (run in the pipeline, not in the app)
- **Inflation forecast:** port the final model from `nigeria-inflation-forecast` (read its notebook;
  keep the same method and its naive baseline). Save the next 12 months with a range.
- **Naira outlook:** port the calibrated jump model and the four scenarios from `naira-scenarios`.
  Save the 50% and 80% ranges for the standard dates and each scenario.
- **Reproduce the articles first:** on data up to Sep 2026 the outputs must match the published
  numbers within a small tolerance (e.g. Sep 2030 80% range about ₦1,090–₦6,870; the four scenario
  ranges). Fix the random seed. Show me the comparison.
- If a model can't be ported cleanly, tell me and propose the simplest honest alternative. Don't
  quietly change the method.

### 4.4 Validation before saving
`validate.py` must pass before anything in `data/processed/` is replaced:
- one row per month, no duplicates, no gaps except the known ones
- the new latest month is the same as or after the previous one (no going backwards)
- values in plausible ranges (e.g. inflation −5% to 60%, ₦/$ within 50% of last month)
- months up to Sep 2026 unchanged from the reference snapshot, except known revisions (which must be
  listed in the run log)
If validation fails, keep the old data and fail the run with a clear message.

### 4.5 GitHub Action (`.github/workflows/monthly.yml`)
- Runs on a schedule (around the 10th of each month) and manually (`workflow_dispatch`).
- Installs requirements, runs `python pipeline/run_all.py`.
- If `data/processed/` changed and validation passed, commits with a message like
  "Monthly data update: data up to October 2026". Streamlit Cloud redeploys on the push.
- If nothing changed, exits quietly. If it fails, the run shows red and the app keeps the old data.
- The CBN site may block requests from GitHub's servers. Test this early with a manual run. If it's
  blocked, tell me and suggest options; don't work around a block.

---

## 5. Look and feel
- White background, matching all my project charts. Navy text `#0F1E33`, blue `#2A6FDB`, orange
  `#D9822B` for highlights and "you", light grey gridlines. Plotly charts, no chart junk.
- Inputs on the page (in a bordered box at the top), never in the sidebar.
- Mobile first: check every page at phone width.
- Naira as ₦ with thousand separators; rates to at most 2 decimal places.
- Plain-words help text on every term (real rate, MPR, prime rate, PPP, range).

---

## 6. Build in phases (stop after each for my review)

1. **Pipeline + Home + My savings.** Fetch, clean, build, validate; `money_math.py` with self-checks;
   the Home and savings pages. Spot-check: ₦100,000 from Jan 2006 to Sep 2026 reproduces the savings
   article for every option (savings account ₦208,347 = ₦13,459 in Jan 2006 naira; cash ₦6,460;
   fixed deposit ₦37,648; T-bills ₦39,887; dollars ₦66,701). Deploy to Streamlit Cloud.
2. **Prices + The naira.** Port the models, reproduce the article numbers, build both pages.
3. **Borrowing + the monthly GitHub Action.** Test the Action with a manual run.
4. **Polish:** README in my storytelling style, screenshots, accessibility and phone checks.

## 7. Checks for every phase
- `python src/money_math.py` and `python pipeline/run_all.py` pass.
- Every number on screen comes from `data/processed/`, never typed in.
- Silly inputs (₦0, start month after end month) give friendly messages, not errors.
- Every page works at phone width.
- Commit after each phase; ask me before pushing.

## 8. Ask me before you start
1. The four article links for the footer.
2. The Streamlit app address you'd like (e.g. money-matters-ng.streamlit.app), if it's available.
3. Anything unclear in the old notebooks: ask, don't guess.
