import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from app.src.logger import logger
from app.src.games import GameConfig
from app.src.statistics import analise_intervalo_confianca, get_historico_jogos
from app.src.validator import validar_jogo
from app.ui.game_constants import get_constants_for_game


def render_bolao(df, config: GameConfig):
    st.subheader("👥 Auditoria de Bolão")
    st.write(
        f"Cole todos os jogos do seu bolão da {config.name} aqui. Vamos analisar a qualidade do grupo e se há erros (jogos repetidos ou mal distribuídos)."
    )

    qtd_aposta = config.bet_size

    # Ajusta o range para não estourar o limite de números do jogo (ex: range(4, 54) na Lotomania)
    start_ex1 = 1
    end_ex1 = start_ex1 + qtd_aposta

    nums_exemplo1 = " ".join([f"{n:02d}" for n in range(start_ex1, end_ex1)])

    # Segundo exemplo deslocado
    start_ex2 = 2
    end_ex2 = start_ex2 + qtd_aposta
    nums_exemplo2 = " ".join([f"{n:02d}" for n in range(start_ex2, end_ex2)])

    texto_bolao = st.text_area(
        "Cole os jogos (um por linha):",
        placeholder=f"{nums_exemplo1}\n{nums_exemplo2}\n...",
        height=200,
    )

    historico_set = get_historico_jogos(df, config)

    if st.button("🔍 Auditar Bolão"):
        # 1. Processamento dos Dados
        jogos_validos, jogos_invalidos, todos_numeros = _processar_input_jogos(
            texto_bolao, config
        )
        ic_info = analise_intervalo_confianca(df, config)

        if not jogos_validos:
            st.warning(
                "Nenhum jogo válido identificado. Verifique a formatação e a quantidade de números."
            )
            if jogos_invalidos:
                st.caption(f"Exemplo de linha rejeitada: {jogos_invalidos[0]}")
            st.stop()

        # 2. Cálculo de Estatísticas
        stats = _calcular_estatisticas_grupo(jogos_validos, todos_numeros, config)

        # 3. Renderização dos Cards (KPIs)
        _renderizar_cards_kpi(stats)

        st.divider()

        # 4. Gráficos e Análise Técnica
        col_grafico, col_tecnica = st.columns([2, 1])

        with col_grafico:
            _renderizar_heatmap_bolao(todos_numeros, config)

        with col_tecnica:
            _renderizar_analise_qualidade(
                jogos_validos, todos_numeros, historico_set, ic_info, config
            )

        # 5. Lista Simples e Erros
        _renderizar_lista_resumo(jogos_validos, historico_set, ic_info, config)
        if jogos_invalidos:
            st.error(
                f"Ignoramos {len(jogos_invalidos)} linhas que não pareciam jogos válidos (quantidade incorreta ou caracteres inválidos)."
            )

        # 6. Relatório Detalhado
        _renderizar_detalhes_profundos(jogos_validos, historico_set, ic_info, config)


# --- FUNÇÕES AUXILIARES (UI HELPERS) ---


def _processar_input_jogos(texto, config: GameConfig):
    """Lê o texto bruto e separa em jogos válidos e inválidos."""
    validos = []
    invalidos = []
    todos_nums = []

    qtd_esperada = config.bet_size

    linhas = texto.strip().split("\n")
    logger.info(f"Processando input de bolão: {len(linhas)} linhas para {config.name}")

    for linha in linhas:
        if not linha.strip():
            continue

        limpa = linha.replace(",", " ").replace("-", " ").replace(";", " ")
        try:
            nums = sorted(
                list(set([int(n) for n in limpa.split() if n.strip().isdigit()]))
            )

            # Valida usando qtd_esperada (50 para Mania, k para outros)
            if len(nums) == qtd_esperada and all(
                1 <= n <= config.n_numbers for n in nums
            ):
                validos.append(nums)
                todos_nums.extend(nums)
            else:
                invalidos.append(linha)
        except:
            invalidos.append(linha)

    if invalidos:
        logger.warning(
            f"Auditoria de Bolão: {len(invalidos)} linhas inválidas rejeitadas."
        )
        logger.debug(f"Amostra inválida: {invalidos[0]}")

    if validos:
        logger.info(f"Auditoria de Bolão: {len(validos)} jogos válidos processados.")

    return validos, invalidos, todos_nums


def _calcular_estatisticas_grupo(jogos, todos_numeros, config: GameConfig):
    """Calcula métricas financeiras e de cobertura."""
    qtd = len(jogos)
    # Usa preço do jogo definido na config
    preco = config.game_price
    custo = qtd * preco

    # Verifica duplicatas comparando tamanho da lista vs set de tuplas
    jogos_tuple = [tuple(j) for j in jogos]
    tem_duplicata = len(jogos_tuple) != len(set(jogos_tuple))

    unicos = len(set(todos_numeros))
    cobertura_perc = (unicos / config.n_numbers) * 100

    return {
        "qtd": qtd,
        "custo": custo,
        "duplicata": tem_duplicata,
        "unicos": unicos,
        "cobertura": cobertura_perc,
        "universo": config.n_numbers,
    }


def _renderizar_cards_kpi(stats):
    """Exibe os 4 cards principais no topo."""
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total de Jogos", stats["qtd"])
    k2.metric("Custo Total", f"R$ {stats['custo']:,.2f}")
    k3.metric(
        "Cobertura do Volante",
        f"{stats['unicos']}/{stats['universo']} ({stats['cobertura']:.0f}%)",
    )

    if stats["duplicata"]:
        k4.metric("Duplicatas?", "SIM ⚠️", delta="Erro", delta_color="inverse")
        st.error(
            "⚠️ **ATENÇÃO:** Existem jogos idênticos repetidos na lista! Você está pagando duas vezes pelo mesmo bilhete."
        )
    else:
        k4.metric("Duplicatas?", "Não", delta="Ok")


def _renderizar_heatmap_bolao(todos_numeros, config: GameConfig):
    st.markdown("##### 🔥 Mapa de Calor do Bolão")
    st.caption(
        "Quais números seu grupo está jogando mais? (Mais escuro = Mais apostado)"
    )

    contagem = pd.Series(todos_numeros).value_counts().sort_index()
    max_freq = contagem.max() if not contagem.empty else 1

    layout = config.layout

    base_w = 6.8
    aspect = layout.rows / layout.cols if layout.cols else 1.0
    fig_h = max(3.2, base_w * aspect)
    fig, ax = plt.subplots(figsize=(base_w, fig_h))

    ax.set_xlim(-0.5, layout.cols - 0.5)
    ax.set_ylim(-0.5, layout.rows - 0.5)
    ax.axis("off")
    ax.set_aspect("equal", adjustable="box")

    # raio adaptativo
    r = 0.40
    if min(layout.rows, layout.cols) <= 5:
        r = 0.34
    elif min(layout.rows, layout.cols) >= 8:
        r = 0.38
    theme = get_constants_for_game(config)
    heat_color = theme["heat_color"]
    for n in range(1, config.n_numbers + 1):
        qtd = contagem.get(n, 0)

        if qtd == 0:
            color = "#f0f0f0"
            alpha = 1
        else:
            color = heat_color
            alpha = 0.2 + (0.8 * (qtd / max_freq))

        row, col = config.layout.pos(n)
        y = config.layout.rows - 1 - row

        ax.add_patch(plt.Circle((col, y), r, color=color, alpha=alpha))

        ax.text(col, y, str(n), ha="center", va="center", fontsize=6)

        if qtd > 0:
            ax.text(
                col,
                y - 0.25,
                f"x{qtd}",
                ha="center",
                va="center",
                fontsize=4,
                color="black",
            )

    st.pyplot(fig)


def _renderizar_analise_qualidade(jogos, todos_numeros, historico, ic_info, config):
    """Calcula score médio e mostra números esquecidos."""
    st.markdown("##### 🌡️ Qualidade Técnica")

    scores = [
        validar_jogo(j, config, historico_jogos=historico, ic_info=ic_info)["score"]
        for j in jogos
    ]
    media_score = sum(scores) / len(scores) if scores else 0

    st.metric("Score Médio do Grupo", f"{media_score:.0f}/100")

    if media_score < 60:
        st.warning("Seu bolão tem muitos jogos 'ruins' estatisticamente.")
    else:
        st.success("O bolão está bem equilibrado.")

    st.markdown("**Números Esquecidos:**")
    esquecidos = [
        str(n) for n in range(1, config.n_numbers + 1) if n not in todos_numeros
    ]

    if esquecidos:
        st.caption(f"Vocês não jogaram: {', '.join(esquecidos)}")
    else:
        st.success(f"Parabéns! Vocês cercaram todos os {config.n_numbers} números.")


def _renderizar_lista_resumo(jogos, historico, ic_info, config):
    """Exibe o expander com a lista simples."""
    with st.expander("📋 Ver Lista Detalhada dos Jogos"):
        for i, jogo in enumerate(jogos):
            val = validar_jogo(jogo, config, historico_jogos=historico, ic_info=ic_info)
            icone = "🟢" if val["score"] >= 80 else "🟡" if val["score"] >= 50 else "🔴"
            st.write(f"**Jogo {i+1}:** {jogo} {icone} (Score: {val['score']})")


def _renderizar_detalhes_profundos(jogos, historico, ic_info, config):
    """Exibe a seção final com cards detalhados jogo a jogo."""
    st.write("---")
    st.subheader("📋 Detalhes Jogo a Jogo")
    st.caption(
        "Clique no jogo para ver a análise individual completa (Gauss, Quadrantes, Alertas)."
    )

    for i, jogo in enumerate(jogos):
        val = validar_jogo(jogo, config, historico_jogos=historico, ic_info=ic_info)

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
