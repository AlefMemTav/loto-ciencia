# app/ui/validator_ui.py
from datetime import date
import streamlit as st
import pandas as pd
from app.core.logger import logger
from app.ui.views.board import render_volante_marcado
from app.core.game_constants import get_constants_for_game
from app.auth.api_client import APIClient


def render_validator(ctx, svc):
    config = ctx.config
    slug = config.slug
    df = ctx.df
    constants = get_constants_for_game(config)
    color = constants.get("heat_color", "#ef4444")

    st.markdown(
        f"<h3>🧪 Laboratório de Validação da <span style='color: {color};'>{config.name}</span></h3>",
        unsafe_allow_html=True,
    )
    st.write(f"Digite seus números da {config.name} para validação estatística.")

    qtd_aposta = config.bet_size
    nums_exemplo = " ".join([f"{n:02d}" for n in range(4, 4 + qtd_aposta)])

    entrada = st.text_input(
        f"Seus {qtd_aposta} números:",
        placeholder=f"Ex: {nums_exemplo}",
        help="Separe por espaço, vírgula ou traço.",
    )

    if st.button("🔬 Analisar Qualidade", type="primary", use_container_width=True):
        try:
            texto = entrada.replace(",", " ").replace("-", " ")
            nums = sorted(
                list(set([int(n) for n in texto.split() if n.strip().isdigit()]))
            )

            if len(nums) != qtd_aposta:
                st.warning(
                    f"⚠️ Precisamos de **exatamente {qtd_aposta} números** únicos (entre 1 e {config.n_numbers})."
                )
                return

            if not all(1 <= n <= config.n_numbers for n in nums):
                st.error(
                    f"❌ Todos os números devem estar entre 1 e {config.n_numbers}."
                )
                return

            logger.info(f"[{config.name}] Validação manual solicitada para: {nums}")

            relatorio = svc.validate(slug, nums)

            if APIClient.get_plan() != "pro":
                today = date.today().isoformat()
                if st.session_state.get("validator_marked_date") != today:
                    success, msg = APIClient.mark_resource_used("validator")
                    if success:
                        st.session_state.validator_marked_date = today
                        logger.info(f"✅ Validação marcada para {APIClient.get_plan()}")

            logger.info(
                f"[{config.name}] Resultado validação: Score {relatorio['score']} | Status: {relatorio['status']}"
            )

            # Cards de resultado
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            score = relatorio["score"]
            score_original = relatorio.get("score_original", 0)
            ja_saiu = relatorio.get("ja_saiu", False)

            if ja_saiu:
                display_score = "0/100"
                delta_msg = f"Score Técnico: {score_original}/100"
                classe_css_delta = "status-off"
                logger.warning(
                    f"[{config.name}] Usuário validou um jogo que JÁ SAIU: {nums}"
                )
            else:
                display_score = f"{score}/100"
                if score >= 80:
                    score_icon = "💎"
                elif score >= 50:
                    score_icon = "⚠️"
                else:
                    score_icon = "🗑️"
                delta_msg = f"{score_icon} {relatorio['status']}"
                classe_css_delta = "status-good" if score >= 80 else "status-warn"

            with c1:
                st.markdown(
                    f"""
                <div class="custom-metric-card">
                    <div class="metric-label">Qualidade Técnica</div>
                    <div class="metric-value">{display_score}</div>
                    <div class="metric-delta {classe_css_delta}">
                        {delta_msg}
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            risco = relatorio.get("risco_divisao", "Desconhecido")
            risco_class = "status-good" if "Baixo" in risco else "status-bad"

            with c2:
                st.markdown(
                    f"""
                <div class="custom-metric-card">
                    <div class="metric-label">Risco de Divisão</div>
                    <div class="metric-value">{risco.split(' ')[0]}</div>
                    <div class="metric-delta {risco_class}">{"Blindado" if "Baixo" in risco else "Risco Financeiro"}</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)

            # Backtesting
            _render_backtesting(config, nums, svc)

            # Métricas
            st.markdown("##### 📊 Métricas Técnicas")

            metricas = relatorio.get("metricas", {})

            # Renderiza métricas geométricas com nova estrutura
            _render_geometric_metrics(metricas)

            # Renderiza métricas avançadas (Hamming, Quadrantes)
            _render_advanced_metrics(metricas)

            col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

            col_m1.metric("Soma", metricas.get("soma", 0))
            col_m2.metric("Entropia", f"{metricas.get('entropia', 0):.2f}")
            col_m3.metric("Gini", f"{metricas.get('gini', 0):.3f}")
            col_m4.metric("Pares", metricas.get("pares", 0))
            col_m5.metric("Sequências", metricas.get("sequencias", 0))

            # Mensagens
            st.markdown("##### 📝 Relatório do Analista")
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

            # Volante visual
            st.markdown("---")

            col_volante, col_info = st.columns([1, 1])
            with col_volante:
                st.caption("Visualização Geométrica:")
                render_volante_marcado(nums, config)
            with col_info:
                st.markdown("##### 💡 Dicas")
                if score >= 80:
                    st.success("✅ Jogo de alta qualidade estatística!")
                elif score >= 60:
                    st.info("ℹ️ Jogo aceitável, mas pode melhorar.")
                else:
                    st.warning("⚠️ Considere gerar um novo jogo.")

                if "ALTO" in risco:
                    st.error(
                        "💸 Padrão muito popular. Se saísse, o prêmio seria dividido com muitos ganhadores."
                    )

        except Exception as e:
            logger.error(f"Erro na validação manual: {e}", exc_info=True)
            st.error(f"Não entendi esses números. Tente digitar assim: {nums_exemplo}")


def _render_backtesting(config, nums, svc):
    """Mostra histórico de acertos (backtesting visual)."""
    with st.expander("📊 Histórico (Backtesting)", expanded=False):
        if config.slug == "loto_mania_sorteio":
            alvos = [20, 19, 18, 0]
        else:
            alvos = [config.k, config.k - 1, config.k - 2]

        res = svc.check_historical_matches(config.slug, nums, targets=alvos)

        cols = st.columns(len(alvos))

        for i, alvo in enumerate(alvos):
            with cols[i]:
                hits = alvo
                achou = res.get(hits, [])

                if config.slug == "loto_mania_sorteio" and hits == 0:
                    label = "Zero Acertos (🏆)"
                elif hits == config.k:
                    label = f"{hits} Acertos (Máx)"
                else:
                    label = f"{hits} Acertos"

                st.metric(label, len(achou))

                if achou:
                    st.caption(", ".join(achou[:5]) + ("..." if len(achou) > 5 else ""))


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
                    use_container_width=True,
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
                st.dataframe(df_quad, hide_index=True, use_container_width=True)

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
