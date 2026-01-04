import streamlit as st
import matplotlib.pyplot as plt
from app.src.validator import validar_jogo
from app.src.statistics import verificar_historico_sena


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

            relatorio = validar_jogo(nums)

            # --- ÁREA DE RESULTADOS (CARDS PRO) ---
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)

            # Definição de Cores baseada no Score
            score = relatorio["score"]
            if score >= 80:
                score_class = "status-good"
                score_icon = "💎"
            elif score >= 50:
                score_class = "status-warn"
                score_icon = "⚠️"
            else:
                score_class = "status-bad"
                score_icon = "🗑️"

            # CARD SCORE
            with c1:
                st.markdown(
                    f"""
                <div class="custom-metric-card">
                    <div class="metric-label">Qualidade Técnica</div>
                    <div class="metric-value">{score}/100</div>
                    <div class="metric-delta {score_class}">{score_icon} {relatorio['status']}</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            # Lógica Risco
            risco = relatorio.get("risco_divisao", "Desconhecido")
            risco_class = "status-good" if "Baixo" in risco else "status-bad"

            # CARD RISCO
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

            # Feedback Textual (Mensagens do Validador)
            st.markdown("##### 📝 Relatório do Analista")
            for msg in relatorio["msgs"]:
                if "❌" in msg:
                    st.markdown(
                        f"<span style='color:#ef4444; font-weight:600;'>{msg}</span>",
                        unsafe_allow_html=True,
                    )
                elif "✅" in msg:
                    st.caption(f"{msg}")  # Menos destaque para o que está bom
                else:
                    st.markdown(
                        f"<span style='color:#f59e0b;'>{msg}</span>",
                        unsafe_allow_html=True,
                    )

            # Volante Visual
            st.markdown("---")
            col_volante, col_vazio = st.columns([1, 1])
            with col_volante:
                st.caption("Visualização Geométrica:")
                _render_volante_aposta(nums)

        except Exception as e:
            st.error(
                f"Não entendi esses números. Tente digitar assim: 05 10 15 20 25 30. ({e})"
            )


def _render_volante_aposta(nums):
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 7)
    ax.axis("off")
    for n in range(1, 61):
        row, col = (n - 1) // 10, (n - 1) % 10
        # Cores alinhadas com a marca
        color = (
            "#d97706" if n in nums else "#f1f5f9"
        )  # Accent se marcado, Cinza claro se não
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
