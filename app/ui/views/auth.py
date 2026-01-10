# app/ui/views/auth.py
import streamlit as st
import time
from app.ui.services.auth_client import AUTHClient


def render_login_view():
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
                        st.switch_page("pages/1_Painel.py")
                    else:
                        st.error(f"❌ {message}")

    st.markdown("---")
    _render_auth_footer(is_login=True)


def render_register_view():
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
    st.title("👑 Escolha seu Plano")

    # Se já for PRO
    current_plan = st.session_state.get("user_plan", "free")
    if current_plan == "pro":
        st.success("✅ Você já é PRO! Aproveite todos os recursos.")
        if st.button("🏠 Voltar ao Painel"):
            st.switch_page("pages/1_Painel.py")
        return

    # Comparação
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🆓 FREE")
        st.markdown(
            """
    **Grátis para sempre**
    
    ✅ 1 validação/dia  
    ✅ 1 geração/dia  
    ✅ Painel de estatísticas  
    ✅ Análise básica  
    ❌ Fechamentos  
    ❌ Sistema de bolão  
    """
        )
        if not AUTHClient.is_authenticated():
            if st.button("📝 Criar Conta FREE", use_container_width=True):
                st.switch_page("pages/7_Registro.py")

    with col2:
        st.markdown("### 👑 PRO")
        st.markdown(
            """
            **R$ 9,00/mês**
            
            ✅ **Validações ilimitadas**  
            ✅ **Gerações ilimitadas**  
            ✅ **Fechamentos avançados**  
            ✅ **Sistema de bolão**  
            ✅ **Estatísticas avançadas**  
            ✅ Suporte prioritário  
            """
        )

        if AUTHClient.is_authenticated():
            if st.button("🚀 Fazer Upgrade", type="primary", use_container_width=True):
                with st.spinner("Processando..."):
                    success, message = AUTHClient.upgrade_to_pro()
                    if success:
                        st.balloons()
                        st.success(message)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(message)
        else:
            st.info("Faça login para assinar")

    st.markdown("---")
    # FAQ
    with st.expander("❓ Perguntas Frequentes"):
        st.markdown(
            """
        **Como funciona o pagamento?**  
        Atualmente o upgrade é manual para o MVP. Em breve integraremos com Stripe/Mercado Pago.
        
        **Posso cancelar a qualquer momento?**  
        Sim! Sem burocracia.
        
        **Os dados são seguros?**  
        Sim. Utilizamos criptografia e seguimos as melhores práticas de segurança.
        """
        )


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
