# (+234) Money Matters

**Understand what the economy is doing to your money.**
*Nigeria's economy, through the numbers.*

Money Matters is a data-driven platform that helps Nigerians understand how the economy affects
their everyday finances. It brings together key economic indicators such as inflation, exchange
rates, interest rates, savings and borrowing into one interactive dashboard. Users can explore
historical trends, understand how the value of their money has changed over time, compare
financial scenarios, and see what the numbers mean for their personal and business decisions.
The platform brings together data from multiple research projects into one place, with regular
monthly updates.

> Work in progress. Phase 1 (data pipeline, Home, My savings) is built. The full README comes in Phase 4.

## Run it on your computer

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt

python pipeline/run_all.py      # pull the latest CBN data, check it, rebuild data/processed/
python src/money_math.py        # self-check: reproduces the savings article
streamlit run app/Home.py       # open the app at http://localhost:8501
```

`python pipeline/run_all.py --offline` rebuilds from the raw files already saved, without downloading.

Educational, not financial advice. Data: Central Bank of Nigeria. Built by Freedom Oboh with Python and Streamlit.
