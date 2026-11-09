# app/ui/bolao.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from app.core.logger import logger
from app.core.lottery import GameConfig


def render_bolao(ctx, svc):
    config = ctx.config
    slug = config.slug
    df = ctx.df
    constants = config.as_constants_dict()
    main_color = constants.get("heat_color", "#ef4444")

    st.markdown(
        f"""
        <div style="background: linear-gradient(90deg, #f8fafc 0%, #e2e8f0 100%); padding: 20px; border-radius: 10px; border-left: 5px solid {main_color}; margin-bottom: 25px;">
            <h2 style="color: #1e293b; margin:0;">👥 Auditoria de Bolão: <span style="color: {main_color};">{config.name}</span></h2>
            <p style="color: #475569; font-size: 1rem; margin-top: 5px;">
                Analise a <strong>Inteligência Coletiva</strong> do seu grupo. Descubra vícios, jogos repetidos, 
                buracos na cobertura e a qualidade estatística global das apostas.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- ÁREA DE INPUT ---
    with st.container(border=True):
        col_inst, col_input = st.columns([1, 2])

        qtd_aposta = config.bet_size

        # Exemplo dinâmico
        ex1 = " ".join([f"{n:02d}" for n in range(1, qtd_aposta + 1)])
        ex2 = " ".join([f"{n:02d}" for n in range(3, qtd_aposta + 3)])

        with col_inst:
            st.markdown("#### 📥 Como usar?")
            st.markdown("""
                1. Exporte seus jogos (Excel/Txt).
                2. Copie apenas os números.
                3. Cole na caixa ao lado.
                """)
            st.info(
                f"**Formatos aceitos:**\n\n"
                f"• `01 02 03...` (Espaço)\n"
                f"• `01,02,03...` (Vírgula)\n"
                f"• `01-02-03...` (Hífen)\n\n"
                f"Um jogo por linha.",
                icon="ℹ️",
            )

        with col_input:
            texto_bolao = st.text_area(
                "📋 Cole a lista de jogos aqui:",
                placeholder=f"{ex1}\n{ex2}\n...",
                height=250,
                help="O sistema limpará espaços extras e caracteres estranhos automaticamente.",
            )

    # Botão de Ação
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(
        "🔍 Auditar Qualidade do Grupo",
        type="primary",
        width="stretch",
    ):
        if not texto_bolao.strip():
            st.warning("⚠️ A caixa de texto está vazia.")
            st.stop()

        # 1. Processamento dos Dados
        with st.spinner("Analisando matematicamente cada aposta..."):
            jogos_validos, jogos_invalidos, todos_numeros = _processar_input_jogos(
                texto_bolao, config
            )

        # 2. Validação Inicial
        if not jogos_validos:
            st.error(
                "❌ Nenhum jogo válido identificado. Verifique se a quantidade de números por linha está correta."
            )
            if jogos_invalidos:
                st.caption(f"Exemplo de linha rejeitada: `{jogos_invalidos[0]}`")
            st.stop()

        # 3. Cálculo de Estatísticas
        stats = _calcular_estatisticas_grupo(jogos_validos, todos_numeros, config)

        # 4. Renderização dos Resultados
        st.markdown("---")
        st.subheader("Relatório de Auditoria")

        # KPIs Principais
        _renderizar_cards_kpi(stats)

        # Alerta de Duplicatas (Crítico)
        if stats["duplicata"]:
            st.error(
                """
                🚨 **ALERTA CRÍTICO: JOGOS REPETIDOS DETECTADOS!**
                
                Existem jogos idênticos na sua lista. Isso significa que você está pagando 
                duas vezes pela mesma combinação matemática. Remova as duplicatas antes de registrar!
                """,
                icon="💸",
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # Layout Gráfico + Técnico
        col_grafico, col_tecnica = st.columns([1.5, 1])

        with col_grafico:
            with st.container(border=True):
                _renderizar_heatmap_bolao(todos_numeros, config)

        with col_tecnica:
            with st.container(border=True):
                _renderizar_analise_qualidade(jogos_validos, todos_numeros, ctx, svc)

        # Lista de Erros (se houver)
        if jogos_invalidos:
            with st.expander(
                f"⚠️ {len(jogos_invalidos)} Linhas Ignoradas (Formato Inválido)",
                expanded=False,
            ):
                st.caption(
                    "Estas linhas não tinham a quantidade correta de números ou continham caracteres inválidos:"
                )
                st.code(
                    "\n".join(jogos_invalidos[:10])
                    + ("\n..." if len(jogos_invalidos) > 10 else "")
                )

        # Detalhamento Profundo
        _renderizar_detalhes_profundos(jogos_validos, ctx, svc)

        st.markdown("---")

        # Compartilhar
        st.subheader("📱 Compartilhar no Grupo")

        # Calcula média rápida para o texto
        scores_temp = [svc.validate(slug, j)["score"] for j in jogos_validos]
        media_temp = sum(scores_temp) / len(scores_temp) if scores_temp else 0

        msg_whats = _gerar_texto_whatsapp(stats, media_temp, config)

        c_txt, c_btn = st.columns([3, 1])
        with c_txt:
            st.text_area("Copie o texto abaixo:", value=msg_whats, height=180)
        with c_btn:
            st.info(
                "👆 Copie o texto ao lado e cole no grupo do seu bolão para mostrar transparência e profissionalismo."
            )
        # ---------------------------------------------


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

        # Limpeza agressiva: troca tudo que não é digito por espaço
        limpa = (
            linha.replace(",", " ")
            .replace("-", " ")
            .replace(";", " ")
            .replace(".", " ")
        )
        try:
            # Extrai números
            nums = sorted(
                list(set([int(n) for n in limpa.split() if n.strip().isdigit()]))
            )

            # Valida regras do jogo
            if len(nums) == qtd_esperada and all(
                1 <= n <= config.n_numbers for n in nums
            ):
                validos.append(nums)
                todos_nums.extend(nums)
            else:
                invalidos.append(linha)
        except:
            invalidos.append(linha)

    return validos, invalidos, todos_nums


def _calcular_estatisticas_grupo(jogos, todos_numeros, config: GameConfig):
    """Calcula métricas financeiras e de cobertura."""
    qtd = len(jogos)
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

    k1.metric(
        "Total de Jogos", stats["qtd"], help="Quantidade de linhas válidas processadas."
    )
    k2.metric(
        "Custo Estimado",
        f"R$ {stats['custo']:,.2f}",
        help="Valor aproximado na lotérica.",
    )
    k3.metric(
        "Cobertura do Volante",
        f"{stats['cobertura']:.1f}%",
        f"{stats['unicos']}/{stats['universo']} Números",
        help="Quantos números únicos do volante foram usados no total.",
    )

    if stats["duplicata"]:
        k4.metric(
            "Duplicatas",
            "SIM ⚠️",
            delta="-Erro",
            delta_color="inverse",
            help="Existem jogos idênticos.",
        )
    else:
        k4.metric(
            "Duplicatas",
            "Não",
            delta="Ok",
            delta_color="normal",
            help="Todos os jogos são únicos.",
        )


def _renderizar_heatmap_bolao(todos_numeros, config: GameConfig):
    st.markdown("##### 🔥 Mapa de Calor do Grupo")
    st.caption("Visualização da concentração das apostas no volante.")

    if not todos_numeros:
        st.info("Sem dados para o mapa.")
        return

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

    # Ajuste fino do raio das bolas
    r = 0.40
    if min(layout.rows, layout.cols) <= 5:
        r = 0.34
    elif min(layout.rows, layout.cols) >= 8:
        r = 0.38

    theme = config.as_constants_dict()
    heat_color = theme.get("heat_color", "#ef4444")

    for n in range(1, config.n_numbers + 1):
        qtd = contagem.get(n, 0)

        # Cor dinâmica
        if qtd == 0:
            color = "#f1f5f9"  # Slate 100
            alpha = 1
            text_color = "#cbd5e1"
        else:
            color = heat_color
            # Alpha mínimo 0.2 para ver a cor, max 1.0
            alpha = 0.2 + (0.8 * (qtd / max_freq))
            text_color = "white" if alpha > 0.6 else "black"

        row, col = config.layout.pos(n)
        y = config.layout.rows - 1 - row

        # Bola
        ax.add_patch(plt.Circle((col, y), r, color=color, alpha=alpha))
        # Número
        ax.text(
            col,
            y,
            str(n),
            ha="center",
            va="center",
            fontsize=7,
            fontweight="bold",
            color=text_color,
        )

        # Contador de frequência (pequeno abaixo)
        if qtd > 0:
            ax.text(
                col,
                y - 0.28,
                f"x{qtd}",
                ha="center",
                va="center",
                fontsize=5,
                color="#334155",
                fontweight="bold",
            )

    st.pyplot(fig)


def _renderizar_analise_qualidade(jogos, todos_numeros, ctx, svc):
    """Calcula score médio e mostra números esquecidos."""
    st.markdown("##### 🌡️ Diagnóstico Técnico")

    config = ctx.config
    slug = config.slug

    scores = []

    # Processa barra de progresso
    prog_bar = st.progress(0, text="Calculando qualidade...")

    total = len(jogos)
    for i, jogo in enumerate(jogos):
        val = svc.validate(slug, jogo)
        scores.append(val["score"])
        if i % 10 == 0:
            prog_bar.progress((i + 1) / total)

    prog_bar.empty()

    media_score = sum(scores) / len(scores) if scores else 0

    # Exibe Score Médio com cor condicional
    cor_score = "red"
    if media_score >= 80:
        cor_score = "green"
    elif media_score >= 60:
        cor_score = "orange"

    st.markdown(
        f"""
        <div style="text-align: center; margin: 10px 0;">
            <span style="font-size: 0.9rem; color: #64748b;">Score Médio do Grupo</span><br>
            <span style="font-size: 2.5rem; font-weight: bold; color: {cor_score};">{media_score:.0f}</span>
            <span style="font-size: 1rem; color: #94a3b8;">/100</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if media_score < 60:
        st.warning(
            "⚠️ **Grupo Desequilibrado:** Muitos jogos com baixa probabilidade estatística.",
            icon="📉",
        )
    elif media_score < 80:
        st.info(
            "✅ **Grupo Equilibrado:** A maioria dos jogos segue o padrão.", icon="⚖️"
        )
    else:
        st.success(
            "💎 **Grupo de Elite:** Jogos otimizados matematicamente.", icon="🚀"
        )

    st.divider()

    st.markdown("**Números Esquecidos (Não Jogados):**")
    esquecidos = [n for n in range(1, config.n_numbers + 1) if n not in todos_numeros]

    if esquecidos:
        # Formata bonitinho como tags
        html_tags = "".join(
            [
                f"<span style='background:#f1f5f9; color:#64748b; padding:2px 6px; border-radius:4px; margin:2px; font-size:0.8rem; border:1px solid #e2e8f0;'>{n:02d}</span>"
                for n in sorted(esquecidos)
            ]
        )
        st.markdown(
            f"<div style='display:flex; flex-wrap:wrap;'>{html_tags}</div>",
            unsafe_allow_html=True,
        )
        st.caption(f"Total: {len(esquecidos)} números ignorados.")
    else:
        st.success("🏆 Cobertura Total! Vocês cercaram todos os números do volante.")


def _renderizar_detalhes_profundos(jogos, ctx, svc):
    """Exibe a lista detalhada com formatação visual."""
    st.subheader("Detalhes Jogo a Jogo")

    config = ctx.config
    slug = config.slug

    # Tabela visual customizada em vez de expanders padrão
    for i, jogo in enumerate(jogos, 1):
        val = svc.validate(slug, jogo)
        score = val["score"]

        # Definição de estilo por score
        if score >= 80:
            border_color = "#22c55e"  # Green
            bg_badge = "#dcfce7"
            color_badge = "#166534"
            label = "Excelente"
        elif score >= 60:
            border_color = "#eab308"  # Yellow
            bg_badge = "#fef9c3"
            color_badge = "#854d0e"
            label = "Bom"
        else:
            border_color = "#ef4444"  # Red
            bg_badge = "#fee2e2"
            color_badge = "#991b1b"
            label = "Fraco"

        nums_fmt = " ".join([f"{n:02d}" for n in sorted(jogo)])

        with st.expander(f"Jogo #{i:02d} | {nums_fmt}"):
            c1, c2 = st.columns([3, 1])

            with c1:
                # Mensagens de validação
                for msg in val["msgs"]:
                    if "✅" in msg:
                        st.markdown(
                            f"<span style='color:#16a34a; font-size:0.9rem;'>{msg}</span>",
                            unsafe_allow_html=True,
                        )
                    elif "⚠️" in msg:
                        st.markdown(
                            f"<span style='color:#d97706; font-size:0.9rem;'>{msg}</span>",
                            unsafe_allow_html=True,
                        )
                    elif "❌" in msg:
                        st.markdown(
                            f"<span style='color:#dc2626; font-size:0.9rem;'>{msg}</span>",
                            unsafe_allow_html=True,
                        )

            with c2:
                # Badge de Score Grande
                st.markdown(
                    f"""
                    <div style="
                        background-color: {bg_badge}; 
                        color: {color_badge}; 
                        border: 1px solid {border_color};
                        border-radius: 8px; 
                        padding: 10px; 
                        text-align: center;
                    ">
                        <div style="font-size: 0.8rem; font-weight: bold;">SCORE</div>
                        <div style="font-size: 1.8rem; font-weight: 800; line-height: 1;">{score}</div>
                        <div style="font-size: 0.7rem;">{label}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Métricas rápidas
                metricas = val.get("metricas", {})
                st.caption(f"Soma: {metricas.get('soma', '-')}")
                st.caption(f"Pares: {metricas.get('pares', '-')}")


def _gerar_texto_whatsapp(stats, media_score, config: GameConfig):
    """Gera um texto formatado para colar no grupo."""
    emoji_qualidade = "💎" if media_score >= 80 else "✅" if media_score >= 60 else "⚠️"

    txt = f"*BOLÃO {config.name.upper()}* 🎱\n"
    txt += f"--------------------------------\n"
    txt += f"📊 *Resumo da Auditoria:*\n"
    txt += f"• Jogos: {stats['qtd']}\n"
    txt += f"• Custo Total: R$ {stats['custo']:,.2f}\n"
    txt += f"• Cobertura: {stats['cobertura']:.1f}% do volante\n"
    txt += f"• Qualidade Técnica: {media_score:.0f}/100 {emoji_qualidade}\n"
    txt += f"--------------------------------\n"

    if stats["duplicata"]:
        txt += f"🚨 *ATENÇÃO:* Há jogos duplicados!\n"

    txt += f"🔍 *Validado por LotoCiencia*"
    return txt
