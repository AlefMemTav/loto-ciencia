# app/ui/closures.py
import streamlit as st
from app.core.logger import logger
from app.ui.services.auth_client import AUTHClient


def render_closures(ctx, svc):
    config = ctx.config
    slug = config.slug
    constants = config.as_constants_dict()
    color = constants.get("heat_color", "#ef4444")

    st.markdown(
        f"<h3>📦 Fechamentos Matemáticos da <span style='color: {color};'>{config.name}</span></h3>",
        unsafe_allow_html=True,
    )

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
    can_use = AUTHClient.check_and_render_access("closures", "Fechamentos Matemáticos")
    if st.button(
        "⚙️ Calcular Fechamento",
        use_container_width=True,
        type="primary",
        disabled=not can_use,
    ):
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

            if not base:
                st.error("❌ Digite ao menos um número.")
                return

            if not all(1 <= n <= config.n_numbers for n in base):
                st.error(
                    f"❌ Todos os números devem estar entre 1 e {config.n_numbers}."
                )
                return

            if min_base <= len(base) <= max_base:
                logger.info(
                    f"[{config.name}] Gerando fechamento para base de {len(base)} números: {base}"
                )

                # Usa o service para gerar fechamento
                # max_combinacoes serve como proteção contra explosão combinatória
                max_combinacoes = 10000

                try:
                    jogos = svc.closures(slug, base, max_combinacoes=max_combinacoes)
                except ValueError as e:
                    st.error(f"❌ {str(e)}")
                    return
                except Exception as e:
                    logger.error(f"Erro no fechamento: {e}")
                    st.error(f"❌ Erro ao gerar fechamento: {e}")
                    return

                custo = len(jogos) * config.game_price

                logger.info(
                    f"[{config.name}] Fechamento gerado com sucesso: {len(jogos)} jogos."
                )

                st.success(f"✅ Operação realizada! Geramos **{len(jogos)} jogos**.")

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

                with st.expander("📋 Ver Lista de Jogos", expanded=False):
                    txt = ""
                    for i, jogo in enumerate(jogos, 1):
                        nums_fmt = " ".join([f"{n:02d}" for n in jogo])
                        st.text(f"Jogo {i:3d}: {nums_fmt}")
                        txt += f"{nums_fmt}\n"

                st.download_button(
                    "📥 Baixar Arquivo TXT",
                    txt,
                    f"fechamento_{config.slug}_{len(jogos)}_jogos.txt",
                    use_container_width=True,
                )
            else:
                st.warning(
                    f"⚠️ Para a {config.name}, escolha entre **{min_base} e {max_base} números**."
                )
        except ValueError as e:
            logger.error(f"Erro ao processar entrada: {e}")
            st.error(
                f"❌ Entrada inválida. Use apenas números separados por espaço ou vírgula."
            )
        except Exception as e:
            logger.error(f"Erro inesperado no fechamento: {e}", exc_info=True)
            st.error(f"❌ Erro inesperado: {e}")
