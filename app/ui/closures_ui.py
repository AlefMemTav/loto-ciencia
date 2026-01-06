import streamlit as st
from app.src.generator import gerar_fechamento
from app.src.logger import logger
from app.src.games import GameConfig


def render_closures(config: GameConfig):
    st.markdown("### 📦 Fechamentos Matemáticos")

    qtd_aposta = config.bet_size

    min_base = qtd_aposta + 1
    max_base = qtd_aposta + 6

    st.info(
        f"Cercar números garante prêmios menores na {config.name}. "
        f"Escolha de {min_base} a {max_base} números e geraremos "
        f"todas as combinações matemáticas de {qtd_aposta} dezenas possíveis."
    )

    placeholder_ex = " ".join([f"{n:02d}" for n in range(1, qtd_aposta + 3)])

    entrada_base = st.text_input(
        "Seus números base:",
        placeholder=f"Ex: {placeholder_ex} ...",
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

            if min_base <= len(base) <= max_base:
                logger.info(
                    f"[{config.name}] Gerando fechamento para base de {len(base)} números: {base}"
                )

                resultado = gerar_fechamento(base, config)

                if isinstance(resultado, dict) and "erro" in resultado:
                    st.error(resultado["erro"])
                    return

                jogos = resultado
                custo = len(jogos) * config.game_price

                logger.info(
                    f"[{config.name}] Fechamento gerado com sucesso: {len(jogos)} jogos."
                )

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
                st.warning(
                    f"⚠️ Para a {config.name}, escolha entre **{min_base} e {max_base} números**."
                )
        except Exception as e:
            logger.error(f"Erro no fechamento: {e}")
            st.error(f"Erro: {e}")
