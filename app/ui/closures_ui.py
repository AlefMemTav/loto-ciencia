import streamlit as st
from app.src.generator import gerar_fechamento


def render_closures():
    st.subheader("📦 Gerador de Fechamentos (Combinatória)")
    st.write(
        "Escolha de 7 a 12 números para cercar o prêmio. O sistema gera TODOS os jogos possíveis para garantir o prêmio matemático."
    )
    entrada_base = st.text_input(
        "Digite seus números base (Ex: 8 números):",
        placeholder="01 02 03 04 05 06 07 08",
    )

    if st.button("Gerar Fechamento"):
        try:
            base = sorted(
                list(set([int(n) for n in entrada_base.replace(",", " ").split()]))
            )
            if 7 <= len(base) <= 12:
                jogos = gerar_fechamento(base)
                st.success(
                    f"{len(jogos)} jogos gerados. Custo real: R$ {len(jogos)*5:.2f}"
                )

                txt = ""
                for j in jogos:
                    st.text(str(j))
                    txt += f"{j}\n"

                st.download_button("📥 Baixar", txt, "fechamento.txt")
            else:
                st.warning("Escolha entre 7 e 12 números.")
        except:
            st.error("Erro nos números. Verifique a digitação.")
