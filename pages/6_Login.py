# pages/6_Login.py
"""Página de Login"""
import streamlit as st
from app.auth.api_client import APIClient
from app.ui.core.styles import apply_custom_css

st.set_page_config(page_title="Login - LotoScience", page_icon="🔐", layout="centered")
apply_custom_css()
APIClient.init()
if APIClient.is_authenticated():
    st.success(f"✅ Você já está logado como {st.session_state.user_email}")

    plan_emoji = "👑" if st.session_state.user_plan == "pro" else "🆓"
    st.info(f"{plan_emoji} **Plano:** {st.session_state.user_plan.upper()}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏠 Ir para Painel", use_container_width=True):
            st.switch_page("pages/1_Painel.py")
    with col2:
        if st.button("🚪 Sair", use_container_width=True):
            APIClient.logout()
            st.rerun()

    st.stop()

# ===== FORMULÁRIO DE LOGIN =====
st.title("🔐 Login")
st.markdown("Entre na sua conta para acessar todas as funcionalidades.")

with st.form("login_form"):
    email = st.text_input("📧 E-mail", placeholder="seu@email.com")
    password = st.text_input("🔒 Senha", type="password", placeholder="Sua senha")

    col1, col2 = st.columns(2)
    with col1:
        submit = st.form_submit_button(
            "Entrar", type="primary", use_container_width=True
        )
    with col2:
        cancel = st.form_submit_button("Cancelar", use_container_width=True)

    if cancel:
        st.switch_page("pages/0_Inicio.py")

    if submit:
        if not email or not password:
            st.error("❌ Preencha todos os campos")
        else:
            with st.spinner("Entrando..."):
                success, message, data = APIClient.login(email, password)

                if success:
                    st.success(message)
                    st.balloons()

                    # Aguarda um pouco para usuário ver a mensagem
                    import time

                    time.sleep(1)

                    # Redireciona para o Painel (NÃO para login novamente)
                    st.switch_page("pages/1_Painel.py")
                else:
                    st.error(f"❌ {message}")

st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Não tem conta?**")
    if st.button("📝 Criar Conta Grátis", use_container_width=True):
        st.switch_page("pages/7_Registro.py")

with col2:
    st.markdown("**Esqueceu a senha?**")
    st.caption("Em breve: recuperação de senha")

# Usuário demo
st.info(
    """
**💡 Teste sem cadastro:**
- E-mail: `demo@lotoscience.com`
- Senha: `demo123`
- Plano: **Pro** (recursos ilimitados)
"""
)
