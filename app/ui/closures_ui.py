import streamlit as st
from app.src.generator import (
    gerar_fechamento,
)
from app.src.games import GameConfig


def render_closures(config: GameConfig):
    st.markdown("### 📦 Fechamentos Matemáticos")
    st.info(
        f"Cercar números garante prêmios menores na {config.name}. Escolha de {config.k+1} a {config.k+6} números "
        f"e geraremos todas as combinações matemáticas possíveis."
    )

    entrada_base = st.text_input(
        "Seus números base:",
        placeholder=f"Ex: " + " ".join([f"{n:02d}" for n in range(1, config.k + 3)]),
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

            if not all(1 <= n <= config.n_numbers for n in base):
                st.error(
                    f"❌ Todos os números devem estar entre 1 e {config.n_numbers}."
                )
                return

            min_base = config.k + 1
            max_base = config.k + 6

            if min_base <= len(base) <= max_base:

                resultado = gerar_fechamento(base, config)

                if isinstance(resultado, dict) and "erro" in resultado:
                    st.error(resultado["erro"])
                    return

                jogos = resultado
                custo = len(jogos) * 5.00

                st.success(f"Operação realizada! Geramos **{len(jogos)} jogos**.")

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
                    "📥 Baixar Arquivo",
                    txt,
                    f"fechamento_{config.slug}.txt",
                    width="stretch",
                )
            else:
                st.warning(f"⚠️ Escolha entre **{min_base} e {max_base} números**.")
        except Exception as e:
            st.error(f"Erro: {e}")
