# app/auth/cookie_manager.py
"""
Gerenciador de cookies para persistir autenticação.
"""
import streamlit as st
import extra_streamlit_components as stx
from app.core.logger import logger

GUEST_ID_COOKIE = "lotoscience_guest_id"


# Cookie manager
@st.cache_resource
def get_cookie_manager():
    logger.debug("Inicializando CookieManager (cache_resource).")
    cm = stx.CookieManager()
    logger.debug("CookieManager inicializado.")
    return cm


cookies = get_cookie_manager()


def init_cookies():
    """Inicializa cookie manager"""
    # extra-streamlit-components já está sempre pronto
    logger.debug("init_cookies chamado — extra-streamlit-components pronto.")
    return True


def save_auth_to_cookies(access_token: str, email: str, plan: str):
    """Salva dados de autenticação nos cookies"""
    try:
        logger.debug("Salvando cookies de autenticação...")
        cookies.set("lotoscience_access_token", access_token, expires_at=None)
        cookies.set("lotoscience_user_email", email, expires_at=None)
        cookies.set("lotoscience_user_plan", plan, expires_at=None)
        cookies.set("lotoscience_authenticated", "true", expires_at=None)
        logger.info(
            f"Cookies de autenticação salvos para o usuário: {email} (plan={plan})."
        )
    except Exception:
        logger.exception("Erro ao salvar cookies de autenticação.")
        st.error("Erro ao salvar cookies: verifique os logs.")


def load_auth_from_cookies():
    """Carrega dados de autenticação dos cookies para session_state"""
    try:
        # Obtém todos os cookies
        all_cookies = cookies.get_all()
        logger.debug(f"Cookies carregados: chaves={list(all_cookies.keys())}")

        if all_cookies.get("lotoscience_authenticated") == "true":
            token = all_cookies.get("lotoscience_access_token")
            email = all_cookies.get("lotoscience_user_email")
            plan = all_cookies.get("lotoscience_user_plan")

            if token and email and plan:
                st.session_state.access_token = token
                st.session_state.user_email = email
                st.session_state.user_plan = plan
                st.session_state.authenticated = True
                logger.info(
                    f"Autenticação restaurada a partir de cookies para o usuário: {email} (plan={plan})."
                )
                return True
            else:
                logger.info(
                    "Cookie de autenticação presente, mas faltam dados (token/email/plan)."
                )
        else:
            logger.debug(
                "Cookie 'lotoscience_authenticated' ausente ou diferente de 'true'."
            )
    except Exception:
        # Cookies ainda não carregados ou erro ao acessar — registra e retorna False
        logger.exception("Erro ao carregar cookies de autenticação.")
    return False


def clear_auth_cookies():
    """Remove dados de autenticação dos cookies"""
    try:
        logger.debug("Removendo cookies de autenticação...")
        cookies.delete("lotoscience_access_token")
        cookies.delete("lotoscience_user_email")
        cookies.delete("lotoscience_user_plan")
        cookies.delete("lotoscience_authenticated")
        logger.info("Cookies de autenticação removidos com sucesso.")
    except Exception:
        logger.exception("Erro ao limpar cookies de autenticação.")
        st.error("Erro ao limpar cookies: verifique os logs.")
