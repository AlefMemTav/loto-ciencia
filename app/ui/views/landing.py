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
                st.switch_page("pages/4_Validador.py")

        with col_cta2:
            if st.button("📖 Como Funciona?", width="stretch"):
                st.switch_page("pages/1_Como_funciona.py")

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
            st.switch_page("pages/4_Validador.py")

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
            - Prêmio de 60 milhões de reais ÷ 10.000 = **6.000 reais cada**

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
