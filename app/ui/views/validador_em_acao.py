# app/pages/validador_em_acao.py
import streamlit as st
import pandas as pd
from app.services.lottery_service import LotteryService
from app.ui.core.styles import apply_custom_css

# Configuração da página para parecer um portal de notícias de loteria
st.set_page_config(
    page_title="Últimos Resultados e Análise", page_icon="🎱", layout="wide"
)


@st.cache_data(ttl=3600)  # Cache de 1 hora para resultados
def validar_sorteio_cached(slug: str, concurso: int, numeros_tuple: tuple):
    """Valida o sorteio e retorna a análise técnica."""
    service = LotteryService()
    numeros = list(numeros_tuple)
    return service.validate(slug, numeros)


def render_result_balls(numeros, color="#667eea"):
    """Renderiza as bolas do sorteio estilo TV/Caixa"""
    html = f"""
    <div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-bottom: 20px;">
    """
    for n in sorted(numeros):
        html += f"""
<div style="
    width: 50px; height: 50px; 
    background: radial-gradient(circle at 30% 30%, {color}, #2d3748);
    color: white; border-radius: 50%; display: flex; 
    align-items: center; justify-content: center; 
    font-weight: bold; font-size: 1.2rem;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    border: 2px solid white;
">
            {n:02d}
        </div>
        """
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_stats_summary(numeros, metricas):
    """Mostra o que o apostador técnico quer ver: Pares, Soma, Primos"""
    st.markdown("##### 🕵️ Detalhes que todo apostador olha:")
    c1, c2, c3, c4 = st.columns(4)

    n = len(numeros)
    pares = sum(1 for x in numeros if x % 2 == 0)
    impares = n - pares
    soma = sum(numeros)

    # Tenta pegar primos das métricas ou calcula simples
    primos_count = metricas.get("primos_count", "N/A")

    with c1:
        st.metric("Soma Total", soma)
    with c2:
        st.metric("Pares / Ímpares", f"{pares} / {impares}")
    with c3:
        st.metric("Primos", primos_count)
    with c4:
        repetidos = metricas.get("repetidos_concurso_anterior", "N/A")
        st.metric("Repetidos", repetidos, help="Do concurso anterior")


def render_validador_em_acao():
    apply_custom_css()

    # --- HEADER DE PORTAL DE NOTÍCIAS ---
    st.markdown(
        """
<div style='text-align: center; margin-bottom: 2rem;'>
    <h1 style='font-size: 2.5rem; margin-bottom: 0;'>📢 Últimos Resultados</h1>
    <p style='color: #666; font-size: 1.1rem;'>
        Confira os números sorteados e veja a <strong>Análise da Inteligência Estatística</strong> sobre o resultado.
    </p>
</div>
        """,
        unsafe_allow_html=True,
    )

    # Menu de Navegação Rápida
    col_nav1, col_nav2 = st.columns([1, 4])
    with col_nav1:
        if st.button("← Voltar", width="stretch"):
            st.switch_page("pages/2_Painel.py")

    # Seletor de Loteria (Estilo Abas)
    loteria_map = {
        "loto_facil_sorteio": {"nome": "Lotofácil", "cor": "#9333ea"},  # Roxo
        "mega_sena_sorteio": {"nome": "Mega-Sena", "cor": "#16a34a"},  # Verde
        "quina_sorteio": {"nome": "Quina", "cor": "#2563eb"},  # Azul
        "loto_mania_sorteio": {"nome": "Lotomania", "cor": "#f97316"},  # Laranja
    }

    col_sel, _ = st.columns([2, 2])
    with col_sel:
        slug_selecionado = st.selectbox(
            "Selecione o Sorteio:",
            list(loteria_map.keys()),
            format_func=lambda x: f"{loteria_map[x]['nome']}",
        )

    info_loteria = loteria_map[slug_selecionado]

    # --- LÓGICA DE CARREGAMENTO ---
    service = LotteryService()
    try:
        ctx = service.get_context(slug_selecionado)
        if ctx.df is None or ctx.df.empty:
            st.error("⚠️ Atualizando base de dados... Tente novamente em instantes.")
            return

        # Pega o último sorteio (Concurso mais recente)
        ultimo_sorteio = ctx.df.iloc[-1]
        concurso = ultimo_sorteio.name

        # Tenta pegar a data se existir no DF
        data_sorteio = ultimo_sorteio.get("Data", "Data não inf.")
        if hasattr(data_sorteio, "strftime"):
            data_sorteio = data_sorteio.strftime("%d/%m/%Y")

        numeros = sorted(ultimo_sorteio.tolist())

        # --- ÁREA DO RESULTADO (VISUAL DE TV) ---
        st.markdown(
            f"""
<div style="
    background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%);
    border: 1px solid #cbd5e1;
    border-radius: 15px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    margin-bottom: 30px;
">
    <h2 style="color: #334155; margin:0;">{info_loteria['nome']} - Concurso {concurso}</h2>
    <p style="color: #64748b; font-size: 0.9rem; margin-top: 5px;">Sorteio realizado em: {data_sorteio}</p>
    <hr style="margin: 15px 0; border-color: #cbd5e1;">
            """,
            unsafe_allow_html=True,
        )

        # Renderiza as bolas coloridas
        render_result_balls(numeros, color=info_loteria["cor"])
        st.markdown("</div>", unsafe_allow_html=True)

        # --- ANÁLISE TÉCNICA (O DIFERENCIAL) ---
        st.subheader("🤖 O que a Inteligência Estatística achou desse resultado?")

        # Roda a validação
        with st.spinner("Calculando estatísticas do sorteio..."):
            resultado = validar_sorteio_cached(
                slug_selecionado, concurso, tuple(numeros)
            )
            score = resultado.get("score_original", 0)
            metricas = resultado.get("metricas", {})
            risco = resultado.get("risco_divisao", "N/A")

        # Layout de 2 colunas para análise
        c_score, c_stats = st.columns([1.5, 2.5])

        with c_score:
            # Gauge do Score
            st.markdown(
                f"""
<div style="background: white; padding: 20px; border-radius: 10px; border: 1px solid #e5e7eb; text-align: center; height: 100%;">
    <div style="font-size: 1rem; color: #666; margin-bottom: 10px;">Score Estatístico</div>
    <div style="font-size: 3.5rem; font-weight: 800; color: {info_loteria['cor']}; line-height: 1;">
        {score}<span style="font-size: 1.5rem; color: #999;">/100</span>
    </div>
    <div style="margin-top: 10px; font-weight: bold; color: #444;">
        {"✅ Padrão Normal" if score > 60 else "⚠️ Resultado Atípico (Zebra)"}
    </div>
</div>
                """,
                unsafe_allow_html=True,
            )

        with c_stats:
            # Card de Detalhes
            with st.container(border=True):
                render_stats_summary(numeros, metricas)

                # Feedback humano
                if score > 75:
                    msg = "Este resultado seguiu perfeitamente as leis da probabilidade. Quem jogou baseado em estatística teve mais chances."
                elif score > 50:
                    msg = "Um resultado mediano. Alguns padrões saíram do comum, mas nada impossível."
                else:
                    msg = "🦓 ZEBRA! Este sorteio foi matematicamente improvável (muitos números seguidos ou fora de padrão). Difícil de acertar."

                st.info(f"💡 **Análise do Robô:** {msg}")

        # --- CALL TO ACTION (VENDA) ---
        st.markdown("---")
        st.markdown(
            """
<div style="
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    padding: 30px;
    border-radius: 15px;
    text-align: center;
    color: white;
    margin-top: 20px;
">
    <h2 style="color: white; margin-bottom: 10px;">Quer jogar com essa inteligência?</h2>
    <p style="color: #cbd5e1; max-width: 600px; margin: 0 auto 20px auto;">
        Nosso sistema não só analisa resultados passados, ele ajuda você a criar jogos futuros 
        com <strong>Score Alto</strong> para parar de perder dinheiro com zebras.
    </p>
    <a href="/Validador" target="_self">
        <button style="
            background-color: #22c55e; border: none; color: white; 
            padding: 12px 30px; border-radius: 25px; 
            font-weight: bold; font-size: 1.1rem; cursor: pointer;
            box-shadow: 0 4px 14px rgba(34, 197, 94, 0.4);
        ">
            🚀 Validar Meus Próximos Jogos
        </button>
    </a>
</div>
            """,
            unsafe_allow_html=True,
        )

        # --- HISTÓRICO RECENTE (SEO E RETENÇÃO) ---
        st.markdown("### 📅 Histórico Recente")

        # Tabela simplificada
        ultimos = ctx.df.tail(10).sort_index(ascending=False)

        # Prepara dados para tabela limpa
        dados_tabela = []
        for idx, row in ultimos.iterrows():
            # Recalcula score rápido (com cache)
            res_hist = validar_sorteio_cached(
                slug_selecionado, idx, tuple(row.tolist())
            )
            sc = res_hist.get("score_original", 0)

            nums_fmt = " - ".join([f"{n:02d}" for n in sorted(row.tolist())])
            dados_tabela.append(
                {
                    "Concurso": idx,
                    "Números Sorteados": nums_fmt,
                    "Score Inteligência Estatística": sc,
                    "Qualidade": (
                        "🟢 Ótimo" if sc > 70 else "🟡 Médio" if sc > 50 else "🔴 Zebra"
                    ),
                }
            )

        df_display = pd.DataFrame(dados_tabela)
        st.dataframe(
            df_display,
            hide_index=True,
            width="stretch",
            column_config={
                "Score da nossa Inteligência Estatística": st.column_config.ProgressColumn(
                    "Score Inteligência Estatística",
                    help="Qualidade estatística do resultado",
                    format="%d",
                    min_value=0,
                    max_value=100,
                ),
            },
        )

    except Exception as e:
        st.error(f"Erro ao carregar resultados: {e}")
        # Em produção, logar o erro silenciosamente
        # logger.error(e)
