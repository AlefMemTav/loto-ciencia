# app/ui/generator.py
from datetime import date
import streamlit as st
import time
from app.core.logger import logger
from app.ui.services.auth_client import AUTHClient


def render_generator(ctx, svc):
    config = ctx.config
    slug = config.slug
    constants = config.as_constants_dict()

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
    can_use = AUTHClient.check_and_render_access("generator", "Gerador")

    btn_gerar = st.button(
        "✨ Gerar Agora", type="primary", width="stretch", disabled=not can_use
    )

    # --- LÓGICA DO BOTÃO ---
    if btn_gerar:
        bar_text = st.empty()
        bar = st.progress(0)
        start_time = time.time()

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

            # Marca uso (se não for PRO)
            if jogos and AUTHClient.get_plan() != "pro":
                today = date.today().isoformat()
                # Verifica para evitar duplicidade de cobrança no mesmo clique
                if st.session_state.get("generator_marked_date") != today:
                    success, msg = AUTHClient.mark_resource_used("generator")
                    if success:
                        st.session_state.generator_marked_date = today
                        logger.info(f"✅ Geração marcada para {AUTHClient.get_plan()}")

            # Salva resultado no estado
            tempo_total = time.time() - start_time
            st.session_state.generator_result = {
                "jogos": jogos,
                "estrategia": estrategia,
                "tempo": tempo_total,
                "new": True,  # Flag para mostrar mensagem de sucesso após o rerun
            }

            # Recarrega a página para atualizar o contador de limite
            st.rerun()

        except Exception as e:
            bar.empty()
            bar_text.empty()
            st.error(f"❌ Erro ao gerar jogos: {e}")
            return

    # --- RENDERIZAÇÃO DO RESULTADO (FORA DO IF) ---
    if st.session_state.get("generator_result"):
        res = st.session_state.generator_result

        # Mostra mensagem de sucesso apenas se for novo
        if res.get("new"):
            st.success(
                f"✅ {len(res['jogos'])} jogos encontrados em {res['tempo']:.2f}s!"
            )
            # Remove a flag para não mostrar a mensagem novamente em outros reruns
            res["new"] = False

        _render_generated_games(res["jogos"], res["estrategia"], config, svc)


def _render_generated_games(jogos, estrategia, config, svc):
    slug = config.slug
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
                    st.caption("🛡️ Blindado")
                elif "Médio" in risco:
                    st.caption("⚠️ Médio")
                else:
                    st.caption("🚨 Alto Risco")

        txt_out += f"{nums_fmt}\n"

    st.markdown("<br>", unsafe_allow_html=True)

    st.download_button(
        "📥 Baixar Jogos (.txt)",
        txt_out,
        f"jogos_{slug}_{estrategia}.txt",
        width="stretch",
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
