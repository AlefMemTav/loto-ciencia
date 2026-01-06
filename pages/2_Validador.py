import streamlit as st
from app.ui.header import render_app_header
from app.ui.nav import top_nav
from app.ui.page_config import apply_page_config
from app.ui.styles import apply_custom_css
from app.ui.shared import init_game_state, load_context, render_game_selector
from app.ui.validator_ui import render_validator

apply_page_config()
apply_custom_css()
init_game_state()
df, freq, poisson_finais, config = load_context()
render_app_header(config, df)
top_nav()
render_game_selector()
render_validator(df, config)
