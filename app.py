"""受付日誌 入力システム - Streamlit エントリポイント"""

import streamlit as st

st.set_page_config(
    page_title="受付日誌 入力システム",
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed",
)

pages = [
    st.Page("pages/1_📝_入力.py",  title="📝 入力",  icon="📝", default=True),
    st.Page("pages/2_📋_履歴.py",  title="📋 履歴",  icon="📋"),
    st.Page("pages/3_⚙️_設定.py",  title="⚙️ 設定",  icon="⚙️"),
]

pg = st.navigation(pages)
pg.run()
