# pages/3_Gerador.py

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
from app.ui.generator_ui import render_generator
from app.auth.api_client import APIClient
import streamlit as st

# Configuração inicial
apply_page_config()
apply_custom_css()
APIClient.init()
init_game_state()

# Status de autenticação na sidebar
render_auth_status()

# ✅ EXIGE LOGIN
if not APIClient.is_authenticated():
    st.warning("🔒 Faça login para usar o Gerador.")
    st.markdown(
        """
        ### 🎲 Recursos do Gerador:
        - ✅ Algoritmo estatístico avançado
        - ✅ Múltiplas estratégias (conservadora, agressiva, balanceada)
        - ✅ Garantia de diversidade
        - ✅ Validação automática de qualidade
        
        **Crie uma conta gratuita e gere 1 jogo por dia!**
        """
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📝 Criar Conta Grátis", use_container_width=True):
            st.switch_page("pages/7_Registro.py")
    with col2:
        if st.button("🔐 Login", use_container_width=True):
            st.switch_page("pages/6_Login.py")
    with col3:
        if st.button("👑 Ver Plano PRO", type="primary", use_container_width=True):
            st.switch_page("pages/8_Planos.py")
    st.stop()

# ✅ VERIFICA rate limit
can_use, message = APIClient.check_rate_limit("generator")

if message:
    st.info(message)

if not can_use:
    st.error("⛔ Limite diário atingido. Volte amanhã ou faça upgrade para PRO.")
    st.markdown(
        """
        ### 👑 Upgrade para PRO
        - ✅ Gerações ilimitadas
        - ✅ Validações ilimitadas
        - ✅ Fechamentos avançados
        - ✅ Sistema de bolão
        
        **Apenas R$ 9/mês**
        """
    )
    if st.button("🚀 Fazer Upgrade Agora", type="primary", use_container_width=True):
        st.switch_page("pages/8_Planos.py")
    st.stop()

# ===== RENDERIZAÇÃO =====
ctx, svc = load_context()
render_app_header(ctx.config, ctx.df)
top_nav()
render_game_selector()
render_generator(ctx, svc)
