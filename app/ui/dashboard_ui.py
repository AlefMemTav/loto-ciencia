import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from app.src.constants import (
    CANTOS,
    CRUZ,
    LOST_NUMBERS,
    MIOLO,
    PRIMOS,
    FIBONACCI,
    GEMEOS,
    MOLDURA,
    Q1,
    Q2,
    Q3,
    Q4,
    XIS,
)
from app.src.statistics import get_reis_da_sequencia


def render_dashboard(df, freq, poisson_finais):
    st.markdown("### 🔭 Panorama Geral da Mega-Sena")

    _render_kpis(freq, df)

    st.divider()

    reis_seq = get_reis_da_sequencia(df)
    top_quentes = freq.head(15).index.tolist()
    top_frios = freq.tail(15).index.tolist()

    # Tratamento seguro para último sorteio
    if not df.empty:
        ultimo_idx = df.index.max()
        # Garante que é uma lista plana
        ultimo_sorteio = df.loc[
            ultimo_idx, ["D1", "D2", "D3", "D4", "D5", "D6"]
        ].values.tolist()
    else:
        ultimo_sorteio = []

    conjuntos = {
        "Todos os Números": list(range(1, 61)),
        "Top 15 Mais Quentes": top_quentes,
        "Top 15 Mais Frios": top_frios,
        "Último Sorteio": ultimo_sorteio,
        "Moldura": list(MOLDURA),
        "Miolo": MIOLO,
        "Cruz": CRUZ,
        "Xis": XIS,
        "Cantos": CANTOS,
        "Primos": PRIMOS,
        "Perdidos": LOST_NUMBERS,
        "Fibonacci": FIBONACCI,
        "Gêmeos": GEMEOS,
        "Reis da Sequência": reis_seq,
        "Quadrante 1 (Sup. Esq)": Q1,
        "Quadrante 2 (Sup. Dir)": Q2,
        "Quadrante 3 (Inf. Esq)": Q3,
        "Quadrante 4 (Inf. Dir)": Q4,
    }

    _render_heatmap_section(freq, conjuntos)

    st.divider()

    _render_probability_report(df, conjuntos)

    st.divider()

    _render_bar_charts(freq, 10)

    if poisson_finais:
        st.info("🧬 **Análise de Poisson:** Dígitos finais estatisticamente atrasados:")
        cols = st.columns(len(poisson_finais))
        for i, item in enumerate(poisson_finais):
            cols[i].metric(f"Final {item['digito']}", f"p={item['p_value']}")


def _render_kpis(freq, df):
    if not freq.empty:
        num_mais = freq.idxmax()
        qtd_mais = freq.max()
        num_menos = freq.idxmin()
        qtd_menos = freq.min()
        media = freq.mean()
    else:
        num_mais, qtd_mais, num_menos, qtd_menos, media = 0, 0, 0, 0, 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total de Jogos", len(df))
    k2.metric("Rei da Mesa (Mais Saiu)", f"Nº {num_mais}", f"{qtd_mais} vezes")
    k3.metric("O Esquecido (Menos Saiu)", f"Nº {num_menos}", f"{qtd_menos} vezes")
    k4.metric("Média", f"{media:.1f} vezes")


def _render_heatmap_section(freq, conjuntos):
    st.subheader("Mapa de Calor Interativo")
    st.caption("Número em cima / Quantidade de vezes que saiu embaixo.")
    col_graf, col_filtros = st.columns([3, 1])

    with col_filtros:
        st.markdown("**🔎 Filtros de Análise**")
        filtro = st.radio("Destaque:", list(conjuntos.keys()))
        nums_filtro = conjuntos[filtro]
        if not freq.empty:
            freq_filtro = freq[freq.index.isin(nums_filtro)]
            media_grupo = freq_filtro.mean()
            st.caption(f"Média de saída deste grupo: **{media_grupo:.1f}**")

            quente_grupo = freq_filtro.idxmax()
            st.caption(f"Mais quente do grupo: **{quente_grupo}**")

    with col_graf:
        _plot_heatmap_matplotlib(freq, nums_filtro)


def _plot_heatmap_matplotlib(freq, nums_filtro):
    """Helper privado para desenhar o gráfico"""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.set_xlim(-0.5, 9.5)
    ax.set_ylim(-0.5, 5.5)
    ax.axis("off")
    plt.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)

    max_val = freq.max() if not freq.empty else 1
    min_val = freq.min() if not freq.empty else 0

    for n in range(1, 61):
        row = (n - 1) // 10
        col = (n - 1) % 10
        val = freq.get(n, 0)

        if n in nums_filtro:
            intensity = (
                0.1 + (0.9 * ((val - min_val) / (max_val - min_val)))
                if max_val > min_val
                else 0.5
            )
            face = "green"
            alpha = intensity
            edge = "#444"
            lw = 1.5
            txt_col = "white" if intensity > 0.6 else "black"
            weight = "bold"
        else:
            face = "#f0f0f0"
            alpha = 0.3
            edge = "#e0e0e0"
            lw = 0.5
            txt_col = "#ccc"
            weight = "normal"

        ax.add_patch(
            plt.Circle((col, 5 - row), 0.42, color=face, alpha=alpha, ec=edge, lw=lw)
        )
        ax.text(
            col,
            5 - row + 0.1,
            str(n),
            ha="center",
            va="center",
            color=txt_col,
            fontweight=weight,
            fontsize=10,
        )
        if n in nums_filtro:
            ax.text(
                col,
                5 - row - 0.15,
                str(val),
                ha="center",
                va="center",
                color=txt_col,
                fontsize=7,
            )

    st.pyplot(fig, width="stretch")


def _render_probability_report(df, conjuntos):
    st.subheader("📊 Relatório de Probabilidade por Filtro")
    st.caption(
        "Baseado em todo o histórico, qual a chance de um sorteio cair COMPLETAMENTE dentro destes grupos?"
    )

    if df.empty:
        st.warning("Sem dados para calcular probabilidades.")
        return

    dados_relatorio = []
    # Pré-calcula sets (performance)
    historico_sets = [set(row) for row in df.values]
    total_concursos = len(historico_sets)

    progresso = st.progress(0)

    for i, (nome_filtro, lista_numeros) in enumerate(conjuntos.items()):
        set_filtro = set(lista_numeros)

        # Cálculo Estatístico
        ocorrencias_full = sum(
            1 for sorteio in historico_sets if sorteio.issubset(set_filtro)
        )
        probabilidade = (ocorrencias_full / total_concursos) * 100

        soma_acertos = sum(
            len(sorteio.intersection(set_filtro)) for sorteio in historico_sets
        )
        media_presenca = soma_acertos / total_concursos

        dados_relatorio.append(
            {
                "Filtro": nome_filtro,
                "Tamanho do Grupo": len(set_filtro),
                "Jogos Completos (6 acertos)": ocorrencias_full,
                "% Chance Histórica": f"{probabilidade:.4f}%",
                "Média de Dezenas por Jogo": f"{media_presenca:.1f}",
            }
        )
        progresso.progress((i + 1) / len(conjuntos))

    progresso.empty()

    df_rel = pd.DataFrame(dados_relatorio)
    df_rel = df_rel.sort_values(by="Jogos Completos (6 acertos)", ascending=False)

    st.dataframe(
        df_rel,
        column_config={
            "Filtro": st.column_config.TextColumn("Grupo / Padrão"),
            "Tamanho do Grupo": st.column_config.ProgressColumn(
                "Tamanho (de 60)", format="%d", min_value=0, max_value=60
            ),
            "% Chance Histórica": st.column_config.NumberColumn(
                "Probabilidade (Jogo Cheio)", format="%s"
            ),
            "Média de Dezenas por Jogo": st.column_config.NumberColumn(
                "Média Esperada",
                help="Quantos números desse grupo costumam sair em um sorteio normal.",
            ),
        },
        hide_index=True,
        width="stretch",
    )

    st.info(
        "💡 **Interpretação:** Filtros pequenos raramente contêm as 6 dezenas. O segredo é olhar a **'Média de Dezenas'**. Exemplo: Se a média dos Primos é 2.0, seus jogos devem ter cerca de 2 primos, e não 6."
    )


def _render_bar_charts(freq, num):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"#### 🔥 Top {num} Quentes")
        st.bar_chart(freq.head(num), color="#a79f28")
    with c2:
        st.markdown(f"#### ❄️ Top {num} Frios")
        st.bar_chart(freq.tail(num), color="#17a2b8")
