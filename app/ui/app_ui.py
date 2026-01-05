import streamlit as st
from scipy.stats import poisson

from app.src.data_loader import carregar_dados_loteria_excel
from app.src.games import GAMES
from app.src.statistics import get_numeros_quentes_frios
from app.src.statistics import analise_poisson
from app.ui.bolao_ui import render_bolao
from app.ui.closures_ui import render_closures
from app.ui.generator_ui import render_generator
from app.ui.styles import apply_custom_css
from app.ui.validator_ui import render_validator
from app.ui.dashboard_ui import render_dashboard


def render_app_logic():

    apply_custom_css()

    # seletor moderno: cartões clicáveis (botões em grade)
    jogos = list(GAMES.keys())
    if "selected_game" not in st.session_state:
        st.session_state.selected_game = jogos[0]

    n_cols = 3  # ajuste para número de colunas por linha
    for i in range(0, len(jogos), n_cols):
        row_keys = jogos[i : i + n_cols]
        cols = st.columns(len(row_keys) * 2)  # colunas duplas para espaçamento
        for col, key in zip(cols, row_keys):
            game = GAMES[key]
            # botão que seleciona o jogo; label visível como um "cartão"
            if col.button(game.name, key=f"game_btn_{key}"):
                st.session_state.selected_game = key
            # descrição opcional do jogo (se existir)
            if hasattr(game, "description"):
                col.caption(getattr(game, "description"))

    slug = st.session_state.selected_game
    config = GAMES[slug]

    df = carregar_dados_loteria_excel(config, f"data/{slug}.xlsx")

    if df.empty:
        st.warning("Aguardando dados... Verifique o arquivo Excel.")
        st.stop()

    freq = get_numeros_quentes_frios(df, config)
    poisson_finais = analise_poisson(df, config, 0.05)

    c1, c2 = st.columns([2, 4])
    with c1:
        st.write("**LotoScience**")
    with c2:
        # Saudação ou Status
        st.caption(
            f"Base de Dados ({config.name}) Atualizada: {len(df)} concursos analisados."
        )
    st.markdown("---")

    abas = st.tabs(
        [
            "🏠 Início",
            "✅ Validar Jogo",
            "🤖 Gerador Inteligente",
            "📦 Fechamentos",
            "👥 Análise de Bolão",
        ]
    )

    with abas[0]:
        render_dashboard(df, freq, poisson_finais, config)
    with abas[1]:
        render_validator(df, config)

    with abas[2]:
        render_generator(df, freq, poisson_finais, config)

    with abas[3]:
        render_closures(config)

    with abas[4]:
        render_bolao(df, config)
