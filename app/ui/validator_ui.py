import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from app.src.logger import logger
from app.src.games import GameConfig
from app.src.validator import validar_jogo
from app.src.statistics import (
    get_historico_jogos,
    analise_intervalo_confianca,
    verificar_historico,
)
from app.ui.board_ui import render_volante_marcado


def render_validator(df, config: GameConfig):
    st.markdown("### 🧪 Laboratório de Validação")
    st.write(f"Digite seus números da {config.name} para validação estatística.")

    # Placeholder dinâmico
    nums_exemplo = " ".join([f"{n:02d}" for n in range(4, 4 + config.k)])

    entrada = st.text_input(
        f"Seus {config.k} números:",
        placeholder=f"Ex: {nums_exemplo}",
        help="Separe por espaço, vírgula ou traço.",
    )

    if st.button("🔍 Analisar Qualidade", type="primary", width="stretch"):
        try:
            texto = entrada.replace(",", " ").replace("-", " ")
            nums = sorted(
                list(set([int(n) for n in texto.split() if n.strip().isdigit()]))
            )

            # Validação dinâmica
            if len(nums) != config.k:
                st.warning(
                    f"⚠️ Precisamos de **exatamente {config.k} números** únicos (entre 1 e {config.n_numbers})."
                )
                return

            if not all(1 <= n <= config.n_numbers for n in nums):
                st.error(
                    f"❌ Todos os números devem estar entre 1 e {config.n_numbers}."
                )
                return

            logger.info(f"[{config.name}] Validação manual solicitada para: {nums}")

            # Busca dados
            historico = get_historico_jogos(df, config)
            ic_info = analise_intervalo_confianca(df, config)

            # Validação
            relatorio = validar_jogo(
                nums,
                config,
                historico_jogos=historico,
                ic_info=ic_info,
                df_historico=df,
            )

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
            # --- DETALHES ---
            st.markdown("<br>", unsafe_allow_html=True)

            _render_backtesting(df, config, nums)

            # Métricas
            st.markdown("##### 📊 Métricas Técnicas")

            metricas = relatorio.get("metricas", {})
            _render_geometric_metrics(metricas)

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

            # Volante visual (usando board_ui genérico)
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
                        "💸 Padrão muito popular. Se saisse, o prêmio seria dividido com muitos ganhadores."
                    )

        except Exception as e:
            logger.error(f"Erro na validação manual: {e}")
            st.error(
                f"Não entendi esses números. Tente digitar assim: {nums_exemplo}. ({e})"
            )


def _render_backtesting(df, config, nums):
    with st.expander("Histórico (Backtesting)", expanded=False):
        alvos = [config.k, config.k - 1, config.k - 2]
        res = verificar_historico(nums, df, config, alvos=alvos)

        k1, k2, k3 = st.columns(3)

        with k1:
            hits = config.k
            achou = res.get(hits, [])
            st.metric(f"Já Saiu {hits} acertos (jogo cheio)?", len(achou))
            if achou:
                st.caption(", ".join(achou[:10]) + ("..." if len(achou) > 10 else ""))

        with k2:
            hits = config.k - 1
            achou = res.get(hits, [])
            st.metric(f"Já Saiu {hits} acertos?", len(achou))
            if achou:
                st.caption(", ".join(achou[:10]) + ("..." if len(achou) > 10 else ""))

        with k3:
            hits = config.k - 2
            achou = res.get(hits, [])
            st.metric(f"Já Saiu {hits} acertos?", len(achou))
            if achou:
                st.caption(", ".join(achou[:10]) + ("..." if len(achou) > 10 else ""))


def _render_geometric_metrics(metricas):
    geom = metricas.get("geom_detalhes", None)
    score_geom = metricas.get("score_geom", None)

    if geom:
        with st.expander("Geometria do Volante (padrões visuais)", expanded=False):
            if score_geom is not None:
                st.caption(f"Score Geométrico: {score_geom}/100")

            linhas = []
            ordem = ["moldura", "miolo", "cruz", "xis", "cantos"]
            nomes = {
                "moldura": "Moldura",
                "miolo": "Miolo",
                "cruz": "Cruz",
                "xis": "Xis",
                "cantos": "Cantos",
            }

            for key in ordem:
                if key not in geom:
                    continue
                item = geom[key]
                linhas.append(
                    {
                        "Grupo": nomes.get(key, key),
                        "No jogo": int(item.get("presentes", 0)),
                        "Ideal (média)": float(item.get("ideal", 0.0)),
                        "Risco jogo cheio (%)": float(item.get("risco_cheio", 0.0)),
                    }
                )

            df_geom = pd.DataFrame(linhas)
            st.dataframe(
                df_geom,
                hide_index=True,
                width="stretch",
                column_config={
                    "Grupo": st.column_config.TextColumn("Grupo"),
                    "No jogo": st.column_config.NumberColumn("No jogo", format="%d"),
                    "Ideal (média)": st.column_config.NumberColumn(
                        "Ideal (média)", format="%.2f"
                    ),
                    "Risco jogo cheio (%)": st.column_config.NumberColumn(
                        "Risco jogo cheio (%)", format="%.4f"
                    ),
                },
            )
    else:
        pass
