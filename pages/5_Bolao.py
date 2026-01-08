# pages/5_Bolao.py
from app.ui.header import render_app_header
from app.ui.nav import top_nav
from app.ui.page_config import apply_page_config
from app.ui.styles import apply_custom_css
from app.ui.shared import (
    init_game_state,
    load_context,
    render_game_selector,
    render_auth_status,
)
from app.ui.bolao_ui import render_bolao
from app.middleware.access_control import require_pro
import streamlit as st
from app.auth.api_client import APIClient

apply_page_config()
apply_custom_css()
APIClient.init()
init_game_state()

render_auth_status()


@require_pro
def render_page():
    ctx, svc = load_context()
    render_app_header(ctx.config, ctx.df)
    top_nav()
    render_game_selector()
    render_bolao(ctx, svc)


render_page()
