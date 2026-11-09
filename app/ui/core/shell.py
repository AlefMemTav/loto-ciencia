# app/ui/core/shell.py
import streamlit as st
from app.ui.core.styles import apply_custom_css
from app.ui.components.header import render_app_header
from app.ui.components.nav import top_nav
from app.ui.core.state import load_context, init_game_state
from app.ui.components.sidebar import render_game_selector


def init_page(title: str, icon: str = "🧬"):
    st.set_page_config(
        page_title=f"{title} | LotoCiencia",
        layout="wide",
        page_icon=icon,
        initial_sidebar_state="collapsed",
    )
    apply_custom_css()
    init_game_state()

    ctx, svc = load_context()

    render_app_header(ctx.config, ctx.df)
    top_nav()
    render_game_selector()

    return ctx, svc
