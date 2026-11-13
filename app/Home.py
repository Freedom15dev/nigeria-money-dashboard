"""(+234) Money Matters: the entry point. Run with:  streamlit run app/Home.py"""

import streamlit as st

from components import APP_NAME, base_css

st.set_page_config(page_title=APP_NAME, page_icon="₦", layout="centered", initial_sidebar_state="collapsed")
base_css()

pages = [
    st.Page("pages/home.py", title="Home", icon="🏠", default=True),
    st.Page("pages/savings.py", title="My savings", icon="💰", url_path="savings"),
    # Phase 2: Prices, The naira. Phase 3: Borrowing.
]
st.navigation(pages, position="top").run()
