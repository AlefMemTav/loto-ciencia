# app/ui/header.py
import streamlit as st
from app.ui.services.auth_client import AUTHClient


def render_app_header(config, df):
    """Header principal com logo, info do jogo e status de autenticação"""

    col1, col2, col3 = st.columns([2, 3, 2])

    with col1:
        st.markdown("### 🧪 **LotoScience**")

    with col2:
        st.caption(f"📊 {config.name} • {len(df)} concursos analisados")

    with col3:
        _render_auth_badge()

    st.markdown("---")


def _render_auth_badge():
    """Badge minimalista de autenticação no header"""

    if AUTHClient.is_authenticated():
        query_params = st.query_params

        if query_params.get("paid") == "true":
            st.success("🎉 Pagamento confirmado! Seu plano PRO está sendo ativado...")

            success, msg = AUTHClient.upgrade_to_pro()

            if success:
                st.balloons()
                st.query_params.clear()
                st.rerun()

        email = st.session_state.get("user_email", "Usuário")
        plan = st.session_state.get("user_plan", "free")

        # Mostra email truncado + badge + popover
        email_short = email.split("@")[0] if "@" in email else email
        if len(email_short) > 15:
            email_short = email_short[:15] + "..."

        if plan == "pro":
            badge_html = f"""
            <div style='text-align: right; line-height: 1.4;'>
                <span style='font-size: 0.85rem; color: #6b7280;'>👤 {email_short}</span>
                <span style='margin-left: 6px; background: linear-gradient(90deg, #fbbf24, #f59e0b); 
                       padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; 
                       font-weight: 600; color: #000;'>👑 PRO</span>
            </div>
            """
        else:
            badge_html = f"""
            <div style='text-align: right; line-height: 1.4;'>
                <span style='font-size: 0.85rem; color: #6b7280;'>👤 {email_short}</span>
                <span style='margin-left: 6px; background: #e5e7eb; 
                       padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; 
                       font-weight: 600; color: #374151;'>FREE</span>
            </div>
            """

        col_badge, col_menu = st.columns([4, 1])

        with col_badge:
            st.markdown(badge_html, unsafe_allow_html=True)

        with col_menu:
            # Menu minimalista com popover
            with st.popover("⚙️"):
                if plan != "pro":
                    if st.button("👑 Upgrade PRO", width="stretch", type="primary"):
                        st.switch_page("pages/8_Planos.py")
                    st.divider()

                if st.button("🚪 Sair", width="stretch"):
                    with st.spinner("Desconectando..."):
                        AUTHClient.logout()
    else:
        # Não autenticado - links minimalistas
        st.markdown(
            """
            <div style='text-align: right; font-size: 0.9rem;'>
                <a href='/Login' target="_self" 
                   style='text-decoration: none; color: #3b82f6; margin-right: 12px;'>
                   🔐 Entrar
                </a>
                <a href='/Registro' target="_self" 
                   style='text-decoration: none; color: #10b981; font-weight: 600;'>
                   📝 Criar conta
                </a>
            </div>
            """,
            unsafe_allow_html=True,
        )
