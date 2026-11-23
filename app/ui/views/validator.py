# app/ui/views/validator.py
import math
import streamlit as st
import pandas as pd
from app.core.logger import logger
from app.ui.views.board import render_volante_marcado


def render_validator(ctx, svc):
    config = ctx.config
    slug = config.slug
    df = ctx.df
    constants = config.as_constants_dict()
    color = constants.get("heat_color", "#ef4444")

    # --- HEADER COM COPYWRITING ---
    st.markdown(
        f"""
        <div style="text-align: center; margin-bottom: 25px;">
            <h2 style="margin:0;">🔬 Auditor de Jogos <span style='color: {color};'>{config.name}</span></h2>
            <p style="color: #777; font-size: 1.1rem; margin-top: 5px;">
                Não jogue no escuro. Descubra se seus números são <strong>"viciados"</strong> ou se têm potencial matemático real.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    qtd_aposta = config.bet_size
    nums_exemplo = " ".join([f"{n:02d}" for n in range(1, 1 + qtd_aposta)])

    # --- ÁREA DE INPUT ---
    col_input, col_dica = st.columns([2, 1])

    with col_input:
        st.write(f"**Digite seus {qtd_aposta} números para o Raio-X:**")
        entrada = st.text_area(
            label="Números",
            label_visibility="collapsed",
            placeholder=f"Exemplo: {nums_exemplo} ...",
            height=100,
            help="Pode colar do Excel, WhatsApp ou digitar separado por espaço, vírgula ou traço.",
        )

    with col_dica:
        st.info(
            "💡 **Por que validar?**\n\n"
            "Jogos com padrões visuais (linhas, colunas) ou datas de aniversário "
            "costumam pagar **prêmios 90% menores** em caso de vitória."
        )

    # Limpa o resultado anterior se o usuário trocar de jogo ou mudar o texto
    if st.session_state.get("last_validator_slug") != slug:
        st.session_state.validator_result = None
        st.session_state.last_validator_slug = slug

    current_input_hash = (slug, hash(entrada))
    if st.session_state.get("last_validator_input") != current_input_hash:
        st.session_state.validator_result = None
        st.session_state.last_validator_input = current_input_hash

    # Botão de Ação
    if st.button(
        "🚀 Auditar Meu Jogo Agora",
        type="primary",
        width="stretch",
    ):
        try:
            texto = entrada.replace(",", " ").replace("-", " ").replace("\n", " ")
            nums_set = set()
            for token in texto.split():
                tk = token.strip()
                if not tk.isdigit():
                    continue
                val = int(tk)
                if slug == "loto_mania_sorteio" and val == 0:
                    val = 100
                nums_set.add(val)
            nums = sorted(nums_set)

            # Validações de Input
            if len(nums) != qtd_aposta:
                st.warning(
                    f"⚠️ Atenção: Você digitou **{len(nums)} números**. "
                    f"Para a {config.name}, precisamos de **exatamente {qtd_aposta}**."
                )
                return

            if not all(1 <= n <= config.n_numbers for n in nums):
                st.error(
                    f"❌ Erro: Existem números fora do volante (1 a {config.n_numbers})."
                )
                return

            # Spinner com texto rico
            with st.spinner("🤖 A IA está analisando vários filtros estatísticos..."):
                logger.info(f"[{config.name}] Validação manual: {nums}")

                # 1. Gera o relatório
                relatorio = svc.validate(slug, nums)

                # 2. Salva no Estado
                st.session_state.validator_result = {
                    "relatorio": relatorio,
                    "nums": nums,
                    "slug": slug,
                    "config": config,
                    "new": True,
                }

            st.rerun()

        except Exception as e:
            logger.error(f"Erro validação: {e}")
            st.error("❌ Não consegui ler seus números. Verifique a digitação.")

    # --- RENDERIZAÇÃO DO RESULTADO ---
    if st.session_state.get("validator_result"):
        res = st.session_state.validator_result
        if res.get("slug") != slug:
            st.session_state.validator_result = None
        else:
            if res.get("new"):
                score = res["relatorio"]["score"]
                if score >= 80:
                    st.balloons()
                res["new"] = False

            _render_validator_results(res["relatorio"], res["nums"], ctx, svc)


def _render_validator_results(relatorio, nums, ctx, svc):
    """Renderiza o relatório com foco em COPYWRITING e CLAREZA."""
    config = ctx.config

    # Dados principais
    score = relatorio["score"]
    score_original = relatorio.get("score_original", 0)
    ja_saiu = relatorio.get("ja_saiu", False)
    risco = relatorio.get("risco_divisao", "Médio")

    st.markdown("---")

    # 1. VEREDITO FINAL (O que o usuário quer saber primeiro)
    st.subheader("📋 Veredito do Analista")

    if ja_saiu:
        st.warning(
            "⚠️ **Combinação já sorteada no histórico.** "
            "Matematicamente ela mantém a mesma chance individual de qualquer outro volante no próximo sorteio, "
            "mas repetir exatamente uma combinação premiada costuma atrair apostadores que copiam resultados antigos (maior risco de divisão)."
        )
        st.caption(f"Score Técnico Original: {score_original}/100")
        return  # Interrompe a exibição detalhada se já saiu (regra de UX)

    col_veredicto, col_score = st.columns([3, 1])

    with col_veredicto:
        if score >= 85:
            st.success(
                "💎 **PERFIL ESTRUTURAL TÍPICO!** Bem alinhado às faixas mais frequentes do espaço combinatório. "
                "Lembrando: todas as apostas válidas têm a mesma chance individual de sorteio; este score avalia equilíbrio estrutural e risco de divisão."
            )
        elif score >= 60:
            st.info(
                "👍 **JOGO EQUILIBRADO.** Passou na maioria dos filtros estruturais, com alguns traços "
                "menos usuais ou leves alertas de concentração/popularidade."
            )
        elif score >= 40:
            st.warning(
                "⚠️ **JOGO ATÍPICO / CONCENTRADO.** Detectamos padrões visualmente previsíveis ou pouco usuais "
                "(ex: sequências ou forte desequilíbrio), o que pode aumentar o risco de divisão ou concentrar o volante."
            )
        else:
            st.error(
                "🚨 **PADRÃO MUITO ATÍPICO / POPULAR.** Esse jogo concentra vários alertas estruturais ou padrões humanos comuns. "
                "Embora tenha a mesma chance matemática individual no sorteio, tende a sofrer maior risco de divisão ou forte concentração."
            )

    with col_score:
        # Mostrador de Score Visual
        cor_score = (
            "#22c55e" if score >= 70 else "#f59e0b" if score >= 50 else "#ef4444"
        )
        st.markdown(
            f"""
            <div style="text-align: center; border: 2px solid {cor_score}; border-radius: 10px; padding: 10px;">
                <span style="font-size: 0.9rem; color: #777;">SCORE TÉCNICO</span><br>
                <span style="font-size: 2.5rem; font-weight: bold; color: {cor_score}; line-height: 1;">{score}</span>
                <span style="font-size: 1rem; color: {cor_score};">/100</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. RISCO FINANCEIRO
    st.markdown("<br>", unsafe_allow_html=True)

    risco_val = risco.split(" ")[0].upper()  # BAIXO, MÉDIO, ALTO

    if "BAIXO" in risco_val:
        msg_risco = "✅ <b>Seu prêmio está protegido.</b> Poucas pessoas jogam padrões como esse. Se ganhar, leva sozinho (ou divide com poucos)."
        cor_box = "background-color: #f0fdf4; border-left: 5px solid #22c55e;"
    elif "ALTO" in risco_val:
        msg_risco = "🚨 <b>ALERTA DE DILUIÇÃO!</b> Você está jogando padrões virais (datas, sequências, desenhos). Se ganhar, vai dividir com milhares."
        cor_box = "background-color: #fef2f2; border-left: 5px solid #ef4444;"
    else:
        msg_risco = "⚠️ <b>Atenção Moderada.</b> Jogo comum. Existe risco de divisão de prêmio, mas não é crítico."
        cor_box = "background-color: #fffbeb; border-left: 5px solid #f59e0b;"

    st.markdown(
        f"""
        <div style="{cor_box} padding: 15px; border-radius: 5px;">
            <strong> Análise de Risco Financeiro:</strong><br>
            {msg_risco}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3. VOLANTE VISUAL + MÉTRICAS CHAVE
    st.markdown("### Raio-X dos Padrões")

    c_volante, c_metricas = st.columns([1, 1.5])

    with c_volante:
        st.caption("Distribuição Espacial:")
        render_volante_marcado(nums, config)

    with c_metricas:
        metricas = relatorio.get("metricas", {})

        # Métricas "Humanas" (Traduzindo estatística)
        st.markdown("**O que a IA viu:**")

        # Par/Impar
        pares = metricas.get("pares", 0)
        st.write(f"- **Equilíbrio:** {pares} Pares / {config.bet_size - pares} Ímpares")

        # Soma
        soma = metricas.get("soma", 0)
        st.write(f"- **Peso do Jogo (Soma):** {soma}")

        # Entropia normalizada pelo máximo teórico log2(k-1) de cada modalidade
        entropia = float(metricas.get("entropia", 0.0) or 0.0)
        entropia_max = math.log2(max(2, config.bet_size - 1))
        ratio_entropia = entropia / entropia_max if entropia_max > 0 else 0.0
        if ratio_entropia >= 0.75:
            nivel_caos = f"Alto ({ratio_entropia:.0%} do máx.)"
        elif ratio_entropia >= 0.50:
            nivel_caos = f"Moderado ({ratio_entropia:.0%} do máx.)"
        else:
            nivel_caos = f"Baixo — previsível ({ratio_entropia:.0%} do máx.)"
        st.write(f"- **Imprevisibilidade dos Espaços:** {nivel_caos}")

        # Hamming (histórico completo vs últimos 100)
        hamming_hist = metricas.get(
            "hamming_historico_min", metricas.get("hamming_min", "N/A")
        )
        hamming_rec = metricas.get("hamming_recente_100")
        if hamming_hist != "N/A":
            if hamming_rec is not None and hamming_rec != "N/A":
                st.write(
                    f"- **Originalidade:** Difere {hamming_hist} número(s) no histórico completo "
                    f"({hamming_rec} nos últimos 100 concursos)."
                )
            else:
                st.write(
                    f"- **Originalidade:** Difere {hamming_hist} números do sorteio mais parecido da história."
                )

        # Repetidas do último concurso
        rep_ult = metricas.get("repetidas_ultimo_sorteio")
        if isinstance(rep_ult, dict) and "qtd" in rep_ult:
            st.write(
                f"- **Repetidas do Último Concurso:** {rep_ult['qtd']}/{config.k} "
                f"(faixa P5–P95: {rep_ult['p5']:.0f}–{rep_ult['p95']:.0f})"
            )

        # Popularidade Medida (ganhadores reais) vs Heurística Comportamental
        pop_pct = metricas.get("popularidade_medida_percentil")
        pop_raz = metricas.get("popularidade_medida_razao")
        pop_ic90 = metricas.get("popularidade_medida_ic90")
        if pop_pct is not None:
            razao_txt = (
                f" · razão estimada {pop_raz:.2f}x"
                if pop_raz is not None
                else ""
            )
            ic_txt = (
                f" (IC90% conformal: {pop_ic90[0]:.2f}x–{pop_ic90[1]:.2f}x)"
                if isinstance(pop_ic90, (list, tuple)) and len(pop_ic90) == 2
                else ""
            )
            st.write(
                f"- **Popularidade Medida (Ganhadores Reais):** Percentil {pop_pct:.0f}{razao_txt}{ic_txt}"
            )

        pop_heur = metricas.get("popularidade_heuristica")
        if isinstance(pop_heur, dict):
            alertas_h = pop_heur.get("alertas", [])
            if alertas_h:
                st.write(
                    f"- **Heurística Comportamental:** {', '.join(alertas_h)}"
                )
    # 4.CLUSTER PROFILE
    perfil = relatorio.get("perfil_cluster", {})
    if perfil.get("disponivel"):
        st.markdown("---")
        _render_cluster_profile(perfil)

    bootstrap = relatorio.get("bootstrap", {})
    if bootstrap and bootstrap.get("disponivel"):
        st.markdown("---")
        _render_bootstrap_analysis(bootstrap, sum(nums))

    # 6. BACKTESTING
    st.markdown("---")
    _render_backtesting(config, nums, svc)

    # 7. DETALHES TÉCNICOS
    with st.expander("🔬 Ver Análise Técnica Profunda (Avançado)"):
        st.markdown("##### Geometria e Quadrantes")
        _render_geometric_metrics(metricas)
        st.markdown("##### Análise de Similaridade")
        _render_advanced_metrics(metricas)

    # 8. MENSAGENS ESTRATÉGICAS
    if relatorio["msgs"]:
        st.markdown("##### 📝 Notas do Algoritmo:")
    for msg in relatorio["msgs"]:
        if "❌" in msg:
            st.markdown(
                f"<span style='color:#ef4444; font-weight:600;'>{msg}</span>",
                unsafe_allow_html=True,
            )
        elif "ℹ️" in msg:
            st.markdown(
                f"<span style='color:#3b82f6; font-weight:600;'>{msg}</span>",
                unsafe_allow_html=True,
            )
        elif "✅" in msg:
            st.caption(f"{msg}")
        else:
            st.markdown(
                f"<span style='color:#f59e0b;'>{msg}</span>",
                unsafe_allow_html=True,
            )


def _render_backtesting(config, nums, svc):
    """Mostra histórico de acertos."""
    st.markdown("##### Máquina do Tempo (Backtest)")
    st.caption(
        f"Se você tivesse jogado esses números desde o concurso 1 da {config.name}, você teria ganho:"
    )

    if config.slug == "loto_mania_sorteio":
        alvos = [20, 19, 18, 0]
    else:
        alvos = [config.k, config.k - 1, config.k - 2]  # Ex: 15, 14, 13

    res = svc.check_historical_matches(config.slug, nums, targets=alvos)

    cols = st.columns(len(alvos))

    for i, alvo in enumerate(alvos):
        with cols[i]:
            hits = alvo
            achou = res.get(hits, [])
            qtd = len(achou)

            # Formatação de Destaque
            cor_metric = "normal" if qtd > 0 else "off"

            if config.slug == "loto_mania_sorteio" and hits == 0:
                label = "Zero Acertos (🏆)"
            elif hits == config.k:
                label = f"🏆 {hits} Acertos (Máx)"
            else:
                label = f"{hits} Acertos"

            st.metric(label, f"{qtd}x", delta_color=cor_metric)


def _render_geometric_metrics(metricas):
    """Renderiza métricas geométricas com nova estrutura estatística."""
    geom = metricas.get("geom_detalhes", None)
    score_geom = metricas.get("score_geom", None)

    if geom:
        with st.expander(
            "🎯 Geometria do Volante (análise estatística)", expanded=False
        ):
            if score_geom is not None:
                st.caption(f"Score Geométrico: {score_geom}/100")

            linhas = []
            ordem = [
                "Moldura (Borda)",
                "Miolo (Centro)",
                "Cruz",
                "Xis (Diagonais)",
                "Cantos",
            ]
            nomes = {
                "Moldura (Borda)": "Moldura",
                "Miolo (Centro)": "Miolo",
                "Cruz": "Cruz",
                "Xis (Diagonais)": "Xis",
                "Cantos": "Cantos",
            }

            for key in ordem:
                if key not in geom:
                    continue
                item = geom[key]
                linhas.append(
                    {
                        "Grupo": nomes.get(key, key),
                        "No jogo": int(item.get("presentes", 0)),
                        "Média histórica": float(item.get("media_historica", 0.0)),
                        "Z-Score": float(item.get("z_score", 0.0)),
                        "Categoria": item.get("categoria", "Normal"),
                    }
                )

            if linhas:
                df_geom = pd.DataFrame(linhas)
                st.dataframe(
                    df_geom,
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "Grupo": st.column_config.TextColumn("Grupo"),
                        "No jogo": st.column_config.NumberColumn(
                            "No jogo", format="%d"
                        ),
                        "Média histórica": st.column_config.NumberColumn(
                            "Média histórica", format="%.2f"
                        ),
                        "Z-Score": st.column_config.NumberColumn(
                            "Z-Score",
                            format="%.2f",
                            help="Quantos desvios-padrão do normal. |Z| > 2 é raro.",
                        ),
                        "Categoria": st.column_config.TextColumn("Categoria"),
                    },
                )


def _render_advanced_metrics(metricas):
    """Renderiza métricas avançadas (Hamming, Quadrantes, Regressão)."""

    # 1. Distância de Hamming
    hamming_hist = metricas.get("hamming_historico_min", metricas.get("hamming_min", None))
    hamming_rec = metricas.get("hamming_recente_100", None)
    similaridade = metricas.get("similaridade_max", None)

    if hamming_hist is not None and hamming_hist != "N/A":
        with st.expander("🔍 Análise de Similaridade (Hamming)", expanded=False):
            sim_txt = (
                f"{similaridade:.1%}"
                if isinstance(similaridade, (int, float))
                else str(similaridade)
            )
            if hamming_rec is not None and hamming_rec != "N/A":
                col1, col2, col3 = st.columns(3)
                col1.metric(
                    "Distância Mín. (Histórico)",
                    hamming_hist,
                    help="Quantos números diferentes do sorteio mais próximo em todo o histórico",
                )
                col2.metric(
                    "Distância Mín. (Últimos 100)",
                    hamming_rec,
                    help="Quantos números diferentes do sorteio mais próximo nos últimos 100 concursos",
                )
                col3.metric(
                    "Similaridade Máx.",
                    sim_txt,
                    help="0% = totalmente diferente, 100% = idêntico",
                )
            else:
                col1, col2 = st.columns(2)
                col1.metric(
                    "Distância Mínima",
                    hamming_hist,
                    help="Quantos números diferentes do sorteio mais próximo",
                )
                col2.metric(
                    "Similaridade Máx.",
                    sim_txt,
                    help="0% = totalmente diferente, 100% = idêntico",
                )

    # 2. Quadrantes
    quadrantes = metricas.get("quadrantes", None)
    if quadrantes and quadrantes.get("detalhes"):
        with st.expander("🗺️ Distribuição por Quadrantes", expanded=False):
            score_q = quadrantes.get("score_quadrantes", 100)
            st.caption(f"Score de Quadrantes: {score_q}/100")

            detalhes = quadrantes["detalhes"]
            linhas = []
            for q in ["Q1", "Q2", "Q3", "Q4"]:
                if q in detalhes:
                    item = detalhes[q]
                    linhas.append(
                        {
                            "Quadrante": q,
                            "Números": item["presentes"],
                            "Esperado": item["esperado"],
                            "Z-Score": item["z_score"],
                            "Status": item["categoria"],
                        }
                    )

            if linhas:
                df_quad = pd.DataFrame(linhas)
                st.dataframe(df_quad, hide_index=True, width="stretch")

    # 3. Regressão à Média (informativo)
    regressao = metricas.get("regressao_media") or metricas.get("regressao")
    if isinstance(regressao, dict) and "correlacao" in regressao:
        with st.expander("📈 Validação: Regressão à Média", expanded=False):
            st.caption("Evidência histórica de que números atrasados tendem a sair:")
            col1, col2, col3 = st.columns(3)
            col1.metric(
                "Correlação ρ",
                f"{regressao['correlacao']:.3f}",
                help="Correlação entre atraso e saída futura",
            )
            col2.metric(
                "Taxa de Retorno",
                f"{regressao['taxa_retorno']:.1%}",
                help="% dos números atrasados que saíram",
            )
            col3.metric("Interpretação", regressao["interpretacao"])
    elif isinstance(regressao, dict) and regressao.get("status"):
        with st.expander("📈 Validação: Regressão à Média", expanded=False):
            st.info(
                f"{regressao['status']} (mínimo {regressao.get('minimo_necessario', 100)}, "
                f"disponível {regressao.get('disponivel', 0)})."
            )
    elif isinstance(regressao, str) and regressao:
        with st.expander("📈 Validação: Regressão à Média", expanded=False):
            st.info(regressao)


def _render_cluster_profile(perfil):
    """Renderiza o card de personalidade do jogo (Cluster)."""
    st.subheader("DNA do Jogo (Personalidade)")

    c1, c2 = st.columns([1, 2])

    with c1:
        # Ícone Grande e Nome
        st.markdown(
            f"""
<div style="text-align: center; background: #f8fafc; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0;">
    <div style="font-size: 3rem;">{perfil['icone']}</div>
    <div style="font-weight: bold; font-size: 1.1rem; color: #334155; margin-top: 5px;">{perfil['nome_cluster']}</div>
</div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        # Descrição e Detalhes
        st.markdown(f"**O que isso significa?**")
        st.markdown(f"{perfil['descricao']}")

        # Tags Técnicas
        tags_html = ""
        for feat in perfil["caracteristicas"]:
            tags_html += f'<span style="background: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; margin-right: 5px;">{feat}</span>'

        st.markdown(
            f"<div style='margin-top: 10px;'>{tags_html}</div>", unsafe_allow_html=True
        )

        d_mahal = perfil.get("distancia_mahalanobis")
        lim_mahal = perfil.get("limiar_mahalanobis_p95")
        mahal_txt = (
            f" · Distância de Mahalanobis: **{d_mahal:.2f}** (P95: {lim_mahal:.2f})"
            if d_mahal is not None and lim_mahal is not None
            else ""
        )

        if perfil.get("is_outlier"):
            st.warning(
                f"⚠️ **Nota:** Este jogo está na cauda estrutural (outlier multivariado{mahal_txt}). "
                "A probabilidade de sorteio é idêntica, mas a combinação difere do perfil típico."
            )
        else:
            st.caption(
                f"Este perfil representa {perfil.get('percentual_historico', 0)}% dos sorteios históricos{mahal_txt}."
            )


def _render_bootstrap_analysis(boot, soma_jogo):
    """Renderiza a barra do Intervalo de Predição 95% para bilhete único e o IC da média."""
    st.subheader("Validação Científica (Faixa de Predição 95%)")

    ic = boot["ic_bootstrap"]
    lower = ic.get("pred_lower", ic["ic_lower"])
    upper = ic.get("pred_upper", ic["ic_upper"])
    media = ic.get("media_predicao", ic["media_bootstrap"])

    # Normaliza a soma dentro de um range um pouco maior que o intervalo para dar contexto
    span = max(upper - lower, 1.0)
    range_min = lower - span * 0.5
    range_max = upper + span * 0.5

    # Clamp (trava valores entre 0 e 1)
    pos_pct = (soma_jogo - range_min) / (range_max - range_min)
    pos_pct = max(0.0, min(1.0, pos_pct))

    # Define cor da barra baseado se está dentro ou fora
    dentro_ic = lower <= soma_jogo <= upper
    cor_barra = "#22c55e" if dentro_ic else "#ef4444"  # Verde ou Vermelho

    st.markdown(
        f"""
<div style="margin-bottom: 5px; font-size: 0.9rem; font-weight: bold;">
    Análise da Soma ({soma_jogo}):
    <span style="color: {cor_barra};">{'✅ DENTRO' if dentro_ic else '⚠️ FORA'} da Faixa Típica (95% dos bilhetes)</span>
</div>
<div style="background: #e2e8f0; width: 100%; height: 20px; border-radius: 10px; position: relative;">
    <div style="
        position: absolute;
        left: {((lower - range_min) / (range_max - range_min)) * 100}%;
        width: {((upper - lower) / (range_max - range_min)) * 100}%;
        height: 100%;
        background: #bbf7d0;
        border-left: 2px solid #22c55e;
        border-right: 2px solid #22c55e;
        opacity: 0.6;">
    </div>
    <div style="
        position: absolute;
        left: {pos_pct * 100}%;
        top: -5px;
        width: 4px;
        height: 30px;
        background: {cor_barra};
        border: 2px solid white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
    </div>
</div>
<div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #64748b; margin-top: 5px;">
    <span>P2,5: {lower:.0f}</span>
    <span>Média Esperada: {media:.0f}</span>
    <span>P97,5: {upper:.0f}</span>
</div>
    """,
        unsafe_allow_html=True,
    )

    if "ic_media_lower" in ic and "ic_media_upper" in ic:
        st.caption(
            f"📊 IC Bootstrap 95% da média histórica de todos os sorteios: "
            f"[{ic['ic_media_lower']:.1f}, {ic['ic_media_upper']:.1f}] (incerteza da média, não de um bilhete isolado)."
        )

    # Mensagens detalhadas do Bootstrap
    for msg in boot.get("mensagens", []):
        if "⚠️" in msg:
            st.caption(msg)
