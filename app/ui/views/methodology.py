import streamlit as st

from app.ui.components.footer import render_footer
from app.ui.core.styles import apply_custom_css


def render_como_funciona():
    """
    Página Como Funciona otimizada:
    - Storytelling científico (por que + como)
    - Transparência metodológica sem revelar segredos
    - Credibilidade técnica + acessibilidade
    - CTAs estratégicos para conversão
    """
    apply_custom_css()

    # NAVEGAÇÃO
    if st.button("← Voltar para Início", key="back_button"):
        st.switch_page("pages/2_Painel.py")

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================
    # HEADER DA PÁGINA
    # ========================================
    st.markdown(
        """
<div style="text-align: center; padding: 30px 0 20px 0;">
    <div style="font-size: 4rem; margin-bottom: 20px;">🔬</div>
    <h1 style="
        color: #0f172a;
        margin-bottom: 15px;
        font-size: 2.5rem;
        line-height: 1.2;
    ">
        A Metodologia LotoScience
    </h1>
    <p style="
        font-size: 1.25rem;
        color: #64748b;
        max-width: 850px;
        margin: 0 auto;
        line-height: 1.6;
    ">
        Por que seu cérebro joga errado e como a <strong>ciência</strong> 
        pode proteger seu dinheiro (sem promessas mágicas)
    </p>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ========================================
    # SEÇÃO 1: O PROBLEMA (viés cognitivo + exemplo)
    # ========================================
    c1, c2 = st.columns([2, 1], gap="large")

    with c1:
        st.markdown("## Por Que Seu Cérebro Joga Errado?")

        st.markdown(
            """
<p style="font-size: 1.1rem; line-height: 1.7; color: #475569; margin-bottom: 20px;">
    Humanos são <strong>péssimos geradores de números aleatórios</strong>. 
    Temos vieses cognitivos que nos fazem escolher padrões previsíveis 
    (exatamente os mesmos que <strong>milhares de outras pessoas</strong> também escolhem).
</p>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
<div style="
    background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
    padding: 25px;
    border-radius: 12px;
    border-left: 5px solid #ef4444;
    box-shadow: 0 4px 12px rgba(239, 68, 68, 0.15);
    margin: 20px 0;
">
    <h4 style="color: #991b1b; margin-top: 0; font-size: 1.25rem;">
        Os 4 Erros Mais Comuns
    </h4>
    <ol style="color: #7f1d1d; line-height: 2; font-size: 1.05rem; padding-left: 22px;">
        <li style="margin-bottom: 14px;">
            <strong>Datas de aniversário (01–31)</strong><br>
            <span style="font-size: 0.95rem; opacity: 0.9;">
            Limitam números a apenas 51% do volante da Mega-Sena. 
            Concentração massiva nessa faixa.
            </span>
        </li>
        <li style="margin-bottom: 14px;">
            <strong>Sequências óbvias (1-2-3-4-5-6)</strong><br>
            <span style="font-size: 0.95rem; opacity: 0.9;">
            Um dos jogos <em>mais apostados</em> do Brasil. 
            Se sair, divisão garantida.
            </span>
        </li>
        <li style="margin-bottom: 14px;">
            <strong>Números famosos (Lost: 4-8-15-16-23-42)</strong><br>
            <span style="font-size: 0.95rem; opacity: 0.9;">
            Padrão viral jogado por milhares toda semana.
            </span>
        </li>
        <li style="margin-bottom: 0;">
            <strong>Formas geométricas no volante</strong><br>
            <span style="font-size: 0.95rem; opacity: 0.9;">
            Desenhar linhas, cruzes, xis ou quadrados é comportamento humano previsível.
            </span>
        </li>
    </ol>
</div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
<div style="
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: white;
    padding: 20px 25px;
    border-radius: 12px;
    font-size: 1.05rem;
    line-height: 1.7;
    box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
    margin-top: 20px;
">
    <strong>✅ A Solução do LotoScience:</strong><br>
    Não prometemos prever números (impossível). Mas garantimos que você 
    <strong>não jogue como a massa</strong>, aumentando a eficiência estatística 
    e reduzindo o risco de divisão do prêmio.
</div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        try:
            st.image(
                "assets/mascote_sena.png",
                caption="Otto, o Analista",
                width=250,
            )
        except Exception:
            st.markdown(
                """
<div style="
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 60px 20px;
    border-radius: 16px;
    text-align: center;
    color: white;
    font-size: 4rem;
">
    🎲
</div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            """
<div style="
    background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
    padding: 20px;
    border-radius: 12px;
    margin-top: 25px;
    border-left: 4px solid #f59e0b;
">
    <h4 style="color: #92400e; margin-top: 0; font-size: 1.1rem;">
        💡 Você Sabia?
    </h4>
    <p style="color: #78350f; font-size: 1rem; line-height: 1.7; margin-bottom: 0;">
        Se <strong>1-2-3-4-5-6</strong> sair na Mega-Sena com prêmio de R$ 60 milhões 
        e 10.000 pessoas jogaram isso, cada um levaria <strong style="color: #dc2626;">apenas R$ 6.000</strong> 
        ao invés de milhões.
    </p>
</div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    # ========================================
    # SEÇÃO 2: OS 4 PILARES DO SISTEMA
    # ========================================
    st.markdown("## Os 4 Pilares do Score Técnico")

    st.markdown(
        """
<p style="
    font-size: 1.1rem;
    color: #475569;
    margin-bottom: 35px;
    line-height: 1.7;
">
    Cada jogo passa por <strong>mais de 20 filtros estatísticos independentes</strong>, 
    organizados em 4 pilares principais. O sistema acumula <strong>penalidades ou bônus</strong> 
    até gerar o score final (0–100).
    <br><br>
    <strong style="color: #6366f1;">Todos os thresholds são auto-ajustados</strong> 
    pela densidade do jogo (Mega-Sena tem critérios diferentes de Lotofácil).
</p>
        """,
        unsafe_allow_html=True,
    )

    # Grid 2x2 dos 4 pilares
    col1, col2 = st.columns(2, gap="large")

    with col1:
        # PILAR 1
        st.markdown(
            """
<div style="
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 35px;
    border-radius: 14px;
    color: white;
    min-height: 320px;
    box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3);
">
    <div style="font-size: 3.5rem; margin-bottom: 15px; text-align: center;">📊</div>
    <h3 style="
        color: white;
        margin: 10px 0;
        text-align: center;
        font-size: 1.4rem;
    ">
        Pilar 1: Análise Estatística Clássica
    </h3>
    <div style="margin-top: 20px; line-height: 1.8; font-size: 0.98rem;">
        <p style="margin-bottom: 12px;">
            <strong>O que valida:</strong> Soma total, distribuição par/ímpar, 
            finais (0-9), concentração espacial, intervalos de confiança históricos (IC95%).
        </p>
        <p style="margin-bottom: 12px;">
            <strong>Tecnologia:</strong> Z-score, Coeficiente de Gini, Teste de Uniformidade, 
            Análise de Variância.
        </p>
        <p style="margin-bottom: 0;">
            <strong style="color: #fca5a5;">Penalidades:</strong> Até <strong>-25 pts</strong> 
            por desvios extremos (ex: soma fora do IC95% ou 100% pares).
        </p>
    </div>
</div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # PILAR 2
        st.markdown(
            """
<div style="
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    padding: 35px;
    border-radius: 14px;
    color: white;
    min-height: 320px;
    box-shadow: 0 8px 20px rgba(240, 147, 251, 0.3);
">
    <div style="font-size: 3.5rem; margin-bottom: 15px; text-align: center;">🚨</div>
    <h3 style="
        color: white;
        margin: 10px 0;
        text-align: center;
        font-size: 1.4rem;
    ">
        Pilar 2: Detecção de Popularidade
    </h3>
    <div style="margin-top: 20px; line-height: 1.8; font-size: 0.98rem;">
        <p style="margin-bottom: 12px;">
            <strong>O que valida:</strong> Padrões populares que aumentam risco de divisão 
            (sequências, datas, números famosos, formas geométricas no volante).
        </p>
        <p style="margin-bottom: 12px;">
            <strong>Tecnologia:</strong> Entropia de Shannon, Análise de Motifs, 
            Banco de Dados de Padrões Virais (Lost, Fibonacci, PA).
        </p>
        <p style="margin-bottom: 0;">
            <strong style="color: #fca5a5;">Penalidades:</strong> Até <strong>-15 pts por padrão</strong>. 
            Marca <strong>"Risco: ALTO"</strong> se 3+ padrões simultâneos.
        </p>
    </div>
</div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        # PILAR 3
        st.markdown(
            """
<div style="
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    padding: 35px;
    border-radius: 14px;
    color: white;
    min-height: 320px;
    box-shadow: 0 8px 20px rgba(79, 172, 254, 0.3);
">
    <div style="font-size: 3.5rem; margin-bottom: 15px; text-align: center;">🔬</div>
    <h3 style="
        color: white;
        margin: 10px 0;
        text-align: center;
        font-size: 1.4rem;
    ">
        Pilar 3: Análise de Unicidade
    </h3>
    <div style="margin-top: 20px; line-height: 1.8; font-size: 0.98rem;">
        <p style="margin-bottom: 12px;">
            <strong>O que valida:</strong> O quão único é seu jogo comparado ao 
            histórico completo e aos padrões mais apostados (co-ocorrência de pares raros/comuns).
        </p>
        <p style="margin-bottom: 12px;">
            <strong>Tecnologia:</strong> Distância de Hamming, Análise de Co-ocorrência, 
            Distribuição Geométrica por Quadrantes (moldura/miolo).
        </p>
        <p style="margin-bottom: 0;">
            <strong style="color: #86efac;">Bônus:</strong> Até <strong>+5 pts</strong> 
            se jogo é estatisticamente raro e bem distribuído.
        </p>
    </div>
</div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # PILAR 4
        st.markdown(
            """
<div style="
    background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
    padding: 35px;
    border-radius: 14px;
    color: white;
    min-height: 320px;
    box-shadow: 0 8px 20px rgba(250, 112, 154, 0.3);
">
    <div style="font-size: 3.5rem; margin-bottom: 15px; text-align: center;">🎯</div>
    <h3 style="
        color: white;
        margin: 10px 0;
        text-align: center;
        font-size: 1.4rem;
    ">
        Pilar 4: Inteligência Preditiva
    </h3>
    <div style="margin-top: 20px; line-height: 1.8; font-size: 0.98rem;">
        <p style="margin-bottom: 12px;">
            <strong>O que valida:</strong> Usa regressão à média <em>validada estatisticamente</em> 
            para identificar se números atrasados têm poder preditivo real.
        </p>
        <p style="margin-bottom: 12px;">
            <strong>Tecnologia:</strong> Correlação de Spearman, Order Statistics, 
            Análise de Compressibilidade, Testes de Hipótese.
        </p>
        <p style="margin-bottom: 0;">
            <strong style="color: #86efac;">Bônus:</strong> Até <strong>+5 pts</strong> 
            se correlação >0.3 <em>e</em> jogo tem 40%+ números atrasados.
        </p>
    </div>
</div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================
    # SEÇÃO EXTRA: IA HÍBRIDA (Simbólica + Estatística)
    # ========================================
    st.markdown(
        """
<div style="
    background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
    padding: 40px;
    border-radius: 16px;
    color: white;
    border: 1px solid #334155;
    position: relative;
    overflow: hidden;
">
    <div style="position: absolute; top: -20px; right: -20px; font-size: 8rem; opacity: 0.05;">🧠</div>
    <h3 style="color: white; margin-top: 0; font-size: 1.8rem;">
        O Segredo: Inteligência Artificial Híbrida
    </h3>
    <p style="font-size: 1.1rem; line-height: 1.7; color: #cbd5e1; max-width: 800px; margin-bottom: 30px;">
        A maioria dos "geradores de loteria" usa apenas aleatoriedade (caos). O LotoScience combina duas escolas da computação para criar o <strong>Motor de Decisão Perfeito</strong>:
    </p>
    <div style="display: flex; flex-wrap: wrap; gap: 20px;">
        <div style="flex: 1; min-width: 300px; background: rgba(255,255,255,0.05); padding: 25px; border-radius: 12px; border-left: 4px solid #f59e0b;">
            <div style="font-weight: 700; color: #f59e0b; margin-bottom: 10px; font-size: 1.1rem;">
                1. IA Simbólica (O Otto)
            </div>
            <p style="font-size: 0.95rem; color: #e2e8f0; line-height: 1.6; margin: 0;">
                Baseada em <strong>regras, lógica e restrições rígidas</strong>. Ela atua como um "auditor fiscal", garantindo que nenhum jogo viole as leis matemáticas da loteria (ex: soma, pares, primos). É determinística e à prova de falhas.
            </p>
        </div>
        <div style="flex: 1; min-width: 300px; background: rgba(255,255,255,0.05); padding: 25px; border-radius: 12px; border-left: 4px solid #3b82f6;">
            <div style="font-weight: 700; color: #3b82f6; margin-bottom: 10px; font-size: 1.1rem;">
                2. Machine Learning
            </div>
            <p style="font-size: 0.95rem; color: #e2e8f0; line-height: 1.6; margin: 0;">
                Baseada em <strong>probabilidade e padrões históricos</strong> (K-Means Clustering). Ela "aprende" o comportamento dos sorteios passados para identificar tendências sutis que regras simples não capturam.
            </p>
        </div>
    </div>
    <div style="margin-top: 25px; text-align: center;">
        <span style="color: #34d399; padding: 6px 16px; font-size: 0.9rem; font-weight: 600;">
            Resultado: Jogos únicos e seguros
        </span>
    </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================
    # CARD: COMO FUNCIONA NA PRÁTICA
    # ========================================
    st.markdown(
        """
<div style="
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    padding: 35px;
    border-radius: 14px;
    border: 2px solid #e2e8f0;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
">
    <h4 style="
        color: #0f172a;
        margin-top: 0;
        text-align: center;
        font-size: 1.4rem;
    ">
        🧮 Como Funciona na Prática
    </h4>
    <p style="
        font-size: 1.05rem;
        color: #475569;
        text-align: center;
        line-height: 1.8;
        margin-bottom: 25px;
    ">
        Cada jogo começa com <strong>100 pontos</strong>. Os 20+ filtros aplicam 
        <strong>penalidades ou bônus</strong> baseados em desvios estatísticos 
        de milhares de sorteios reais.
    </p>
    <div style="
        text-align: center;
        font-size: 1.3rem;
        font-family: 'Courier New', monospace;
        color: #334155;
        margin: 25px 0;
        padding: 20px;
        background-color: white;
        border-radius: 10px;
        border: 2px dashed #cbd5e1;
    ">
        <strong>Score = 100 − Σ(penalidades) + Σ(bônus)</strong>
    </div>
    <p style="
        font-size: 0.95rem;
        color: #64748b;
        text-align: center;
        margin-top: 25px;
        line-height: 1.7;
    ">
        <strong style="color: #6366f1;">🔬 Correção de Bonferroni Aplicada:</strong><br>
        Para evitar falsos positivos em testes múltiplos, ajustamos o p-value 
        para <strong>α = 0.0033</strong> (ao invés de 0.05 padrão). 
        Isso garante rigor científico nas validações.
    </p>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================
    # BADGES DE TECNOLOGIAS (9 badges = credibilidade)
    # ========================================
    st.markdown("### Tecnologias Estatísticas Empregadas")

    col_tech1, col_tech2, col_tech3 = st.columns(3)

    with col_tech1:
        st.markdown(
            """
<div style="text-align: center; padding: 15px;">
    <div style="
        background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
        color: #1e40af;
        padding: 12px 22px;
        border-radius: 25px;
        display: inline-block;
        margin: 8px;
        font-size: 0.95rem;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.2);
    ">
        Z-Score
    </div>
    <div style="
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        color: #92400e;
        padding: 12px 22px;
        border-radius: 25px;
        display: inline-block;
        margin: 8px;
        font-size: 0.95rem;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(251, 191, 36, 0.2);
    ">
        Entropia de Shannon
    </div>
    <div style="
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        color: #065f46;
        padding: 12px 22px;
        border-radius: 25px;
        display: inline-block;
        margin: 8px;
        font-size: 0.95rem;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2);
    ">
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
    <div style="
        background: linear-gradient(135deg, #fae8ff 0%, #f3e8ff 100%);
        color: #6b21a8;
        padding: 12px 22px;
        border-radius: 25px;
        display: inline-block;
        margin: 8px;
        font-size: 0.95rem;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(147, 51, 234, 0.2);
    ">
        Distância de Hamming
    </div>
    <div style="
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        color: #991b1b;
        padding: 12px 22px;
        border-radius: 25px;
        display: inline-block;
        margin: 8px;
        font-size: 0.95rem;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(239, 68, 68, 0.2);
    ">
        Correlação de Spearman
    </div>
    <div style="
        background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
        color: #047857;
        padding: 12px 22px;
        border-radius: 25px;
        display: inline-block;
        margin: 8px;
        font-size: 0.95rem;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2);
    ">
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
    <div style="
        background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
        color: #78350f;
        padding: 12px 22px;
        border-radius: 25px;
        display: inline-block;
        margin: 8px;
        font-size: 0.95rem;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(245, 158, 11, 0.2);
    ">
        IC Bootstrap
    </div>
    <div style="
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        color: #1e3a8a;
        padding: 12px 22px;
        border-radius: 25px;
        display: inline-block;
        margin: 8px;
        font-size: 0.95rem;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.2);
    ">
        Teste de Uniformidade
    </div>
    <div style="
        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
        color: #7f1d1d;
        padding: 12px 22px;
        border-radius: 25px;
        display: inline-block;
        margin: 8px;
        font-size: 0.95rem;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(220, 38, 38, 0.2);
    ">
        Correção de Bonferroni
    </div>
</div>
            """,
            unsafe_allow_html=True,
        )

    # Disclaimer de transparência
    st.info(
        "💡 **Por que não revelamos todos os filtros?** "
        "Nosso algoritmo é resultado de meses de pesquisa e testes estatísticos. "
        "Revelamos a **filosofia** (4 pilares) e as **tecnologias** empregadas, "
        "mas os thresholds, pesos e a arquitetura exata são nosso diferencial competitivo."
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()

    # ========================================
    # SEÇÃO 3: COMO USAR (passo a passo visual)
    # ========================================
    st.markdown("## Como Usar o LotoScience")

    step1, step2, step3 = st.columns(3)

    with step1:
        st.markdown(
            """
<div style="
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 35px 25px;
    border-radius: 14px;
    color: white;
    text-align: center;
    min-height: 260px;
    box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3);
">
    <div style="
        font-size: 3.5rem;
        margin-bottom: 15px;
        background: rgba(255,255,255,0.2);
        width: 80px;
        height: 80px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 20px auto;
    ">
        1️⃣
    </div>
    <h3 style="color: white; margin: 15px 0; font-size: 1.3rem;">
        Cole ou Digite
    </h3>
    <p style="font-size: 1rem; opacity: 0.95; line-height: 1.6; margin-top: 15px;">
        Escolha a loteria (Mega-Sena, Quina, Lotofácil) e 
        digite ou cole seus números no validador.
    </p>
</div>
            """,
            unsafe_allow_html=True,
        )

    with step2:
        st.markdown(
            """
<div style="
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    padding: 35px 25px;
    border-radius: 14px;
    color: white;
    text-align: center;
    min-height: 260px;
    box-shadow: 0 8px 20px rgba(240, 147, 251, 0.3);
">
    <div style="
        font-size: 3.5rem;
        margin-bottom: 15px;
        background: rgba(255,255,255,0.2);
        width: 80px;
        height: 80px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 20px auto;
    ">
        2️⃣
    </div>
    <h3 style="color: white; margin: 15px 0; font-size: 1.3rem;">
        Receba o Diagnóstico
    </h3>
    <p style="font-size: 1rem; opacity: 0.95; line-height: 1.6; margin-top: 15px;">
        Em <strong>3 segundos</strong> veja: Score técnico (0-100) + 
        Risco de divisão + Alertas do analista.
    </p>
</div>
            """,
            unsafe_allow_html=True,
        )

    with step3:
        st.markdown(
            """
<div style="
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    padding: 35px 25px;
    border-radius: 14px;
    color: white;
    text-align: center;
    min-height: 260px;
    box-shadow: 0 8px 20px rgba(79, 172, 254, 0.3);
">
    <div style="
        font-size: 3.5rem;
        margin-bottom: 15px;
        background: rgba(255,255,255,0.2);
        width: 80px;
        height: 80px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 20px auto;
    ">
        3️⃣
    </div>
    <h3 style="color: white; margin: 15px 0; font-size: 1.3rem;">
        Gere ou Ajuste
    </h3>
    <p style="font-size: 1rem; opacity: 0.95; line-height: 1.6; margin-top: 15px;">
        Se o score estiver baixo, use o <strong>Gerador Inteligente</strong> 
        (Pro) para criar jogos melhores automaticamente.
    </p>
</div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()

    # ========================================
    # SEÇÃO 4: EXEMPLO PRÁTICO (antes vs depois)
    # ========================================
    st.markdown("## Exemplo Prático: Antes vs Depois")

    col_antes, col_depois = st.columns(2, gap="large")

    with col_antes:
        st.markdown(
            """
<div style="
    background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
    padding: 30px;
    border-radius: 14px;
    border: 3px solid #fca5a5;
    box-shadow: 0 4px 12px rgba(239, 68, 68, 0.2);
">
    <h3 style="color: #991b1b; margin-top: 0; font-size: 1.3rem;">
        ❌ ANTES (jogo comum)
    </h3>
    <div style="
        font-size: 1.4rem;
        font-family: 'Courier New', monospace;
        color: #7f1d1d;
        margin: 20px 0;
        text-align: center;
        background-color: rgba(127, 29, 29, 0.1);
        padding: 15px;
        border-radius: 10px;
    ">
        <strong>03 - 07 - 12 - 18 - 25 - 31</strong>
    </div>
    <hr style="border-color: #fca5a5; margin: 20px 0;">
    <div style="color: #7f1d1d; font-size: 1rem; line-height: 1.9;">
        <p style="margin-bottom: 12px;">
            <strong>Score técnico:</strong> 
            <span style="
                background-color: #fee2e2;
                padding: 4px 12px;
                border-radius: 6px;
                font-weight: 700;
            ">37/100 ⚠️</span>
        </p>
        <p style="margin-bottom: 12px;">
            <strong>Risco de divisão:</strong> 
            <span style="
                background-color: #dc2626;
                color: white;
                padding: 4px 12px;
                border-radius: 6px;
                font-weight: 700;
            ">ALTO 🚨</span>
        </p>
        <p style="margin-bottom: 12px;">
            <strong>Problema:</strong> Todos números ≤ 31 (datas)
        </p>
        <p style="margin-bottom: 0;">
            <strong>Alerta:</strong> Padrão muito popular. 
            Se sair, prêmio dividido com milhares.
        </p>
    </div>
</div>
            """,
            unsafe_allow_html=True,
        )

    with col_depois:
        st.markdown(
            """
<div style="
    background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
    padding: 30px;
    border-radius: 14px;
    border: 3px solid #86efac;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2);
">
    <h3 style="color: #166534; margin-top: 0; font-size: 1.3rem;">
        ✅ DEPOIS (gerado pelo LotoScience)
    </h3>
    <div style="
        font-size: 1.4rem;
        font-family: 'Courier New', monospace;
        color: #15803d;
        margin: 20px 0;
        text-align: center;
        background-color: rgba(21, 128, 61, 0.1);
        padding: 15px;
        border-radius: 10px;
    ">
        <strong>08 - 17 - 23 - 34 - 42 - 58</strong>
    </div>
    <hr style="border-color: #86efac; margin: 20px 0;">
    <div style="color: #15803d; font-size: 1rem; line-height: 1.9;">
        <p style="margin-bottom: 12px;">
            <strong>Score técnico:</strong> 
            <span style="
                background-color: #dcfce7;
                padding: 4px 12px;
                border-radius: 6px;
                font-weight: 700;
            ">87/100 ✅</span>
        </p>
        <p style="margin-bottom: 12px;">
            <strong>Risco de divisão:</strong> 
            <span style="
                background-color: #10b981;
                color: white;
                padding: 4px 12px;
                border-radius: 6px;
                font-weight: 700;
            ">BAIXO 🛡️</span>
        </p>
        <p style="margin-bottom: 12px;">
            <strong>Qualidade:</strong> Soma OK, entropia alta, finais equilibrados
        </p>
        <p style="margin-bottom: 0;">
            <strong>Status:</strong> Jogo de alta qualidade estatística! 
            Risco de divisão minimizado.
        </p>
    </div>
</div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()

    # ========================================
    # SEÇÃO 5: VALIDAÇÃO CIENTÍFICA
    # ========================================
    st.markdown("## Validação Científica: Backtest")

    st.markdown(
        """
<div style="
    background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
    padding: 35px;
    border-radius: 14px;
    border-left: 6px solid #3b82f6;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
">
    <h4 style="color: #1e40af; margin-top: 0; font-size: 1.3rem;">
        Como Sabemos Que o Sistema Funciona?
    </h4>
    <p style="font-size: 1.05rem; color: #1e3a8a; line-height: 1.8; margin-bottom: 20px;">
        Testamos nosso sistema de scoring em <strong>milhares de sorteios históricos reais</strong> mensalmente. 
        O resultado validou nossa metodologia:
    </p>
    <ul style="color: #1e3a8a; font-size: 1.05rem; line-height: 2; padding-left: 25px;">
        <li style="margin-bottom: 10px;">
            ✅ Scores altos (80+) correlacionam com <strong>maior unicidade</strong> 
            (distância de Hamming)
        </li>
        <li style="margin-bottom: 10px;">
            ✅ Scores altos correlacionam com <strong>menos alertas de risco</strong>
        </li>
        <li style="margin-bottom: 10px;">
            ✅ Jogos com score alto têm <strong>menor similaridade</strong> com padrões populares
        </li>
    </ul>
    <div style="
        margin-top: 25px;
        padding: 20px;
        background-color: rgba(59, 130, 246, 0.1);
        border-radius: 10px;
    ">
        <p style="font-size: 1rem; color: #1e40af; margin-bottom: 8px; font-weight: 600;">
            📊 Metodologia do Backtest:
        </p>
        <ul style="font-size: 0.95rem; color: #1e3a8a; line-height: 1.8; margin-bottom: 0;">
            <li><strong>1.000 jogos aleatórios</strong> gerados</li>
            <li>Validação contra <strong>histórico completo</strong> (2.900+ sorteios)</li>
            <li>Cálculo de <strong>correlação de Spearman</strong></li>
            <li>Análise de <strong>distribuições por bucket</strong> de score</li>
            <li><strong>Correção de Bonferroni</strong> aplicada (α = 0.0033)</li>
        </ul>
    </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()

    # ========================================
    # SEÇÃO 6: AS 3 ESTRATÉGIAS DO GERADOR
    # ========================================
    st.markdown("## As 3 Estratégias do Gerador Inteligente")

    st.markdown(
        """
<p style="
    font-size: 1.1rem;
    color: #475569;
    margin-bottom: 30px;
    line-height: 1.7;
">
    Cada estratégia tem uma <strong>filosofia estatística diferente</strong>. 
    Escolha baseado no seu perfil de jogo:
</p>
        """,
        unsafe_allow_html=True,
    )

    col_conserv, col_balanc, col_agress = st.columns(3)

    with col_conserv:
        st.markdown(
            """
<div style="
    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
    padding: 28px;
    border-radius: 12px;
    border: 2px solid #fbbf24;
    min-height: 340px;
">
    <div style="text-align: center; font-size: 2.5rem; margin-bottom: 15px;">🟡</div>
    <h4 style="color: #92400e; margin-top: 0; text-align: center; font-size: 1.2rem;">
        Conservadora
    </h4>
    <div style="color: #78350f; font-size: 0.98rem; line-height: 1.8;">
        <p style="margin-bottom: 12px;">
            <strong>Filosofia:</strong> "O que está quente continua quente"
        </p>
        <p style="margin-bottom: 12px;">
            <strong>Pesos:</strong> 70% frequência recente, 30% números atrasados
        </p>
        <p style="margin-bottom: 12px;">
            <strong>Para quem:</strong> Prefere apostar em números que saíram recentemente
        </p>
        <p style="margin-bottom: 0;">
            <strong>Risco:</strong> Baixo (segue tendências)
        </p>
    </div>
</div>
            """,
            unsafe_allow_html=True,
        )

    with col_balanc:
        st.markdown(
            """
<div style="
    background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
    padding: 28px;
    border-radius: 12px;
    border: 3px solid #3b82f6;
    min-height: 340px;
    box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
">
    <div style="text-align: center; font-size: 2.5rem; margin-bottom: 15px;">⭐</div>
    <h4 style="color: #1e40af; margin-top: 0; text-align: center; font-size: 1.2rem;">
        Balanceada
    </h4>
    <div style="color: #1e3a8a; font-size: 0.98rem; line-height: 1.8;">
        <p style="margin-bottom: 12px;">
            <strong>Filosofia:</strong> Mix inteligente (equilíbrio)
        </p>
        <p style="margin-bottom: 12px;">
            <strong>Pesos:</strong> 40% frequência, 60% números atrasados
        </p>
        <p style="margin-bottom: 12px;">
            <strong>Para quem:</strong> Quer equilíbrio entre quentes e frios
        </p>
        <p style="margin-bottom: 12px;">
            <strong>Risco:</strong> Médio (versatilidade)
        </p>
        <p style="
            text-align: center;
            margin-top: 15px;
            margin-bottom: 0;
            font-weight: 700;
            color: #3b82f6;
        ">
            ✨ Mais recomendada
        </p>
    </div>
</div>
            """,
            unsafe_allow_html=True,
        )

    with col_agress:
        st.markdown(
            """
<div style="
    background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
    padding: 28px;
    border-radius: 12px;
    border: 2px solid #ef4444;
    min-height: 340px;
">
    <div style="text-align: center; font-size: 2.5rem; margin-bottom: 15px;">🔴</div>
    <h4 style="color: #991b1b; margin-top: 0; text-align: center; font-size: 1.2rem;">
        Agressiva
    </h4>
    <div style="color: #7f1d1d; font-size: 0.98rem; line-height: 1.8;">
        <p style="margin-bottom: 12px;">
            <strong>Filosofia:</strong> Regressão à média (aposta em atrasados)
        </p>
        <p style="margin-bottom: 12px;">
            <strong>Pesos:</strong> 20% frequência, 80% números atrasados
        </p>
        <p style="margin-bottom: 12px;">
            <strong>Para quem:</strong> Acredita que números atrasados "precisam sair"
        </p>
        <p style="margin-bottom: 0;">
            <strong>Risco:</strong> Alto (requer correlação >0.3 validada)
        </p>
    </div>
</div>
            """,
            unsafe_allow_html=True,
        )

    st.info(
        "💡 **Dica:** Se a análise de regressão à média mostrar **correlação >0.3**, "
        "a estratégia Agressiva é cientificamente justificada. Caso contrário, "
        "preferimos Balanceada ou Conservadora."
    )

    st.markdown("<br><br>", unsafe_allow_html=True)

    # ========================================
    # CTA FINAL
    # ========================================
    st.markdown(
        """
<div style="
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 50px 40px;
    border-radius: 18px;
    text-align: center;
    color: white;
    margin-top: 40px;
    box-shadow: 0 15px 40px rgba(118, 75, 162, 0.5);
">
    <div style="font-size: 3.5rem; margin-bottom: 20px;">🎯</div>
    <h2 style="margin: 0; color: white; font-size: 2.2rem; line-height: 1.3;">
        Agora Que Você Entendeu a Metodologia...
    </h2>
    <p style="
        font-size: 1.15rem;
        margin: 25px auto 40px auto;
        opacity: 0.95;
        max-width: 700px;
        line-height: 1.7;
    ">
        Está pronto para <strong>auditar seu próximo jogo</strong> e ver o 
        Score Técnico + Risco de Divisão em <strong>tempo real?</strong>
    </p>
    <a href="Validador" target="_self" style="text-decoration: none;">
        <div style="
            background-color: #22c55e;
            color: white;
            padding: 18px 40px;
            border-radius: 999px;
            display: inline-block;
            box-shadow: 0 6px 20px rgba(34, 197, 94, 0.4);
            cursor: pointer;
            font-weight: 700;
            font-size: 1.1rem;
            transition: transform 0.2s;
        "
        onmouseover="this.style.transform='scale(1.05)'"
        onmouseout="this.style.transform='scale(1)'"
        >
            🚀 Ir para o Validador Agora
        </div>
    </a>
    <p style="
        font-size: 0.9rem;
        margin-top: 25px;
        opacity: 0.85;
    ">
        ✅ Grátis • 3 validações por dia • Sem cartão de crédito
    </p>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br><br>", unsafe_allow_html=True)
    render_footer()
