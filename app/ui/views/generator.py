# app/ui/generator.py
from datetime import date
import streamlit as st
import time
from app.core.logger import logger
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

    st.markdown(
        f"""
        <div style="background: linear-gradient(90deg, #f8fafc 0%, #e2e8f0 100%); padding: 20px; border-radius: 10px; border-left: 5px solid {main_color}; margin-bottom: 25px;">
            <h2 style="color: #1e293b; margin:0;">⛏️ Mineração de Jogos: <span style="color: {main_color};">{config.name}</span></h2>
            <p style="color: #475569; font-size: 1rem; margin-top: 5px;">
                Esta engine utiliza algoritmos e filtros estatísticos para encontrar combinações 
                plausíveis, diversas e menos contaminadas por vícios humanos de escolha.
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
            # Permite ao usuário escolher a quantidade de jogos a minerar
            qtd = st.slider(
                "Quantidade de Jogos a Minerar:",
                min_value=1,
                max_value=20,
                value=5,
                step=1,
                on_change=limpar_sessao,
            )

        with col_strat:
            # Mapas de display para ficar mais amigável
            strat_display = {
                "cauda_controlada": "🎯 Cauda Controlada (Experimental)",
                "cauda_agressiva": "🚀 Cauda Agressiva (Experimental)",
                "cauda_convexa": "🔶 Cauda Convexa (Experimental)",
                "balanceada": "⚖️ Balanceada",
                "conservadora": "🛡️ Conservadora (Frequentes)",
                "agressiva": "🔥 Agressiva (Recomendada)",
                "pura": "🎲 Aleatória Pura (Caos)",
            }
            strategy_options = [
                "agressiva",
                "cauda_convexa",
                "cauda_agressiva",
                "cauda_controlada",
                "balanceada",
                "conservadora",
                "pura",
            ]
            if slug != "mega_sena_sorteio":
                strategy_options = [
                    "balanceada",
                    "conservadora",
                    "agressiva",
                    "cauda_convexa",
                    "cauda_agressiva",
                    "cauda_controlada",
                    "pura",
                ]
                strat_display["balanceada"] = "⚖️ Balanceada (Recomendada)"
                strat_display["agressiva"] = "🔥 Agressiva (Atrasados)"
                strat_display["cauda_controlada"] = "🎯 Cauda Controlada"
                strat_display["cauda_agressiva"] = "🚀 Cauda Agressiva"
                strat_display["cauda_convexa"] = "🔶 Cauda Convexa"

            strat_key = st.selectbox(
                "Estratégia Matemática:",
                options=strategy_options,
                format_func=lambda x: strat_display[x],
                on_change=limpar_sessao,
            )

        # Explicação dinâmica da estratégia selecionada
        info_strats = {
            "cauda_controlada": "Parte da agressiva e otimiza o pacote final para concentrar sinal sem perder diversidade.",
            "cauda_agressiva": "Busca cauda premiável com núcleos de pares/dezenas mais densos, mantendo tetos de exposição.",
            "cauda_convexa": "Permite núcleo moderado por pares, mas protege o pacote contra repetição de trincas e quadras.",
            "balanceada": "Mistura frequência, atraso e plausibilidade estrutural sem deixar o portfólio ficar concentrado demais.",
            "conservadora": "Dá mais peso a números historicamente frequentes, mas com controles contra superconcentração.",
            "agressiva": "Dá mais espaço a atrasos e ciclos, mantendo freios contra falácia do apostador e padrões artificiais.",
            "pura": "Reduz o viés histórico dos números, mas ainda evita combinações humanas óbvias e estruturalmente pobres.",
        }
        st.info(f"💡 **Lógica:** {info_strats[strat_key]}")

        col_modo, col_esforco = st.columns([2, 1])
        with col_modo:
            modo_jogo_real = st.toggle(
                "🎯 Modo Jogo Real",
                value=False,
                help="Roda um torneio de pacotes e compara o pacote escolhido contra Monte Carlo.",
                on_change=limpar_sessao,
            )
        with col_esforco:
            if modo_jogo_real:
                perfil_esforco = st.selectbox(
                    "Esforço",
                    options=["forte", "rapido", "maximo"],
                    format_func=lambda x: {
                        "rapido": "Rápido",
                        "forte": "Forte",
                        "maximo": "Máximo",
                    }[x],
                    on_change=limpar_sessao,
                )
            else:
                perfil_esforco = "forte"

        if modo_jogo_real:
            st.caption(
                "O Modo Jogo Real usa o motor vetorial, escolhe o pacote por torneio e registra seed/Monte Carlo para auditoria."
            )
            tipo_motor = "⚡ Vetorial (Modo Jogo Real)"
            usar_genetico = False
        else:
            st.markdown("##### Motor de Inteligência")

            col_motor, col_info_motor = st.columns([3, 1])
            with col_motor:
                tipo_motor = st.radio(
                    "Escolha o algoritmo:",
                    ["⚡ Vetorial (Alta Performance)", "🧬 Genético (Evolutivo)"],
                    captions=[
                        "Instantâneo. Amostra muitos candidatos e seleciona um portfólio plausível e diverso.",
                        "Mais lento (5-10s). Evolui gerações buscando plausibilidade histórica e baixa compressibilidade.",
                    ],
                    index=0,
                    horizontal=True,
                    on_change=limpar_sessao,
                )

            usar_genetico = "Genético" in tipo_motor

    # --- RESTRIÇÕES AVANÇADAS ---
    restrictions_ok = True
    with st.expander("Configurações Avançadas (Opcional)"):
        st.text(
            "Use apenas se souber o que está fazendo. Por padrão, o gerador já está configurado da forma como recomendamos que os jogos sejam gerados."
        )
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

        st.markdown("##### Calibração Estatística")
        col_pct_min, col_pct_max, col_forca = st.columns(3)
        with col_pct_min:
            percentil_min = st.number_input(
                "Percentil mínimo",
                min_value=0.0,
                max_value=49.0,
                value=5.0,
                step=1.0,
                help="Limite inferior das faixas plausíveis do modelo combinatório.",
                on_change=limpar_sessao,
            )
        with col_pct_max:
            percentil_max = st.number_input(
                "Percentil máximo",
                min_value=51.0,
                max_value=100.0,
                value=95.0,
                step=1.0,
                help="Limite superior das faixas plausíveis do modelo combinatório.",
                on_change=limpar_sessao,
            )
        with col_forca:
            historical_signal_strength = st.slider(
                "Força histórica",
                min_value=0.0,
                max_value=2.0,
                value=1.0,
                step=0.1,
                help="Controla a intensidade dos sinais históricos habilitados.",
                on_change=limpar_sessao,
            )

        col_cal1, col_cal2, col_cal3 = st.columns(3)
        with col_cal1:
            usar_calibracao_score = st.toggle(
                "Calibração de score",
                value=True,
                help="Controla a distribuição de perfis estruturais para evitar jogos perfeitos demais ou artificiais.",
                on_change=limpar_sessao,
            )
        with col_cal2:
            calibration_strength = st.slider(
                "Força da calibração",
                min_value=0.0,
                max_value=2.0,
                value=1.0,
                step=0.1,
                help="Peso do controle por buckets de score estrutural.",
                on_change=limpar_sessao,
            )
        with col_cal3:
            calibration_target = st.selectbox(
                "Alvo de calibração",
                options=["historico_nulo", "historico", "nulo"],
                format_func=lambda x: {
                    "historico_nulo": "Histórico + nulo",
                    "historico": "Histórico",
                    "nulo": "Modelo nulo",
                }[x],
                on_change=limpar_sessao,
            )

        st.markdown("##### Sinais Históricos")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            usar_quentes = st.toggle(
                "Quentes",
                value=True,
                help="Inclui frequência histórica como inclinação fraca.",
                on_change=limpar_sessao,
            )
            usar_atrasados = st.toggle(
                "Atrasados",
                value=True,
                help="Inclui atraso/gap histórico como inclinação fraca.",
                on_change=limpar_sessao,
            )
        with col_s2:
            usar_markov = st.toggle(
                "Markov",
                value=True,
                help="Inclui transições entre concursos como inclinação fraca.",
                on_change=limpar_sessao,
            )
            usar_ciclo = st.toggle(
                "Ciclo",
                value=True,
                help="Inclui números faltantes do ciclo atual como inclinação fraca.",
                on_change=limpar_sessao,
            )
        with col_s3:
            usar_coocorrencia = st.toggle(
                "Coocorrência",
                value=True,
                help="Inclui pares históricos como inclinação fraca.",
                on_change=limpar_sessao,
            )
            frequencia_recente = st.toggle(
                "Freq. recente",
                value=True,
                help="Mantém o sinal de frequência ativo no backend.",
                on_change=limpar_sessao,
            )

        if strat_key == "pura":
            st.caption(
                "No modo Pura, os sinais históricos são ignorados; ficam apenas os controles estruturais."
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
            restrictions_ok = False
        else:
            # Feedback visual útil
            if nums_fixos or nums_evitados:
                st.caption(
                    f"📊 Status: Fixos **{len(nums_fixos)}** | "
                    f"Excluídos **{len(nums_evitados)}** | "
                    f"Disponíveis para sorteio **{numeros_restantes_no_pool}**"
                )

    can_use = restrictions_ok

    # --- BOTÃO DE AÇÃO ---
    st.markdown("<br>", unsafe_allow_html=True)

    # Texto do botão muda conforme o motor para dar feedback claro
    if modo_jogo_real:
        texto_botao = f"🎯 Gerar {qtd} Jogos Reais"
    else:
        texto_botao = (
            f"🧬 Evoluir {qtd} Jogos de Elite"
            if usar_genetico
            else f"⚡ Minerar {qtd} Jogos Rápidos"
        )

    btn_gerar = st.button(
        texto_botao,
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
            "estrategia_base": strat_key,
            "perfil_esforco": perfil_esforco,
            "numeros_fixos": nums_fixos,
            "numeros_evitados": nums_evitados,
            "percentil_min": percentil_min,
            "percentil_max": percentil_max,
            "historical_signal_strength": historical_signal_strength,
            "usar_quentes": usar_quentes,
            "usar_atrasados": usar_atrasados,
            "usar_markov": usar_markov,
            "usar_ciclo": usar_ciclo,
            "usar_coocorrencia": usar_coocorrencia,
            "frequencia_recente": frequencia_recente,
            "usar_calibracao_score": usar_calibracao_score,
            "calibration_strength": calibration_strength,
            "calibration_target": calibration_target,
        }

        try:
            relatorio_jogo_real = None
            # --- RAMIFICAÇÃO: GENÉTICO vs VETORIAL ---

            if modo_jogo_real:
                steps = [
                    "Montando pool de candidatos...",
                    "Pontuando plausibilidade...",
                    "Disputando pacotes...",
                    "Rodando Monte Carlo...",
                    "Escolhendo pacote final...",
                ]
                for i, step in enumerate(steps):
                    bar_text.text(f"🎯 {step}")
                    bar.progress((i + 1) * 16)
                    time.sleep(0.15)

                resultado_real = svc.generate_real_game(slug, payload, None)
                jogos = resultado_real["jogos"]
                relatorio_jogo_real = resultado_real["relatorio"]
                bar.progress(100)
                bar_text.text("✅ Jogo Real concluído!")

            elif usar_genetico:
                bar_text.text("🧬 Inicializando Sopa Primordial...")
                bar.progress(10)

                # Toast para avisar que a demora é normal
                st.toast("🧬 Otimizando gerações... Aguarde.", icon="⏳")

                # Passo intermediário visual
                bar_text.text("🧬 Aplicando Mutações...")
                bar.progress(30)

                # Chamada pesada ao Service
                jogos = svc.generate_genetic(slug, payload, None)

                bar.progress(100)
                bar_text.text("✅ Evolução Concluída!")

            else:
                steps = [
                    "Carregando histórico...",
                    "Calculando frequências...",
                    "Aplicando filtros...",
                    "Validando geometria...",
                    "Finalizando...",
                ]
                for i, step in enumerate(steps):
                    bar_text.text(f"⚙️ {step}")
                    bar.progress((i + 1) * 20)
                    time.sleep(0.15)

                # Chamada rápida ao Service
                jogos = svc.generate(slug, payload, None)

            # --- PÓS-PROCESSAMENTO (MANTIDO IGUAL) ---

            # Salva resultado na sessão
            tempo_total = time.time() - start_time
            st.session_state.generator_result = {
                "jogos": jogos,
                "estrategia": strat_key,
                "tempo": tempo_total,
                "new": True,
                "slug": slug,
                "motor": (
                    "Jogo Real"
                    if modo_jogo_real
                    else ("Genético" if usar_genetico else "Vetorial")
                ),
                "modo_jogo_real": modo_jogo_real,
                "relatorio_jogo_real": relatorio_jogo_real,
            }
            st.rerun()

        except Exception as e:
            bar.empty()
            bar_text.empty()
            st.error(f"❌ Erro na mineração")
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
            res["jogos"],
            res["estrategia"],
            config,
            svc,
            main_color,
            relatorio_jogo_real=res.get("relatorio_jogo_real"),
        )

    st.markdown(
        """
    <div style="text-align: center; margin-top: 15px; color: #94a3b8; font-size: 0.8rem;">
    O LotoScience não garante prêmios. Estes jogos buscam plausibilidade estatística, diversidade e menor risco de escolhas humanas óbvias. Loterias são jogos de azar. Jogue com responsabilidade.
    Aposte somente o que você pode perder.
    </div>
        """,
        unsafe_allow_html=True,
    )


def _render_generated_games(
    jogos,
    estrategia,
    config,
    svc,
    color_theme,
    relatorio_jogo_real=None,
):
    slug = config.slug

    st.markdown("---")
    st.subheader(f"💎 Resultados da Mineração ({len(jogos)} jogos)")

    txt_out = f"LotoScience - Jogos Otimizados {config.name}\n"
    txt_out += f"Estratégia: {estrategia.upper()} | Data: {date.today().strftime('%d/%m/%Y')}\n"
    if relatorio_jogo_real:
        txt_out += (
            f"Modo: JOGO REAL | Perfil: {relatorio_jogo_real.get('perfil_esforco')} | "
            f"Seed: {relatorio_jogo_real.get('seed')}\n"
        )
        txt_out += (
            f"Percentil vs MC: {relatorio_jogo_real.get('percentil_vs_monte_carlo')} | "
            f"p_emp: {relatorio_jogo_real.get('p_empirico_mc_supera_ou_iguala')}\n"
        )
    txt_out += "=" * 40 + "\n\n"

    if relatorio_jogo_real:
        st.markdown("#### 🎯 Relatório do Jogo Real")
        with st.container(border=True):
            r1, r2, r3, r4 = st.columns(4)
            r1.metric(
                "Percentil vs MC",
                f"{relatorio_jogo_real.get('percentil_vs_monte_carlo', 0):.1f}",
            )
            r2.metric(
                "p-empírico",
                f"{relatorio_jogo_real.get('p_empirico_mc_supera_ou_iguala', 0):.3f}",
            )
            r3.metric("Seed", relatorio_jogo_real.get("seed", "-"))
            r4.metric("Perfil", str(relatorio_jogo_real.get("perfil_esforco", "-")))

            r5, r6, r7, r8 = st.columns(4)
            r5.caption(
                f"Pool: **{relatorio_jogo_real.get('candidate_pool_size', '-')}**"
            )
            r6.caption(
                f"Torneio: **{relatorio_jogo_real.get('tournament_packages', '-')}**"
            )
            r7.caption(
                f"Monte Carlo: **{relatorio_jogo_real.get('monte_carlo_packages', '-')}**"
            )
            r8.caption(
                f"Modelo nulo: **{relatorio_jogo_real.get('null_model_samples', '-')}**"
            )

            with st.expander("Ver diagnóstico completo do pacote"):
                st.json(relatorio_jogo_real)

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

            # 1. Cria o container flex para as bolas
            html_balls_full = "<div style='display: flex; flex-wrap: wrap; gap: 5px; margin: 10px 0;'>"

            # 2. Gera o HTML de cada bola individualmente e adiciona à string principal
            for n in sorted(jogo):
                html_balls_full += render_ball_html(n, color_theme)

            # 3. Fecha o container
            html_balls_full += "</div>"

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
