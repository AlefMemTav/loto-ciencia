import streamlit as st
from app.src.generator import gerar_jogo_perfeito, gerar_multiplos_jogos
from app.src.validator import validar_jogo
from app.src.statistics import analise_intervalo_confianca, get_historico_jogos


def render_generator(df, freq, poisson_finais):
    st.markdown("### 🤖 Gerador Híbrido")
    st.write(
        "Nosso algoritmo mistura estatística (Quentes/Frios) com aleatoriedade controlada."
    )

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
        "Garantir diversidade (max 4 números em comum)", value=True
    )

    btn_gerar = st.button("✨ Gerar Agora", type="primary", use_container_width=True)

    if btn_gerar:
        # Busca ic_info e historico
        ic_info = analise_intervalo_confianca(df)
        historico = get_historico_jogos(df)

        # Preparação
        digits_poisson = (
            [item["digito"] for item in poisson_finais] if poisson_finais else None
        )

        # Barra de progresso
        bar_text = st.empty()
        bar = st.progress(0)

        # Usa nova função gerar_multiplos_jogos
        jogos = []

        if qtd == 1:
            # Geração única
            bar_text.text("Minerando jogo otimizado...")
            jogo = gerar_jogo_perfeito(
                df, finais_poisson=digits_poisson, estrategia=estrategia
            )
            jogos.append(jogo)
            bar.progress(1.0)
        else:
            # Geração múltipla com diversidade
            bar_text.text(f"Minerando {qtd} jogos otimizados...")
            jogos = gerar_multiplos_jogos(
                df,
                quantidade=qtd,
                estrategia=estrategia,
                garantir_diversidade=diversidade,
                finais_poisson=digits_poisson,
            )
            bar.progress(1.0)

        bar.empty()
        bar_text.empty()

        st.success(f"✅ {len(jogos)} jogos de alta performance encontrados!")

        # Informação sobre estratégia usada
        if estrategia != "balanceada":
            emoji_estrategia = {"conservadora": "⏰", "agressiva": "🔥", "pura": "🎲"}
            st.info(
                f"{emoji_estrategia.get(estrategia, '')} Estratégia: **{estrategia.title()}**"
            )

        st.markdown("---")

        txt_out = f"LotoScience - Jogos Gerados ({estrategia.title()})\n\n"

        # Exibição dos jogos
        for i, jogo in enumerate(jogos):
            # Passa ic_info e historico para validação
            val = validar_jogo(jogo, historico_jogos=historico, ic_info=ic_info)

            nums_fmt = "  ".join([f"{n:02d}" for n in jogo])

            with st.container():
                c_nums, c_score, c_perfil = st.columns([3, 1, 1])

                with c_nums:
                    st.markdown(
                        f"**Jogo {i+1}:** <code style='font-size:1.1rem; color:#0f172a'>{nums_fmt}</code>",
                        unsafe_allow_html=True,
                    )

                with c_score:
                    if val["score"] >= 80:
                        st.caption(f"💎 Score: {val['score']}")
                    elif val["score"] >= 70:
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

        # Download
        st.download_button(
            "📥 Baixar Jogos (.txt)",
            txt_out,
            f"jogos_lotoscience_{estrategia}.txt",
            use_container_width=True,
        )

        # Expander com detalhes
        with st.expander("📊 Ver Análise Detalhada dos Jogos"):
            for i, jogo in enumerate(jogos):
                val = validar_jogo(jogo, historico_jogos=historico, ic_info=ic_info)

                st.markdown(f"**Jogo {i+1}:** {jogo}")

                # Métricas
                metricas = val.get("metricas", {})
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Soma", metricas.get("soma", 0))
                col2.metric("Entropia", metricas.get("entropia", 0))
                col3.metric("Gini", metricas.get("gini", 0))
                col4.metric("Pares", metricas.get("pares", 0))

                # Mensagens
                for msg in val["msgs"][:3]:  # Mostra só as 3 primeiras
                    st.caption(msg)

                st.markdown("---")
