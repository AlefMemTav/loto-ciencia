# app/ui/components/sidebar.py
import streamlit as st
from app.core.lottery import GAMES
from app.ui.services.auth_client import AUTHClient
from app.ui.core.state import GLOBAL_KEY, WIDGET_KEY, sync_widget_to_global


def render_game_selector():
    """Seletor de jogo com segmented control"""
    jogos = list(GAMES.keys())

    st.segmented_control(
        "Jogo",
        options=jogos,
        format_func=lambda k: GAMES[k].name,
        key=WIDGET_KEY,
        on_change=sync_widget_to_global,
    )

    # Exibe informações do jogo selecionado (mantendo estilo original)
    slug = st.session_state.get(GLOBAL_KEY, jogos[0])
    config = GAMES[slug]

    st.caption(
        f"{config.name}: {config.n_numbers} números • aposta de {config.bet_size} • {config.odds_text}"
    )
    st.caption(config.how_to_play)


def render_auth_status():
    """
    Renderiza status minimalista na sidebar (Login/Registro/Perfil)
    """
    st.sidebar.markdown("---")

    if AUTHClient.is_authenticated():
        # Usuário Logado
        email = st.session_state.get("user_email", "Usuário")
        plan = st.session_state.get("user_plan", "free")

        # Emoji do plano
        emoji = "👑" if plan == "pro" else "🆓"

        st.sidebar.write(f"👤 **{email}**")
        st.sidebar.write(f"📊 Plano: {emoji} {plan.upper()}")

        if st.sidebar.button("Sair", key="sidebar_logout"):
            AUTHClient.logout()
            st.rerun()

    else:
        # Usuário Deslogado (Visitante)
        st.sidebar.info("🔒 **Faça login**")
        st.sidebar.caption("Acesse validador e gerador")

        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("Entrar", key="sidebar_login", width="stretch"):
                st.switch_page("pages/6_Login.py")
        with col2:
            if st.button(
                "Cadastro",
                key="sidebar_register",
                width="stretch",
                type="primary",
            ):
                st.switch_page("pages/7_Registro.py")
