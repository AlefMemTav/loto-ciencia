# app/ui/views/auth.py
import streamlit as st
import time
from app.services.payment import get_checkout_url
from app.ui.services.auth_client import AUTHClient


def render_login_view():
    # Botão voltar no topo
    if st.button("← Voltar para Painel"):
        st.switch_page("pages/2_Painel.py")
    st.title("🔐 Login")
    st.markdown("Entre na sua conta para acessar todas as funcionalidades.")

    with st.form("login_form"):
        email = st.text_input("📧 E-mail", placeholder="seu@email.com")
        password = st.text_input("🔒 Senha", type="password", placeholder="Sua senha")

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Entrar", type="primary", width="stretch")
        with col2:
            cancel = st.form_submit_button("Cancelar", width="stretch")

        if cancel:
            st.switch_page("pages/0_Inicio.py")

        if submit:
            if not email or not password:
                st.error("❌ Preencha todos os campos")
            else:
                with st.spinner("Entrando..."):
                    success, message, _ = AUTHClient.login(email, password)
                    if success:
                        st.success(message)
                        st.balloons()
                        time.sleep(1)
                        st.switch_page("pages/2_Painel.py")
                    else:
                        st.error(f"❌ {message}")

    st.markdown("---")
    _render_auth_footer(is_login=True)


def render_register_view():
    # Botão voltar no topo
    if st.button("← Voltar para Painel"):
        st.switch_page("pages/2_Painel.py")
    st.title("Criar Conta Grátis")
    st.markdown("Cadastre-se para ter acesso completo ao sistema.")

    with st.form("register_form"):
        email = st.text_input("📧 E-mail", placeholder="seu@email.com")
        password = st.text_input(
            "🔒 Senha", type="password", placeholder="Mínimo 6 caracteres"
        )
        password_confirm = st.text_input("🔒 Confirmar Senha", type="password")

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button(
                "Criar Conta", type="primary", width="stretch"
            )
        with col2:
            cancel = st.form_submit_button("Cancelar", width="stretch")

        if cancel:
            st.switch_page("pages/0_Inicio.py")

        if submit:
            if not email or not password or not password_confirm:
                st.error("❌ Preencha todos os campos")
            elif len(password) < 6:
                st.error("❌ A senha deve ter pelo menos 6 caracteres")
            elif password != password_confirm:
                st.error("❌ As senhas não coincidem")
            elif email == "demo@lotoscience.com":
                st.error("❌ Este e-mail é reservado.")
            else:
                with st.spinner("Criando conta..."):
                    success, message, _ = AUTHClient.register(email, password)
                    if success:
                        st.success(message)
                        st.balloons()
                        st.info("🎉 Conta criada! Você já está logado.")
                        time.sleep(1)
                        st.switch_page("pages/2_Painel.py")
                    else:
                        st.error(f"❌ {message}")

    st.markdown("---")
    _render_auth_footer(is_login=False)


def render_plans_view():
    # Botão voltar no topo
    if st.button("← Voltar para Painel"):
        st.switch_page("pages/2_Painel.py")

    st.markdown("<br>", unsafe_allow_html=True)
    """Página de planos otimizada: Free (3 usos/dia) + Pro (R$ 19,90)"""

    st.title("💎 Escolha Seu Plano")

    # Se já for PRO
    current_plan = st.session_state.get("user_plan", "free")
    if current_plan == "pro":
        st.success("✅ Você já é PRO! Aproveite todos os recursos ilimitados.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🏠 Voltar ao Painel", width="stretch"):
                st.switch_page("pages/2_Painel.py")
        with col2:
            if st.button("❓ Precisa de ajuda?", width="stretch"):
                st.info("📧 Suporte: contato@lotoscience.com")
        return

    # Header explicativo
    st.markdown(
        '<p style="text-align: center; color: #64748b; font-size: 1.1rem; margin-bottom: 35px;">'
        "Comece grátis e faça upgrade quando precisar de mais poder."
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
    <h3 style="color: #64748b; margin-top: 10px; font-size: 1.4rem;">Essencial</h3>
    <div style="font-size: 2.2rem; color: #1e293b; margin: 20px 0; font-weight: 800;">
        R$ 9,90<span style="font-size: 1rem; font-weight: normal; color: #94a3b8;">/mês</span>
    </div>
    <p style="color: #64748b; font-size: 0.9rem; margin-bottom: 25px;">Para o apostador casual</p>
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
        R$ 19,90<span style="font-size: 1rem; font-weight: normal; color: #94a3b8;">/mês</span>
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
</div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if AUTHClient.is_authenticated():
        col_cta1, col_cta_central, col_cta2 = st.columns([1, 2, 1])
        with col_cta_central:

            if st.button("🚀 Fazer Upgrade para PRO", type="primary", width="stretch"):
                with st.spinner("Conectando ao pagamento seguro..."):
                    # 1. Pega o email do usuário logado
                    user_email = st.session_state.get("user_email")

                    # 2. Gera o link do Stripe
                    checkout_url = get_checkout_url(user_email)

                    # 3. Redireciona (Hack do Streamlit para abrir link externo)
                    if checkout_url:
                        st.link_button(
                            "💳 Clique aqui para Pagar no Stripe",
                            checkout_url,
                            type="primary",
                            width="stretch",
                        )
                        # Opcional: Redirecionamento automático via JS (mais fluido)
                        st.markdown(
                            f'<meta http-equiv="refresh" content="0;url={checkout_url}">',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.error(
                            "Não foi possível conectar ao Stripe. Tente novamente."
                        )

            st.markdown(
                '<p style="text-align: center; color: #94a3b8; font-size: 0.85rem; margin-top: 10px;">'
                "🔒 Pagamento seguro via Stripe • Cancele quando quiser • 7 dias de garantia"
                "</p>",
                unsafe_allow_html=True,
            )
    else:
        # Usuário não logado → CTA para criar conta Free
        col_cta1, col_cta_central, col_cta2 = st.columns([1, 2, 1])
        with col_cta_central:
            st.markdown(
                '<p style="text-align: center; color: #94a3b8; font-size: 0.85rem; margin-top: 10px;">'
                "Começa agora GRÁTIS, crie uma conta • Sem cartão de crédito • 3 validações/dia para sempre"
                "</p>",
                unsafe_allow_html=True,
            )

    # Link discreto para Enterprise
    st.markdown(
        '<p style="text-align: center; margin-top: 30px; color: #94a3b8; font-size: 0.9rem;">'
        "🏢 <strong>Grupos grandes ou empresas?</strong> "
        '<a href="mailto:contato@lotoscience.com" style="color: #6366f1; text-decoration: none;">'
        "Fale conosco sobre o plano Enterprise</a> "
        "(API, white-label, geração em lote)"
        "</p>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    st.markdown("<br>", unsafe_allow_html=True)


# Helper privado para rodapé de auth
def _render_auth_footer(is_login=True):
    col1, col2 = st.columns(2)

    with col1:
        if is_login:
            st.markdown("**Não tem conta?**")
            if st.button("Criar Conta Grátis", width="stretch"):
                st.switch_page("pages/10_Registro.py")
        else:
            st.markdown("**Já tem conta?**")
            if st.button("🔐 Fazer Login", width="stretch"):
                st.switch_page("pages/9_Login.py")

    with col2:
        st.markdown("**Ajuda?**")
        st.caption("Suporte: contato@lotoscience.com")
