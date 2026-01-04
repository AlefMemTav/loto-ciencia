import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from app.src.statistics import get_historico_jogos
from app.src.validator import validar_jogo


def render_bolao(df):
    st.subheader("👥 Auditoria de Bolão")
    st.write(
        "Cole todos os jogos do seu bolão aqui. Vamos analisar a qualidade do grupo e se há erros (jogos repetidos ou mal distribuídos)."
    )

    texto_bolao = st.text_area(
        "Cole os jogos (um por linha):",
        placeholder="01 02 03 04 05 06\n10 12 14 16 18 20\n...",
    )

    historico_set = get_historico_jogos(df)

    if st.button("🔍 Auditar Bolão"):
        # 1. Processamento dos Dados
        jogos_validos, jogos_invalidos, todos_numeros = _processar_input_jogos(
            texto_bolao
        )

        if not jogos_validos:
            st.warning("Nenhum jogo válido identificado. Verifique a formatação.")
            st.stop()

        # 2. Cálculo de Estatísticas
        stats = _calcular_estatisticas_grupo(jogos_validos, todos_numeros)

        # 3. Renderização dos Cards (KPIs)
        _renderizar_cards_kpi(stats)

        st.divider()

        # 4. Gráficos e Análise Técnica
        col_grafico, col_tecnica = st.columns([2, 1])

        with col_grafico:
            _renderizar_heatmap_bolao(todos_numeros)

        with col_tecnica:
            _renderizar_analise_qualidade(jogos_validos, todos_numeros, historico_set)

        # 5. Lista Simples e Erros
        _renderizar_lista_resumo(jogos_validos, historico_set)

        if jogos_invalidos:
            st.error(
                f"Ignoramos {len(jogos_invalidos)} linhas que não pareciam jogos válidos."
            )

        # 6. Relatório Detalhado
        _renderizar_detalhes_profundos(jogos_validos, historico_set)


# --- FUNÇÕES AUXILIARES (UI HELPERS) ---


def _processar_input_jogos(texto):
    """Lê o texto bruto e separa em jogos válidos e inválidos."""
    validos = []
    invalidos = []
    todos_nums = []

    linhas = texto.strip().split("\n")
    for linha in linhas:
        if not linha.strip():
            continue

        limpa = linha.replace(",", " ").replace("-", " ").replace(";", " ")
        try:
            nums = sorted(
                list(set([int(n) for n in limpa.split() if n.strip().isdigit()]))
            )
            if len(nums) == 6 and all(1 <= n <= 60 for n in nums):
                validos.append(nums)
                todos_nums.extend(nums)
            else:
                invalidos.append(linha)
        except:
            invalidos.append(linha)

    return validos, invalidos, todos_nums


def _calcular_estatisticas_grupo(jogos, todos_numeros):
    """Calcula métricas financeiras e de cobertura."""
    qtd = len(jogos)
    custo = qtd * 6.00

    # Verifica duplicatas comparando tamanho da lista vs set de tuplas
    jogos_tuple = [tuple(j) for j in jogos]
    tem_duplicata = len(jogos_tuple) != len(set(jogos_tuple))

    unicos = len(set(todos_numeros))
    cobertura_perc = (unicos / 60) * 100

    return {
        "qtd": qtd,
        "custo": custo,
        "duplicata": tem_duplicata,
        "unicos": unicos,
        "cobertura": cobertura_perc,
    }


def _renderizar_cards_kpi(stats):
    """Exibe os 4 cards principais no topo."""
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total de Jogos", stats["qtd"])
    k2.metric("Custo Total", f"R$ {stats['custo']:,.2f}")
    k3.metric(
        "Cobertura do Volante", f"{stats['unicos']}/60 ({stats['cobertura']:.0f}%)"
    )

    if stats["duplicata"]:
        k4.metric("Duplicatas?", "SIM ⚠️", delta="Erro", delta_color="inverse")
        st.error(
            "⚠️ **ATENÇÃO:** Existem jogos idênticos repetidos na lista! Você está pagando duas vezes pelo mesmo bilhete."
        )
    else:
        k4.metric("Duplicatas?", "Não", delta="Ok")


def _renderizar_heatmap_bolao(todos_numeros):
    """Gera e exibe o mapa de calor com Matplotlib."""
    st.markdown("##### 🔥 Mapa de Calor do Bolão")
    st.caption(
        "Quais números seu grupo está jogando mais? (Mais escuro = Mais apostado)"
    )

    contagem = pd.Series(todos_numeros).value_counts().sort_index()
    max_freq = contagem.max() if not contagem.empty else 1

    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.set_xlim(-0.5, 9.5)
    ax.set_ylim(-0.5, 5.5)
    ax.axis("off")

    for n in range(1, 61):
        qtd = contagem.get(n, 0)

        # Lógica de cor
        if qtd == 0:
            color = "#f0f0f0"
            alpha = 1
        else:
            color = "green"
            alpha = 0.2 + (0.8 * (qtd / max_freq))

        ax.add_patch(
            plt.Circle(((n - 1) % 10, 5 - (n - 1) // 10), 0.4, color=color, alpha=alpha)
        )

        # Texto do número
        ax.text(
            (n - 1) % 10,
            5 - (n - 1) // 10,
            str(n),
            ha="center",
            va="center",
            fontsize=6,
        )

        # Texto da quantidade (se houver)
        if qtd > 0:
            ax.text(
                (n - 1) % 10,
                5 - (n - 1) // 10 - 0.25,
                f"x{qtd}",
                ha="center",
                va="center",
                fontsize=4,
                color="black",
            )

    st.pyplot(fig)


def _renderizar_analise_qualidade(jogos, todos_numeros, historico):
    """Calcula score médio e mostra números esquecidos."""
    st.markdown("##### 🌡️ Qualidade Técnica")

    scores = [validar_jogo(j, historico_jogos=historico)["score"] for j in jogos]
    media_score = sum(scores) / len(scores) if scores else 0

    st.metric("Score Médio do Grupo", f"{media_score:.0f}/100")

    if media_score < 60:
        st.warning("Seu bolão tem muitos jogos 'ruins' estatisticamente.")
    else:
        st.success("O bolão está bem equilibrado.")

    st.markdown("**Números Esquecidos:**")
    esquecidos = [str(n) for n in range(1, 61) if n not in todos_numeros]

    if esquecidos:
        st.caption(f"Vocês não jogaram: {', '.join(esquecidos)}")
    else:
        st.success("Parabéns! Vocês cercaram todos os 60 números.")


def _renderizar_lista_resumo(jogos, historico):
    """Exibe o expander com a lista simples."""
    with st.expander("📋 Ver Lista Detalhada dos Jogos"):
        for i, jogo in enumerate(jogos):
            val = validar_jogo(jogo, historico_jogos=historico)
            icone = "🟢" if val["score"] >= 80 else "🟡" if val["score"] >= 50 else "🔴"
            st.write(f"**Jogo {i+1}:** {jogo} {icone} (Score: {val['score']})")


def _renderizar_detalhes_profundos(jogos, historico):
    """Exibe a seção final com cards detalhados jogo a jogo."""
    st.write("---")
    st.subheader("📋 Detalhes Jogo a Jogo")
    st.caption(
        "Clique no jogo para ver a análise individual completa (Gauss, Quadrantes, Alertas)."
    )

    for i, jogo in enumerate(jogos):
        val = validar_jogo(jogo, historico_jogos=historico)

        if val["score"] >= 80:
            icone, label = "🟢", "Excelente"
        elif val["score"] >= 50:
            icone, label = "🟡", "Razoável"
        else:
            icone, label = "🔴", "Fraco"

        with st.expander(
            f"{icone} Jogo {i+1}: {jogo} — Score: {val['score']} ({label})"
        ):
            for msg in val["msgs"]:
                if "✅" in msg:
                    st.caption(msg)
                elif "⚠️" in msg:
                    st.warning(msg)
                elif "❌" in msg:
                    st.error(msg)

            soma = sum(jogo)
            pares = len([n for n in jogo if n % 2 == 0])
            st.text(f"📊 Soma: {soma} | Pares: {pares}")
