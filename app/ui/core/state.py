# app/ui/core/state.py
"""Gerenciamento de estado global do jogo selecionado"""
import streamlit as st
from app.services.lottery_service import LotteryService
from app.core.lottery import GAMES
from app.core.logger import logger

GLOBAL_KEY = "selected_game"
WIDGET_KEY = "selected_game_widget"


@st.cache_resource
def get_service():
    """Singleton do serviço de loteria cacheado pelo Streamlit"""
    return LotteryService()


def init_game_state():
    """Garante que as chaves de sessão existam"""
    jogos = list(GAMES.keys())

    if GLOBAL_KEY not in st.session_state or st.session_state[GLOBAL_KEY] not in jogos:
        st.session_state[GLOBAL_KEY] = jogos[0]

    if WIDGET_KEY not in st.session_state or st.session_state[WIDGET_KEY] not in jogos:
        st.session_state[WIDGET_KEY] = st.session_state[GLOBAL_KEY]


def sync_widget_to_global():
    """Callback: Sincroniza o seletor visual com a variável global"""
    novo_jogo = st.session_state[WIDGET_KEY]
    if novo_jogo != st.session_state.get(GLOBAL_KEY):
        logger.info(f"Troca de contexto: Usuário mudou para {novo_jogo}")
        st.session_state[GLOBAL_KEY] = novo_jogo


def load_context():
    """
    Carrega o contexto via LotteryService.
    Retorna: (ctx, svc) onde ctx é o GameContext
    """
    # Garante inicialização antes de carregar
    init_game_state()

    slug = st.session_state[GLOBAL_KEY]
    svc = get_service()

    # Retorna contexto + serviço (para chamadas futuras)
    return svc.get_context(slug), svc
