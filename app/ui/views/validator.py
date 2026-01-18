# app/ui/views/validator.py
from datetime import date
import streamlit as st
import pandas as pd
from app.core.logger import logger
from app.services import auth_service
from app.ui.views.board import render_volante_marcado
from app.ui.services.auth_client import AUTHClient


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

    # Limpa o resultado anterior se o usuário mudar o texto
    current_input_hash = hash(entrada)
    if st.session_state.get("last_validator_input") != current_input_hash:
        st.session_state.validator_result = None
        st.session_state.last_validator_input = current_input_hash

    # Verifica acesso
    can_use = AUTHClient.check_and_render_access("validator", "Validador Profissional")

    # Botão de Ação
    if st.button(
        "🚀 Auditar Meu Jogo Agora",
        type="primary",
        width="stretch",
        disabled=not can_use,
    ):
        try:
            texto = entrada.replace(",", " ").replace("-", " ").replace("\n", " ")
            nums = sorted(
                list(set([int(n) for n in texto.split() if n.strip().isdigit()]))
            )

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

                # 2. Marca o uso
                if AUTHClient.get_plan() != "pro":
                    AUTHClient.mark_resource_used("validator")

                # 3. Salva no Estado
                st.session_state.validator_result = {
                    "relatorio": relatorio,
                    "nums": nums,
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
        if res.get("new"):
            # Feedback visual imediato
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
        st.error(
            "🛑 **PARE AGORA!** Esse jogo **JÁ SAIU** na história da loteria. "
            "A chance de repetir o mesmo resultado é astronômica. Não jogue dinheiro fora."
        )
        st.caption(f"Score Técnico Original: {score_original}/100")
        return  # Interrompe a exibição detalhada se já saiu (regra de UX)

    col_veredicto, col_score = st.columns([3, 1])

    with col_veredicto:
        if score >= 85:
            st.success(
                "💎 **JOGO DE ELITE!** Estatisticamente forte. "
                "Este volante tem todas as características dos sorteios premiados. "
            )
        elif score >= 60:
            st.info(
                "👍 **JOGO SÓLIDO.** Passou na maioria dos testes, mas tem alguns padrões "
                "comuns. É um jogo seguro, mas não extraordinário."
            )
        elif score >= 40:
            st.warning(
                "⚠️ **JOGO ARRISCADO.** Detectamos padrões viciados (ex: muitas sequências "
                "ou desequilíbrio par/ímpar). A estatística joga contra você aqui."
            )
        else:
            st.error(
                "🗑️ **LIXO ESTATÍSTICO.** Esse jogo viola quase todas os nossos dados estatísticos. "
                "Jogar isso é quase uma doação para a Caixa. Recomendamos usar o Gerador."
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

        # Entropia (Traduzida)
        entropia = metricas.get("entropia", 0)
        nivel_caos = "Alto (Bom)" if entropia > 3.5 else "Baixo (Previsível)"
        st.write(f"- **Imprevisibilidade:** {nivel_caos}")

        # Hamming
        hamming = metricas.get("hamming_min", 0)
        if hamming != "N/A":
            st.write(
                f"- **Originalidade:** Difere {hamming} números do sorteio mais parecido da história."
            )

    # 4. BACKTESTING (A Prova Real)
    st.markdown("---")
    _render_backtesting(config, nums, svc)

    # 5. DETALHES TÉCNICOS (Accordion fechado para não assustar)
    with st.expander("🔬 Ver Análise Técnica Profunda (Avançado)"):
        st.markdown("##### Geometria e Quadrantes")
        _render_geometric_metrics(metricas)
        st.markdown("##### Análise de Similaridade")
        _render_advanced_metrics(metricas)

    # 6. MENSAGENS ESTRATÉGICAS
    if relatorio["msgs"]:
        st.markdown("##### 📝 Notas do Algoritmo:")
    for msg in relatorio["msgs"]:
        if "❌" in msg:
            st.markdown(
                f"<span style='color:#ef4444; font-weight:600;'>{msg}</span>",
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
    hamming = metricas.get("hamming_min", None)
    similaridade = metricas.get("similaridade_max", None)

    if hamming and hamming != "N/A":
        with st.expander("🔍 Análise de Similaridade (Hamming)", expanded=False):
            col1, col2 = st.columns(2)
            col1.metric(
                "Distância Mínima",
                hamming,
                help="Quantos números diferentes do sorteio mais próximo",
            )
            col2.metric(
                "Similaridade Máx.",
                f"{similaridade:.1%}",
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
    regressao = metricas.get("regressao", None)
    if regressao:
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
