import streamlit as st

from app.ui.components.footer import render_footer
from app.ui.core.styles import apply_custom_css


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
    <a href="Validador" target="_self" style="text-decoration: none;">
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
