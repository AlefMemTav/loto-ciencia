# pages/7_Registro.py
import streamlit as st
from app.ui.services.auth_client import AUTHClient
from app.ui.core.styles import apply_custom_css
from app.ui.views.auth import render_register_view

st.set_page_config(page_title="Criar Conta", page_icon="📝", layout="centered")
apply_custom_css()
AUTHClient.init()

if AUTHClient.is_authenticated():
    st.switch_page("pages/1_Painel.py")

render_register_view()
