import streamlit as st

from app.ui.footer import render_footer
from app.ui.styles import apply_custom_css


def render_landing_page():
    apply_custom_css()

    c1, c2 = st.columns([1, 5])
    with c1:
        try:
            st.image("assets/mascote_sena.png", width=50)
        except:
            st.markdown("🎲")  # Fallback
    with c2:
        st.markdown(
            "<div style='padding-top: 12px; font-weight: 700; font-size: 1.2rem; color: #0f172a;'>LotoScience</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # -- HERO SECTION --
    # Layout: Texto na Esquerda (1), Imagem na Direita (1.2) -> Padrão Z-Pattern
    col_text, col_img = st.columns([1.1, 1], gap="large")

    with col_text:
        st.markdown('<div class="hero-container">', unsafe_allow_html=True)
        st.markdown(
            '<div class="hero-tag">✨ Beta Aberto v1.0</div>', unsafe_allow_html=True
        )

        # Título de Impacto
        st.markdown(
            '<div class="hero-title">Não é Sorte.<br>É Ciência.</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="hero-subtitle">Pare de jogar dinheiro fora com datas e superstições. '
            "Utilize modelos estatísticos avançados para proteger seu patrimônio e otimizar suas apostas nas Loterias da Caixa.</div>",
            unsafe_allow_html=True,
        )

        # st.markdown(
        #    "<div style='margin-top:10px; color:#64748b; font-size:0.95rem;'>"
        #    "Não aumenta sua probabilidade de ganhar; reduz padrões repetidos e o risco de dividir o prêmio."
        #    "</div>",
        #    unsafe_allow_html=True,
        # )

        st.markdown(
            """
            <div style="margin-top: 14px; margin-bottom: 10px; color:#334155; font-size:1.02rem; line-height:1.55">
            <b>Em 30 segundos você consegue:</b>
            <ul style="margin-top: 8px;">
            <li><b>Raio‑X do jogo:</b> veja quais números estão “quentes”, “frios” e atrasados.</li>
            <li><b>Validador anti‑padrão:</b> descubra se seu jogo está popular demais (risco de dividir prêmio).</li>
            <li><b>Gerador inteligente:</b> crie jogos melhores em 1 clique; sem superstição.</li>
            </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Botões de Ação
        b1, b2 = st.columns([1, 1.2])
        with b1:
            if st.button("Iniciar Análise", type="primary", width="stretch"):
                st.switch_page("pages/1_Painel.py")

        with b2:
            if st.button("📖 Entender a Ciência", width="stretch"):
                st.switch_page("pages/0_Como_funciona.py")

        st.markdown("</div>", unsafe_allow_html=True)

    with col_img:
        # Ajuste fino para centralizar o robô verticalmente
        st.markdown("<br>", unsafe_allow_html=True)
        try:
            # Dica: O robô realista (full) fica aqui.
            # width=400 é um bom tamanho para telas HD.
            st.image("assets/mascote_sena_full.png", width=400)
        except:
            st.info("🖼️ (Insira 'mascote_sena_full.png' na pasta assets)")

    # -- FEATURES SECTION (CARDS) --
    st.markdown("<br><br>", unsafe_allow_html=True)

    # Título da Seção
    st.markdown(
        "<h3 style='text-align:center; color:#0f172a; margin-bottom:2rem;'>Por que usar o LotoScience?</h3>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3, gap="medium")

    with c1:
        st.markdown(
            """
            <div class="feature-card">
                <div class="icon-box">📊</div>
                <div class="card-title">Filtro de Gauss</div>
                <div class="card-text">
                    Eliminamos combinações estatisticamente improváveis (somas extremas) baseadas na Curva Normal histórica.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            """
            <div class="feature-card">
                <div class="icon-box">🛡️</div>
                <div class="card-title">Proteção Financeira</div>
                <div class="card-text">
                    Identificamos padrões de "efeito manada" (datas, números de Lost, sequências) para evitar divisão de prêmio.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            """
            <div class="feature-card">
                <div class="icon-box">🧬</div>
                <div class="card-title">Entropia & Poisson</div>
                <div class="card-text">
                    Análise de caos e distribuição de finais para garantir que seus jogos sejam matematicamente equilibrados.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    render_footer()


def render_como_funciona():
    apply_custom_css()

    # Header Simples
    if st.button("← Voltar para Início"):
        st.switch_page("pages/0_Inicio.py")

    st.markdown("<br>", unsafe_allow_html=True)

    # Layout de 2 Colunas para o Topo
    c1, c2 = st.columns([2, 1])

    with c1:
        st.markdown("# 🧠 A Metodologia LotoScience")
        st.markdown("### Por que seu cérebro joga errado?")
        st.markdown(
            """
            <p style='font-size:1.05rem; line-height:1.6; color:#475569;'>
            Humanos são péssimos geradores de números aleatórios. Nós temos <strong>vieses cognitivos</strong>:
            jogamos datas de aniversário (01-31), desenhamos formas no volante e copiamos sequências famosas.
            <br><br>
            <strong>O Problema:</strong> Quando você joga assim, você não diminui sua chance de ganhar, 
            mas aumenta drasticamente a chance de <span style='color:#d97706; font-weight:700;'>DIVIDIR O PRÊMIO</span> com milhares de pessoas.
            </p>
            """,
            unsafe_allow_html=True,
        )

        st.success(
            "💡 **O LotoScience é um 'Auditor de Qualidade'**: garantimos alta qualidade estatística e baixo risco de divisão."
        )

    with c2:
        try:
            st.image("assets/mascote_sena.png", width=220)
        except:
            st.warning("Sem imagem")

    st.divider()

    st.markdown("## ⚙️ Os 5 Pilares do Algoritmo")

    col1, col2, col3, col4, col5 = st.columns(5, gap="medium")

    with col1:
        st.markdown("#### 1. A Curva de Gauss")
        st.caption("Filtro Matemático")
        st.info(
            "A soma das dezenas quase sempre cai entre 140 e 240. Rejeitamos jogos fora dessa 'Zona de Ouro'."
        )

    with col2:
        st.markdown("#### 2. Entropia de Shannon")
        st.caption("Filtro de Caos")
        st.info(
            "Medimos a 'desordem'. Jogos muito organizados (ex: 1, 2, 3, 4, 5, 6) têm baixa entropia e são descartados."
        )

    with col3:
        st.markdown("#### 3. Risco de Popularidade")
        st.caption("Filtro Financeiro")
        st.warning(
            "Comparamos seu jogo com padrões de massa. Se parecer com o de todo mundo, nós avisamos."
        )

    with col4:
        st.markdown("#### 4. Distribuição de Finais")
        st.caption("Filtro de Equilíbrio")
        st.success(
            "Garantimos que os finais (0-9) estejam distribuídos uniformemente, evitando concentrações arriscadas."
        )

    with col5:
        st.markdown("#### 5. Z-Score, Gaps & Quadrantes")
        st.caption("Filtro Avançado")
        st.success(
            "Utilizamos técnicas estatísticas para analisar padrões sutis e garantir diversidade numérica."
        )

    st.markdown("<br><br>", unsafe_allow_html=True)
    render_footer()
