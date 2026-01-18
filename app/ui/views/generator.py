# app/ui/generator.py
from datetime import date
import streamlit as st
import time
from app.core.logger import logger
from app.ui.services.auth_client import AUTHClient
from app.ui.core.styles import apply_custom_css


def render_ball_html(numero, color):
    """Renderiza uma única bola de loteria via HTML/CSS"""
    return f"""
<div style="
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 35px;
    height: 35px;
    border-radius: 50%;
    background: radial-gradient(circle at 30% 30%, {color}, #334155);
    color: white;
    font-weight: bold;
    font-size: 14px;
    margin: 2px;
    border: 2px solid white;
    box-shadow: 1px 1px 3px rgba(0,0,0,0.2);
">
        {numero:02d}
    </div>
    """


def limpar_sessao():
    """Callback para limpar resultados ao alterar filtros."""
    if "generator_result" in st.session_state:
        del st.session_state["generator_result"]


def render_generator(ctx, svc):
    apply_custom_css()
    config = ctx.config
    slug = config.slug
    constants = config.as_constants_dict()
    main_color = constants.get("heat_color", "#ef4444")
    if "generator_result" in st.session_state:
        saved_slug = st.session_state.generator_result.get("slug")
        # Se o slug salvo for diferente do atual, apaga tudo
        if saved_slug != config.slug:
            del st.session_state["generator_result"]
    # --- HEADER COM COPYWRITING ---
    st.markdown(
        f"""
        <div style="background: linear-gradient(90deg, #f8fafc 0%, #e2e8f0 100%); padding: 20px; border-radius: 10px; border-left: 5px solid {main_color}; margin-bottom: 25px;">
            <h2 style="color: #1e293b; margin:0;">⛏️ Mineração de Jogos: <span style="color: {main_color};">{config.name}</span></h2>
            <p style="color: #475569; font-size: 1rem; margin-top: 5px;">
                Esta engine utiliza algoritmos e filtros estatísticos para encontrar combinações 
                que respeitam a <strong>Lei dos Grandes Números</strong> e possuem alta probabilidade matemática.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- CONFIGURAÇÃO DA MINERAÇÃO ---
    with st.container(border=True):
        st.markdown("#### ⚙️ Parâmetros da Engine")

        col_qtd, col_strat = st.columns([1, 2])

        with col_qtd:
            qtd = st.slider(
                "Quantidade de Jogos a Minerar:", 1, 10, 3, on_change=limpar_sessao
            )

        with col_strat:
            # Mapas de display para ficar mais amigável
            strat_display = {
                "balanceada": "⚖️ Balanceada (Recomendada)",
                "conservadora": "🛡️ Conservadora (Frequentes)",
                "agressiva": "🔥 Agressiva (Atrasados)",
                "pura": "🎲 Aleatória Pura (Caos)",
            }

            strat_key = st.selectbox(
                "Estratégia Matemática:",
                options=["balanceada", "conservadora", "agressiva", "pura"],
                format_func=lambda x: strat_display[x],
                on_change=limpar_sessao,
            )

        # Explicação dinâmica da estratégia selecionada
        info_strats = {
            "balanceada": "Busca o equilíbrio perfeito: 60% de números quentes e 40% de atrasados. Maximiza a chance de pegar padrões mistos.",
            "conservadora": "Aposta pesado na tendência. Usa números que estão saindo muito nos últimos concursos.",
            "agressiva": "Caça às zebras. Foca em números que não saem há muito tempo (Regresso à Média). Risco maior.",
            "pura": "Sem viés histórico (todos os números têm peso igual), mas validado matematicamente. Ideal para buscar surpresas estatisticamente viáveis.",
        }
        st.info(f"💡 **Lógica:** {info_strats[strat_key]}")

        # Checkbox melhorado
        diversidade = st.toggle(
            "🛡️ Evitar Jogos Parecidos (Diversidade)",
            value=True,
            help=f"Ativa o filtro de Distância de Hamming para garantir que os jogos gerados não sejam quase iguais entre si.",
            on_change=limpar_sessao,
        )

    # --- RESTRIÇÕES AVANÇADAS (INTEGRADO) ---
    with st.expander("Restrições (Números Fixos e Excluídos)"):
        col_fix, col_exc = st.columns(2)

        # Cria lista de 1 a N
        todos_numeros = list(range(1, config.n_numbers + 1))

        with col_fix:
            nums_fixos = st.multiselect(
                "📌 Fixar Números (Devem aparecer):",
                options=todos_numeros,
                help="Estes números estarão presentes em TODOS os jogos gerados.",
                on_change=limpar_sessao,
            )

        with col_exc:
            # Remove os fixos das opções de exclusão
            opcoes_exclusao = [n for n in todos_numeros if n not in nums_fixos]
            nums_evitados = st.multiselect(
                "🚫 Excluir Números (Nunca aparecerão):",
                options=opcoes_exclusao,
                help="Estes números serão banidos da geração.",
                on_change=limpar_sessao,
            )

        # --- VALIDAÇÃO MATEMÁTICA EM TEMPO REAL ---
        # 1. Quantos números faltam preencher?
        vagas_abertas = config.bet_size - len(nums_fixos)

        # 2. Quantos números sobraram no pote (Pool)?
        # Total - Fixos - Excluídos
        numeros_restantes_no_pool = (
            config.n_numbers - len(nums_fixos) - len(nums_evitados)
        )

        # Lógica de Bloqueio
        erro_validacao = None

        if len(nums_fixos) > config.bet_size:
            erro_validacao = f"❌ Você fixou {len(nums_fixos)} números, mas o jogo só permite {config.bet_size}."

        elif numeros_restantes_no_pool < vagas_abertas:
            erro_validacao = (
                f"❌ Matemática impossível! Você precisa preencher mais {vagas_abertas} vaga(s), "
                f"mas só sobraram {numeros_restantes_no_pool} números disponíveis no universo."
            )

        # Mostra erro ou status
        if erro_validacao:
            st.error(erro_validacao)
            can_use = False  # Bloqueia o botão
        else:
            # Feedback visual útil
            if nums_fixos or nums_evitados:
                st.caption(
                    f"📊 Status: Fixos **{len(nums_fixos)}** | "
                    f"Excluídos **{len(nums_evitados)}** | "
                    f"Disponíveis para sorteio **{numeros_restantes_no_pool}**"
                )

    # --- VERIFICAÇÃO DE ACESSO ---
    can_use = AUTHClient.check_and_render_access("generator", "Gerador Inteligente")

    # --- BOTÃO DE AÇÃO ---
    st.markdown("<br>", unsafe_allow_html=True)
    btn_gerar = st.button(
        f"✨ Minerar {qtd} Jogos Otimizados",
        type="primary",
        width="stretch",
        disabled=not can_use,
    )

    # --- LÓGICA DE GERAÇÃO ---
    if btn_gerar:
        bar_text = st.empty()
        bar = st.progress(0)
        start_time = time.time()

        payload = {
            "quantidade": qtd,
            "estrategia": strat_key,
            "garantir_diversidade": diversidade,
            "numeros_fixos": nums_fixos,
            "numeros_evitados": nums_evitados,
        }

        try:
            steps = [
                "Carregando histórico...",
                "Calculando frequências...",
                "Aplicando filtros de Entropia...",
                "Validando geometria...",
                "Finalizando...",
            ]
            for i, step in enumerate(steps):
                bar_text.text(f"⚙️ {step}")
                bar.progress((i + 1) * 20)
                time.sleep(
                    0.15
                )  # Pequeno delay cosmético para dar sensação de processamento

            jogos = svc.generate(slug, payload)

            # Marca uso (se não for PRO)
            if jogos and AUTHClient.get_plan() != "pro":
                today = date.today().isoformat()
                if st.session_state.get("generator_marked_date") != today:
                    success, msg = AUTHClient.mark_resource_used("generator")
                    if success:
                        st.session_state.generator_marked_date = today
                        logger.info(f"✅ Geração marcada para {AUTHClient.get_plan()}")

            # Salva resultado
            tempo_total = time.time() - start_time
            st.session_state.generator_result = {
                "jogos": jogos,
                "estrategia": strat_key,
                "tempo": tempo_total,
                "new": True,
                "slug": slug,
            }
            st.rerun()

        except Exception as e:
            bar.empty()
            bar_text.empty()
            st.error(f"❌ Erro na mineração: {e}")
            logger.error(f"Erro gerador: {e}", exc_info=True)
            return

    # --- RENDERIZAÇÃO DOS RESULTADOS ---
    if st.session_state.get("generator_result"):
        res = st.session_state.generator_result

        # Feedback de sucesso (apenas na primeira vez)
        if res.get("new"):
            st.toast(f"✅ Mineração concluída em {res['tempo']:.2f}s!", icon="🚀")
            res["new"] = False

        _render_generated_games(
            res["jogos"], res["estrategia"], config, svc, main_color
        )

    st.markdown(
        """
    <div style="text-align: center; margin-top: 15px; color: #94a3b8; font-size: 0.8rem;">
    O LotoScience não garante prêmios. Estes jogos são estatisticamente equilibrados para aumentar suas probabilidades matemáticas e evitar divisões de prêmio. Jogue com responsabilidade.
    </div>
        """,
        unsafe_allow_html=True,
    )


def _render_generated_games(jogos, estrategia, config, svc, color_theme):
    slug = config.slug

    st.markdown("---")
    st.subheader(f"💎 Resultados da Mineração ({len(jogos)} jogos)")

    txt_out = f"LotoScience - Jogos Otimizados {config.name}\n"
    txt_out += f"Estratégia: {estrategia.upper()} | Data: {date.today().strftime('%d/%m/%Y')}\n"
    txt_out += "=" * 40 + "\n\n"

    # Container principal dos resultados
    for i, jogo in enumerate(jogos, 1):
        # Validação em tempo real para pegar score atualizado
        val = svc.validate(slug, jogo)
        score = val.get("score", 0)
        risco = val.get("risco_divisao", "Desconhecido")
        metricas = val.get("metricas", {})

        # Formatação para TXT
        nums_fmt_txt = " ".join([f"{n:02d}" for n in sorted(jogo)])
        txt_out += f"Jogo {i:02d}: {nums_fmt_txt} | Score: {score} | Risco: {risco}\n"

        # --- CARD DO JOGO (VISUAL PREMIUM) ---
        with st.container(border=True):
            # Header do Card (Jogo # + Badges)
            col_label, col_badges = st.columns([1, 2])
            with col_label:
                st.markdown(f"**Jogo #{i:02d}**")
            with col_badges:
                # Badge de Score
                score_color = (
                    "#22c55e"
                    if score >= 80
                    else "#eab308" if score >= 60 else "#ef4444"
                )
                st.markdown(
                    f"""
<div style="display: flex; gap: 10px; justify-content: flex-end;">
    <span style="background: {score_color}20; color: {score_color}; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; border: 1px solid {score_color};">
        <b>Score {score}</b>
    </span>
    <span style="background: #f1f5f9; color: #475569; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; border: 1px solid #cbd5e1;">
        Risco {risco}
    </span>
</div>
                    """,
                    unsafe_allow_html=True,
                )

            # --- CORREÇÃO AQUI: As Bolas Coloridas ---
            # 1. Cria o container flex para as bolas
            html_balls_full = "<div style='display: flex; flex-wrap: wrap; gap: 5px; margin: 10px 0;'>"

            # 2. Gera o HTML de cada bola individualmente e adiciona à string principal
            for n in sorted(jogo):
                html_balls_full += render_ball_html(n, color_theme)

            # 3. Fecha o container
            html_balls_full += "</div>"

            # 4. O PULO DO GATO: Renderiza tudo como HTML inseguro
            st.markdown(html_balls_full, unsafe_allow_html=True)
            # ------------------------------------------

            # Métricas Rápidas (Mini Dashboard)
            m1, m2, m3, m4 = st.columns(4)
            m1.caption(f"Soma: **{metricas.get('soma', '-')}**")
            m2.caption(f"Pares: **{metricas.get('pares', '-')}**")
            m3.caption(f"Primos: **{metricas.get('qtd_primos', '-')}**")
            m4.caption(f" Entropia: **{metricas.get('entropia', 0):.2f}**")

    # Botão de Download
    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        label="📥 Baixar Jogos em Texto (.txt)",
        data=txt_out,
        file_name=f"lotoscience_{slug}_{estrategia}_{int(time.time())}.txt",
        mime="text/plain",
        type="secondary",
        width="stretch",
    )
