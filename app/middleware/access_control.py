# app/middleware/access_control.py
"""
Middleware de controle de acesso para Streamlit.
"""
import streamlit as st
from functools import wraps
from app.auth.api_client import APIClient


def require_auth(func):
    """Decorator: exige autenticação"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not APIClient.is_authenticated():
            st.warning("🔒 Faça login para acessar esta página")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔐 Fazer Login", use_container_width=True):
                    st.switch_page("pages/6_Login.py")
            with col2:
                if st.button("📝 Criar Conta", use_container_width=True):
                    st.switch_page("pages/7_Registro.py")

            st.stop()
        return func(*args, **kwargs)

    return wrapper


def require_pro(func):
    """Decorator: exige plano Pro"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not APIClient.is_pro():
            st.error("👑 Recurso exclusivo para usuários Pro")

            st.markdown(
                """
            ### ✨ Desbloqueie o Poder Completo
            
            **Com o plano PRO você tem:**
            - ✅ Validador ilimitado
            - ✅ Gerador ilimitado
            - ✅ Fechamentos avançados
            - ✅ Sistema de bolão completo
            - ✅ Estatísticas sem restrições
            
            **Apenas R$ 9/mês**
            """
            )

            if st.button("🚀 Fazer Upgrade", type="primary", use_container_width=True):
                st.switch_page("pages/8_Planos.py")

            st.stop()
        return func(*args, **kwargs)

    return wrapper


def preview_mode(full_content_func, preview_content_func):
    """
    Renderiza preview para Free, conteúdo completo para Pro
    """
    if APIClient.is_pro():
        full_content_func()
    else:
        preview_content_func()
        st.info("👁️ **Modo Preview** - Upgrade para Pro para ver tudo!")
        if st.button("👑 Ver Planos", key="preview_upgrade"):
            st.switch_page("pages/8_Planos.py")
