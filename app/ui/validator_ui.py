import streamlit as st
import matplotlib.pyplot as plt
from app.src.validator import validar_jogo
from app.src.statistics import (
    get_historico_jogos,
    verificar_historico_sena,
    analise_intervalo_confianca,
)


def render_validator(df):
    st.markdown("### 🧪 Laboratório de Validação")
    st.write("Digite seus números para passar pelo nosso crivo estatístico.")

    # Input melhorado
    entrada = st.text_input(
        "Seus 6 números:",
        placeholder="Ex: 04 12 25 33 41 58",
        help="Separe por espaço, vírgula ou traço.",
    )

    if st.button("🔍 Analisar Qualidade", type="primary", use_container_width=True):
        try:
            texto = entrada.replace(",", " ").replace("-", " ")
            nums = sorted(
                list(set([int(n) for n in texto.split() if n.strip().isdigit()]))
            )

            if len(nums) != 6:
                st.warning(
                    "⚠️ Precisamos de **exatamente 6 números** únicos (entre 1 e 60)."
                )
                return

            # Busca ic_info e historico
            historico = get_historico_jogos(df)
            ic_info = analise_intervalo_confianca(df)

            # Passa ic_info para validação
            relatorio = validar_jogo(nums, historico_jogos=historico, ic_info=ic_info)

            # --- ÁREA DE RESULTADOS (CARDS PRO) ---
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            score = relatorio["score"]
            score_original = relatorio.get("score_original", 0)
            ja_saiu = relatorio.get("ja_saiu", False)

            if ja_saiu:
                score_class = "status-bad"
                score_icon = "⛔"
                display_score = "0/100"
                delta_msg = f"Score Técnico: {score_original}/100"
                classe_css_delta = "status-off"
            else:
                display_score = f"{score}/100"
                if score >= 80:
                    score_class = "status-good"
                    score_icon = "💎"
                elif score >= 50:
                    score_class = "status-warn"
                    score_icon = "⚠️"
                else:
                    score_class = "status-bad"
                    score_icon = "🗑️"

                delta_msg = f"{score_icon} {relatorio['status']}"
                classe_css_delta = score_class

            # CARD SCORE
            with c1:
                estilo_extra = (
                    "color: #94a3b8;" if classe_css_delta == "status-off" else ""
                )

                st.markdown(
                    f"""
                <div class="custom-metric-card">
                    <div class="metric-label">Qualidade Técnica</div>
                    <div class="metric-value">{display_score}</div>
                    <div class="metric-delta {classe_css_delta}" style="{estilo_extra}">
                        {delta_msg}
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            # CARD RISCO
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

            # Histórico (Backtesting)
            senas, quinas, quadras = verificar_historico_sena(nums, df)
            k1, k2, k3 = st.columns(3)
            k1.metric("Já deu Sena (6)?", f"{len(senas)} vezes")
            if len(senas) > 0:
                k1.warning(f"Já saiu em: {senas[0]}")
            k2.metric("Já deu Quina (5)?", f"{len(quinas)} vezes")
            k3.metric("Já deu Quadra (4)?", f"{len(quadras)} vezes")

            if senas:
                st.error(
                    f"🚨 **ALERTA MÁXIMO:** Esses números já saíram em {senas[0]}! (Chance de repetir é quase nula)."
                )
            else:
                st.caption(
                    "✅ **Inédito:** Essa combinação completa de 6 números nunca foi sorteada na história."
                )

            # Métricas detalhadas
            st.markdown("---")
            st.markdown("##### Métricas Técnicas")

            metricas = relatorio.get("metricas", {})
            col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

            col_m1.metric("Soma", metricas.get("soma", 0))
            col_m2.metric("Entropia", f"{metricas.get('entropia', 0):.2f}")
            col_m3.metric("Gini", f"{metricas.get('gini', 0):.3f}")
            col_m4.metric("Pares", metricas.get("pares", 0))
            col_m5.metric("Sequências", metricas.get("sequencias", 0))

            # Feedback Textual
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

            # Volante Visual
            st.markdown("---")
            col_volante, col_info = st.columns([1, 1])

            with col_volante:
                st.caption("Visualização Geométrica:")
                _render_volante_aposta(nums)

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
                        "💸 Padrão muito popular. Prêmio seria dividido com muitos ganhadores."
                    )

        except Exception as e:
            st.error(
                f"Não entendi esses números. Tente digitar assim: 05 10 15 20 25 30. ({e})"
            )


def _render_volante_aposta(nums):
    """Renderiza o volante visual com os números marcados."""
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 7)
    ax.axis("off")

    for n in range(1, 61):
        row, col = (n - 1) // 10, (n - 1) % 10

        color = "#d97706" if n in nums else "#f1f5f9"
        txt_col = "white" if n in nums else "#94a3b8"
        font_w = "bold" if n in nums else "normal"

        ax.text(
            col + 0.5,
            6 - row - 0.5,
            str(n),
            ha="center",
            va="center",
            color=txt_col,
            fontweight=font_w,
            bbox=dict(boxstyle="circle,pad=0.3", fc=color, ec="none"),
        )

    st.pyplot(fig)
