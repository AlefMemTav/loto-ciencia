# pages/8_Planos.py
import streamlit as st
from app.ui.services.auth_client import AUTHClient
from app.ui.core.styles import apply_custom_css
from app.ui.views.auth import render_plans_view

st.set_page_config(page_title="Planos", page_icon="👑", layout="centered")
apply_custom_css()
AUTHClient.init()

render_plans_view()
