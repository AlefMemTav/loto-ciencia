import streamlit as st

from app.ui.components.footer import render_footer
from app.ui.core.styles import apply_custom_css


def render_landing_page():
    """Landing page educacional com foco em conversão orgânica."""
    apply_custom_css()

    # ========================================
    # HERO SECTION
    # ========================================
    col_hero_left, col_hero_right = st.columns([3, 2], gap="large")

    with col_hero_left:
        # HEADLINE PRINCIPAL (hook emocional + específico)
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

        # CTA PRINCIPAL
        col_cta1, col_cta2 = st.columns([3, 2])
        with col_cta1:
            if st.button(
                "🚀 Validar Meu Jogo Agora (Grátis)",
                type="primary",
                width="stretch",
            ):
                st.switch_page("pages/1_Painel.py")

        with col_cta2:
            if st.button("📖 Como Funciona?", width="stretch"):
                st.switch_page("pages/0_Como_funciona.py")

        # SOCIAL PROOF
        st.markdown(
            """
            <div style="margin-top: 20px; padding: 12px; background-color: #f0fdf4; border-radius: 8px; border-left: 3px solid #10b981;">
                <span style="color: #065f46; font-size: 0.9rem;">
                ✅ <b>Backtest validado:</b> Sistema testado em milhares de sorteios históricos reais
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_hero_right:
        try:
            st.image("assets/mascote_sena_full.png", width="stretch")
        except:
            st.info("🎲 Imagem do mascote aqui")

    st.markdown("<br><br>", unsafe_allow_html=True)

    # ========================================
    # SEÇÃO: O PROBLEMA (educação de mercado)
    # ========================================
    st.markdown("---")
    st.markdown("## 🧠 O Problema: Seu Cérebro Joga Errado")

    col_prob1, col_prob2 = st.columns(2, gap="large")

    with col_prob1:
        st.markdown(
            """
            <div style="background-color: #fef2f2; padding: 25px; border-radius: 10px; border-left: 4px solid #ef4444;">
                <h4 style="color: #991b1b; margin-top: 0;">❌ Padrões que matam seu prêmio:</h4>
                <ul style="color: #7f1d1d; line-height: 1.8;">
                    <li><b>Datas de aniversário</b> (01-31): Só cobrem 51% do volante da Mega-Sena</li>
                    <li><b>Sequências óbvias</b> (1-2-3-4-5-6): Milhares apostam isso toda semana</li>
                    <li><b>Números da sorte</b> (4-8-15-16-23-42 do Lost): Padrão viral = divisão certa</li>
                    <li><b>Formas geométricas</b>: Desenhar linhas/cruzes no volante é comum</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_prob2:
        st.markdown(
            """
            <div style="background-color: #eff6ff; padding: 25px; border-radius: 10px; border-left: 4px solid #3b82f6;">
                <h4 style="color: #1e40af; margin-top: 0;">💡 Por que isso é perigoso?</h4>
                <p style="color: #1e3a8a; line-height: 1.7;">
                Se um padrão popular <b>sair mesmo</b>, o prêmio será dividido entre 
                <b>milhares de ganhadores</b>. Você levaria uma fração ridícula do valor esperado.
                </p>
                <p style="color: #1e3a8a; line-height: 1.7; margin-top: 15px;">
                <b>Exemplo real:</b> Se 1-2-3-4-5-6 ganhasse a Mega-Sena com prêmio de R$ 60 milhões 
                e 10.000 pessoas jogaram isso, cada um levaria <b>R$ 6.000</b> ao invés de milhões.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.success(
        "✅ **O LotoScience é seu auditor de risco:** Detectamos esses padrões em segundos "
        "e te alertamos antes de você apostar."
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================
    # SEÇÃO: FEATURES (3 cards principais)
    # ========================================
    st.markdown("---")
    st.markdown("## ⚙️ As 3 Ferramentas Principais")

    feat1, feat2, feat3 = st.columns(3, gap="medium")

    with feat1:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 25px; border-radius: 12px; color: white; text-align: center; min-height: 320px;">
                <div style="font-size: 3rem; margin-bottom: 15px;">🔍</div>
                <h3 style="color: white; margin: 10px 0;">Validador Técnico</h3>
                <p style="font-size: 0.95rem; opacity: 0.95; line-height: 1.6;">
                Digite seus números e receba em 3 segundos:<br><br>
                • <b>Score 0-100</b> (qualidade estatística)<br>
                • <b>Risco de Divisão</b> (Alto/Médio/Baixo)<br>
                • <b>Alertas do Analista</b> (o que está errado)<br><br>
                <em>Baseado em 18+ filtros matemáticos</em>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with feat2:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                        padding: 25px; border-radius: 12px; color: white; text-align: center; min-height: 320px;">
                <div style="font-size: 3rem; margin-bottom: 15px;">🤖</div>
                <h3 style="color: white; margin: 10px 0;">Gerador Inteligente</h3>
                <p style="font-size: 0.95rem; opacity: 0.95; line-height: 1.6;">
                Crie jogos de alta qualidade automaticamente:<br><br>
                • <b>3 estratégias</b> (conservadora/balanceada/agressiva)<br>
                • <b>Score garantido 80+</b> (após até 10k tentativas)<br>
                • <b>Sem padrões populares</b> (datas, sequências, Lost)<br><br>
                <em>Usa dados históricos reais</em>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with feat3:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                        padding: 25px; border-radius: 12px; color: white; text-align: center; min-height: 320px;">
                <div style="font-size: 3rem; margin-bottom: 15px;">👥</div>
                <h3 style="color: white; margin: 10px 0;">Auditor de Bolão</h3>
                <p style="font-size: 0.95rem; opacity: 0.95; line-height: 1.6;">
                Cole todos os jogos do seu grupo e veja:<br><br>
                • <b>Score médio do bolão</b><br>
                • <b>Cobertura do volante</b> (% de números jogados)<br>
                • <b>Jogos duplicados</b> (você está pagando 2x?)<br><br>
                <em>Ideal para grupos de WhatsApp</em>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================
    # SEÇÃO: PLANOS OTIMIZADOS (2 visíveis + Enterprise oculto)
    # ========================================
    st.markdown("---")
    st.markdown("## 💎 Escolha Seu Plano")

    st.markdown(
        '<p style="text-align: center; color: #64748b; font-size: 1.05rem; margin-bottom: 30px;">'
        "Comece grátis e faça upgrade quando precisar de mais poder."
        "</p>",
        unsafe_allow_html=True,
    )

    # Grid 2 colunas (Free + Pro) com espaçamento lateral
    col_spacing1, plan1, plan2, col_spacing2 = st.columns([0.5, 2, 2, 0.5], gap="large")

    with plan1:
        st.markdown(
            """
<div style="background-color: #f8fafc; padding: 30px; border-radius: 12px; border: 2px solid #e2e8f0; text-align: center; min-height: 520px;">
    <h3 style="color: #334155; margin-top: 0; font-size: 1.5rem;">🆓 Free</h3>
    <div style="font-size: 2.5rem; color: #64748b; margin: 20px 0; font-weight: bold;">R$ 0</div>
    <p style="color: #64748b; font-size: 1rem; margin-bottom: 25px;">Para sempre</p>
    <div style="background-color: #f1f5f9; padding: 10px; border-radius: 8px; margin-bottom: 20px;">
        <span style="color: #475569; font-size: 0.95rem; font-weight: 600;">
        ✅ Teste de verdade: 3 validações/dia
        </span>
    </div>
    <hr style="border-color: #e2e8f0; margin: 25px 0;">
    <ul style="text-align: left; color: #475569; line-height: 2; font-size: 1rem; list-style: none; padding-left: 0;">
        <li><span style="color: #10b981; font-weight: bold;">✅</span> Validador técnico (3 usos/dia)</li>
        <li><span style="color: #10b981; font-weight: bold;">✅</span> Score 0-100 + Risco de Divisão</li>
        <li><span style="color: #10b981; font-weight: bold;">✅</span> Dashboard de inteligência básico</li>
        <li><span style="color: #10b981; font-weight: bold;">✅</span> Análise de padrões populares</li>
        <li style="margin-top: 15px;"><span style="color: #94a3b8;">❌</span> Gerador inteligente</li>
        <li><span style="color: #94a3b8;">❌</span> Auditor de bolão</li>
        <li><span style="color: #94a3b8;">❌</span> Dashboard avançado (heatmap)</li>
        <li><span style="color: #94a3b8;">❌</span> Exportar/salvar jogos</li>
    </ul>
</div>
            """,
            unsafe_allow_html=True,
        )

    with plan2:
        st.markdown(
            """
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 30px; border-radius: 12px; border: 3px solid #6366f1; text-align: center; 
            position: relative; box-shadow: 0 10px 40px rgba(102, 126, 234, 0.4); min-height: 520px;">
    <!-- Badge "Recomendado" -->
    <div style="position: absolute; top: -20px; left: 50%; transform: translateX(-50%); 
                background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                color: white; padding: 8px 25px; border-radius: 25px; 
                font-size: 0.9rem; font-weight: bold; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);">
        ⭐ RECOMENDADO PARA VOCÊ
    </div>
    <h3 style="color: white; margin-top: 40px; font-size: 1.5rem;">💎 Pro</h3>
    <div style="font-size: 2.5rem; color: white; margin: 20px 0; font-weight: bold;">
        R$ 19,90<span style="font-size: 1.2rem; font-weight: normal;">/mês</span>
    </div>
    <p style="color: rgba(255,255,255,0.9); font-size: 1rem; margin-bottom: 25px;">
        Ou R$ 199/ano <span style="background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 5px; font-weight: 600;">(2 meses grátis)</span>
    </p>
    <div style="background-color: rgba(255,255,255,0.15); padding: 10px; border-radius: 8px; margin-bottom: 20px;">
        <span style="color: white; font-size: 0.95rem; font-weight: 600;">
        🚀 Todas as armas para jogar melhor
        </span>
    </div>
    <hr style="border-color: rgba(255,255,255,0.3); margin: 25px 0;">
    <ul style="text-align: left; color: white; line-height: 2; font-size: 1rem; opacity: 0.98; list-style: none; padding-left: 0;">
        <li><span style="font-weight: bold;">✅</span> Validador <strong>ilimitado</strong></li>
        <li><span style="font-weight: bold;">✅</span> Gerador inteligente (3 estratégias)</li>
        <li><span style="font-weight: bold;">✅</span> Auditor de bolão completo</li>
        <li><span style="font-weight: bold;">✅</span> Dashboard avançado (heatmap, atrasados)</li>
        <li><span style="font-weight: bold;">✅</span> Análise de regresso à média</li>
        <li><span style="font-weight: bold;">✅</span> Exportar jogos (CSV/TXT)</li>
        <li><span style="font-weight: bold;">✅</span> Histórico de jogos salvos</li>
        <li><span style="font-weight: bold;">✅</span> Suporte prioritário</li>
    </ul>
</div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # CTA secundário centralizado
    col_cta1, col_cta_central, col_cta2 = st.columns([1, 2, 1])
    with col_cta_central:
        if st.button("🚀 Começar Grátis Agora", type="primary", width="stretch"):
            st.switch_page("pages/1_Painel.py")

        st.markdown(
            '<p style="text-align: center; color: #94a3b8; font-size: 0.85rem; margin-top: 10px;">'
            "Sem cartão de crédito • Upgrade a qualquer momento"
            "</p>",
            unsafe_allow_html=True,
        )

    # Link discreto para Enterprise (não compete visualmente)
    st.markdown(
        '<p style="text-align: center; margin-top: 30px; color: #94a3b8; font-size: 0.9rem;">'
        "🏢 <strong>Grupos grandes ou empresas?</strong> "
        '<a href="mailto:contato@lotoscience.com" style="color: #6366f1; text-decoration: none;">'
        "Fale conosco sobre o plano Enterprise</a> "
        "(API, white-label, geração em lote)"
        "</p>",
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================
    # SEÇÃO: FAQ
    # ========================================
    st.markdown("---")
    st.markdown("## ❓ Perguntas Frequentes")

    with st.expander(
        "🤔 O LotoScience aumenta minhas chances de ganhar?", expanded=False
    ):
        st.markdown(
            """
            **Não.** Nenhum sistema pode prever números da loteria (isso é matematicamente impossível).

            O que fazemos é:

            1. **Proteger seu bolso:** Evitamos que você jogue padrões populares que diluem o prêmio
            2. **Melhorar a qualidade estatística:** Jogos com score alto são mais equilibrados e únicos
            3. **Educar:** Mostramos por que datas e sequências são ruins financeiramente

            **Em resumo:** Não aumentamos a chance de ganhar, mas **se você ganhar**, o prêmio será maior.
            """
        )

    with st.expander("📊 Como é calculado o Score Técnico?", expanded=False):
        st.markdown(
            """
            Cada jogo passa por **mais de 18 filtros estatísticos independentes**:

            - Soma (IC95% histórico)
            - Distribuição par/ímpar
            - Entropia de Shannon (detecção de padrões)
            - Distância de Hamming (unicidade)
            - Análise geométrica (moldura, miolo, quadrantes)
            - Co-ocorrência de pares (raros ou populares)
            - Detecção de PA, Fibonacci, primos, múltiplos
            - Order statistics, span, gaps

            Todos os thresholds são **ajustados automaticamente** pela densidade do jogo 
            (Mega-Sena tem critérios diferentes de Lotofácil).

            👉 [Veja a metodologia completa aqui](/Como_Funciona)
            """
        )

    with st.expander("🎲 O que é 'Risco de Divisão'?", expanded=False):
        st.markdown(
            """
            É a probabilidade de você **dividir o prêmio com muitas pessoas** caso ganhe.

            **Exemplo real:**
            - Se você jogar 1-2-3-4-5-6 e ganhar, vai dividir com ~10.000 pessoas
            - Prêmio de R$ 60 milhões ÷ 10.000 = **R$ 6.000 cada**

            **Como calculamos:**
            - ✅ **Baixo:** Jogo único, sem padrões populares detectados
            - ⚠️ **Médio:** 1-2 padrões populares (ex: algumas datas)
            - 🚨 **Alto:** 3+ padrões populares simultâneos

            Nosso sistema tem um banco de dados de padrões virais (Lost, Fibonacci, 
            sequências, formas geométricas) e compara seu jogo com eles.
            """
        )

    with st.expander("🤖 Como funciona o Gerador Inteligente?", expanded=False):
        st.markdown(
            """
            Ele cria jogos usando **3 estratégias estatísticas**:

            1. **Conservadora (70% frequência, 30% atrasos)**
               - Prioriza números que saíram recentemente
               - "O que está quente continua quente"

            2. **Balanceada (40% frequência, 60% atrasos)** ⭐ Recomendada
               - Mix inteligente de números quentes e frios

            3. **Agressiva (20% frequência, 80% atrasos)**
               - Aposta em números atrasados (regresso à média)
               - Só funciona se correlação >0.3 for detectada

            Cada jogo gerado tem **score garantido 80+** após até 10.000 tentativas.
            """
        )

    with st.expander("✅ O sistema foi validado cientificamente?", expanded=False):
        st.markdown(
            """
            **Sim.** Fizemos backtest com 1.000 amostras aleatórias comparadas ao histórico completo.

            **Resultados:**
            - ✅ Scores altos (80+) correlacionam com **maior unicidade** (Hamming)
            - ✅ Scores altos correlacionam com **menos alertas de risco**
            - ✅ Jogos com score alto têm **menor similaridade** com padrões populares

            **Metodologia:**
            - 1.000 jogos aleatórios gerados
            - Validação contra histórico completo (2.900+ sorteios)
            - Cálculo de correlação de Spearman
            - Análise de distribuições por bucket de score

            Os resultados provam que o sistema funciona como prometido.
            """
        )

    st.markdown("<br><br>", unsafe_allow_html=True)

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
