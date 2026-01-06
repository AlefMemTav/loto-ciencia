import streamlit as st
import time
from app.src.games import GameConfig
from app.src.generator import gerar_jogo_perfeito, gerar_multiplos_jogos
from app.src.validator import validar_jogo
from app.src.statistics import analise_intervalo_confianca, get_historico_jogos


def render_generator(df, freq, poisson_finais, config: GameConfig):
    st.markdown("### 🤖 Gerador Híbrido")
    st.write(f"Algoritmo estatístico para gerar jogos otimizados da {config.name}.")

    # Opções de configuração
    col_config1, col_config2 = st.columns(2)

    with col_config1:
        qtd = st.slider("Quantidade de Jogos:", 1, 10, 3)

    with col_config2:
        estrategia = st.selectbox(
            "Estratégia:",
            ["balanceada", "conservadora", "agressiva", "pura"],
            help="Balanceada: 40% freq + 60% atraso | Conservadora: 70% quentes | Agressiva: 80% atrasados | Pura: 100% aleatório",
        )

    diversidade = st.checkbox(
        f"Garantir diversidade (max {int(config.k*0.7)} números em comum)",
        value=True,
    )

    btn_gerar = st.button("✨ Gerar Agora", type="primary", width="stretch")

    if btn_gerar:
        # Busca dados
        ic_info = analise_intervalo_confianca(df, config)
        historico = get_historico_jogos(df, config)

        digits_poisson = (
            [item["digito"] for item in poisson_finais] if poisson_finais else None
        )

        # Barra de progresso e timer
        bar_text = st.empty()
        bar = st.progress(0)
        start_time = time.time()

        jogos = []

        if qtd == 1:
            bar_text.text("Minerando jogo otimizado...")
            jogo = gerar_jogo_perfeito(
                df, config, finais_poisson=digits_poisson, estrategia=estrategia
            )
            jogos.append(jogo)
            bar.progress(1.0)
        else:
            bar_text.text(f"Minerando {qtd} jogos otimizados...")
            jogos = gerar_multiplos_jogos(
                df,
                config,
                quantidade=qtd,
                estrategia=estrategia,
                garantir_diversidade=diversidade,
                finais_poisson=digits_poisson,
            )
            bar.progress(1.0)

        bar.empty()
        bar_text.empty()
        tempo_total = time.time() - start_time

        st.success(f"✅ {len(jogos)} jogos encontrados em {tempo_total:.2f}s!")

        # --- Feedback Contextual sobre a Dificuldade ---
        # Se for Lotofácil (k >= 15), explica que scores menores são normais
        # if config.k >= 15:
        #    st.info(
        #        "ℹ️ **Nota sobre Lotofácil:** Com 15 números, é estatisticamente muito #difícil "
        #        "obter scores acima de 80 sem viciar o jogo. Um score entre **60 e 75** é #considerado matematicamente excelente."
        #    )

        if estrategia != "balanceada":
            emoji_estrategia = {"conservadora": "⏰", "agressiva": "🔥", "pura": "🎲"}
            st.caption(
                f"{emoji_estrategia.get(estrategia, '')} Estratégia: **{estrategia.title()}**"
            )

        st.markdown("---")

        txt_out = f"LotoScience - Jogos {config.name} ({estrategia.title()})\n\n"

        # Exibição dos jogos
        for i, jogo in enumerate(jogos):
            val = validar_jogo(jogo, config, historico_jogos=historico, ic_info=ic_info)

            nums_fmt = "  ".join([f"{n:02d}" for n in jogo])

            with st.container():
                c_nums, c_score, c_perfil = st.columns([3, 1, 1])

                with c_nums:
                    st.markdown(
                        f"**Jogo {i+1}:** <code style='font-size:1.1rem; color:#0f172a'>{nums_fmt}</code>",
                        unsafe_allow_html=True,
                    )

                with c_score:
                    # Usa os targets do config para colorir
                    if (
                        val["score"] >= config.target_score_excellent
                    ):  # Ex: 85 (Mega) ou 75 (Loto)
                        st.caption(f"💎 Score: {val['score']}")
                    elif val["score"] >= config.target_score_accept:
                        st.caption(f"✅ Score: {val['score']}")
                    else:
                        st.caption(f"⚠️ Score: {val['score']}")

                with c_perfil:
                    risco = val.get("risco_divisao", "Baixo")
                    if "Baixo" in risco:
                        st.caption("💎 Blindado")
                    elif "Médio" in risco:
                        st.caption("⚠️ Médio")
                    else:
                        st.caption("🚨 Alto Risco")

            txt_out += f"{nums_fmt}\n"

        st.markdown("<br>", unsafe_allow_html=True)

        st.download_button(
            "📥 Baixar Jogos (.txt)",
            txt_out,
            f"jogos_{config.slug}_{estrategia}.txt",
            width="stretch",
        )

        # Expander com detalhes
        with st.expander("📊 Ver Análise Detalhada dos Jogos"):
            for i, jogo in enumerate(jogos):
                val = validar_jogo(
                    jogo, config, historico_jogos=historico, ic_info=ic_info
                )

                st.markdown(f"**Jogo {i+1}:** {jogo}")

                metricas = val.get("metricas", {})
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Soma", metricas.get("soma", 0))
                col2.metric("Entropia", metricas.get("entropia", 0))
                col3.metric("Gini", metricas.get("gini", 0))
                col4.metric("Pares", metricas.get("pares", 0))

                for msg in val["msgs"][:3]:
                    st.caption(msg)

                st.markdown("---")
