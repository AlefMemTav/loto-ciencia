# app/ui/core/shell.py
import streamlit as st
from app.ui.core.styles import apply_custom_css
from app.ui.components.header import render_app_header
from app.ui.components.nav import top_nav
from app.ui.core.state import load_context, init_game_state
from app.ui.components.sidebar import render_game_selector, render_auth_status
from app.ui.services.auth_client import AUTHClient


def init_page(
    title: str,
    icon: str = "🧬",
    require_auth: bool = False,
    require_pro: bool = False,
    resource_usage: str = None,  # Ex: "generator", "validator"
):
    """
    Inicializa o 'Shell' da aplicação:
    Configura CSS, Auth, Sidebar, Header, Nav e Carrega Contexto.

    Retorna:
        ctx: O contexto do jogo (dados, config)
        svc: O serviço de loteria instanciado
    """
    # 1. Configuração Básica e Estilos
    st.set_page_config(
        page_title=f"{title} | LotoScience", layout="wide", page_icon=icon
    )
    apply_custom_css()

    # 2. Inicialização de Estado e Auth
    init_game_state()
    AUTHClient.init()

    # 3. Renderiza a Sidebar (Status de Auth)
    render_auth_status()

    # 4. Barreira de Autenticação (Login Wall)
    if require_auth and not AUTHClient.is_authenticated():
        _render_lock_screen(title)
        st.stop()

    # 5. Barreira de Plano (Paywall - Pro Only)
    if require_pro and not AUTHClient.is_pro():
        _render_paywall_screen()
        st.stop()

    # 6. Verificação de Rate Limit (Uso Diário para Free)
    if resource_usage:
        can_use, message = AUTHClient.check_rate_limit(resource_usage)
        if message and "🔒" not in message:  # Ignora msg de login se já passou
            st.info(message)

        if not can_use:
            _render_rate_limit_screen()
            st.stop()

    # 7. Se passou por tudo, carrega os dados
    ctx, svc = load_context()

    # 8. Renderiza Elementos Comuns de UI
    render_app_header(ctx.config, ctx.df)
    top_nav()
    render_game_selector()

    return ctx, svc


# --- Telas de Bloqueio Auxiliares ---


def _render_lock_screen(feature_name):
    st.warning(f"🔒 Faça login para acessar: {feature_name}")
    st.markdown("### 🚀 Recursos Exclusivos")
    st.markdown(
        "- Algoritmos avançados\n- Histórico completo\n- Ferramentas profissionais"
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔐 Fazer Login", use_container_width=True):
            st.switch_page("pages/6_Login.py")
    with c2:
        if st.button("📝 Criar Conta", use_container_width=True):
            st.switch_page("pages/7_Registro.py")


def _render_paywall_screen():
    st.error("👑 Este recurso é exclusivo para assinantes PRO")
    st.markdown("Desbloqueie validações ilimitadas, fechamentos e muito mais.")
    if st.button("🚀 Ver Planos e Upgrade", type="primary", use_container_width=True):
        st.switch_page("pages/8_Planos.py")


def _render_rate_limit_screen():
    st.error("⛔ Limite diário gratuito atingido.")
    st.markdown(
        """
        **Você atingiu seu limite diário para esta ferramenta.**
        
        Faça upgrade para o plano **PRO** e tenha acesso ilimitado agora mesmo.
        """
    )
    if st.button("💎 Virar PRO Agora", type="primary"):
        st.switch_page("pages/8_Planos.py")
