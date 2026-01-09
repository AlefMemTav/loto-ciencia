# pages/7_Registro.py
"""Página de Registro"""
import streamlit as st
from app.auth.api_client import APIClient
from app.ui.core.styles import apply_custom_css


st.set_page_config(
    page_title="Criar Conta - LotoScience", page_icon="📝", layout="centered"
)
apply_custom_css()
APIClient.init()
# ===== REDIRECIONA SE JÁ ESTÁ LOGADO =====
if APIClient.is_authenticated():
    st.success(f"✅ Você já possui uma conta: {st.session_state.user_email}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏠 Ir para Painel", use_container_width=True):
            st.switch_page("pages/1_Painel.py")
    with col2:
        if st.button("🚪 Sair e criar nova conta", use_container_width=True):
            APIClient.logout()
            st.rerun()

    st.stop()

# ===== FORMULÁRIO DE REGISTRO =====
st.title("📝 Criar Conta Grátis")
st.markdown("Cadastre-se para ter acesso completo ao sistema.")

with st.form("register_form"):
    email = st.text_input("📧 E-mail", placeholder="seu@email.com")
    password = st.text_input(
        "🔒 Senha", type="password", placeholder="Mínimo 6 caracteres"
    )
    password_confirm = st.text_input(
        "🔒 Confirmar Senha", type="password", placeholder="Repita sua senha"
    )

    st.markdown("---")
    st.caption("✅ **Plano FREE inclui:**")
    st.caption("• 1 validação por dia")
    st.caption("• 1 geração de jogos por dia")
    st.caption("• Acesso ao painel de estatísticas")

    col1, col2 = st.columns(2)
    with col1:
        submit = st.form_submit_button(
            "Criar Conta", type="primary", use_container_width=True
        )
    with col2:
        cancel = st.form_submit_button("Cancelar", use_container_width=True)

    if cancel:
        st.switch_page("pages/0_Inicio.py")

    if submit:
        # Validações
        if not email or not password or not password_confirm:
            st.error("❌ Preencha todos os campos")
        elif len(password) < 6:
            st.error("❌ A senha deve ter pelo menos 6 caracteres")
        elif password != password_confirm:
            st.error("❌ As senhas não coincidem")
        elif email == "demo@lotoscience.com":
            st.error("❌ Este e-mail é reservado para o usuário demo. Escolha outro.")
        else:
            with st.spinner("Criando conta..."):
                success, message, data = APIClient.register(email, password)

                if success:
                    st.success(message)
                    st.balloons()
                    st.info("🎉 Conta criada! Você já está logado.")

                    # Aguarda um pouco
                    import time

                    time.sleep(1)

                    # Redireciona para o Painel
                    st.switch_page("pages/1_Painel.py")
                else:
                    st.error(f"❌ {message}")

st.markdown("---")

st.markdown("**Já tem conta?**")
if st.button("🔐 Fazer Login", use_container_width=True):
    st.switch_page("pages/6_Login.py")

st.markdown("---")
st.markdown("**👑 Quer recursos ilimitados?**")
st.caption("Faça upgrade para o Plano PRO após criar sua conta.")
if st.button("Ver Planos", use_container_width=True):
    st.switch_page("pages/8_Planos.py")
