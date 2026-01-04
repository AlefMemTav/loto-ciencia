import streamlit as st
from app.src.generator import gerar_jogo_perfeito
from app.src.validator import validar_jogo


def render_generator(freq, poisson_finais):
    st.markdown("### 🤖 Gerador Híbrido")
    st.write(
        "Nosso algoritmo mistura estatística (Quentes/Frios) com aleatoriedade controlada."
    )

    c1, c2 = st.columns([3, 1])
    with c1:
        qtd = st.slider("Quantidade de Jogos:", 1, 10, 3)
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)  # Alinhamento visual
        btn_gerar = st.button(
            "✨ Gerar Agora", type="primary", use_container_width=True
        )

    if btn_gerar:
        digits_poisson = [item["digito"] for item in poisson_finais]
        jogos = []

        # Barra de progresso visual
        bar_text = st.empty()
        bar = st.progress(0)

        for i in range(qtd):
            bar_text.text(f"Minerando jogo otimizado {i+1} de {qtd}...")
            jogo = gerar_jogo_perfeito(freq, digits_poisson)
            jogos.append(jogo)
            bar.progress((i + 1) / qtd)

        bar.empty()
        bar_text.empty()

        st.success(f"✅ {qtd} jogos de alta performance encontrados!")
        st.markdown("---")

        txt_out = "LotoScience - Jogos Gerados\n\n"

        # Exibição Limpa
        for i, jogo in enumerate(jogos):
            val = validar_jogo(jogo)
            # Formatação visual do jogo
            nums_fmt = "  ".join([f"{n:02d}" for n in jogo])

            # Container visual para cada jogo
            with st.container():
                c_nums, c_score = st.columns([3, 1])
                with c_nums:
                    st.markdown(
                        f"**Jogo {i+1}:** <code style='font-size:1.1rem; color:#0f172a'>{nums_fmt}</code>",
                        unsafe_allow_html=True,
                    )
                with c_score:
                    if val["score"] >= 80:
                        st.caption(f"💎 Score: {val['score']}")
                    else:
                        st.caption(f"⚠️ Score: {val['score']}")

            txt_out += f"{nums_fmt}\n"

        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            "📥 Baixar Jogos (.txt)",
            txt_out,
            "jogos_lotoscience.txt",
            use_container_width=True,
        )
