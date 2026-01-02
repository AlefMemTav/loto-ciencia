import streamlit as st
import pandas as pd
from scipy.stats import poisson
import matplotlib.pyplot as plt

from app.src.data_loader import carregar_dados_mega_sena
from app.src.data_loader import filtrar_mega_virada
from app.src.statistics import get_numeros_quentes_frios
from app.src.statistics import analise_poisson
from app.src.validator import validar_jogo
from app.ui.bolao_ui import render_bolao
from app.ui.closures_ui import render_closures
from app.ui.generator_ui import render_generator
from app.ui.validator_ui import render_validator
from app.ui.dashboard_ui import render_dashboard

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="LotoScience Virada", page_icon="🎱", layout="wide")

# CSS Customizado
st.markdown(
    """
    <style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    .success-box { padding:15px; background-color:#d4edda; color:#155724; border-radius:10px; }
    .warning-box { padding:15px; background-color:#fff3cd; color:#856404; border-radius:10px; }
    .error-box { padding:15px; background-color:#f8d7da; color:#721c24; border-radius:10px; }
    </style>
""",
    unsafe_allow_html=True,
)


# --- INTERFACE VISUAL ---
def main():
    df = carregar_dados_mega_sena()

    if df.empty:
        st.warning("Aguardando dados... Verifique o arquivo Excel.")
        st.stop()  # Para a execução se não tiver dados

    freq = get_numeros_quentes_frios(df)
    poisson_finais = analise_poisson(df, 0.05)

    # Novo Bloco: Switch para Análise Específica
    modo_analise = st.radio(
        "Base de Dados para Análise:",
        ["Todos os Jogos (Histórico Completo)", "Apenas Mega da Virada 🥂"],
    )

    if modo_analise == "Apenas Mega da Virada 🥂":
        st.info(
            "⚠️ A amostra da Mega da Virada é pequena (~15 jogos). Cuidado com padrões ilusórios."
        )
        freq_virada, df_virada = filtrar_mega_virada(df)

        if not freq_virada.empty:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### 🥂 Reis da Virada")
                st.caption("Números que mais saíram em 31/dez")
                st.bar_chart(freq_virada.head(10))
                st.write(
                    f"O número **{freq_virada.index[0]}** saiu {freq_virada.iloc[0]} vezes."
                )
            with c2:
                st.markdown("### ❄️ Gelados na Virada")
                st.caption("Nunca saíram na Virada")
                nunca_sairam = [n for n in range(1, 61) if n not in freq_virada.index]
                st.write(f"Lista: {nunca_sairam}")

        # Substitui a freq usada no gerador pela freq_virada se quiser "forçar" a tendência
        # freq = freq_virada (Opcional, se quiser que o gerador use só dados da virada)
    else:
        # Mostra o gráfico padrão que já estava no código
        pass

    st.title("🏆 LotoScience: A Estratégia da Virada")
    st.write("Não é Sorte 🍀🙅‍♂️, é Ciência 🤓")
    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "📊 Dashboard de Tendências",
            "🧪 Validador de Jogos",
            "🤖 Gerador Híbrido",
            "📦 Gerador de Fechamentos",
            "👥 Análise de Bolão",
        ]
    )

    with tab1:
        render_dashboard(df, freq, poisson_finais)
    with tab2:
        render_validator(df)

    with tab3:
        render_generator(freq, poisson_finais)

    with tab4:
        render_closures()

    with tab5:
        render_bolao()


if __name__ == "__main__":
    main()
