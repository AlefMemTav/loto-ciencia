import streamlit as st


def apply_page_config():
    st.set_page_config(
        page_title="LotoScience - A Ciência da Loteria",
        page_icon="🧬",
        layout="wide",
        initial_sidebar_state="collapsed",  # Options: "auto", "expanded", "collapsed",
        menu_items=None,
    )
