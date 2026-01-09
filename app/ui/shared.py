# app/ui/shared.py

import streamlit as st
import pandas as pd
from app.core.lottery import GAMES
from app.services.lottery_service import LotteryService
from app.core.logger import logger

GLOBAL_KEY = "selected_game"
WIDGET_KEY = "selected_game_widget"


@st.cache_resource
def get_service():
    return LotteryService()


def init_game_state():
    jogos = list(GAMES.keys())
    if GLOBAL_KEY not in st.session_state or st.session_state[GLOBAL_KEY] not in jogos:
        st.session_state[GLOBAL_KEY] = jogos[0]
    if WIDGET_KEY not in st.session_state or st.session_state[WIDGET_KEY] not in jogos:
        st.session_state[WIDGET_KEY] = st.session_state[GLOBAL_KEY]


def _sync_widget_to_global():
    novo_jogo = st.session_state[WIDGET_KEY]
    if novo_jogo != st.session_state.get(GLOBAL_KEY):
        logger.info(f"Troca de contexto: Usuário mudou para {novo_jogo}")
        st.session_state[GLOBAL_KEY] = novo_jogo


def render_auth_status():
    """
    Renderiza status minimalista na sidebar
    """
    from app.auth.api_client import APIClient

    st.sidebar.markdown("---")

    if APIClient.is_authenticated():
        email = st.session_state.get("user_email", "Usuário")
        plan = st.session_state.get("user_plan", "free")

        # Email compacto
        st.sidebar.caption(f"👤 {email}")

        # Badge do plano
        if plan == "pro":
            st.sidebar.markdown(
                '<span style="background: linear-gradient(90deg, #fbbf24, #f59e0b); '
                "padding: 4px 12px; border-radius: 12px; font-size: 0.75rem; "
                'font-weight: 700; color: #000;">👑 PRO</span>',
                unsafe_allow_html=True,
            )
        else:
            st.sidebar.markdown(
                '<span style="background: #e5e7eb; padding: 4px 12px; '
                "border-radius: 12px; font-size: 0.75rem; font-weight: 600; "
                'color: #374151;">🆓 FREE</span>',
                unsafe_allow_html=True,
            )
            st.sidebar.caption("⚡ 1 validação/geração por dia")
            if st.sidebar.button(
                "⬆️ Upgrade", key="sidebar_upgrade", use_container_width=True
            ):
                st.switch_page("pages/8_Planos.py")

        st.sidebar.markdown("")  # espaçamento

        if st.sidebar.button("🚪 Sair", key="sidebar_logout", use_container_width=True):
            APIClient.logout()
            st.rerun()

    else:
        st.sidebar.caption("🔒 **Faça login**")
        st.sidebar.caption("Acesse validador e gerador")

        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("Entrar", key="sidebar_login", use_container_width=True):
                st.switch_page("pages/6_Login.py")
        with col2:
            if st.button(
                "Cadastro",
                key="sidebar_register",
                use_container_width=True,
                type="primary",
            ):
                st.switch_page("pages/7_Registro.py")


def render_game_selector():
    """Seletor de jogo com segmented control"""
    jogos = list(GAMES.keys())
    st.segmented_control(
        "Jogo",
        options=jogos,
        format_func=lambda k: GAMES[k].name,
        key=WIDGET_KEY,
        on_change=_sync_widget_to_global,
    )

    slug = st.session_state[GLOBAL_KEY]
    config = GAMES[slug]
    st.caption(
        f"{config.name}: {config.n_numbers} números • aposta de {config.bet_size} • {config.odds_text}"
    )
    st.caption(config.how_to_play)


def load_context():
    """
    Carrega o contexto via LotteryService.
    Retorna: (ctx, svc) onde ctx é o GameContext
    """
    slug = st.session_state[GLOBAL_KEY]
    svc = get_service()

    try:
        ctx = svc.get_context(slug)
    except Exception as e:
        st.error(f"Erro ao carregar contexto: {e}")
        st.stop()

    if ctx.df is None or ctx.df.empty:
        st.warning("Aguardando dados...")
        st.stop()

    return ctx, svc
