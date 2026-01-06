import streamlit as st
import pandas as pd
import altair as alt
import matplotlib.pyplot as plt
from app.src.games import GameConfig
from app.src.statistics import (
    calcular_atrasos,
    calcular_chi_quadrado,
    calcular_coeficiente_variacao,
    get_reis_da_sequencia,
    get_tabela_inteligencia,
)
from app.ui.game_constants import get_constants_for_game
from app.src.advanced_statistics import (
    calcular_distribuicoes_geometricas,
    calcular_taxa_regressao,
)


def render_dashboard(df, freq, poisson_finais, config: GameConfig):
    constants = get_constants_for_game(config)
    color = constants.get("heat_color", "#ef4444")
    st.markdown(
        f"<h3>🔭 O Raio-X da <span style='color: {color};'>{config.name}</span></h3>",
        unsafe_allow_html=True,
    )
    st.write(
        "Bem-vindo ao painel de inteligência. Aqui transformamos dados brutos em estratégias de jogo."
    )

    # 1. KPIs (Resumo Rápido)
    _render_kpis(freq, df, config)
    st.markdown("---")

    # 2. Oportunidades (O que o usuário quer ver primeiro)
    _render_gap_bar_charts(df, config)
    st.markdown("---")

    # 3. Tendências de Longo Prazo (LLN e Quentes/Frios)
    _render_bar_charts(freq, 15, config)
    st.markdown("---")

    # 4. Mapa Visual
    # Preparação de dados para o mapa
    reis_seq = get_reis_da_sequencia(df, config)
    top_quentes = freq.head(15).index.tolist()
    top_frios = freq.tail(15).index.tolist()

    if not df.empty:
        ultimo_idx = df.index.max()
        ultimo_sorteio = df.loc[ultimo_idx, config.draw_cols].values.tolist()
    else:
        ultimo_sorteio = []

    conjuntos = {
        "Todos os Números": list(range(1, config.n_numbers + 1)),
        "Top 15 Mais Quentes": top_quentes,
        "Top 15 Mais Frios": top_frios,
        "Último Sorteio": ultimo_sorteio,
        "Moldura (Borda)": constants["moldura"],
        "Miolo (Centro)": constants["miolo"],
        "Cruz": constants["cruz"],
        "Xis (Diagonais)": constants["xis"],
        "Cantos": constants["cantos"],
        "Primos": constants["primos"],
        "Números 'Lost'": constants["lost_numbers"],
        "Fibonacci": constants["fibonacci"],
        "Gêmeos (11, 22...)": constants["gemeos"],
        "Reis da Sequência": reis_seq,
        "Quadrante 1 (Sup. Esq)": config.layout.quadrant_numbers(1),
        "Quadrante 2 (Sup. Dir)": config.layout.quadrant_numbers(2),
        "Quadrante 3 (Inf. Esq)": config.layout.quadrant_numbers(3),
        "Quadrante 4 (Inf. Dir)": config.layout.quadrant_numbers(4),
    }

    _render_heatmap_section(freq, conjuntos, config)
    st.markdown("---")

    # 5. Guia de Equilíbrio (Tabela de Probabilidades)
    _render_probability_report(df, conjuntos, config)
    st.markdown("---")

    # 6. Auditoria Técnica (Fica por último para não assustar)
    st.subheader("🛡️ Auditoria de Integridade")
    st.caption("Ferramentas matemáticas para validar se o sorteio é honesto.")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**🔢 Análise de Finais (Poisson)**")
        if poisson_finais:
            st.warning(f"Detectamos {len(poisson_finais)} finais atrasados.")
            cols = st.columns(len(poisson_finais))
            for i, item in enumerate(poisson_finais):
                cols[i].metric(
                    f"Final {item['digito']}",
                    f"p={item['p_value']}",
                    help="Probabilidade estatística baixa. Indica que este final 'deveria' ter saído mais vezes.",
                )
        else:
            st.success("✅ A distribuição dos finais (0-9) está normal.")
            st.caption("Não há finais criticamente atrasados no momento.")

    with c2:
        st.markdown(f"**⚖️ Teste de Honestidade (Chi-Quadrado) para a {config.name}**")
        chi_res = calcular_chi_quadrado(df, config)

        if chi_res:
            p_chi = chi_res.get("p_chi", 0)
            p_ks = chi_res.get("p_ks", 0)

            # Se p_chi > 0.05, não rejeitamos a hipótese nula (distribuição é uniforme) -> Verde
            is_honesto = p_chi > 0.05

            cor = "green" if is_honesto else "red"
            texto = (
                "Aprovado (Distribuição Uniforme)" if is_honesto else "Alerta de Viés"
            )

            # Layout do card
            st.markdown(
                f"""
                <div style="background-color: #f0fdf4; padding: 10px; border-radius: 5px; border-left: 5px solid {cor};">
                    <strong>Status:</strong> {texto}<br>
                    <small>Chi² p-value: {p_chi:.4f} (> 0.05 é ideal)</small><br>
                    <small>KS p-value: {p_ks:.4f} (> 0.05 é ideal)</small>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("Dados insuficientes para teste Chi-Quadrado.")

        cv_res = calcular_coeficiente_variacao(df, config)
        if cv_res:
            st.markdown(f"**📉 Coeficiente de Variação (CV) para a {config.name}**")
            st.caption(
                "Mede quão uniforme está a frequência dos números (quanto menor, mais uniforme)."
            )

            st.metric(
                "CV (%)",
                f"{cv_res['coeficiente_variacao']:.2f}",
                help=cv_res["interpretacao"],
            )
        else:
            st.info("Dados insuficientes para calcular o CV.")

    # NOVO: Validação de Regressão à Média
    _render_regression_analysis(df, config)

    # 7. Tabela Científica (Escondida para curiosos)
    _render_z_score_gaps_section(df, config)


def _render_kpis(freq, df, config: GameConfig):
    if not freq.empty:
        num_mais = freq.idxmax()
        qtd_mais = freq.max()
        num_menos = freq.idxmin()
        qtd_menos = freq.min()
        media = freq.mean()
    else:
        num_mais, qtd_mais, num_menos, qtd_menos, media = 0, 0, 0, 0, 0

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.markdown(
            f"""
        <div class="custom-metric-card">
            <div class="metric-label">Total de Sorteios</div>
            <div class="metric-value">{len(df)}</div>
            <div class="metric-delta status-good">Desde {config.start_year}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with k2:
        st.markdown(
            f"""
        <div class="custom-metric-card">
            <div class="metric-label">Rei da Mesa 🔥</div>
            <div class="metric-value">Nº {num_mais}</div>
            <div class="metric-delta status-good">Saiu {qtd_mais} vezes</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with k3:
        st.markdown(
            f"""
        <div class="custom-metric-card">
            <div class="metric-label">O Tímido ❄️</div>
            <div class="metric-value">Nº {num_menos}</div>
            <div class="metric-delta status-bad">Saiu {qtd_menos} vezes</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with k4:
        st.markdown(
            f"""
        <div class="custom-metric-card">
            <div class="metric-label">Média Esperada</div>
            <div class="metric-value">~{media:.0f}</div>
            <div class="metric-delta status-warn">Vezes por número</div>
        </div>
        """,
            unsafe_allow_html=True,
        )


def _render_gap_bar_charts(df, config: GameConfig):
    st.subheader("⏰ Relógio dos Atrasados")
    st.write(
        "Estes números estão 'dormindo' há muito tempo. Segundo a estatística, a chance deles acordarem aumenta a cada sorteio."
    )

    atrasos = calcular_atrasos(df, config)

    # Mostra os 20 mais atrasados
    top_atrasados = atrasos.head(20)

    # Destaque visual
    col_graph, col_info = st.columns([3, 1])

    with col_graph:
        st.bar_chart(top_atrasados, color="#ef4444", height=250)

    with col_info:
        maior_gap = atrasos.index[0]
        tempo = atrasos.iloc[0]
        st.markdown(
            f"""
            <div style="background-color: #fef2f2; padding: 15px; border-radius: 10px; border: 1px solid #fca5a5;">
                <h4 style="color: #991b1b; margin:0;">🚨 Alerta</h4>
                <p style="font-size: 0.9em; color: #7f1d1d;">
                    O número <strong>{maior_gap}</strong> é o campeão de atraso.<br>
                    Ele não aparece há <strong>{tempo} jogos</strong>.
                </p>
                <small style="color: #ef4444;">Alta probabilidade de retorno em breve.</small>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_bar_charts(freq, num, config: GameConfig):
    """
    Renderiza gráficos de barra usando Altair para incluir a Linha de Média (LLN).
    """
    total_aparicoes = freq.sum()
    media_teorica = total_aparicoes / config.n_numbers

    st.subheader("⚖️ Equilíbrio Matemático (LLN)")
    st.markdown(
        f"""
        A linha vermelha pontilhada mostra onde todos os números **deveriam estar** (~{media_teorica:.0f} vezes).
        """
    )

    c1, c2 = st.columns(2)

    # --- GRÁFICO 1: QUENTES ---
    with c1:
        st.markdown(f"**🔥 Os {num} Mais Quentes** (Acima da Média)")
        st.caption("Eles estão saindo mais do que o normal. Cuidado: podem esfriar.")

        dados_quentes = freq.head(num).reset_index()
        dados_quentes.columns = ["Dezena", "Frequencia"]

        barras = (
            alt.Chart(dados_quentes)
            .mark_bar(color="#a79f28")
            .encode(
                x=alt.X("Dezena:O", sort="-y", title="Dezena"),
                y=alt.Y("Frequencia", title="Saídas"),
                tooltip=["Dezena", "Frequencia"],
            )
        )

        regua = (
            alt.Chart(pd.DataFrame({"y": [media_teorica]}))
            .mark_rule(color="red", strokeDash=[5, 5], size=2)
            .encode(y="y")
        )

        st.altair_chart(barras + regua, width="stretch")

    # --- GRÁFICO 2: FRIOS ---
    with c2:
        st.markdown(f"**❄️ Os {num} Mais Frios** (Abaixo da Média)")
        st.caption("Eles estão devendo aparições. A tendência é subirem.")

        dados_frios = freq.tail(num).reset_index()
        dados_frios.columns = ["Dezena", "Frequencia"]

        barras_frias = (
            alt.Chart(dados_frios)
            .mark_bar(color="#17a2b8")
            .encode(
                x=alt.X("Dezena:O", sort="y", title="Dezena"),
                y=alt.Y("Frequencia", title="Saídas"),
                tooltip=["Dezena", "Frequencia"],
            )
        )

        st.altair_chart(barras_frias + regua, width="stretch")


def _render_heatmap_section(freq, conjuntos, config: GameConfig):
    st.subheader("🗺️ Mapa de Calor")
    st.write(
        "Visualize onde os números caem no volante. Use os filtros para ver padrões ocultos."
    )

    col_graf, col_filtros = st.columns([3, 1])

    with col_filtros:
        st.markdown("**🔎 Escolha um Padrão:**")
        filtro = st.radio(
            "Visualizar:", list(conjuntos.keys()), label_visibility="collapsed"
        )
        nums_filtro = conjuntos[filtro]

        # Mini estatística do filtro selecionado
        if not freq.empty:
            st.markdown("---")
            freq_filtro = freq[freq.index.isin(nums_filtro)]
            media_grupo = freq_filtro.mean() if not freq_filtro.empty else 0
            st.caption(
                f"Neste grupo, cada número saiu em média **{media_grupo:.1f} vezes**."
            )

    with col_graf:
        _plot_heatmap_matplotlib(freq, nums_filtro, config)


def _plot_heatmap_matplotlib(freq, nums_filtro, config: GameConfig):
    layout = config.layout

    base_w = 8.0
    aspect = layout.rows / layout.cols if layout.cols else 1.0
    fig_h = max(3.2, base_w * aspect)
    fig, ax = plt.subplots(figsize=(base_w, fig_h))

    ax.set_xlim(-0.5, layout.cols - 0.5)
    ax.set_ylim(-0.5, layout.rows - 0.5)
    ax.axis("off")

    ax.set_aspect("equal", adjustable="box")

    plt.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)

    maxval = freq.max() if not freq.empty else 1
    minval = freq.min() if not freq.empty else 0
    nums_filtro_set = set(nums_filtro)

    r = 0.42
    if min(layout.rows, layout.cols) <= 5:
        r = 0.36
    elif min(layout.rows, layout.cols) >= 8:
        r = 0.40

    for n in range(1, config.n_numbers + 1):
        row, col = config.layout.pos(n)
        val = freq.get(n, 0)

        y = config.layout.rows - 1 - row
        theme = get_constants_for_game(config)
        heat_color = theme["heat_color"]

        if n in nums_filtro_set:
            intensity = (
                0.1 + 0.9 * (val - minval) / (maxval - minval)
                if maxval != minval
                else 0.5
            )
            face = heat_color
            alpha = intensity
            edge = "#444"
            lw = 1.5
            txtcol = "white" if intensity > 0.6 else "black"
            weight = "bold"
        else:
            face = "#f0f0f0"
            alpha = 0.3
            edge = "#e0e0e0"
            lw = 0.5
            txtcol = "#ccc"
            weight = "normal"

        ax.add_patch(plt.Circle((col, y), r, color=face, alpha=alpha, ec=edge, lw=lw))
        ax.text(
            col,
            y + 0.10,
            str(n),
            ha="center",
            va="center",
            color=txtcol,
            fontweight=weight,
            fontsize=10,
        )

        if n in nums_filtro_set:
            ax.text(
                col,
                y - 0.15,
                str(val),
                ha="center",
                va="center",
                color=txtcol,
                fontsize=7,
            )

    st.pyplot(fig, width="stretch")


def _render_probability_report(df, conjuntos, config: GameConfig):
    """
    Usa análise estatística avançada com distribuições empíricas.
    Mostra média, desvio-padrão e percentis baseados em dados reais.
    """
    st.subheader("📊 Guia de Equilíbrio (Análise Estatística)")
    st.write(
        "Baseado em **análise estatística real** dos sorteios históricos. "
        "A tabela mostra quantos números de cada grupo aparecem tipicamente nos sorteios."
    )

    if df.empty:
        st.warning("Sem dados para calcular.")
        return

    # Filtra apenas os grupos geométricos relevantes para a análise
    grupos_geometricos = {
        "Moldura (Borda)": conjuntos["Moldura (Borda)"],
        "Miolo (Centro)": conjuntos["Miolo (Centro)"],
        "Cruz": conjuntos["Cruz"],
        "Xis (Diagonais)": conjuntos["Xis (Diagonais)"],
        "Cantos": conjuntos["Cantos"],
        "Quadrante 1 (Sup. Esq)": conjuntos["Quadrante 1 (Sup. Esq)"],
        "Quadrante 2 (Sup. Dir)": conjuntos["Quadrante 2 (Sup. Dir)"],
        "Quadrante 3 (Inf. Esq)": conjuntos["Quadrante 3 (Inf. Esq)"],
        "Quadrante 4 (Inf. Dir)": conjuntos["Quadrante 4 (Inf. Dir)"],
    }

    # Calcula distribuições empíricas usando nova função estatística
    distribuicoes = calcular_distribuicoes_geometricas(df, grupos_geometricos, config)

    if not distribuicoes:
        st.info("Dados insuficientes para análise estatística.")
        return

    # Prepara dados para a tabela
    dados_relatorio = []

    for nome, dist in distribuicoes.items():
        # Ajuste para jogos grandes (Lotomania: aposta 50 vs sorteio 20)
        if config.k != config.bet_size and config.k > 0:
            fator = config.bet_size / config.k
            mean_ajustada = dist.mean * fator
            std_ajustada = dist.std * fator
            p5_ajustado = dist.percentiles[5] * fator
            p95_ajustado = dist.percentiles[95] * fator
        else:
            mean_ajustada = dist.mean
            std_ajustada = dist.std
            p5_ajustado = dist.percentiles[5]
            p95_ajustado = dist.percentiles[95]

        dados_relatorio.append(
            {
                "Grupo": nome,
                "Média (μ)": f"{mean_ajustada:.2f}",
                "Desvio (σ)": f"{std_ajustada:.2f}",
                "Intervalo Normal": f"{p5_ajustado:.1f} - {p95_ajustado:.1f}",
                "_raw_media": mean_ajustada,
            }
        )

    df_rel = pd.DataFrame(dados_relatorio)
    df_rel = df_rel.sort_values(by="_raw_media", ascending=False)

    with st.expander("Ver Tabela Estatística Completa", expanded=True):
        st.caption(
            f"💡 **Como usar:** Procure manter seus jogos dentro do 'Intervalo Normal' (90% dos sorteios históricos). "
            f"Por exemplo, se a Moldura tem média de 2.5, escolha 2-3 números da borda."
        )

        st.dataframe(
            df_rel[["Grupo", "Média (μ)", "Desvio (σ)", "Intervalo Normal"]],
            column_config={
                "Grupo": st.column_config.TextColumn("Grupo de Números"),
                "Média (μ)": st.column_config.TextColumn(
                    "Média Histórica",
                    help=f"Quantos números deste grupo aparecem, em média, nos sorteios de {config.k} números.",
                ),
                "Desvio (σ)": st.column_config.TextColumn(
                    "Desvio-Padrão",
                    help="Medida de variabilidade. Menor = mais consistente.",
                ),
                "Intervalo Normal": st.column_config.TextColumn(
                    "Faixa Esperada (90%)",
                    help="90% dos sorteios históricos ficaram dentro desta faixa. Sair muito deste intervalo é estatisticamente raro.",
                ),
            },
            hide_index=True,
            width="stretch",
        )

        st.info(
            "📈 **Nota Estatística:** Esta análise usa distribuições empíricas reais "
            "ao invés de heurísticas fixas. Os valores mostram o comportamento histórico "
            f"dos últimos {len(df)} sorteios da {config.name}."
        )


def _render_regression_analysis(df, config: GameConfig):
    """
    Exibe análise de regressão à média validando a estratégia "agressiva".
    """
    regressao = calcular_taxa_regressao(df, config, janela=100)

    if not regressao:
        return

    with st.expander("📈 Validação: Regressão à Média Funciona?", expanded=False):
        st.markdown(
            "**Pergunta:** Números atrasados realmente tendem a sair? "
            "Analisamos os últimos 100 sorteios para validar esta hipótese estatística."
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            cor = (
                "green"
                if regressao["correlacao"] > 0.2
                else "orange" if regressao["correlacao"] > 0.1 else "red"
            )
            st.markdown(
                f"""
                <div style="background-color: #f0fdf4; padding: 15px; border-radius: 8px; border-left: 4px solid {cor};">
                    <strong>Correlação (ρ)</strong><br>
                    <span style="font-size: 1.5em; color: {cor};">{regressao['correlacao']}</span><br>
                    <small>Entre atraso e saída futura</small>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                f"""
                <div style="background-color: #eff6ff; padding: 15px; border-radius: 8px; border-left: 4px solid #3b82f6;">
                    <strong>Taxa de Retorno</strong><br>
                    <span style="font-size: 1.5em; color: #1e40af;">{regressao['taxa_retorno']:.1%}</span><br>
                    <small>Atrasados que voltaram</small>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col3:
            st.markdown(
                f"""
                <div style="background-color: #fef3c7; padding: 15px; border-radius: 8px; border-left: 4px solid #f59e0b;">
                    <strong>Interpretação</strong><br>
                    <span style="font-size: 1.1em; color: #92400e;">{regressao['interpretacao']}</span><br>
                    <small>p-value: {regressao['p_value']:.4f}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if regressao["correlacao"] > 0.2:
            st.success(
                "✅ **Evidência forte de regressão à média!** "
                "Isso valida estratégias que priorizam números atrasados (modo 'Agressivo' no gerador)."
            )
        elif regressao["correlacao"] > 0.1:
            st.info(
                "ℹ️ **Evidência moderada de regressão.** "
                "Há alguma tendência, mas não é muito forte."
            )
        else:
            st.warning(
                "⚠️ **Sem evidência clara.** "
                "Neste período específico, números atrasados não mostraram tendência forte de retorno."
            )


def _render_z_score_gaps_section(df, config: GameConfig):
    with st.expander("🤓 Área Nerd: Dados Brutos (Z-Score & Gaps)"):
        st.write(
            "Estes são os dados matemáticos que alimentam o Gerador de Jogos. O 'Peso' define a probabilidade de escolha."
        )
        tabela = get_tabela_inteligencia(df, config)
        st.dataframe(
            tabela.style.background_gradient(subset=["Peso_Geracao"], cmap="Greens"),
            width="stretch",
        )
