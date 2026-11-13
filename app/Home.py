"""(+234) Money Matters: the entry point. Run with:  streamlit run app/Home.py"""

import streamlit as st

from components import APP_NAME, inject_css

st.set_page_config(page_title=APP_NAME, page_icon="₦", layout="wide", initial_sidebar_state="collapsed")
inject_css()

pages = [
    st.Page("pages/home.py", title=APP_NAME, default=True),
    st.Page("pages/savings.py", title=f"My savings · {APP_NAME}", url_path="savings"),
    # Phase 2: Prices, The naira. Phase 3: Borrowing.
]
# Streamlit's own menu is hidden: each page draws the brand header with its tabs (components.brand_header).
st.navigation(pages, position="hidden").run()
