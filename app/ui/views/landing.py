import streamlit as st

from app.ui.components.footer import render_footer
from app.ui.core.styles import apply_custom_css


def render_landing_page():
    apply_custom_css()

    # ========================================
    # HEADER COM LOGO
    # ========================================
    c1, c2 = st.columns([1, 5])
    with c1:
        st.image("assets/mascote_sena.png", width=60)
    with c2:
        st.markdown(
            "<div style='padding-top:15px; font-weight:800; font-size:1.4rem; color:#0f172a;'>LotoScience</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ========================================
    # HERO SECTION - LAYOUT Z-PATTERN
    # ========================================
    col_text, col_img = st.columns([1.1, 1], gap="large")

    with col_text:
        st.markdown('<div class="hero-container">', unsafe_allow_html=True)

        # Badge de status
        st.markdown(
            '<div class="hero-tag">✨ Aberto v1.0</div>', unsafe_allow_html=True
        )

        st.markdown(
            '<div class="hero-title">Seu Jogo Pode Valer<br>Centavos em Vez de Milhões</div>',
            unsafe_allow_html=True,
        )

        # SUBHEADLINE (promessa concreta + prova)
        st.markdown(
            '<div class="hero-subtitle">Se 1-2-3-4-5-6 sair na Mega-Sena, <strong>milhares de pessoas ganharão junto com você</strong>. Seu prêmio? Uma fração ridícula. O LotoScience avalia o <strong>Risco de Divisão</strong> do seu jogo e detecta padrões populares que sabotam seu bolso. Em 30 segundos, você sabe se está jogando igual à massa.</div>',
            unsafe_allow_html=True,
        )

        # BULLETS (ação + benefício)
        st.markdown(
            """
            <div style="margin-top: 25px; margin-bottom: 15px; color: #1e293b; font-size: 1.05rem; line-height: 1.6; background: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #6366f1;">
            <b>O que você descobre agora:</b>
            <ul style="margin-top: 10px; list-style-type: none; padding-left: 5px;">
                <li style="margin-bottom: 8px;">🔍 <b>Score Técnico:</b> Seu jogo é estatisticamente bom ou "lixo preditível"?</li>
                <li style="margin-bottom: 8px;">🚨 <b>Risco de Divisão:</b> Você vai dividir o prêmio com milhares ou está protegido?</li>
                <li style="margin-bottom: 0px;">⚡ <b>Gerador Inteligente:</b> Crie jogos melhores sem datas, sequências ou superstição.</li>
            </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # BOTÕES DE AÇÃO (2 CTAs lado a lado)
        b1, b2 = st.columns([1, 1.2])
        with b1:
            if st.button(
                "🚀 Validar Meu Jogo Agora (Grátis)",
                type="primary",
                use_container_width=True,
            ):
                st.switch_page("pages/1_Painel.py")
        with b2:
            if st.button("📖 Como funciona", use_container_width=True):
                st.switch_page("pages/0_Como_funciona.py")

        st.markdown("</div>", unsafe_allow_html=True)

    with col_img:
        # Imagem do mascote (lado direito do hero)
        st.markdown("<br>", unsafe_allow_html=True)
        try:
            st.image("assets/mascote_sena_full.png", width=500)
        except:
            st.info("💡 Insira 'mascote_sena_full.png' na pasta assets")

    st.markdown("<br><br>", unsafe_allow_html=True)

    # ========================================
    # SEÇÃO 2: O PROBLEMA (educação do mercado)
    # ========================================
    st.markdown(
        '<h3 style="text-align: center; color: #0f172a; margin-bottom: 1rem;">⚠️ O problema oculto: você não diminui chance de ganhar, mas aumenta o risco de dividir prêmio</h3>',
        unsafe_allow_html=True,
    )

    col_problema1, col_problema2 = st.columns(2)

    with col_problema1:
        st.markdown(
            """
            <div style="background-color: #fef2f2; padding: 20px; border-radius: 10px; border-left: 4px solid #ef4444;">
            <h4 style="color: #991b1b; margin-top: 0;">Por que seu cérebro joga errado?</h4>
            <p style="font-size: 0.95rem; color: #7f1d1d; line-height: 1.6;">
            Humanos são péssimos geradores de números aleatórios. Jogamos <strong>datas de aniversário (01-31)</strong>, 
            desenhamos formas no volante e copiamos <strong>sequências famosas</strong> (4, 8, 15, 16, 23, 42 de Lost).
            </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_problema2:
        st.markdown(
            """
            <div style="background-color: #fffbeb; padding: 20px; border-radius: 10px; border-left: 4px solid #f59e0b;">
            <h4 style="color: #92400e; margin-top: 0;">O risco financeiro</h4>
            <p style="font-size: 0.95rem; color: #78350f; line-height: 1.6;">
            Quando milhares de pessoas jogam o mesmo padrão, <strong>o prêmio é dividido</strong>. 
            O LotoScience detecta esses padrões e alerta você <em>antes</em> de apostar.
            <br><br>
            <strong>Não prometemos ganho. Prometemos proteção.</strong>
            </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================
    # SEÇÃO 3: FEATURES (3 cards principais)
    # ========================================
    st.markdown(
        '<h3 style="text-align: center; color: #0f172a; margin-bottom: 2rem;">🎯 O que o LotoScience faz por você</h3>',
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3, gap="medium")

    with c1:
        st.markdown(
            """
            <div class="feature-card">
                <div class="icon-box">🔬</div>
                <div class="card-title">Validador de Jogos</div>
                <div class="card-text">
                    Cole seus números e receba:
                    <ul style="margin-top: 8px; font-size: 0.9rem;">
                        <li><strong>Score técnico</strong> (0-100)</li>
                        <li><strong>Risco de divisão</strong> (Baixo/Alto)</li>
                        <li><strong>Alertas do analista</strong></li>
                    </ul>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            """
            <div class="feature-card">
                <div class="icon-box">⚙️</div>
                <div class="card-title">Gerador Inteligente</div>
                <div class="card-text">
                    Crie 1-10 jogos em segundos:
                    <ul style="margin-top: 8px; font-size: 0.9rem;">
                        <li><strong>Conservadora:</strong> números quentes</li>
                        <li><strong>Balanceada:</strong> mix inteligente</li>
                        <li><strong>Agressiva:</strong> aposta em atrasados</li>
                    </ul>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            """
            <div class="feature-card">
                <div class="icon-box">👥</div>
                <div class="card-title">Auditoria de Bolão</div>
                <div class="card-text">
                    Cole todos os jogos do grupo:
                    <ul style="margin-top: 8px; font-size: 0.9rem;">
                        <li><strong>Detecta duplicatas</strong> (pagos 2x)</li>
                        <li><strong>Cobertura</strong> do volante</li>
                        <li><strong>Score médio</strong> do bolão</li>
                    </ul>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================
    # SEÇÃO 4: SOCIAL PROOF / CREDIBILIDADE
    # ========================================
    st.markdown(
        """
        <div style="background-color: #f0fdf4; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #86efac;">
            <h4 style="color: #166534; margin: 0;">✅ Metodologia validada com backtest científico</h4>
            <p style="color: #15803d; margin-top: 8px; font-size: 0.95rem;">
            Testamos nosso algoritmo em milhares de sorteios reais. Scores altos correlacionam com 
            <strong>menor popularidade</strong> e <strong>maior equilíbrio estatístico</strong>.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================
    # SEÇÃO 5: PLANOS (destaque visual maior)
    # ========================================
    st.markdown(
        '<h3 style="text-align: center; color: #0f172a; margin-bottom: 1.5rem;">💳 Escolha seu Plano</h3>',
        unsafe_allow_html=True,
    )

    col_free, col_pro = st.columns(2, gap="large")

    with col_free:
        st.markdown(
            """
<div style="background-color: #f8fafc; padding: 30px; border-radius: 12px; border: 2px solid #e2e8f0; height: 100%;">
    <h3 style="color: #475569; margin-top: 0;">FREE</h3>
    <div style="font-size: 2rem; font-weight: 700; color: #0f172a; margin: 10px 0;">Grátis</div>
    <div style="font-size: 0.9rem; color: #64748b; margin-bottom: 20px;">Para sempre</div>
    <ul style="list-style: none; padding: 0; color: #334155; line-height: 2;">
        <li>✅ 1 validação/dia</li>
        <li>✅ 1 geração/dia</li>
        <li>✅ Painel de estatísticas</li>
        <li>✅ Análise básica</li>
        <li>✅ Sistema de bolão</li>
        <li>❌ Fechamentos avançados</li>
        <li>❌ Estatísticas avançadas</li>
    </ul>
</div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🎁 Criar Conta FREE", use_container_width=True, key="btn_free"):
            st.switch_page("pages/7_Registro.py")

    with col_pro:
        st.markdown(
            """
<div style="background-color: #fefce8; padding: 30px; border-radius: 12px; border: 3px solid #fbbf24; height: 100%; position: relative;">
    <div style="font-size: 0.8rem; color: #b45309; background: #fffbeb; padding: 2px 8px; border-radius: 4px; display: inline-block; margin-bottom: 5px;">
        ⚡ Preço garantido por 12 meses
    </div>
    <div style="position: absolute; top: -12px; right: 20px; background: #fbbf24; color: #78350f; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700;">
        🔥 MAIS ESCOLHIDO
    </div>
    <h3 style="color: #92400e; margin-top: 0;">PRO</h3>
    <div style="font-size: 2rem; font-weight: 700; color: #0f172a; margin: 10px 0;">
        R$ 9<span style="font-size: 1rem; color: #64748b;">/mês</span>
    </div>
    <ul style="list-style: none; padding: 0; color: #334155; line-height: 2;">
        <li>✅ <strong>Validações ilimitadas</strong></li>
        <li>✅ <strong>Gerações ilimitadas</strong></li>
        <li>✅ Fechamentos avançados</li>
        <li>✅ Sistema de bolão</li>
        <li>✅ Estatísticas avançadas</li>
        <li>✅ Dashboard completo</li>
        <li>✅ Suporte prioritário</li>
    </ul>
</div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "🚀 Assinar PRO", type="primary", use_container_width=True, key="btn_pro"
        ):
            st.switch_page("pages/6_Login.py")

    # Badge de confiança abaixo dos planos
    st.markdown(
        """
        <div style="text-align: center; margin-top: 20px; color: #64748b; font-size: 0.9rem;">
            🔒 Dados seguros | ❌ Sem fidelidade | 💳 Cancele quando quiser
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br><br>", unsafe_allow_html=True)

    # ========================================
    # SEÇÃO 6: FAQ RÁPIDO
    # ========================================
    st.markdown(
        '<h3 style="text-align: center; color: #0f172a; margin-bottom: 1.5rem;">❓ Perguntas Frequentes</h3>',
        unsafe_allow_html=True,
    )

    with st.expander("🎯 O LotoScience aumenta minhas chances de ganhar?"):
        st.markdown(
            """
            **Não prometemos ganho.** Nosso foco é:
            - ✅ **Reduzir risco de divisão de prêmio** (evitando padrões populares)
            - ✅ **Garantir qualidade estatística** do jogo (equilíbrio matemático)
            - ✅ **Proteger seu investimento** (menos desperdício com padrões ruins)
            """
        )

    with st.expander("🔍 Como funciona a auditoria de risco de divisão?"):
        st.markdown(
            """
            Comparamos seu jogo com **padrões conhecidos de massa**:
            - Datas de aniversário (01-31)
            - Números de Lost (4, 8, 15, 16, 23, 42)
            - Sequências óbvias (1-2-3-4-5-6)
            - Padrões geométricos no volante

            Se detectarmos alta similaridade, alertamos: **"Risco ALTO — Padrão popular"**.
            """
        )

    with st.expander("⚙️ Qual a diferença entre as 3 estratégias do gerador?"):
        st.markdown(
            """
            - **Conservadora:** Prioriza números que saíram recentemente (70% quentes)
            - **Balanceada:** Mix inteligente (40% quentes + 60% atrasados) — **recomendado**
            - **Agressiva:** Aposta em números atrasados (80% gaps) — regresso à média
            - **Pura:** 100% aleatório, sem viés estatístico
            """
        )

    with st.expander("🎲 Funciona para quais loterias?"):
        st.markdown(
            """
            ✅ **Mega-Sena** (60 números, aposta de 6-20)  
            ✅ **Quina** (80 números, aposta de 5-15)  
            ✅ **Lotofácil** (25 números, aposta de 15-20)  
            ✅ **Lotomania** (100 números, aposta de 50)
            """
        )

    with st.expander("💳 Como cancelo o plano Pro?"):
        st.markdown(
            """
            **Sem burocracia!** Basta enviar email para: contato@lotoscience.com

            ℹ️ Atualmente o upgrade é manual (MVP). Em breve integraremos Stripe/Mercado Pago.
            """
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================
    # CTA FINAL
    # ========================================
    st.markdown(
        """
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 50px; border-radius: 16px; text-align: center; color: white; 
            box-shadow: 0 10px 25px -5px rgba(100, 100, 250, 0.4);">
    <h2 style="margin: 0; color: white; font-size: 2rem;">Pronto para auditar seu próximo jogo?</h2>
    <p style="font-size: 1.1rem; margin: 15px 0 30px 0; opacity: 0.95; max-width: 600px; margin-left: auto; margin-right: auto;">
        Comece grátis agora e veja o score do seu jogo em 30 segundos.
    </p>
    <a href="Registro" target="_self" style="text-decoration: none;">
        <div style="
            background-color: #22c55e; 
            color: white; 
            padding: 16px 32px; 
            border-radius: 99px; 
            display: inline-block;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            cursor: pointer;
        " 
        >
            🚀 Começar agora gratuitamente
        </div>
    </a>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br><br>", unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Footer
    render_footer()


def render_como_funciona():
    apply_custom_css()

    # Botão voltar no topo
    if st.button("← Voltar para Início"):
        st.switch_page("pages/0_Inicio.py")

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================
    # HEADER DA PÁGINA
    # ========================================
    st.markdown(
        """
        <div style="text-align: center; padding: 20px 0;">
            <h1 style="color: #0f172a; margin-bottom: 10px;">🔬 A Metodologia LotoScience</h1>
            <p style="font-size: 1.2rem; color: #64748b; max-width: 800px; margin: 0 auto;">
            Por que seu cérebro joga errado e como a ciência pode proteger seu dinheiro
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ========================================
    # SEÇÃO 1: O PROBLEMA (viés cognitivo)
    # ========================================
    c1, c2 = st.columns([2, 1])

    with c1:
        st.markdown("## 🧠 Por que seu cérebro joga errado?")

        st.markdown(
            """
            <p style="font-size: 1.05rem; line-height: 1.6; color: #475569;">
            Humanos são péssimos geradores de números aleatórios. Temos <strong>vieses cognitivos</strong> 
            que nos fazem escolher padrões previsíveis:
            </p>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div style="background-color: #fef2f2; padding: 20px; border-radius: 10px; border-left: 4px solid #ef4444; margin: 15px 0;">
                <h4 style="color: #991b1b; margin-top: 0;">❌ Os 4 erros mais comuns:</h4>
                <ol style="color: #7f1d1d; line-height: 1.8; font-size: 1rem;">
                    <li><strong>Datas de aniversário:</strong> Limitam números a 01-31 (apenas 51% do volante da Mega-Sena)</li>
                    <li><strong>Sequências óbvias:</strong> 1-2-3-4-5-6 é um dos jogos mais apostados do Brasil</li>
                    <li><strong>Números famosos:</strong> Lost (4, 8, 15, 16, 23, 42) é jogado por milhares toda semana</li>
                    <li><strong>Formas geométricas:</strong> Desenhar linhas, cruzes ou quadrados no volante</li>
                </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.success(
            "✅ **O LotoScience é um Auditor de Qualidade:** garantimos alta qualidade estatística "
            "e baixo risco de divisão de prêmio."
        )

    with c2:
        try:
            st.image("assets/mascote_sena.png", width=220)
        except:
            st.warning("🎲 Sem imagem")

        st.markdown(
            """
            <div style="background-color: #fffbeb; padding: 15px; border-radius: 8px; margin-top: 20px;">
                <h4 style="color: #92400e; margin-top: 0;">💡 Você sabia?</h4>
                <p style="color: #78350f; font-size: 0.95rem;">
                Se 1-2-3-4-5-6 sair na Mega-Sena, o prêmio será dividido entre 
                <strong>milhares de ganhadores</strong>. Você levaria centavos.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    # ========================================
    # SEÇÃO 2: OS PILARES DO SISTEMA
    # ========================================
    st.markdown("## ⚙️ A Ciência por Trás do Score: 4 Pilares")

    st.markdown(
        """
        <p style="font-size: 1.05rem; color: #475569; margin-bottom: 30px;">
        Cada jogo passa por <strong>mais de 18 filtros estatísticos independentes</strong>, 
        organizados em 4 pilares principais. O sistema acumula penalidades ou bônus até 
        gerar o score final (0-100). <strong>Todos os thresholds são auto-ajustados</strong> 
        pela densidade do jogo.
        </p>
        """,
        unsafe_allow_html=True,
    )

    # Grid 2x2 dos 4 pilares (sem revelar todos os 18 filtros)
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 30px; border-radius: 12px; color: white; min-height: 280px;">
                <div style="font-size: 3rem; margin-bottom: 15px; text-align: center;">📊</div>
                <h3 style="color: white; margin: 10px 0; text-align: center;">Pilar 1: Análise Estatística Clássica</h3>
                <p style="font-size: 0.95rem; opacity: 0.95; line-height: 1.6;">
                <strong>O que valida:</strong> Soma, distribuição par/ímpar, finais (0-9), 
                concentração espacial, intervalos de confiança históricos.<br><br>
                <strong>Tecnologia:</strong> Z-score, Coeficiente de Gini, Teste de Uniformidade.<br><br>
                <strong>Penalidades:</strong> Até -25 pts por desvios extremos.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                        padding: 30px; border-radius: 12px; color: white; min-height: 280px;">
                <div style="font-size: 3rem; margin-bottom: 15px; text-align: center;">🚨</div>
                <h3 style="color: white; margin: 10px 0; text-align: center;">Pilar 2: Detecção de Popularidade</h3>
                <p style="font-size: 0.95rem; opacity: 0.95; line-height: 1.6;">
                <strong>O que valida:</strong> Padrões populares que aumentam risco de divisão 
                (sequências, datas, números famosos, formas geométricas).<br><br>
                <strong>Tecnologia:</strong> Entropia de Shannon, análise de motifs, 
                banco de dados de padrões virais.<br><br>
                <strong>Penalidades:</strong> Até -15 pts por padrão. Marca "Risco: ALTO" se 3+.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                        padding: 30px; border-radius: 12px; color: white; min-height: 280px;">
                <div style="font-size: 3rem; margin-bottom: 15px; text-align: center;">🔬</div>
                <h3 style="color: white; margin: 10px 0; text-align: center;">Pilar 3: Análise de Unicidade</h3>
                <p style="font-size: 0.95rem; opacity: 0.95; line-height: 1.6;">
                <strong>O que valida:</strong> O quão único é seu jogo comparado ao histórico 
                completo e aos padrões mais apostados.<br><br>
                <strong>Tecnologia:</strong> Distância de Hamming, análise de co-ocorrência de pares, 
                distribuição geométrica por quadrantes.<br><br>
                <strong>Bônus:</strong> +5 pts se jogo é estatisticamente raro e bem distribuído.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); 
                        padding: 30px; border-radius: 12px; color: white; min-height: 280px;">
                <div style="font-size: 3rem; margin-bottom: 15px; text-align: center;">🎯</div>
                <h3 style="color: white; margin: 10px 0; text-align: center;">Pilar 4: Inteligência Preditiva</h3>
                <p style="font-size: 0.95rem; opacity: 0.95; line-height: 1.6;">
                <strong>O que valida:</strong> Usa regressão à média validada estatisticamente 
                para identificar se números atrasados têm poder preditivo real.<br><br>
                <strong>Tecnologia:</strong> Correlação de Spearman, Order Statistics, 
                Análise de Compressibilidade.<br><br>
                <strong>Bônus:</strong> +5 pts se correlação >0.3 e jogo tem 40%+ atrasados.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Card de resumo sem revelar os 18 filtros específicos
    st.markdown(
        """
        <div style="background-color: #f8fafc; padding: 30px; border-radius: 12px; border: 2px solid #e2e8f0;">
            <h4 style="color: #0f172a; margin-top: 0; text-align: center;">🧮 Como funciona na prática</h4>
            <p style="font-size: 1rem; color: #475569; text-align: center; line-height: 1.7; margin-bottom: 20px;">
            Cada jogo começa com <strong>100 pontos</strong>. Os 18+ filtros aplicam penalidades 
            ou bônus baseados em <strong>desvios estatísticos</strong> de milhares de sorteios reais.
            </p>
            <div style="text-align: center; font-size: 1.1rem; font-family: monospace; color: #334155; margin: 20px 0;">
                Score = 100 - Σ(penalidades) + Σ(bônus)
            </div>
            <p style="font-size: 0.9rem; color: #64748b; text-align: center; margin-top: 20px;">
                <strong>Correção de Bonferroni aplicada:</strong> Para evitar falsos positivos em testes múltiplos, 
                ajustamos o p-value para α = 0.0033 (ao invés de 0.05 padrão).
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Grid de badges mostrando tecnologias sem revelar a arquitetura
    st.markdown("### 🔬 Tecnologias Estatísticas Empregadas")

    col_tech1, col_tech2, col_tech3 = st.columns(3)

    with col_tech1:
        st.markdown(
            """
            <div style="text-align: center; padding: 15px;">
                <div style="background-color: #dbeafe; color: #1e40af; padding: 10px 20px; 
                            border-radius: 20px; display: inline-block; margin: 5px; font-size: 0.9rem;">
                    Z-Score
                </div>
                <div style="background-color: #fef3c7; color: #92400e; padding: 10px 20px; 
                            border-radius: 20px; display: inline-block; margin: 5px; font-size: 0.9rem;">
                    Entropia de Shannon
                </div>
                <div style="background-color: #f0fdf4; color: #065f46; padding: 10px 20px; 
                            border-radius: 20px; display: inline-block; margin: 5px; font-size: 0.9rem;">
                    Coeficiente de Gini
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_tech2:
        st.markdown(
            """
            <div style="text-align: center; padding: 15px;">
                <div style="background-color: #fae8ff; color: #6b21a8; padding: 10px 20px; 
                            border-radius: 20px; display: inline-block; margin: 5px; font-size: 0.9rem;">
                    Distância de Hamming
                </div>
                <div style="background-color: #fee2e2; color: #991b1b; padding: 10px 20px; 
                            border-radius: 20px; display: inline-block; margin: 5px; font-size: 0.9rem;">
                    Correlação de Spearman
                </div>
                <div style="background-color: #ecfdf5; color: #047857; padding: 10px 20px; 
                            border-radius: 20px; display: inline-block; margin: 5px; font-size: 0.9rem;">
                    Order Statistics
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_tech3:
        st.markdown(
            """
            <div style="text-align: center; padding: 15px;">
                <div style="background-color: #fffbeb; color: #78350f; padding: 10px 20px; 
                            border-radius: 20px; display: inline-block; margin: 5px; font-size: 0.9rem;">
                    IC Bootstrap
                </div>
                <div style="background-color: #eff6ff; color: #1e3a8a; padding: 10px 20px; 
                            border-radius: 20px; display: inline-block; margin: 5px; font-size: 0.9rem;">
                    Teste de Uniformidade
                </div>
                <div style="background-color: #fef2f2; color: #7f1d1d; padding: 10px 20px; 
                            border-radius: 20px; display: inline-block; margin: 5px; font-size: 0.9rem;">
                    Correção de Bonferroni
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.info(
        "💡 **Por que não revelamos todos os 18 filtros?** Nosso algoritmo é resultado de meses de "
        "pesquisa e testes estatísticos. Revelamos a **filosofia** (4 pilares) e as **tecnologias** empregadas, "
        "mas os thresholds, pesos e a arquitetura exata são nosso diferencial competitivo."
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================
    # SEÇÃO 3: COMO USAR (passo a passo visual)
    # ========================================
    st.markdown("## 🚀 Como usar o LotoScience (passo a passo)")

    # Timeline visual com 3 passos
    step1, step2, step3 = st.columns(3)

    with step1:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 30px; border-radius: 12px; color: white; text-align: center;">
                <div style="font-size: 3rem; margin-bottom: 10px;">1️⃣</div>
                <h3 style="color: white; margin: 10px 0;">Digite ou cole</h3>
                <p style="font-size: 0.95rem; opacity: 0.95; line-height: 1.5;">
                Escolha a loteria (Mega-Sena, Quina, Lotofácil) e digite seus números no validador.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with step2:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                        padding: 30px; border-radius: 12px; color: white; text-align: center;">
                <div style="font-size: 3rem; margin-bottom: 10px;">2️⃣</div>
                <h3 style="color: white; margin: 10px 0;">Receba o diagnóstico</h3>
                <p style="font-size: 0.95rem; opacity: 0.95; line-height: 1.5;">
                Em 3 segundos veja: Score técnico + Risco de divisão + Alertas do analista.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with step3:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                        padding: 30px; border-radius: 12px; color: white; text-align: center;">
                <div style="font-size: 3rem; margin-bottom: 10px;">3️⃣</div>
                <h3 style="color: white; margin: 10px 0;">Gere ou ajuste</h3>
                <p style="font-size: 0.95rem; opacity: 0.95; line-height: 1.5;">
                Se o score for baixo, use o Gerador Inteligente para criar um jogo melhor.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================
    # SEÇÃO 4: EXEMPLO PRÁTICO (antes x depois)
    # ========================================
    st.markdown("## 📊 Exemplo prático: Antes vs Depois")

    col_antes, col_depois = st.columns(2, gap="large")

    with col_antes:
        st.markdown(
            """
            <div style="background-color: #fef2f2; padding: 25px; border-radius: 12px; border: 2px solid #fca5a5;">
                <h3 style="color: #991b1b; margin-top: 0;">❌ ANTES (jogo comum)</h3>
                <div style="font-size: 1.3rem; font-family: monospace; color: #7f1d1d; margin: 15px 0; text-align: center;">
                    <strong>03 - 07 - 12 - 18 - 25 - 31</strong>
                </div>
                <hr style="border-color: #fca5a5;">
                <p style="color: #7f1d1d; font-size: 0.95rem; line-height: 1.6;">
                <strong>Score técnico:</strong> 37/100 ⚠️<br>
                <strong>Risco de divisão:</strong> ALTO 🚨<br>
                <strong>Problema:</strong> Todos números ≤ 31 (datas)<br>
                <strong>Alerta:</strong> Padrão muito popular. Se sair, prêmio dividido com milhares.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_depois:
        st.markdown(
            """
            <div style="background-color: #f0fdf4; padding: 25px; border-radius: 12px; border: 2px solid #86efac;">
                <h3 style="color: #166534; margin-top: 0;">✅ DEPOIS (gerado pelo LotoScience)</h3>
                <div style="font-size: 1.3rem; font-family: monospace; color: #15803d; margin: 15px 0; text-align: center;">
                    <strong>08 - 17 - 23 - 34 - 42 - 58</strong>
                </div>
                <hr style="border-color: #86efac;">
                <p style="color: #15803d; font-size: 0.95rem; line-height: 1.6;">
                <strong>Score técnico:</strong> 87/100 ✅<br>
                <strong>Risco de divisão:</strong> BAIXO 🛡️<br>
                <strong>Qualidade:</strong> Soma OK, entropia alta, finais equilibrados<br>
                <strong>Status:</strong> Jogo de alta qualidade estatística!
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================
    # SEÇÃO 5: CREDIBILIDADE CIENTÍFICA
    # ========================================
    st.markdown("## 🔬 Validação Científica: Backtest")

    st.markdown(
        """
        <div style="background-color: #eff6ff; padding: 30px; border-radius: 12px; border-left: 5px solid #3b82f6;">
            <h4 style="color: #1e40af; margin-top: 0;">Como sabemos que funciona?</h4>
            <p style="font-size: 1.05rem; color: #1e3a8a; line-height: 1.7;">
            Testamos nosso sistema de scoring em <strong>milhares de sorteios históricos reais</strong>. 
            O resultado:
            </p>
            <ul style="color: #1e3a8a; font-size: 1rem; line-height: 1.8;">
                <li>✅ Scores altos (80+) correlacionam com <strong>maior unicidade</strong> (distância de Hamming)</li>
                <li>✅ Scores altos correlacionam com <strong>menos alertas de risco</strong></li>
                <li>✅ Jogos com score alto têm <strong>menor similaridade</strong> com padrões populares</li>
            </ul>
            <p style="font-size: 0.95rem; color: #1e40af; margin-top: 15px;">
            📖 <em>Metodologia: Backtest com 1.000 amostras aleatórias comparadas ao histórico completo.</em>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================
    # SEÇÃO 6: ESTRATÉGIAS DO GERADOR
    # ========================================
    st.markdown("## ⚙️ As 3 Estratégias do Gerador Inteligente")

    st.markdown(
        """
        <p style="font-size: 1.05rem; color: #475569; margin-bottom: 25px;">
        Cada estratégia tem uma <strong>filosofia estatística diferente</strong>. Escolha baseado no seu perfil:
        </p>
        """,
        unsafe_allow_html=True,
    )

    col_conserv, col_balanc, col_agress = st.columns(3)

    with col_conserv:
        st.markdown(
            """
            <div style="background-color: #fef3c7; padding: 20px; border-radius: 10px; border: 2px solid #fbbf24;">
                <h4 style="color: #92400e; margin-top: 0;">🟡 Conservadora</h4>
                <p style="font-size: 0.95rem; color: #78350f; line-height: 1.6;">
                <strong>Filosofia:</strong> "O que está quente continua quente"<br><br>
                <strong>Peso:</strong> 70% frequência, 30% atrasos<br><br>
                <strong>Para quem:</strong> Prefere números que saíram recentemente<br><br>
                <strong>Risco:</strong> Baixo
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_balanc:
        st.markdown(
            """
            <div style="background-color: #dbeafe; padding: 20px; border-radius: 10px; border: 2px solid #3b82f6;">
                <h4 style="color: #1e40af; margin-top: 0;">🔵 Balanceada ⭐</h4>
                <p style="font-size: 0.95rem; color: #1e3a8a; line-height: 1.6;">
                <strong>Filosofia:</strong> "Mix inteligente"<br><br>
                <strong>Peso:</strong> 40% frequência, 60% atrasos<br><br>
                <strong>Para quem:</strong> Quer equilíbrio entre quentes e frios<br><br>
                <strong>Risco:</strong> Médio<br><br>
                <em>✅ Mais recomendada</em>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_agress:
        st.markdown(
            """
            <div style="background-color: #fee2e2; padding: 20px; border-radius: 10px; border: 2px solid #ef4444;">
                <h4 style="color: #991b1b; margin-top: 0;">🔴 Agressiva</h4>
                <p style="font-size: 0.95rem; color: #7f1d1d; line-height: 1.6;">
                <strong>Filosofia:</strong> "Regresso à média"<br><br>
                <strong>Peso:</strong> 20% frequência, 80% atrasos<br><br>
                <strong>Para quem:</strong> Aposta em números atrasados<br><br>
                <strong>Risco:</strong> Alto
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.info(
        "💡 **Dica:** Se a análise de regresso à média mostrar correlação > 0.3, "
        "a estratégia Agressiva é cientificamente justificada!"
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================
    # SEÇÃO 7: DASHBOARD DE INTELIGÊNCIA
    # ========================================
    st.markdown("## 📊 Dashboard de Inteligência: O Raio-X Completo")

    st.markdown(
        """
        <p style="font-size: 1.05rem; color: #475569; margin-bottom: 20px;">
        Além do validador e gerador, o painel mostra <strong>inteligência completa</strong> dos sorteios:
        </p>
        """,
        unsafe_allow_html=True,
    )

    # Grid 2x2 de features do dashboard
    dash1, dash2 = st.columns(2)

    with dash1:
        st.markdown(
            """
            <div style="background-color: #f8fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 15px;">
                <h4 style="color: #0f172a; margin-top: 0;">🔥 Relógio dos Atrasados</h4>
                <p style="color: #475569; font-size: 0.95rem;">
                Gráfico mostrando top 20 números que não aparecem há mais tempo. 
                Segundo a estatística, a chance de voltarem aumenta.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div style="background-color: #f8fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0;">
                <h4 style="color: #0f172a; margin-top: 0;">🗺️ Mapa de Calor Interativo</h4>
                <p style="color: #475569; font-size: 0.95rem;">
                Visualize padrões geométricos no volante: moldura, miolo, cruz, xis, quadrantes. 
                Filtre por grupo para ver concentrações.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with dash2:
        st.markdown(
            """
            <div style="background-color: #f8fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 15px;">
                <h4 style="color: #0f172a; margin-top: 0;">📈 Validação de Regresso à Média</h4>
                <p style="color: #475569; font-size: 0.95rem;">
                Teste estatístico (correlação de Spearman) que valida se números atrasados 
                realmente tendem a sair nos próximos sorteios.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div style="background-color: #f8fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0;">
                <h4 style="color: #0f172a; margin-top: 0;">🔬 Auditoria de Integridade</h4>
                <p style="color: #475569; font-size: 0.95rem;">
                Testes Chi-quadrado e Kolmogorov-Smirnov para validar se o sorteio é 
                estatisticamente honesto (distribuição uniforme).
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        """
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 40px; border-radius: 16px; text-align: center; color: white; margin-top: 40px;
            box-shadow: 0 10px 20px rgba(118, 75, 162, 0.3);">
    <h2 style="margin: 0; color: white;">Agora que você entendeu a metodologia...</h2>
    <p style="font-size: 1.2rem; margin: 20px 0 30px 0; opacity: 0.95;">
    Está pronto para auditar seu próximo jogo e ver o score em tempo real?
    </p>
    <a href="Painel" target="_self" style="text-decoration: none;">
        <div style="
            background-color: #22c55e; 
            color: white; 
            padding: 16px 32px; 
            border-radius: 99px; 
            display: inline-block;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            cursor: pointer;
        "
        >
            🚀 Ir para o Validador agora
        </div>
    </a>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Footer
    render_footer()
