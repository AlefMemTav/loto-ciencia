# app/ui/core/shell.py
import streamlit as st
from app.ui.core.styles import apply_custom_css
from app.ui.components.header import render_app_header
from app.ui.components.nav import top_nav
from app.ui.core.state import load_context, init_game_state
from app.ui.components.sidebar import render_game_selector
from app.ui.services.auth_client import AUTHClient


def init_page(
    title: str,
    icon: str = "🧬",
    require_auth: bool = False,
    require_pro: bool = False,
    resource_usage: str = None,  # Ex: "generator", "validator"
):
    # 1. MIDDLEWARE DE AUTH (Crucial: Deve ser a primeira linha lógica)
    # Tenta restaurar a sessão via Cookie antes de qualquer verificação
    AUTHClient.init()

    # 2. Configuração da Página
    st.set_page_config(
        page_title=f"{title} | LotoScience",
        layout="wide",
        page_icon=icon,
        initial_sidebar_state="collapsed",
    )
    apply_custom_css()
    init_game_state()

    # 4. Barreira de Autenticação (Login Wall)
    if require_auth and not AUTHClient.is_authenticated():
        _render_lock_screen(title)
        st.stop()  # Interrompe a execução aqui. A View não será carregada.

    # 5. Barreira de Plano (Paywall - Pro Only)
    if require_pro and not AUTHClient.is_pro():
        _render_paywall_screen()
        st.stop()

    # 6. Verificação de Rate Limit (Para usuários Free)
    if resource_usage:
        # A lógica de check_rate_limit no cliente já verifica se é PRO
        can_use, message, _, _ = AUTHClient.check_rate_limit(resource_usage)

        # Mostra aviso se estiver bloqueado
        if not can_use:
            _render_rate_limit_screen()
            st.stop()

        # Opcional: Mostrar aviso de quantos usos restam
        # (Isso pode ser feito dentro da view ou aqui, depende do design)

    # 7. Carrega contexto (Pesado - só carrega se passou pelas barreiras)
    ctx, svc = load_context()

    # 8. Renderiza Header e Nav
    render_app_header(ctx.config, ctx.df)
    top_nav()
    render_game_selector()  # Movemos para cá para garantir que apareça mesmo se bloqueado (opcional)

    return ctx, svc


# --- Telas de Bloqueio Auxiliares ---


def _render_lock_screen(feature_name):
    st.warning(f"🔒 Faça login para acessar: {feature_name}")
    st.markdown("### 🚀 Recursos Exclusivos")
    st.markdown(
        "- Algoritmos avançados\n- Histórico completo\n- Ferramentas profissionais"
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔐 Fazer Login", width="stretch"):
            st.switch_page("pages/6_Login.py")
    with c2:
        if st.button("📝 Criar Conta", width="stretch"):
            st.switch_page("pages/7_Registro.py")


def _render_paywall_screen():
    st.error("👑 Este recurso é exclusivo para assinantes PRO")
    st.markdown("Desbloqueie validações ilimitadas, fechamentos e muito mais.")
    if st.button("🚀 Ver Planos e Upgrade", type="primary", width="stretch"):
        st.switch_page("pages/8_Planos.py")


def _render_rate_limit_screen():
    st.error("⛔ Limite diário gratuito atingido.")
    st.markdown(
        """
        **Você atingiu seu limite diário para esta ferramenta.**
        
        Faça upgrade para o plano **PRO** e tenha acesso ilimitado agora mesmo.
        """
    )
    if st.button("💎 Virar PRO Agora", type="primary"):
        st.switch_page("pages/8_Planos.py")
