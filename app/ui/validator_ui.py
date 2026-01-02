import streamlit as st
import matplotlib.pyplot as plt
from app.src.validator import validar_jogo
from app.src.statistics import verificar_historico_sena


def render_validator(df):
    st.subheader("Teste sua intuição")
    entrada = st.text_input(
        "Digite seus 6 números (separados por vírgula, traço ou espaço):", ""
    )

    if st.button("Analisar Aposta"):
        try:
            texto = entrada.replace(",", " ").replace("-", " ")
            nums = sorted(
                list(set([int(n) for n in texto.split() if n.strip().isdigit()]))
            )

            if len(nums) != 6:
                st.error("Digite exatamente 6 números entre 1 e 60.")
                return

            relatorio = validar_jogo(nums)

            # Cards
            c1, c2 = st.columns(2)
            c1.metric(
                "Score Estatístico", f"{relatorio['score']}/100", relatorio["status"]
            )

            risco = relatorio.get("risco_divisao", "Desconhecido")
            delta_color = "off" if "Baixo" in risco else "inverse"
            c2.metric(
                "Chance de Divisão",
                risco,
                delta=(
                    "Proteção de Patrimônio" if "Baixo" in risco else "Risco Financeiro"
                ),
                delta_color=delta_color,
            )

            # Backtesting
            st.write("---")
            st.subheader("📜 Raio-X Histórico")
            senas, quinas, quadras = verificar_historico_sena(nums, df)

            k1, k2, k3 = st.columns(3)
            k1.metric("Já deu Sena (6)?", f"{len(senas)} vezes")
            if len(senas) > 0:
                k1.warning(f"Já saiu em: {senas[0]}")
            k2.metric("Já deu Quina (5)?", f"{len(quinas)} vezes")
            k3.metric("Já deu Quadra (4)?", f"{len(quadras)} vezes")

            if len(senas) == 0:
                st.caption(
                    "✅ **Inédito:** Essa combinação completa de 6 números nunca foi sorteada na história."
                )
            else:
                st.error(
                    "⚠️ **Atenção:** Esses números exatos já saíram! Estatisticamente, repetir a mesma sena é raríssimo."
                )

            # Detalhes
            if relatorio["score"] > 70:
                st.markdown(
                    f'<div class="success-box">{"<br>".join(relatorio["msgs"])}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="error-box">{"<br>".join(relatorio["msgs"])}</div>',
                    unsafe_allow_html=True,
                )

            # Volante
            st.write("---")
            st.write("📍 **Visualização no Volante:**")
            _render_volante_aposta(nums)

        except:
            st.error("Formato inválido.")


def _render_volante_aposta(nums):
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 7)
    ax.axis("off")
    for n in range(1, 61):
        row, col = (n - 1) // 10, (n - 1) % 10
        color = "green" if n in nums else "lightgray"
        weight = "bold" if n in nums else "normal"
        txt = "white" if n in nums else "black"
        ax.text(
            col + 0.5,
            6 - row - 0.5,
            str(n),
            ha="center",
            va="center",
            color=txt,
            bbox=dict(boxstyle="circle,pad=0.3", fc=color, ec="none"),
        )
    st.pyplot(fig)
