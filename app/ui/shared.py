# app/ui/shared.py
import streamlit as st
import pandas as pd

from app.src.games import GAMES
from app.services.lottery_service import LotteryService
from app.src.logger import logger

GLOBAL_KEY = "selected_game"
WIDGET_KEY = "selected_game_widget"


# Instância única do service (cache implícito via lru_cache no service)
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


def render_game_selector():
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
