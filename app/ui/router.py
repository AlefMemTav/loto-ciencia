import streamlit as st
from app.ui.app_ui import render_app_logic
from app.ui.landing_ui import render_landing_page, render_como_funciona


def router():
    if "page" not in st.session_state:
        st.session_state.page = "landing"

    if st.session_state.page == "landing":
        render_landing_page()
    elif st.session_state.page == "how":
        render_como_funciona()
    else:
        render_app_logic()
