import streamlit as st
from app.src.games import GAMES
from app.src.data_loader import carregar_dados_loteria_excel
from app.src.statistics import get_numeros_quentes_frios, analise_poisson

GLOBAL_KEY = "selected_game"  # fonte da verdade (persistente entre páginas)
WIDGET_KEY = "selected_game_widget"  # estado do widget (para UI)


def init_game_state():
    jogos = list(GAMES.keys())

    # 1) garante o global
    if GLOBAL_KEY not in st.session_state or st.session_state[GLOBAL_KEY] not in jogos:
        st.session_state[GLOBAL_KEY] = jogos[0]

    # 2) garante o widget (o que aparece marcado)
    if WIDGET_KEY not in st.session_state or st.session_state[WIDGET_KEY] not in jogos:
        st.session_state[WIDGET_KEY] = st.session_state[GLOBAL_KEY]


def _sync_widget_to_global():
    # callback: roda quando o usuário muda o widget
    st.session_state[GLOBAL_KEY] = st.session_state[WIDGET_KEY]


@st.cache_data()
def _compute_context(slug: str):
    config = GAMES[slug]
    df = carregar_dados_loteria_excel(config, f"data/{slug}.xlsx")
    if df.empty:
        return df, None, None, config
    freq = get_numeros_quentes_frios(df, config)
    poisson_finais = analise_poisson(df, config, 0.05)
    return df, freq, poisson_finais, config


def render_game_selector():
    # init_game_state()

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
        f"{config.name}: {config.n_numbers} números • aposta de {config.k} • {config.odds_text}"
    )


def load_context():
    slug = st.session_state[GLOBAL_KEY]
    df, freq, poisson_finais, config = _compute_context(slug)

    if df is None or df.empty:
        st.warning("Aguardando dados... Verifique o arquivo Excel.")
        st.stop()

    return df, freq, poisson_finais, config
