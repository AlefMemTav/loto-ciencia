# app/pages/validador_em_acao.py
import streamlit as st
from datetime import datetime
from app.services.lottery_service import LotteryService
from app.ui.core.styles import apply_custom_css


@st.cache_data(ttl=86400)
def validar_sorteio_cached(slug: str, concurso: int, numeros_tuple: tuple):
    """Valida um sorteio e cacheia o resultado por 1 dia (86400 segundos)"""
    service = LotteryService()
    numeros = list(numeros_tuple)
    return service.validate(slug, numeros)


def get_personality_message(score_tecnico: int, risco: str) -> dict:
    """Retorna mensagem do robô baseada no SCORE TÉCNICO (antes de zerar por já ter saído)"""

    if score_tecnico >= 85:
        return {
            "emoji": "😎",
            "titulo": "MANDEI BEM!",
            "mensagem": "Olha só esse resultado! O sorteio oficial teve <b>score técnico altíssimo</b>. Estatisticamente, foi um jogo de excelente qualidade!",
            "cor": "#00C853",
            "nivel": "EXCELENTE",
        }
    elif score_tecnico >= 70:
        return {
            "emoji": "👍",
            "titulo": "Tá vendo? Funciona!",
            "mensagem": "Score sólido! O sorteio oficial passou nos nossos filtros com boa nota. A ciência por trás do validador está provada na prática.",
            "cor": "#43A047",
            "nivel": "BOM",
        }
    elif score_tecnico >= 55:
        return {
            "emoji": "🤔",
            "titulo": "Score mediano...",
            "mensagem": "O sorteio oficial ficou na média. Nem todos os sorteios reais são estatisticamente perfeitos - e é isso que torna a análise importante!",
            "cor": "#FB8C00",
            "nivel": "MÉDIO",
        }
    else:
        return {
            "emoji": "😬",
            "titulo": "Esse foi... peculiar",
            "mensagem": f"Score técnico baixo! Esse sorteio teve padrões estatisticamente incomuns. Nosso validador conseguiu detectar essas anomalias - é exatamente isso que ele faz com seus jogos!",
            "cor": "#E53935",
            "nivel": "BAIXO",
        }


def render_validador_em_acao():
    """Página que valida os últimos sorteios reais e mostra o score"""
    apply_custom_css()
    if st.button("← Ir para Validador", key="back_button"):
        st.switch_page("pages/2_Validador.py")
    # Header
    st.markdown(
        """
        <div style='text-align: center; padding: 2rem 0;'>
            <h1 style='font-size: 3rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                       font-weight: 800; margin-bottom: 0.5rem;'>
                🏆 Validador em Ação
            </h1>
            <p style='font-size: 1.3rem; color: #777; margin-top: 0;'>
                Veja como o <strong>LotoScience</strong> analisa os sorteios <strong>reais</strong> que acabaram de sair
            </p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    st.divider()

    # Intro
    st.markdown(
        """
        ### 🔬 Transparência Total
        
        Não acredite só na nossa palavra. Aqui você vê **em tempo real** como o validador
        analisa os sorteios oficiais da Caixa que acabaram de acontecer.
        
        **Como funciona:**
        - Pegamos o **último sorteio oficial** de cada loteria
        - Rodamos no **mesmo validador** que você usa
        - Mostramos o **score técnico** (qualidade estatística do jogo)
        
        ⚠️ *O score final seria 0 (jogo já saiu), mas mostramos o score técnico para você ver a qualidade estatística!*
    """
    )

    st.divider()

    # Seletor de loteria
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        loteria = st.selectbox(
            "Escolha a loteria:",
            [
                "mega_sena_sorteio",
                "loto_facil_sorteio",
                "quina_sorteio",
                "loto_mania_sorteio",
            ],
            format_func=lambda x: {
                "mega_sena_sorteio": "🎰 Mega-Sena",
                "loto_facil_sorteio": "🍀 Lotofácil",
                "quina_sorteio": "🎲 Quina",
                "loto_mania_sorteio": "⭐ Lotomania",
            }[x],
        )

    st.divider()

    # Carrega último sorteio
    with st.spinner("🔍 Buscando último sorteio e validando..."):
        service = LotteryService()

        try:
            ctx = service.get_context(loteria)
            config = ctx.config
            if ctx.df is None or ctx.df.empty:
                st.error("❌ Dados não disponíveis para essa loteria")
                return

            # Último sorteio = última linha (maior concurso)
            ultimo_sorteio = ctx.df.iloc[-1]
            concurso = ultimo_sorteio.name  # índice = concurso
            numeros = ultimo_sorteio.tolist()

            # Valida com cache! (converte lista para tupla para ser hashable)
            resultado = validar_sorteio_cached(loteria, concurso, tuple(numeros))

            # SEMPRE usa score_original (técnico) pois são sorteios reais
            score_tecnico = resultado.get(
                "score_original", resultado.get("score_final", 0)
            )
            risco = resultado.get("risco_divisao", "DESCONHECIDO")

            # Personalidade do robô baseada no score TÉCNICO
            personality = get_personality_message(score_tecnico, risco)

            # ========== DISPLAY DOS RESULTADOS ==========

            # Card do robô
            st.markdown(
                f"""
                <div style='background: linear-gradient(135deg, {personality['cor']}22 0%, {personality['cor']}11 100%);
                            border-left: 5px solid {personality['cor']};
                            padding: 2rem;
                            border-radius: 15px;
                            margin: 2rem 0;'>
                    <div style='display: flex; align-items: center; gap: 1.5rem;'>
                        <div style='font-size: 5rem;'>{personality['emoji']}</div>
                        <div style='flex: 1;'>
                            <h2 style='margin: 0; color: {personality['cor']};'>{personality['titulo']}</h2>
                            <p style='font-size: 1.1rem; margin: 0.5rem 0 0 0; color: #333;'>
                                {personality['mensagem']}
                            </p>
                        </div>
                    </div>
                </div>
            """,
                unsafe_allow_html=True,
            )

            # Info do sorteio
            col_left, col_right = st.columns(2)

            with col_left:
                st.markdown(
                    f"""
                    ### 📊 Dados do Sorteio {config.name}
                    
                    - **Concurso:** {concurso}
                    - **Números:** {' - '.join(map(str, numeros))}
                    - **Status:** 🎯 Sorteio oficial da Caixa
                """
                )

            with col_right:
                st.markdown(
                    f"""
                    ### 🎯 Análise Estatística
                    
                    - **Score Técnico:** {score_tecnico}/100 ({personality['nivel']})
                    - **Risco de Divisão:** {risco}
                    - **Qualidade:** {'✅ Alta' if score_tecnico >= 70 else '⚠️ Média' if score_tecnico >= 55 else '❌ Baixa'}
                """
                )

            st.divider()

            # Score visual
            st.markdown("### 📈 Score Técnico (Qualidade Estatística)")

            progress_color = personality["cor"]

            st.markdown(
                f"""
<div style='background: #f0f0f0; border-radius: 25px; height: 50px; overflow: hidden; position: relative;'>
    <div style='background: linear-gradient(90deg, {progress_color}, {progress_color}88);
                width: {score_tecnico}%; height: 100%; display: flex; align-items: center;
                justify-content: center; font-weight: bold; color: white; font-size: 1.3rem;
                transition: width 1s ease;'>
        {score_tecnico}/100
    </div>
</div>
            """,
                unsafe_allow_html=True,
            )

            st.caption(
                "💡 Este é o score de **qualidade técnica** do jogo. Como já foi sorteado oficialmente, estamos mostrando apenas a análise estatística."
            )

            st.divider()

            # Call to Action
            st.markdown(
                f"""
<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 3rem;
            border-radius: 20px;
            text-align: center;
            color: white;
            margin: 3rem 0;'>
    <h2 style='margin: 0 0 1rem 0; font-size: 2.2rem;'>
        Esse é o mesmo validador que você pode usar AGORA!
    </h2>
    <p style='font-size: 1.2rem; margin-bottom: 2rem; opacity: 0.95;'>
        Analise seus próprios jogos com a mesma tecnologia que analisou o concurso <strong>{concurso}</strong>
    </p>
    <a href="/Validador" target="_self" style='background: white; color: #667eea;
        padding: 1rem 3rem; border-radius: 50px; text-decoration: none;
        font-weight: bold; font-size: 1.2rem; display: inline-block;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);'>
        🚀 Validar Meu Jogo Agora
    </a>
</div>
            """,
                unsafe_allow_html=True,
            )

            # Histórico (últimos 5 sorteios)
            st.markdown("### 📜 Histórico dos Últimos Sorteios")
            st.caption("Veja a qualidade estatística dos últimos 5 concursos oficiais")

            historico_scores = []
            ultimos_5 = ctx.df.tail(5)

            for concurso_hist, row in ultimos_5.iterrows():
                numeros_hist = row.tolist()

                # Valida com cache!
                resultado_hist = validar_sorteio_cached(
                    loteria, concurso_hist, tuple(numeros_hist)
                )

                # Sempre usa score técnico
                score_tecnico_hist = resultado_hist.get(
                    "score_original", resultado_hist.get("score_final", 0)
                )

                historico_scores.append(
                    {
                        "Concurso": int(concurso_hist),
                        "Score Técnico": f"{score_tecnico_hist}/100",
                        "Risco": resultado_hist.get("risco_divisao", "N/A"),
                        "Qualidade": (
                            "✅ Alta"
                            if score_tecnico_hist >= 70
                            else "⚠️ Média" if score_tecnico_hist >= 55 else "❌ Baixa"
                        ),
                    }
                )

            import pandas as pd

            df_historico = pd.DataFrame(historico_scores)
            df_historico = df_historico.sort_values("Concurso", ascending=False)

            st.dataframe(df_historico, use_container_width=True, hide_index=True)

            # Média dos scores técnicos
            scores_numericos = [
                resultado_hist.get(
                    "score_original", resultado_hist.get("score_final", 0)
                )
                for resultado_hist in [
                    validar_sorteio_cached(loteria, concurso_hist, tuple(row.tolist()))
                    for concurso_hist, row in ultimos_5.iterrows()
                ]
            ]

            media_scores = (
                sum(scores_numericos) / len(scores_numericos) if scores_numericos else 0
            )

            st.metric(
                "📊 Score técnico médio dos últimos 5 sorteios",
                f"{media_scores:.1f}/100",
                delta=f"{score_tecnico - media_scores:+.1f} vs média",
            )

        except Exception as e:
            st.error(f"❌ Erro ao processar: {str(e)}")
            import traceback

            st.code(traceback.format_exc())
