# pages/8_Planos.py
"""Página de Planos"""
import streamlit as st
from app.auth.api_client import APIClient
from app.ui.styles import apply_custom_css

st.set_page_config(page_title="Planos - LotoScience", page_icon="👑", layout="centered")
apply_custom_css()
APIClient.init()
st.title("👑 Escolha seu Plano")

# Mostra plano atual se logado
if APIClient.is_authenticated():
    current_plan = st.session_state.get("user_plan", "free")
    if current_plan == "pro":
        st.success("✅ Você já é PRO! Aproveite todos os recursos.")
        if st.button("🏠 Voltar ao Painel"):
            st.switch_page("pages/1_Painel.py")
        st.stop()
    else:
        st.info(f"📊 Plano atual: **FREE**")

# Comparação de planos
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

    if not APIClient.is_authenticated():
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

    if APIClient.is_authenticated():
        if st.button("🚀 Fazer Upgrade", type="primary", use_container_width=True):
            with st.spinner("Processando upgrade..."):
                success, message = APIClient.upgrade_to_pro()

                if success:
                    st.success(message)
                    st.balloons()
                    import time

                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(message)
    else:
        st.info("Faça login para fazer upgrade")

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

if st.button("🏠 Voltar ao Início"):
    st.switch_page("pages/0_Inicio.py")
