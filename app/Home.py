"""(+234) Money Matters: the entry point. Run with:  streamlit run app/Home.py"""

import streamlit as st

from components import APP_NAME, inject_css

st.set_page_config(page_title=APP_NAME, page_icon="₦", layout="wide", initial_sidebar_state="collapsed")
inject_css()

pages = [
    st.Page("views/home.py", title=APP_NAME, default=True),
    st.Page("views/savings.py", title=f"My savings · {APP_NAME}", url_path="savings"),
    st.Page("views/loan.py", title=f"My loan · {APP_NAME}", url_path="loan"),
    st.Page("views/prices.py", title=f"Prices · {APP_NAME}", url_path="prices"),
    st.Page("views/naira.py", title=f"The naira · {APP_NAME}", url_path="naira"),
    st.Page("views/borrowing.py", title=f"Borrowing · {APP_NAME}", url_path="borrowing"),
]
# Streamlit's own menu is hidden: each page draws the brand header with its tabs (components.brand_header).
# The page files live in app/views/, NOT app/pages/: Streamlit auto-loads a "pages" folder as old-style pages,
# and a visitor opening a deep link (e.g. /prices) on a fresh server would get an unstyled page.
st.navigation(pages, position="hidden").run()
