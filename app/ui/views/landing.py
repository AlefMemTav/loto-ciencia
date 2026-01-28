import streamlit as st
from app.ui.components.footer import render_footer
from app.ui.core.styles import apply_custom_css


def render_landing_page():
    """Landing page educacional com foco em conversão de planos pagos."""
    apply_custom_css()
    st.header("LotoScience - Sua IA de jogos de loteria")
    # ========================================
    # HERO SECTION
    # ========================================
    col_hero_left, col_hero_right = st.columns([3, 2], gap="large")

    with col_hero_left:
        st.markdown(
            '<div class="hero-title">Seu Jogo Pode Valer<br>Centavos em Vez de Milhões</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="hero-subtitle">Se 1-2-3-4-5-6 sair na Mega-Sena, <strong>milhares de pessoas ganharão junto com você</strong>. Seu prêmio? Uma fração ridícula. O LotoScience avalia o <strong>Risco de Divisão</strong> do seu jogo e usa Inteligência Artificial para fugir da multidão.</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div style="margin-top: 25px; margin-bottom: 15px; color: #1e293b; font-size: 1.05rem; line-height: 1.6; background: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #6366f1;">
            <b>O que você ganha hoje:</b>
            <ul style="margin-top: 10px; list-style-type: none; padding-left: 5px;">
                <li style="margin-bottom: 8px;">🔍 <b>Auditoria Técnica:</b> Descubra se seu jogo é "lixo estatístico".</li>
                <li style="margin-bottom: 8px;">🧬 <b>DNA do Jogo (IA):</b> Saiba se sua aposta é igual a de todo mundo ou se tem valor real.</li>
                <li style="margin-bottom: 0px;">⚡ <b>Gerador Otimizado:</b> Crie jogos matematicamente perfeitos.</li>
            </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_cta1, col_cta2 = st.columns([3, 2])
        with col_cta1:
            if st.button(
                "🚀 Ver Planos & Começar",
                type="primary",
                width="stretch",
            ):
                st.switch_page("pages/4_Validador.py")

        with col_cta2:
            if st.button("📖 Como Funciona?", width="stretch"):
                st.switch_page("pages/1_Como_funciona.py")

        st.markdown(
            """
            <div style="margin-top: 20px; padding: 12px; background-color: #f0fdf4; border-radius: 8px; border-left: 3px solid #10b981;">
                <span style="color: #065f46; font-size: 0.9rem;">
                ✅ <b>Tecnologia Validada:</b> Usamos o que há de mais avançado em Estatística
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
    # SEÇÃO: O PROBLEMA
    # ========================================
    st.markdown("---")
    st.markdown("## Por que você perde dinheiro (sem saber)")

    col_prob1, col_prob2 = st.columns(2, gap="large")

    with col_prob1:
        st.markdown(
            """
            <div style="background-color: #fef2f2; padding: 25px; border-radius: 10px; border-left: 4px solid #ef4444;">
                <h4 style="color: #991b1b; margin-top: 0;">🕳️ A armadilha dos padrões:</h4>
                <ul style="color: #7f1d1d; line-height: 1.8;">
                    <li><b>Viés de Aniversário:</b> Apostar apenas dias 01-31 ignora 40% do volante.</li>
                    <li><b>Padrões Visuais:</b> Linhas, colunas e cruzes são jogados por milhares.</li>
                    <li><b>Falsa Aleatoriedade:</b> O cérebro humano é péssimo em criar números aleatórios reais.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_prob2:
        st.markdown(
            """
            <div style="background-color: #eff6ff; padding: 25px; border-radius: 10px; border-left: 4px solid #3b82f6;">
                <h4 style="color: #1e40af; margin-top: 0;">💡 A Solução: Matemática Pura</h4>
                <p style="color: #1e3a8a; line-height: 1.7;">
                O LotoScience não promete "números mágicos". Nós usamos <b>Ciência de Dados</b> para limpar suas apostas.
                </p>
                <p style="color: #1e3a8a; line-height: 1.7; margin-top: 15px;">
                Nossa IA analisa o <b>perfil histórico</b> (Clusters) e garante que você jogue com a mesma qualidade estatística de um profissional.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================
    # SEÇÃO: PREÇOS
    # ========================================
    st.markdown("---")
    st.markdown("## Invista na Qualidade do seu Jogo")

    st.markdown(
        '<p style="text-align: center; color: #64748b; font-size: 1.1rem; margin-bottom: 40px;">'
        "Escolha o nível de inteligência que você quer nas suas apostas."
        "</p>",
        unsafe_allow_html=True,
    )

    # Layout de 3 colunas para os planos
    # Coluna do meio um pouco mais larga para destaque
    c_basic, c_pro, c_vip = st.columns([1, 1.1, 1], gap="medium")

    # --- PLANO 1: BÁSICO (Entry Level) ---
    with c_basic:
        st.markdown(
            """
<div style="background-color: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #e2e8f0; text-align: center; min-height: 500px; transition: transform 0.3s;">
    <h3 style="color: #64748b; margin-top: 10px; font-size: 1.4rem;">Gratuito</h3>
    <div style="font-size: 2.2rem; color: #1e293b; margin: 20px 0; font-weight: 800;">
        Grátis<span style="font-size: 1rem; font-weight: normal; color: #94a3b8;">/sempre</span>
    </div>
    <p style="color: #64748b; font-size: 0.9rem; margin-bottom: 25px;">Para conhecer a Inteligência Artificial</p>
    <div style="text-align: left; margin-bottom: 30px;">
        <div style="margin-bottom: 10px;">✅ <b>Validador Técnico</b> (Básico)</div>
        <div style="margin-bottom: 10px;">✅ Score 0-100</div>
        <div style="margin-bottom: 10px;">✅ Análise de Risco de Divisão</div>
        <div style="margin-bottom: 10px;">✅ Gerador de Alto Desempenho</div>
        <div style="margin-bottom: 10px; color: #94a3b8;">❌ Gerador de IA (Genético e Clusters)</div>
        <div style="margin-bottom: 10px; color: #94a3b8;">❌ Auditoria Científica</div>
        <div style="margin-bottom: 10px; color: #94a3b8;">❌ Fechamentos e Desdobramentos</div>
        <div style="margin-bottom: 10px; color: #94a3b8;">❌ Ferramentas de Bolão</div>
    </div>
    <a href="Registro" style="text-decoration: none;">
        <div style="background: #f1f5f9; color: #475569; padding: 12px; border-radius: 8px; font-weight: bold; border: 1px solid #cbd5e1;">Começar Grátis</div>
    </a>
</div>
            """,
            unsafe_allow_html=True,
        )
    # --- PLANO 2: PRO (Recomendado/Hero) ---
    with c_pro:
        st.markdown(
            """
<div style="background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%); padding: 30px; border-radius: 16px; border: 2px solid #6366f1; text-align: center; min-height: 540px; transform: scale(1.02); box-shadow: 0 10px 25px rgba(99, 102, 241, 0.15); position: relative;">
    <div style="position: absolute; top: -15px; left: 50%; transform: translateX(-50%); background: #6366f1; color: white; padding: 5px 15px; border-radius: 20px; font-size: 0.8rem; font-weight: bold;">MAIS POPULAR</div>
    <h3 style="color: #4f46e5; margin-top: 10px; font-size: 1.6rem;">Profissional</h3>
    <div style="font-size: 2.8rem; color: #1e293b; margin: 20px 0; font-weight: 800;">
        R$ 9,90<span style="font-size: 1rem; font-weight: normal; color: #94a3b8;">/mês</span>
    </div>
    <p style="color: #64748b; font-size: 0.9rem; margin-bottom: 25px;">Para quem joga para ganhar</p>
    <div style="text-align: left; margin-bottom: 30px;">
        <div style="margin-bottom: 10px;">✅ <b>Tudo do Essencial</b></div>
        <div style="margin-bottom: 10px;">🔥 <b>Gerador de IA (Genético e Clusters):</b> Crie jogos Conservadores, Balanceados ou Agressivos que seguem nossa Inteligência Estatística.</div>
        <div style="margin-bottom: 10px;">🧬 <b>Perfil do Jogo:</b> Descubra a "personalidade" da sua aposta.</div>
        <div style="margin-bottom: 10px;">🧪 <b>Relatório Avançado:</b> Validação e Dashboards detalhados.</div>
        <div style="margin-bottom: 10px;">🧬 <b>Fechamentos e Desdobramentos:</b> Use Matrizes Otimizadas para economizar em seus jogos.</div>
        <div style="margin-bottom: 10px;">♾️ Validações Ilimitadas</div>
    </div>
    <a href="Registro" style="text-decoration: none;">
        <div style="background: #6366f1; color: white; padding: 15px; border-radius: 8px; font-weight: bold; box-shadow: 0 4px 6px rgba(99, 102, 241, 0.3);">Quero Vantagem Matemática</div>
    </a>
</div>
            """,
            unsafe_allow_html=True,
        )

    # --- PLANO 3: VIP (High Ticket) ---
    with c_vip:
        st.markdown(
            """
<div style="background-color: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #e2e8f0; text-align: center; min-height: 500px;">
    <h3 style="color: #1e293b; margin-top: 10px; font-size: 1.4rem;">Elite</h3>
    <div style="font-size: 2.2rem; color: #1e293b; margin: 20px 0; font-weight: 800;">
        R$ 59,90<span style="font-size: 1rem; font-weight: normal; color: #94a3b8;">/mês</span>
    </div>
    <p style="color: #64748b; font-size: 0.9rem; margin-bottom: 25px;">Para bolões e especialistas</p>
    <div style="text-align: left; margin-bottom: 30px;">
        <div style="margin-bottom: 10px;">✅ <b>Tudo do Profissional</b></div>
        <div style="margin-bottom: 10px;">✅ <b>Auditor de Bolão:</b> Valide milhares de jogos de uma vez.</div>
        <div style="margin-bottom: 10px;">✅ <b>Exportação de Dados:</b> Baixe seus jogos em Excel/TXT.</div>
        <div style="margin-bottom: 10px;">✅ <b>Relatório Mensal:</b> Recebe nossas analises mensais.</div>
        <div style="margin-bottom: 10px;">⭐ Suporte Prioritário</div>
    </div>
    <a href="Registro" style="text-decoration: none;">
        <div style="background: #1e293b; color: white; padding: 12px; border-radius: 8px; font-weight: bold;">Escolher Elite</div>
    </a>
</div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Garantia / Disclaimer de compra
    st.markdown(
        """
        <div style="text-align: center; margin-top: 20px; color: #64748b; font-size: 0.9rem;">
            🔒 Pagamento seguro via Stripe • Cancele quando quiser • 7 dias de garantia
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ========================================
    # SEÇÃO: FAQ (Simplificado)
    # ========================================
    st.markdown("## ❓ Dúvidas Comuns")

    c_faq1, c_faq2 = st.columns(2)

    with c_faq1:
        with st.expander(
            '🤔 O que é o "Gerador de IA" do plano Profissional?', expanded=False
        ):
            st.write(
                'Diferente de geradores aleatórios comuns, nosso sistema usa **Algoritmos Genéticos** e de **Clusterização (K-Means)**. Ele analisa o histórico e gera jogos matematicamente otimizados, evitando combinações "lixo".'
            )

        with st.expander("💳 Posso cancelar a qualquer momento?", expanded=False):
            st.write(
                "Sim. Não há fidelidade. Você pode assinar por um mês para testar e cancelar quando quiser direto no painel ou não renovando. O cancelamento é automático."
            )

    with c_faq2:
        with st.expander("📊 O plano Elite serve para mim?", expanded=False):
            st.write(
                "Se você organiza bolões com amigos ou gosta de analisar dados no Excel, sim. Se você joga apenas para si mesmo, o plano **Profissional** é o ideal e já te dá tudo o que você precisa."
            )

        with st.expander("🛡️ O LotoScience garante prêmios?", expanded=False):
            st.write(
                "Não. Loteria é jogo de azar. O que garantimos é que seus jogos terão a **melhor qualidade matemática possível**, evitando erros amadores que diminuem seu potencial de ganho."
            )

    st.markdown("<br><br>", unsafe_allow_html=True)

    # CTA FINAL
    st.markdown(
        """
<div style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); 
            padding: 50px; border-radius: 16px; text-align: center; color: white; 
            box-shadow: 0 10px 25px -5px rgba(100, 100, 250, 0.4);">
    <h2 style="margin: 0; color: white; font-size: 2rem;">Não jogue dinheiro fora no próximo sorteio</h2>
    <p style="font-size: 1.1rem; margin: 15px 0 30px 0; opacity: 0.9; max-width: 600px; margin-left: auto; margin-right: auto;">
        Faça um upgrade para o plano Profissional e jogue com a inteligência dos dados.
    </p>
    <a href="Registro" target="_self" style="text-decoration: none;">
        <div style="
            background-color: #ffffff; 
            color: #4f46e5; 
            padding: 16px 32px; 
            border-radius: 99px; 
            display: inline-block;
            font-weight: bold;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            cursor: pointer;
            transition: transform 0.2s;
        ">
            🚀 Quero o Plano Profissional
        </div>
    </a>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br><br>", unsafe_allow_html=True)
    render_footer()
