import streamlit as st
from app.src.generator import gerar_jogo_perfeito
from app.src.validator import validar_jogo


def render_generator(freq, poisson_finais):
    st.subheader("Gerador de Alta Performance")
    st.write(
        "Cria jogos combinando: **3 Quentes + 2 Frios + 1 Neutro** + Ajuste de Gauss + Poisson."
    )
    qtd = st.slider("Quantos jogos deseja gerar?", 1, 10, 3)

    if st.button("💎 Gerar Jogos Otimizados"):
        # Extrai apenas os dígitos da lista de dicionários do Poisson
        # O analise_poisson retorna [{'digito': 1, ...}, ...]
        digits_poisson = [item["digito"] for item in poisson_finais]

        jogos = []
        bar = st.progress(0)

        for i in range(qtd):
            jogo = gerar_jogo_perfeito(freq, digits_poisson)
            jogos.append(jogo)
            bar.progress((i + 1) / qtd)

        bar.empty()
        st.success("Jogos Calculados com Sucesso!")
        texto_jogos = "LotoScience - Seus Jogos Otimizados\n\n"

        for i, jogo in enumerate(jogos):
            st.markdown(f"**Jogo {i+1}:** `{'-'.join(map(str, jogo))}`")
            val = validar_jogo(jogo)
            st.caption(f"Score: {val['score']} | {val['status']}")
            st.divider()
            txt_out += f"{jogo}\n"

        st.download_button("📥 Baixar .txt", txt_out, "jogos.txt")
