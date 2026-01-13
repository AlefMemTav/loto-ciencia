# app/ui/views/auth.py
import streamlit as st
import time
from app.services.payment import get_checkout_url
from app.ui.services.auth_client import AUTHClient


def render_login_view():
    # Botão voltar no topo
    if st.button("← Voltar para Painel"):
        st.switch_page("pages/1_Painel.py")
    st.title("🔐 Login")
    st.markdown("Entre na sua conta para acessar todas as funcionalidades.")

    with st.form("login_form"):
        email = st.text_input("📧 E-mail", placeholder="seu@email.com")
        password = st.text_input("🔒 Senha", type="password", placeholder="Sua senha")

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button(
                "Entrar", type="primary", use_container_width=True
            )
        with col2:
            cancel = st.form_submit_button("Cancelar", use_container_width=True)

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
                    else:
                        st.error(f"❌ {message}")

    st.markdown("---")
    _render_auth_footer(is_login=True)


def render_register_view():
    # Botão voltar no topo
    if st.button("← Voltar para Painel"):
        st.switch_page("pages/1_Painel.py")
    st.title("📝 Criar Conta Grátis")
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
                "Criar Conta", type="primary", use_container_width=True
            )
        with col2:
            cancel = st.form_submit_button("Cancelar", use_container_width=True)

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
                        st.switch_page("pages/1_Painel.py")
                    else:
                        st.error(f"❌ {message}")

    st.markdown("---")
    _render_auth_footer(is_login=False)


def render_plans_view():
    # Botão voltar no topo
    if st.button("← Voltar para Painel"):
        st.switch_page("pages/1_Painel.py")

    st.markdown("<br>", unsafe_allow_html=True)
    """Página de planos otimizada: Free (3 usos/dia) + Pro (R$ 19,90)"""

    st.title("💎 Escolha Seu Plano")

    # Se já for PRO
    current_plan = st.session_state.get("user_plan", "free")
    if current_plan == "pro":
        st.success("✅ Você já é PRO! Aproveite todos os recursos ilimitados.")

        # Exibir benefícios ativos
        st.markdown(
            """
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 20px; border-radius: 10px; color: white; margin: 20px 0;">
    <h3 style="color: white; margin-top: 0;">🎉 Seus Benefícios PRO Ativos:</h3>
    <ul style="line-height: 1.8;">
        <li>✅ <strong>Validações ilimitadas</strong> (sem limite diário)</li>
        <li>✅ <strong>Gerador inteligente</strong> (3 estratégias)</li>
        <li>✅ <strong>Auditor de bolão</strong> completo</li>
        <li>✅ <strong>Dashboard avançado</strong> (heatmap, atrasados)</li>
        <li>✅ <strong>Análise de regresso à média</strong></li>
        <li>✅ <strong>Exportar jogos</strong> (CSV/TXT)</li>
        <li>✅ <strong>Histórico de jogos</strong> salvos</li>
        <li>✅ <strong>Suporte prioritário</strong></li>
    </ul>
</div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🏠 Voltar ao Painel", use_container_width=True):
                st.switch_page("pages/1_Painel.py")
        with col2:
            if st.button("❓ Precisa de ajuda?", use_container_width=True):
                st.info("📧 Suporte: contato@lotoscience.com")
        return

    # Header explicativo
    st.markdown(
        '<p style="text-align: center; color: #64748b; font-size: 1.1rem; margin-bottom: 35px;">'
        "Comece grátis e faça upgrade quando precisar de mais poder."
        "</p>",
        unsafe_allow_html=True,
    )

    # Grid 2 colunas (Free + Pro) com espaçamento lateral
    col_spacing1, plan1, plan2, col_spacing2 = st.columns([0.5, 2, 2, 0.5], gap="large")

    with plan1:
        st.markdown(
            """
<div style="background-color: #f8fafc; padding: 30px; border-radius: 12px; border: 2px solid #e2e8f0; text-align: center; min-height: 560px;">
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
            position: relative; box-shadow: 0 10px 40px rgba(102, 126, 234, 0.4); min-height: 560px;">
    <!-- Badge "Recomendado" -->
    <div style="position: absolute; top: -15px; left: 50%; transform: translateX(-50%); 
                background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                color: white; padding: 8px 25px; border-radius: 25px; 
                font-size: 0.9rem; font-weight: bold; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);">
        ⭐ RECOMENDADO PARA VOCÊ
    </div>
    <h3 style="color: white; margin-top: 15px; font-size: 1.5rem;">💎 Pro</h3>
    <div style="font-size: 2.5rem; color: white; margin: 20px 0; font-weight: bold;">
        R$ 19,90<span style="font-size: 1.2rem; font-weight: normal;">/mês</span>
    </div>
    <!-- Âncora de preço -->
    <p style="color: rgba(255,255,255,0.95); font-size: 0.95rem; margin-bottom: 10px;">
        💡 Menos que 1 aposta de 7 números (R$ 31,50)
    </p>
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

    if AUTHClient.is_authenticated():
        col_cta1, col_cta_central, col_cta2 = st.columns([1, 2, 1])
        with col_cta_central:

            if st.button(
                "🚀 Fazer Upgrade para PRO", type="primary", use_container_width=True
            ):
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
                            use_container_width=True,
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
                "Ambiente seguro Stripe • Cancele a qualquer momento"
                "</p>",
                unsafe_allow_html=True,
            )
    else:
        # Usuário não logado → CTA para criar conta Free
        col_cta1, col_cta_central, col_cta2 = st.columns([1, 2, 1])
        with col_cta_central:
            if st.button(
                "🎉 Começar Grátis Agora", type="primary", use_container_width=True
            ):
                st.switch_page("pages/7_Registro.py")

            st.markdown(
                '<p style="text-align: center; color: #94a3b8; font-size: 0.85rem; margin-top: 10px;">'
                "Sem cartão de crédito • 3 validações/dia para sempre"
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

    # FAQ Expandido
    with st.expander("❓ Perguntas Frequentes"):
        st.markdown(
            """
            ### **Como funciona o pagamento?**
            Atualmente o upgrade é manual para o MVP. Em breve integraremos com Stripe/Mercado Pago 
            para pagamentos automatizados com cartão de crédito ou PIX.

            ### **Posso cancelar a qualquer momento?**
            Sim! Sem burocracia. Basta solicitar o cancelamento por e-mail e o downgrade é imediato.

            ### **Os dados são seguros?**
            Sim. Utilizamos criptografia moderna e seguimos as melhores práticas de segurança. 
            Seus dados nunca são compartilhados com terceiros.

            ### **O que acontece se eu cancelar o Pro?**
            Você volta para o plano Free (3 validações/dia) mas mantém acesso ao histórico de jogos 
            criados durante o período Pro.

            ### **Quanto custa o plano Enterprise?**
            O Enterprise é personalizado para grandes grupos (50+ usuários), APIs corporativas ou 
            white-label. Entre em contato: contato@lotoscience.com

            ### **Por que 3 validações/dia no Free?**
            Queremos que você teste de verdade: valide seu jogo atual + 2 alternativas. 
            Não é uma limitação frustrante, é um teste real de valor.
            """
        )

    st.markdown("<br>", unsafe_allow_html=True)


# Helper privado para rodapé de auth
def _render_auth_footer(is_login=True):
    col1, col2 = st.columns(2)

    with col1:
        if is_login:
            st.markdown("**Não tem conta?**")
            if st.button("📝 Criar Conta Grátis", use_container_width=True):
                st.switch_page("pages/7_Registro.py")
        else:
            st.markdown("**Já tem conta?**")
            if st.button("🔐 Fazer Login", use_container_width=True):
                st.switch_page("pages/6_Login.py")

    with col2:
        st.markdown("**Ajuda?**")
        st.caption("Suporte: contato@lotoscience.com")
