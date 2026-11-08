# app/ui/components/sidebar.py
import streamlit as st
from app.core.lottery import GAMES
from app.ui.core.state import GLOBAL_KEY, WIDGET_KEY, sync_widget_to_global


def render_game_selector():
    if WIDGET_KEY not in st.session_state:
        st.session_state[WIDGET_KEY] = list(GAMES.keys())[0]
    """Seletor de jogo com segmented control"""
    jogos = list(GAMES.keys())

    st.segmented_control(
        "Jogo",
        options=jogos,
        format_func=lambda k: GAMES[k].name,
        key=WIDGET_KEY,
        on_change=sync_widget_to_global,
    )

    # Exibe informações do jogo selecionado (mantendo estilo original)
    slug = st.session_state.get(GLOBAL_KEY, jogos[0])
    config = GAMES[slug]

    st.caption(
        f"{config.name}: {config.n_numbers} números • aposta de {config.bet_size} • {config.odds_text}"
    )
    st.caption(config.how_to_play)
