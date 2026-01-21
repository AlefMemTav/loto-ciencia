# app/ui/dashboard.py
import streamlit as st
import pandas as pd
import altair as alt
import matplotlib.pyplot as plt


def render_dashboard(ctx, svc):
    config = ctx.config
    df = ctx.df
    freq = ctx.freq
    poisson_finais = ctx.poisson_finais
    atrasos = ctx.atrasos
    chi2 = ctx.chi2
    coef_variacao = ctx.coef_variacao
    regressao = ctx.taxa_regressao
    reis_sequencia = ctx.reis_sequencia
    tabela = ctx.tabela
    ic_info = ctx.ic_info
    ciclo = ctx.ciclo_atual
    somas = ctx.analise_somas
    repetidos = ctx.analise_repetidos
    tendencias = ctx.tendencias
    constants = config.as_constants_dict()
    main_color = constants.get("heat_color", "#ef4444")

    st.markdown(
        f"""
        <div style="background: linear-gradient(90deg, #f8fafc 0%, #e2e8f0 100%); padding: 20px; border-radius: 10px; border-left: 5px solid {main_color}; margin-bottom: 25px;">
            <h2 style="color: #1e293b; margin:0;">🔭 Centro de Inteligência: <span style="color: {main_color};">{config.name}</span></h2>
            <p style="color: #475569; font-size: 1rem; margin-top: 5px;">
                Transformamos os dados brutos de <strong>{len(df)} sorteios</strong> em padrões matemáticos visuais.
                Use este painel para identificar tendências antes de gerar seus jogos.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. KPIs (Resumo Rápido)
    _render_kpis(freq, df, config)
    st.markdown("---")

    # 2. Oportunidades (O que o usuário quer ver primeiro)
    _render_gap_bar_charts(atrasos, config)
    st.markdown("---")

    # === CICLOS E TENDÊNCIAS TEMPORAIS ===
    st.subheader("Dinâmica Temporal")
    st.write(
        "Entenda o momento exato: ciclos de fechamento, temperatura da soma e repetições."
    )

    col_ciclo, col_tempo = st.columns([1, 2])

    with col_ciclo:
        _render_ciclo_section(ciclo, config)

    with col_tempo:
        _render_temporal_charts(somas, repetidos, config)

    _render_momentum_section(tendencias)
    st.markdown("---")

    # 3. Tendências de Longo Prazo (LLN e Quentes/Frios)
    _render_bar_charts(freq, 15, config)
    st.markdown("---")

    # 4. Mapa Visual
    # Preparação de dados para o mapa
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
        "Reis da Sequência": reis_sequencia,
        "Quadrante 1 (Sup. Esq)": config.layout.quadrant_numbers(1),
        "Quadrante 2 (Sup. Dir)": config.layout.quadrant_numbers(2),
        "Quadrante 3 (Inf. Esq)": config.layout.quadrant_numbers(3),
        "Quadrante 4 (Inf. Dir)": config.layout.quadrant_numbers(4),
    }

    _render_heatmap_section(freq, conjuntos, config)
    st.markdown("---")

    # 5. Guia de Equilíbrio (Tabela de Probabilidades)
    _render_probability_report(conjuntos, config, svc, ctx)
    st.markdown("---")

    # 6. Auditoria Técnica (Fica por último para não assustar)
    st.subheader("🛡️ Auditoria de Integridade")
    st.caption(
        "Ferramentas matemáticas avançadas para validar a aleatoriedade e honestidade dos sorteios."
    )

    c1, c2 = st.columns(2)

    with c1:
        with st.container(border=True):
            st.markdown("**🔢 Análise de Finais (Poisson)**")
            if poisson_finais:
                st.warning(f"⚠️ Detectamos {len(poisson_finais)} finais atrasados.")
                cols = st.columns(len(poisson_finais))
                for i, item in enumerate(poisson_finais):
                    cols[i].metric(
                        f"Final {item['digito']}",
                        f"p={item['p_value']}",
                        help="Probabilidade estatística extremamente baixa. Pela Lei de Poisson, este final 'deveria' ter saído mais vezes.",
                    )
            else:
                st.success("✅ A distribuição dos finais (0-9) está normal.")
                st.caption("Não há anomalias estatísticas nos dígitos finais.")

    with c2:
        with st.container(border=True):
            st.markdown(
                f"**⚖️ Teste de Honestidade (Chi-Quadrado e Kolmogorov-Smirnov)**"
            )

            if chi2:
                p_chi = chi2.get("p_chi", 0)
                p_ks = chi2.get("p_ks", 0)

                # Se p_chi > 0.05, não rejeitamos a hipótese nula (distribuição é uniforme) -> Verde
                is_honesto = p_chi > 0.05

                cor = "#22c55e" if is_honesto else "#ef4444"
                texto = "Aprovado (Aleatório)" if is_honesto else "Alerta de Viés"
                bg = "#f0fdf4" if is_honesto else "#fef2f2"

                # Layout do card
                st.markdown(
                    f"""
                    <div style="background-color: {bg}; padding: 10px; border-radius: 5px; border-left: 5px solid {cor};">
                        <strong>Status:</strong> <span style="color:{cor}; font-weight:bold;">{texto}</span><br>
                        <small>Chi² p-value: {p_chi:.4f} (> 0.05 é ideal)</small><br>
                        <small>KS p-value: {p_ks:.4f} (> 0.05 é ideal)</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.info("Dados insuficientes para teste Chi-Quadrado.")

            if coef_variacao:
                st.markdown(f"**📉 Coeficiente de Variação (CV)**")
                st.caption(
                    "Mede quão uniforme está a frequência dos números (quanto menor, mais uniforme)."
                )
                st.metric(
                    "CV (%)",
                    f"{coef_variacao['coeficiente_variacao']:.2f}",
                    help=coef_variacao["interpretacao"],
                )

    _render_regression_analysis(config, ctx)

    # 7. Tabela Científica
    _render_z_score_gaps_section(tabela)

    # --- CTA FINAL ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 30px; border-radius: 15px; text-align: center; color: white;">
            <h2 style="color: white; margin-bottom: 10px;">Viu os padrões? Agora use a IA a seu favor.</h2>
            <p style="color: #cbd5e1; margin-bottom: 20px;">
                Nossa engine usa exatamente esses dados (Atrasos, Z-Score, Regressão) para montar jogos otimizados.
            </p>
            <a href="/Gerador_de_Jogos" target="_self">
                <button style="background-color: #22c55e; border: none; color: white; padding: 12px 30px; border-radius: 25px; font-weight: bold; cursor: pointer; font-size: 1.1rem;">
                    🚀 Gerar Jogos com Base na Estatística
                </button>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_kpis(freq, df, config):
    """Renderiza os 4 KPIs principais com CSS inline para garantir visual."""
    if not freq.empty:
        num_mais = freq.idxmax()
        qtd_mais = freq.max()
        num_menos = freq.idxmin()
        qtd_menos = freq.min()
        media = freq.mean()
    else:
        num_mais, qtd_mais, num_menos, qtd_menos, media = 0, 0, 0, 0, 0

    k1, k2, k3, k4 = st.columns(4)

    def card_html(label, value, sub, color="#64748b"):
        return f"""
        <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; text-align: center;">
            <div style="font-size: 0.85rem; color: #64748b; font-weight: 600; text-transform: uppercase;">{label}</div>
            <div style="font-size: 1.8rem; font-weight: 800; color: #1e293b; margin: 5px 0;">{value}</div>
            <div style="font-size: 0.8rem; color: {color}; font-weight: 500;">{sub}</div>
        </div>
        """

    with k1:
        st.markdown(
            card_html(
                "Base de Dados", len(df), f"Desde {config.start_year}", "#3b82f6"
            ),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            card_html(
                "Rei da Mesa 🔥", f"Nº {num_mais}", f"Saiu {qtd_mais}x", "#22c55e"
            ),
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            card_html("O Tímido ❄️", f"Nº {num_menos}", f"Saiu {qtd_menos}x", "#ef4444"),
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            card_html("Média Esperada", f"~{media:.0f}x", "Por dezena", "#eab308"),
            unsafe_allow_html=True,
        )


def _render_gap_bar_charts(atrasos, config):
    """Renderiza gráfico de números atrasados."""
    st.subheader("Relógio dos Atrasados")
    st.write(
        'Estes números estão "dormindo" há muito tempo. Pela **Teoria do Retorno à Média**, a probabilidade deles saírem aumenta a cada sorteio que passa.'
    )

    # Mostra os 20 mais atrasados
    top_atrasados = atrasos.head(20)

    # Destaque visual
    col_graph, col_info = st.columns([3, 1])

    with col_graph:
        st.bar_chart(top_atrasados, color="#ef4444", height=280)

    with col_info:
        maior_gap = atrasos.index[0]
        tempo = atrasos.iloc[0]
        st.markdown(
            f"""
            <div style="background-color: #fef2f2; padding: 20px; border-radius: 10px; border: 1px solid #fca5a5; text-align: center;">
                <h2 style="color: #dc2626; margin:0; font-size: 2.5rem;">{maior_gap:02d}</h2>
                <div style="color: #991b1b; font-weight: bold; margin-bottom: 10px;">O Grande Atrasado</div>
                <p style="font-size: 0.9em; color: #7f1d1d; margin: 0;">
                    Não sai há<br>
                    <strong style="font-size: 1.2rem;">{tempo} sorteios</strong>
                </p>
                <hr style="border-color: #fca5a5; margin: 10px 0;">
                <small style="color: #ef4444;">Estratégia sugerida:<br>Fixar nos próximos jogos.</small>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_bar_charts(freq, num, config):
    """
    Renderiza gráficos de barra usando Altair para incluir a Linha de Média (LLN).
    """
    total_aparicoes = freq.sum()
    media_teorica = total_aparicoes / config.n_numbers

    st.subheader("Equilíbrio Matemático (Lei dos Grandes Números)")
    st.markdown(
        f"""
        A linha vermelha pontilhada representa a **"Gravidade Estatística"** (~{media_teorica:.0f} vezes).
        Números muito acima tendem a descer (esfriar), e números muito abaixo tendem a subir (esquentar) para buscar o equilíbrio.
        """
    )

    c1, c2 = st.columns(2)

    # --- GRÁFICO 1: QUENTES ---
    with c1:
        st.markdown(f"**Os {num} Mais Quentes** (Acima da Média)")

        dados_quentes = freq.head(num).reset_index()
        dados_quentes.columns = ["Dezena", "Frequencia"]

        barras = (
            alt.Chart(dados_quentes)
            .mark_bar(color="#eab308")  # Yellow-500
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
        st.markdown(f"**Os {num} Mais Frios** (Abaixo da Média)")

        dados_frios = freq.tail(num).reset_index()
        dados_frios.columns = ["Dezena", "Frequencia"]

        barras_frias = (
            alt.Chart(dados_frios)
            .mark_bar(color="#0ea5e9")  # Sky-500
            .encode(
                x=alt.X("Dezena:O", sort="y", title="Dezena"),
                y=alt.Y("Frequencia", title="Saídas"),
                tooltip=["Dezena", "Frequencia"],
            )
        )

        st.altair_chart(barras_frias + regua, width="stretch")


def _render_heatmap_section(freq, conjuntos, config):
    """Renderiza mapa de calor interativo."""
    st.subheader("Mapa de Calor do Volante")
    st.markdown(
        "Identifique **zonas mortas** (claras) e **zonas quentes** (escuras) no desenho do volante."
    )

    col_graf, col_filtros = st.columns([2.5, 1])

    with col_filtros:
        with st.container(border=True):
            st.markdown("**🔎 Filtro de Padrão:**")
            filtro = st.radio(
                "Visualizar:", list(conjuntos.keys()), label_visibility="collapsed"
            )
            nums_filtro = conjuntos[filtro]

            # Mini estatística do filtro selecionado
            if not freq.empty:
                st.markdown("---")
                freq_filtro = freq[freq.index.isin(nums_filtro)]
                media_grupo = freq_filtro.mean() if not freq_filtro.empty else 0
                st.metric(
                    "Média de Saídas",
                    f"{media_grupo:.1f}",
                    help="Neste grupo específico",
                )

    with col_graf:
        _plot_heatmap_matplotlib(freq, nums_filtro, config)


def _plot_heatmap_matplotlib(freq, nums_filtro, config):
    """Plota mapa de calor usando matplotlib."""
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
        theme = config.as_constants_dict()
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
            face = "#f1f5f9"
            alpha = 1.0
            edge = "#cbd5e1"
            lw = 0.5
            txtcol = "#cbd5e1"
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


def _render_probability_report(conjuntos, config, svc, ctx):
    """
    Usa análise estatística avançada com distribuições empíricas.
    Mostra média, desvio-padrão e percentis baseados em dados reais.
    """
    st.subheader("Guia de Equilíbrio (Intervalos de Confiança)")
    st.write(
        "Abaixo você vê a **Assinatura Estatística** do jogo. 90% dos resultados históricos caem dentro do 'Intervalo Normal'."
    )

    # Filtra apenas os grupos geométricos relevantes para a análise
    grupos_geometricos = {
        "Moldura (Borda)": conjuntos["Moldura (Borda)"],
        "Miolo (Centro)": conjuntos["Miolo (Centro)"],
        "Cruz": conjuntos["Cruz"],
        "Xis (Diagonais)": conjuntos["Xis (Diagonais)"],
        "Cantos": conjuntos["Cantos"],
        "Primos": conjuntos["Primos"],
        "Quadrante 1": conjuntos["Quadrante 1 (Sup. Esq)"],
        "Quadrante 2": conjuntos["Quadrante 2 (Sup. Dir)"],
        "Quadrante 3": conjuntos["Quadrante 3 (Inf. Esq)"],
        "Quadrante 4": conjuntos["Quadrante 4 (Inf. Dir)"],
    }

    with st.expander("Abrir Relatório Estatístico Completo", expanded=False):
        # Só executa quando usuário abre o expander
        distribuicoes = svc.analyze_distributions(config.slug, grupos_geometricos)

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

        st.caption(
            f'💡 **Dica Estratégica:** Procure manter os seus jogos dentro da "Zona Segura". Por exemplo, se a Moldura tem média histórica de 10 e intervalo 8-12 (ou seja, volatilidade de 2), evite jogos com apenas 4 números na Moldura. Eles são estatisticamente raros.'
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
                    "Volatilidade",
                    help="Quanto menor, mais confiável é a média.",
                ),
                "Intervalo Normal": st.column_config.TextColumn(
                    "Zona Segura (90%)",
                    help="Tente manter seus jogos dentro desta faixa numérica.",
                ),
            },
            hide_index=True,
            width="stretch",
        )


def _render_regression_analysis(config, ctx):
    """
    Exibe análise de regressão à média validando a estratégia "agressiva".
    """

    with st.expander("📈 Validação Científica: Regressão à Média", expanded=False):

        regressao = ctx.taxa_regressao
        if not regressao:
            st.info("Dados insuficientes.")
            return

        st.markdown(
            "Analisamos os últimos 100 sorteios para responder: **Números atrasados realmente têm mais chance de sair?**"
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
                    <strong>Força da Tendência</strong><br>
                    <span style="font-size: 1.5em; color: {cor};">{regressao['correlacao']}</span><br>
                    <small>Correlação de Pearson entre atraso e saída futura</small>
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
                    <strong>Veredito</strong><br>
                    <span style="font-size: 1.1em; color: #92400e;">{regressao['interpretacao']}</span><br>
                    <small>p-value: {regressao['p_value']:.4f}</small><br>
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


def _render_z_score_gaps_section(tabela):
    """Renderiza tabela de inteligência (usa tabela do ctx)."""
    with st.expander("🤓 Bastidores: Tabela de Pesos (Z-Score & Gaps)"):
        st.write(
            'Esta é a matriz matemática usada pelo nosso Gerador. O "Peso" define a probabilidade de cada bola ser escolhida pela IA.'
        )
        st.dataframe(
            tabela.style.background_gradient(subset=["Peso_Geracao"], cmap="Greens"),
            width="stretch",
        )


def _render_ciclo_section(ciclo, config):
    """Renderiza o card de Ciclo das Dezenas."""
    if not ciclo:
        st.info("Dados de ciclo indisponíveis.")
        return

    with st.container(border=True):
        st.markdown("##### 🔄 Ciclo das Dezenas")

        c1, c2 = st.columns(2)
        c1.metric("Ciclo Atual", f"#{ciclo['ciclo_numero']}")
        c2.metric(
            "Rodadas",
            f"{ciclo['aberto_ha']}",
            help="Há quantos sorteios este ciclo está aberto.",
        )

        progresso = ciclo["progresso"] / 100
        st.caption(f"Progresso: {ciclo['progresso']:.1f}%")
        st.progress(progresso)

        faltam = ciclo["faltam_sair"]

        if not faltam:
            st.success(
                "✅ **Ciclo Fechado!** Todos os números saíram. Um novo ciclo começa no próximo sorteio."
            )
        else:
            st.markdown("**Faltam sair:**")
            # Renderiza bolinhas pequenas para os que faltam
            html = "<div style='display: flex; flex-wrap: wrap; gap: 5px;'>"
            for n in faltam:
                html += f"""
<div style="
    background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1;
    width: 28px; height: 28px; border-radius: 50%; 
    display: flex; align-items: center; justify-content: center; 
    font-weight: bold; font-size: 0.8rem;">
    {n:02d}
</div>
                """
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)

            if config.n_numbers <= 25:  # Lotofácil
                st.caption(
                    "💡 **Dica:** Fixar estes números costuma ser uma estratégia forte."
                )


def _render_temporal_charts(somas_data, repetidos_data, config):
    """Renderiza gráficos de Soma e Repetidos em abas."""

    tab_soma, tab_rep = st.tabs(
        ["📈 Eletrocardiograma (Soma)", "♻️ Repetidos do Anterior"]
    )

    with tab_soma:
        if not somas_data or not somas_data.get("dados"):
            st.info("Dados insuficientes.")
        else:
            df_soma = pd.DataFrame(somas_data["dados"])
            min_ideal = somas_data["min_ideal"]
            max_ideal = somas_data["max_ideal"]

            st.caption(
                f"A faixa verde ({min_ideal} - {max_ideal}) é a zona segura. Picos fora dela indicam 'zebras'."
            )

            # Gráfico Base
            base = alt.Chart(df_soma).encode(
                x=alt.X("Concurso:O", axis=alt.Axis(labels=False))
            )

            # Linha da Soma
            line = base.mark_line(point=True, color="#3b82f6").encode(
                y=alt.Y("Soma", scale=alt.Scale(zero=False)),
                tooltip=["Concurso", "Soma", "Status"],
            )

            # Faixa Ideal (Retângulo de fundo)
            rect = (
                alt.Chart(pd.DataFrame({"y": [min_ideal], "y2": [max_ideal]}))
                .mark_rect(color="green", opacity=0.1)
                .encode(y="y", y2="y2")
            )

            st.altair_chart(rect + line, width="stretch")

    with tab_rep:
        if not repetidos_data or not repetidos_data.get("dados"):
            st.info("Dados insuficientes.")
        else:
            df_rep = pd.DataFrame(repetidos_data["dados"])
            media = repetidos_data["media_repetidos"]

            st.caption(
                f"Média histórica: **{media:.1f} repetidos** por sorteio. Tente jogar perto disso."
            )

            barras = (
                alt.Chart(df_rep)
                .mark_bar(color="#a855f7")
                .encode(
                    x=alt.X("Concurso:O", axis=alt.Axis(labels=False)),
                    y=alt.Y("Repetidos"),
                    tooltip=["Concurso", "Repetidos"],
                )
            )

            regua = (
                alt.Chart(pd.DataFrame({"y": [media]}))
                .mark_rule(color="red", strokeDash=[3, 3])
                .encode(y="y")
            )

            st.altair_chart(barras + regua, width="stretch")


def _render_momentum_section(tendencias):
    """Renderiza cards de números em alta e baixa (estilo bolsa de valores)."""
    st.subheader("Momento do Jogo")
    st.write(
        'Diferente dos "Quentes", estes são os números que estão **mudando de comportamento** recentemente.'
    )
    if tendencias and (tendencias["alta"] or tendencias["baixa"]):
        with st.expander("Números em Tendência", expanded=False):
            c1, c2 = st.columns(2)

            with c1:
                st.markdown("##### Em Alta")
                if not tendencias["alta"]:
                    st.caption("Nenhum número em tendência clara de alta no momento.")
                else:
                    for item in tendencias["alta"]:
                        n = item["numero"]
                        slope = item["slope"] * 100  # Multiplica para ficar legível
                        st.markdown(
                            f"""
        <div style="
            display: flex; justify-content: space-between; align-items: center;
            background: #f0fdf4; border: 1px solid #bbf7d0; 
            padding: 8px 12px; border-radius: 6px; margin-bottom: 6px;">
            <span style="font-weight: bold; font-size: 1.1rem; color: #166534;">Nº {n:02d}</span>
            <div style="text-align: right;">
                <span style="color: #16a34a; font-weight: bold;">+{slope:.2f}%</span><br>
                <span style="font-size: 0.7rem; color: #15803d;">força da subida</span>
            </div>
        </div>
                            """,
                            unsafe_allow_html=True,
                        )

            with c2:
                st.markdown("##### Em Baixa")
                if not tendencias["baixa"]:
                    st.caption("Nenhum número em tendência clara de baixa no momento.")
                else:
                    for item in tendencias["baixa"]:
                        n = item["numero"]
                        slope = item["slope"] * 100
                        st.markdown(
                            f"""
        <div style="
            display: flex; justify-content: space-between; align-items: center;
            background: #fef2f2; border: 1px solid #fecaca; 
            padding: 8px 12px; border-radius: 6px; margin-bottom: 6px;">
            <span style="font-weight: bold; font-size: 1.1rem; color: #991b1b;">Nº {n:02d}</span>
            <div style="text-align: right;">
                <span style="color: #dc2626; font-weight: bold;">{slope:.2f}%</span><br>
                <span style="font-size: 0.7rem; color: #b91c1c;">força da queda</span>
            </div>
        </div>
                            """,
                            unsafe_allow_html=True,
                        )
