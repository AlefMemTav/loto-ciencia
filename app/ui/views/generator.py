# app/ui/generator_ui.py
from datetime import date
import streamlit as st
import time
from app.core.logger import logger
from app.core.game_constants import get_constants_for_game
from app.auth.api_client import APIClient


def render_generator(ctx, svc):
    config = ctx.config
    slug = config.slug
    constants = get_constants_for_game(config)
    color = constants.get("heat_color", "#ef4444")

    st.markdown(
        f"<h3>🤖 Gerador Híbrido da <span style='color: {color};'>{config.name}</span></h3>",
        unsafe_allow_html=True,
    )
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
        f"Garantir diversidade (max {int(config.bet_size*0.7)} números em comum)",
        value=True,
    )

    btn_gerar = st.button("✨ Gerar Agora", type="primary", use_container_width=True)

    if btn_gerar:
        # Barra de progresso e timer
        bar_text = st.empty()
        bar = st.progress(0)
        start_time = time.time()

        # Monta payload para o service
        payload = {
            "quantidade": qtd,
            "estrategia": estrategia,
            "garantir_diversidade": diversidade,
        }

        try:
            if qtd == 1:
                bar_text.text("Minerando jogo otimizado...")
            else:
                bar_text.text(f"Minerando {qtd} jogos otimizados...")

            jogos = svc.generate(slug, payload)

            if jogos and APIClient.get_plan() != "pro":
                today = date.today().isoformat()
                if st.session_state.get("generator_marked_date") != today:
                    success, msg = APIClient.mark_resource_used("generator")
                    if success:
                        st.session_state.generator_marked_date = today
                        logger.info(f"✅ Geração marcada para {APIClient.get_plan()}")

            bar.progress(1.0)

        except Exception as e:
            bar.empty()
            bar_text.empty()
            st.error(f"❌ Erro ao gerar jogos: {e}")
            return

        bar.empty()
        bar_text.empty()

        tempo_total = time.time() - start_time
        st.success(f"✅ {len(jogos)} jogos encontrados em {tempo_total:.2f}s!")

        if estrategia != "balanceada":
            emoji_estrategia = {"conservadora": "⏰", "agressiva": "🔥", "pura": "🎲"}
            st.caption(
                f"{emoji_estrategia.get(estrategia, '')} Estratégia: **{estrategia.title()}**"
            )

        st.markdown("---")

        txt_out = f"LotoScience - Jogos {config.name} ({estrategia.title()})\n\n"

        # Exibição dos jogos
        for i, jogo in enumerate(jogos, 1):
            # Usa o service para validar
            val = svc.validate(slug, jogo)
            nums_fmt = " ".join([f"{n:02d}" for n in jogo])

            with st.container():
                c_nums, c_score, c_perfil = st.columns([3, 1, 1])

                with c_nums:
                    st.markdown(
                        f"**Jogo {i}:** <code style='font-size:1.1rem; color:#0f172a;'>{nums_fmt}</code>",
                        unsafe_allow_html=True,
                    )

                with c_score:
                    # Usa os targets do config para colorir
                    if val["score"] >= config.target_score_excellent:
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
            use_container_width=True,
        )

        # Expander com detalhes
        with st.expander("🔍 Ver Análise Detalhada dos Jogos"):
            for i, jogo in enumerate(jogos, 1):
                # Valida novamente ou reutiliza se cachear
                val = svc.validate(slug, jogo)
                nums_fmt = " ".join([f"{n:02d}" for n in jogo])

                st.markdown(f"**Jogo {i}:** {nums_fmt}")

                metricas = val.get("metricas", {})
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Soma", metricas.get("soma", 0))
                col2.metric("Entropia", f"{metricas.get('entropia', 0):.2f}")
                col3.metric("Gini", f"{metricas.get('gini', 0):.3f}")
                col4.metric("Pares", metricas.get("pares", 0))

                # Mostra primeiras 3 mensagens
                for msg in val.get("msgs", [])[:3]:
                    st.caption(msg)

                st.markdown("---")
