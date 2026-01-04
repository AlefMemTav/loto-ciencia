import streamlit as st
from app.src.generator import gerar_fechamento


def render_closures():
    st.markdown("### 📦 Fechamentos Matemáticos")
    st.info(
        "Cercar números garante prêmios menores. Escolha de 7 a 12 números e geraremos todas as combinações matemáticas possíveis."
    )

    entrada_base = st.text_input(
        "Seus números base:", placeholder="Ex: 01 02 03 04 05 06 07 08"
    )

    if st.button("⚙️ Calcular Fechamento", width="stretch"):
        try:
            base = sorted(
                list(
                    set(
                        [
                            int(n)
                            for n in entrada_base.replace(",", " ").split()
                            if n.strip().isdigit()
                        ]
                    )
                )
            )

            if 7 <= len(base) <= 12:
                jogos = gerar_fechamento(base)
                custo = len(jogos) * 5.00

                st.success(f"Operação realizada! Geramos **{len(jogos)} jogos**.")

                # Card de Custo
                st.markdown(
                    f"""
                <div class="custom-metric-card" style="max-width: 300px; margin: 0 auto;">
                    <div class="metric-label">Custo Estimado</div>
                    <div class="metric-value">R$ {custo:,.2f}</div>
                    <div class="metric-delta status-warn">{len(jogos)} volantes</div>
                </div>
                <br>
                """,
                    unsafe_allow_html=True,
                )

                with st.expander("Ver Lista de Jogos"):
                    txt = ""
                    for j in jogos:
                        st.text(str(j))
                        txt += f"{j}\n"

                st.download_button(
                    "📥 Baixar Arquivo", txt, "fechamento.txt", width="stretch"
                )
            else:
                st.warning("⚠️ Escolha entre **7 e 12 números**.")
        except Exception:
            st.error("Erro na leitura. Verifique se digitou apenas números.")
