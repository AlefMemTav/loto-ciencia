import streamlit as st
from scipy.stats import poisson

from app.src.data_loader import carregar_dados_mega_sena
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

    df = carregar_dados_mega_sena()

    if df.empty:
        st.warning("Aguardando dados... Verifique o arquivo Excel.")
        st.stop()

    freq = get_numeros_quentes_frios(df)
    poisson_finais = analise_poisson(df, 0.05)

    c1, c2 = st.columns([2, 4])
    with c1:
        st.write("**LotoScience**")
    with c2:
        # Saudação ou Status
        st.caption(f"Base de Dados Atualizada: {len(df)} concursos analisados.")
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
        render_dashboard(df, freq, poisson_finais)
    with abas[1]:
        render_validator(df)

    with abas[2]:
        render_generator(df, freq, poisson_finais)

    with abas[3]:
        render_closures()

    with abas[4]:
        render_bolao(df)
