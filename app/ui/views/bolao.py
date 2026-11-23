# app/ui/bolao.py
import math
import numpy as np
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from app.cli.conferir import variancia_media_acertos_exata
from app.core.generator_objective import portfolio_diagnostics
from app.core.logger import logger
from app.core.lottery import GameConfig
from app.core.statistics.prize_model import (
    calcular_kelly_fracionado,
    estimar_ev_concurso_ex_ante,
)


def _brl(valor: float) -> str:
    """Formata valor monetário no padrão brasileiro (R$ 1.234,56)."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_bolao(ctx, svc):
    config = ctx.config
    slug = config.slug
    constants = config.as_constants_dict()
    main_color = constants.get("heat_color", "#ef4444")

    st.markdown(
        f"""
        <div style="background: linear-gradient(90deg, #f8fafc 0%, #e2e8f0 100%); padding: 20px; border-radius: 10px; border-left: 5px solid {main_color}; margin-bottom: 25px;">
            <h2 style="color: #1e293b; margin:0;">👥 Auditoria de Bolão: <span style="color: {main_color};">{config.name}</span></h2>
            <p style="color: #475569; font-size: 1rem; margin-top: 5px;">
                Analise a <strong>estrutura coletiva</strong> do seu grupo. Descubra jogos repetidos,
                concentração de dezenas, sobreposição, risco de divisão de prêmio e o impacto do ágio no EV.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Limpa estado anterior ao trocar de modalidade
    if st.session_state.get("last_bolao_slug") != slug:
        st.session_state.bolao_audit_data = None
        st.session_state.last_bolao_slug = slug

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
            nota_lm = (
                "\n• Na Lotomania, `00` é convertido automaticamente para `100`."
                if slug == "loto_mania_sorteio"
                else ""
            )
            st.info(
                f"**Formatos aceitos:**\n\n"
                f"• `01 02 03...` (Espaço)\n"
                f"• `01,02,03...` (Vírgula)\n"
                f"• `01-02-03...` (Hífen)\n\n"
                f"Um jogo por linha.{nota_lm}",
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
            st.session_state.bolao_audit_data = None
            st.stop()

        validacoes = [svc.validate(slug, j) for j in jogos_validos]
        stats = _calcular_estatisticas_grupo(jogos_validos, todos_numeros, config)
        st.session_state.bolao_audit_data = {
            "jogos_validos": jogos_validos,
            "jogos_invalidos": jogos_invalidos,
            "todos_numeros": todos_numeros,
            "validacoes": validacoes,
            "stats": stats,
        }

    audit_data = st.session_state.get("bolao_audit_data")
    if not audit_data:
        return

    jogos_validos = audit_data["jogos_validos"]
    jogos_invalidos = audit_data["jogos_invalidos"]
    todos_numeros = audit_data["todos_numeros"]
    validacoes = audit_data["validacoes"]
    stats = audit_data["stats"]

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
            _renderizar_analise_qualidade(
                jogos_validos, todos_numeros, ctx, svc, validacoes=validacoes
            )

    # Diagnóstico de Portfólio, Anti-Divisão & Simulador de Ágio
    st.markdown("<br>", unsafe_allow_html=True)
    _renderizar_portfolio_e_agio(jogos_validos, ctx, config)

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
    _renderizar_detalhes_profundos(
        jogos_validos, ctx, svc, validacoes=validacoes
    )

    st.markdown("---")

    # Compartilhar
    st.subheader("📱 Compartilhar no Grupo")

    scores_temp = [v["score"] for v in validacoes]
    media_temp = sum(scores_temp) / len(scores_temp) if scores_temp else 0

    msg_whats = _gerar_texto_whatsapp(stats, media_temp, config)

    c_txt, c_btn = st.columns([3, 1])
    with c_txt:
        st.text_area("Copie o texto abaixo:", value=msg_whats, height=180)
    with c_btn:
        st.info(
            "👆 Copie o texto ao lado e cole no grupo do seu bolão para mostrar transparência e profissionalismo."
        )


# --- FUNÇÕES AUXILIARES (UI HELPERS) ---


def _processar_input_jogos(texto, config: GameConfig):
    """Lê o texto bruto e separa em jogos válidos e inválidos."""
    validos = []
    invalidos = []
    todos_nums = []

    qtd_esperada = config.bet_size
    is_lotomania = config.slug == "loto_mania_sorteio"

    linhas = texto.strip().split("\n")
    logger.info(f"Processando input de bolão: {len(linhas)} linhas para {config.name}")

    for linha in linhas:
        if not linha.strip():
            continue

        # Limpeza: troca separadores comuns por espaço
        limpa = (
            linha.replace(",", " ")
            .replace("-", " ")
            .replace(";", " ")
            .replace(".", " ")
        )
        try:
            brutos = [int(n) for n in limpa.split() if n.strip().isdigit()]
            if is_lotomania:
                brutos = [100 if n == 0 else n for n in brutos]
            nums = sorted(set(brutos))

            # Valida regras do jogo
            if len(nums) == qtd_esperada and all(
                1 <= n <= config.n_numbers for n in nums
            ):
                validos.append(nums)
                todos_nums.extend(nums)
            else:
                invalidos.append(linha)
        except ValueError:
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
        "Custo Base (sem ágio)",
        _brl(stats["custo"]),
        help="Valor oficial das apostas na lotérica (sem taxa de serviço de bolão).",
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


def _renderizar_portfolio_e_agio(jogos_validos, ctx, config: GameConfig):
    """Renderiza diagnóstico de diversificação, popularidade e simulador de ágio de bolão."""
    with st.container(border=True):
        st.markdown("##### 📊 Diagnóstico de Portfólio, Anti-Divisão & Simulador de Ágio")

        arr_jogos = np.asarray(jogos_validos, dtype=int)
        diag = portfolio_diagnostics(arr_jogos, config)
        var_exata = variancia_media_acertos_exata(
            jogos_validos, config.n_numbers, config.k
        )
        dp_exato = math.sqrt(var_exata)

        modelo_pop = getattr(ctx, "modelo_popularidade", None)
        razao_media = 1.0
        q90_pop = 0.0
        if modelo_pop is not None:
            razoes = modelo_pop.razao_ganhadores_batch(arr_jogos)
            razao_media = float(np.mean(razoes))
            q90_pop = float(getattr(modelo_pop, "conformal_q90_log", 0.0) or 0.0)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric(
            "Overlap Máximo",
            f"{diag['overlap_max']}/{config.bet_size}",
            help=f"Overlap médio entre pares de jogos: {diag['overlap_medio']:.2f}.",
        )
        m2.metric(
            "Pares Repetidos (Máx.)",
            f"{diag['max_repeticao_par']}x",
            help="Maior frequência de um mesmo par de dezenas no pacote.",
        )
        m3.metric(
            "DP Hipergeométrico da Média",
            f"{dp_exato:.4f}",
            help="Desvio-padrão exato da média de acertos do pacote condicionado à exposição das dezenas (0 = exposição perfeitamente uniforme).",
        )
        m4.metric(
            "Razão de Ganhadores Média",
            f"{razao_media:.2f}x" if modelo_pop is not None else "N/D",
            help="1,00x = jogo médio; < 1,00x = tende a dividir prêmio com menos pessoas.",
        )

        st.markdown("---")
        agio_pct = st.slider(
            "Taxa de Serviço / Ágio do Bolão (%)",
            min_value=0.0,
            max_value=35.0,
            value=0.0,
            step=1.0,
            help="Bolões vendidos em lotéricas podem cobrar até 35% de tarifa de serviço sobre o valor das cotas.",
        )
        agio_frac = agio_pct / 100.0
        custo_base = len(jogos_validos) * config.game_price
        custo_com_agio = custo_base * (1.0 + agio_frac)

        ev_info = estimar_ev_concurso_ex_ante(
            config,
            razao_popularidade=razao_media,
            agio_bolao=agio_frac,
            conformal_q90_log_pop=q90_pop,
        )
        if ev_info.get("disponivel"):
            c_e1, c_e2, c_e3, c_e4 = st.columns(4)
            c_e1.metric(
                "Custo com Ágio",
                _brl(custo_com_agio),
                delta=f"+{_brl(custo_com_agio - custo_base)}" if agio_pct > 0 else "Sem ágio",
                delta_color="inverse" if agio_pct > 0 else "off",
            )
            c_e2.metric(
                "EV Líquido Ajustado",
                f"R$ {ev_info['ev_por_real_ajustado']:.3f} / R$ 1",
                help=f"IC conformal 90%: [{ev_info['ev_por_real_ic90_low']:.3f}, {ev_info['ev_por_real_ic90_high']:.3f}].",
            )
            c_e3.metric(
                "EV Jogo Aleatório",
                f"R$ {ev_info['ev_por_real_aleatorio']:.3f} / R$ 1",
                help="Retorno esperado de jogos aleatórios com o mesmo ágio.",
            )
            c_e4.metric(
                "Sinal Ex-Ante",
                ev_info.get("recomendacao_aposta", "INDISPONIVEL"),
            )
            if agio_pct >= 20.0:
                st.warning(
                    f"⚠️ Com ágio de **{agio_pct:.0f}%**, o retorno esperado por real cai proporcionalmente "
                    f"por 1/(1 + {agio_frac:.2f}), anulando grande parte do ganho anti-divisão."
                )
            elif ev_info.get("ev_por_real_ajustado", 0.0) > 1.0:
                kelly = calcular_kelly_fracionado(
                    config,
                    ev_por_real=float(ev_info["ev_por_real_ajustado"]),
                    pool1_estimado=float(ev_info.get("pool_faixa1_estimado", 0.0)),
                    banca=max(custo_com_agio, 100.0),
                    agio_bolao=agio_frac,
                )
                st.caption(
                    f"📐 Kelly fracionado (25%, teto 5% da banca): fração sugerida "
                    f"{kelly['f_kelly_fracionado'] * 100:.2f}%."
                )
        else:
            st.caption("ℹ️ Dados financeiros ex-ante indisponíveis para simular o EV com ágio.")


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
    plt.close(fig)


def _renderizar_analise_qualidade(
    jogos, todos_numeros, ctx, svc, validacoes=None
):
    """Calcula score médio e mostra números esquecidos."""
    st.markdown("##### 🌡️ Diagnóstico Técnico")

    config = ctx.config
    slug = config.slug

    if validacoes is None:
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
    else:
        scores = [v["score"] for v in validacoes]

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
            "⚠️ **Grupo Concentrado em Padrões Comuns/Extremos:** Muitos jogos com alto risco de divisão de prêmio ou fora da região típica combinatória.",
            icon="📉",
        )
    elif media_score < 80:
        st.info(
            "✅ **Grupo Equilibrado:** A maioria dos jogos segue o padrão estrutural e tem risco controlado de rateio.",
            icon="⚖️",
        )
    else:
        st.success(
            "💎 **Grupo Bem Estruturado:** Jogos diversificados e com baixo risco de divisão de prêmio.",
            icon="🚀",
        )

    st.divider()

    st.markdown("**Números Esquecidos (Não Jogados):**")
    todos_set = set(todos_numeros)
    esquecidos = [n for n in range(1, config.n_numbers + 1) if n not in todos_set]

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


def _renderizar_detalhes_profundos(jogos, ctx, svc, validacoes=None):
    """Exibe a lista detalhada com formatação visual."""
    st.subheader("Detalhes Jogo a Jogo")

    config = ctx.config
    slug = config.slug

    for i, jogo in enumerate(jogos, 1):
        val = (
            validacoes[i - 1]
            if validacoes is not None
            else svc.validate(slug, jogo)
        )
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
                # Mensagens de validação (inclui ℹ️ e 💸 de popularidade/rateio)
                for msg in val["msgs"]:
                    if "✅" in msg:
                        st.markdown(
                            f"<span style='color:#16a34a; font-size:0.9rem;'>{msg}</span>",
                            unsafe_allow_html=True,
                        )
                    elif "❌" in msg:
                        st.markdown(
                            f"<span style='color:#dc2626; font-size:0.9rem;'>{msg}</span>",
                            unsafe_allow_html=True,
                        )
                    elif "ℹ️" in msg:
                        st.markdown(
                            f"<span style='color:#2563eb; font-size:0.9rem;'>{msg}</span>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"<span style='color:#d97706; font-size:0.9rem;'>{msg}</span>",
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
                if metricas.get("popularidade_medida_razao") is not None:
                    st.caption(f"Rateio: {metricas['popularidade_medida_razao']:.2f}x")


def _gerar_texto_whatsapp(stats, media_score, config: GameConfig):
    """Gera um texto formatado para colar no grupo."""
    emoji_qualidade = "💎" if media_score >= 80 else "✅" if media_score >= 60 else "⚠️"

    txt = f"*BOLÃO {config.name.upper()}* 🎱\n"
    txt += f"--------------------------------\n"
    txt += f"📊 *Resumo da Auditoria:*\n"
    txt += f"• Jogos: {stats['qtd']}\n"
    txt += f"• Custo Base: {_brl(stats['custo'])}\n"
    txt += f"• Cobertura: {stats['cobertura']:.1f}% do volante\n"
    txt += f"• Qualidade Técnica: {media_score:.0f}/100 {emoji_qualidade}\n"
    txt += f"--------------------------------\n"

    if stats["duplicata"]:
        txt += f"🚨 *ATENÇÃO:* Há jogos duplicados!\n"

    txt += f"🔍 *Validado por LotoCiencia*"
    return txt
