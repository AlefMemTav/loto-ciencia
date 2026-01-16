# app/ui/services/auth_client.py
import requests
import streamlit as st
import extra_streamlit_components as stx
from typing import Optional, Tuple
import os
import datetime
import time
from app.core.logger import logger

# Configuração da URL da API
API_URL = os.getenv("API_URL", "http://localhost:8000")


class AUTHClient:
    """
    Cliente de Autenticação Seguro.
    - Persistência: Usa Cookies criptografados no cliente (Navegador).
    - Segurança: Tokens nunca tocam o disco do servidor.
    - Validação: O token do cookie é sempre revalidado na API.
    """

    LIMITS = {
        "validator": 3,
        "generator": 0,
        "closures": 0,
        "bolao": 0,
    }

    # Singleton para o gerenciador de cookies para evitar re-instanciação no rerun
    _cookie_manager = None

    @classmethod
    def get_manager(cls):
        """Retorna a instância do gerenciador de cookies."""
        if cls._cookie_manager is None:
            # key="auth_cookie_manager" garante que o componente não resete
            cls._cookie_manager = stx.CookieManager(key="auth_cookie_manager")
        return cls._cookie_manager

    @staticmethod
    def _get_headers():
        """Retorna headers com token de autenticação."""
        token = st.session_state.get("access_token")
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    @staticmethod
    def init():
        """
        Lógica de Persistência (Executada no topo de cada página).
        1. Verifica session_state (Memória RAM).
        2. Se vazio, verifica Cookie (Navegador).
        3. Se achar Cookie, valida na API e restaura sessão.
        """
        if st.session_state.get("just_logged_out", False):
            del st.session_state["just_logged_out"]
            return False
        cm = AUTHClient.get_manager()

        # Pega todos os cookies (força sincronização do componente)
        cookies = cm.get_all()
        token_cookie = cookies.get("access_token")

        # 1. Se já está logado na memória, tudo certo.
        if st.session_state.get("authenticated", False):
            return True

        # 2. Se não está na memória, mas tem cookie: Tenta restaurar.
        if token_cookie:
            logger.debug("🍪 Cookie encontrado. Tentando restaurar sessão...")

            try:
                # Valida o token com o Backend (Crucial para segurança)
                response = requests.get(
                    f"{API_URL}/auth/me",
                    headers={"Authorization": f"Bearer {token_cookie}"},
                    timeout=5,
                )

                if response.status_code == 200:
                    data = response.json()

                    # ✅ Restaura estado na memória
                    st.session_state.access_token = token_cookie
                    st.session_state.authenticated = True
                    st.session_state.user_email = data["email"]
                    st.session_state.user_plan = data["plan"]

                    logger.info(f"✅ Sessão restaurada via Cookie: {data['email']}")
                    return True
                else:
                    logger.warning("❌ Token do cookie expirado ou inválido.")
                    AUTHClient.logout()  # Limpa o cookie inválido
            except Exception as e:
                logger.error(f"❌ Erro ao validar token do cookie: {e}")

        return False

    @staticmethod
    def login(email: str, password: str) -> Tuple[bool, str, Optional[dict]]:
        """Realiza login e define o Cookie no navegador."""
        try:
            response = requests.post(
                f"{API_URL}/auth/login",
                json={"email": email, "password": password},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                token = data["access_token"]
                user_data = data["user"]

                # 1. Atualiza Memória
                st.session_state.access_token = token
                st.session_state.authenticated = True
                st.session_state.user_email = user_data["email"]
                st.session_state.user_plan = user_data["plan"]

                # 2. Atualiza Navegador (Cookie expira em 30 dias)
                expires_at = datetime.datetime.now() + datetime.timedelta(days=30)
                cm = AUTHClient.get_manager()
                cm.set("access_token", token, expires_at=expires_at)

                logger.info(f"🔐 Login sucesso + Cookie definido: {email}")
                return True, data["message"], data

            return False, response.json().get("detail", "Erro de login"), None
        except Exception as e:
            logger.error(f"❌ Erro no login: {e}")
            return False, f"Erro de conexão: {e}", None

    @staticmethod
    def register(email: str, password: str) -> Tuple[bool, str, Optional[dict]]:
        try:
            response = requests.post(
                f"{API_URL}/auth/register",
                json={"email": email, "password": password},
                timeout=10,
            )

            if response.status_code == 201:
                data = response.json()
                token = data["access_token"]
                user_data = data["user"]

                # Login automático após registro
                st.session_state.access_token = token
                st.session_state.authenticated = True
                st.session_state.user_email = user_data["email"]
                st.session_state.user_plan = user_data["plan"]

                # Define Cookie
                expires_at = datetime.datetime.now() + datetime.timedelta(days=30)
                cm = AUTHClient.get_manager()
                cm.set("access_token", token, expires_at=expires_at)

                return True, data["message"], data

            return False, AUTHClient._handle_error(response), None
        except Exception as e:
            return False, f"Erro: {e}", None

    @staticmethod
    def logout():
        """Limpa memória, apaga o Cookie e força atualização."""
        email = st.session_state.get("user_email", "desconhecido")
        logger.info(f"🚪 Logout: {email}")

        # 1. Apaga cookie
        cm = AUTHClient.get_manager()
        cm.delete("access_token")

        # 2. Limpa toda a memória da sessão
        for key in list(st.session_state.keys()):
            del st.session_state[key]

        # 3. Define a flag que impede o re-login automático imediato
        st.session_state["just_logged_out"] = True

        # 4. Mensagem e Rerun
        placeholder = st.empty()
        placeholder.warning("Saindo...", icon="👋")
        time.sleep(1)
        st.rerun()

    # ===== MÉTODOS AUXILIARES (Mantidos iguais) =====

    @staticmethod
    def get_profile() -> Optional[dict]:
        try:
            response = requests.get(
                f"{API_URL}/auth/me",
                headers=AUTHClient._get_headers(),
                timeout=10,
            )
            return response.json() if response.status_code == 200 else None
        except:
            return None

    @staticmethod
    def check_rate_limit(resource: str) -> Tuple[bool, str, int, int]:
        if AUTHClient.is_pro():
            return True, "Acesso Ilimitado", 0, 0

        try:
            response = requests.get(
                f"{API_URL}/auth/check_limit",
                headers=AUTHClient._get_headers(),
                params={"resource": resource},
                timeout=2,
            )
            data = response.json()
            return (
                data.get("allowed", False),
                data.get("message", ""),
                data.get("usage", 0),
                data.get("limit", 0),
            )
        except Exception as e:
            return False, "Erro de conexão", 999, 0

    @staticmethod
    def mark_resource_used(resource: str) -> Tuple[bool, str]:
        if not AUTHClient.is_authenticated():
            return False, "Login necessário"

        try:
            response = requests.post(
                f"{API_URL}/auth/use-resource/{resource}",
                headers=AUTHClient._get_headers(),
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                # Limpa cache local para forçar nova verificação no UI
                cache_key = f"rate_check_{resource}"
                if cache_key in st.session_state:
                    del st.session_state[cache_key]
                return True, data["message"]
            return False, AUTHClient._handle_error(response)
        except Exception as e:
            return False, f"Erro: {e}"

    @staticmethod
    def upgrade_to_pro() -> Tuple[bool, str]:
        try:
            response = requests.post(
                f"{API_URL}/auth/upgrade",
                headers=AUTHClient._get_headers(),
                timeout=10,
            )
            if response.status_code == 200:
                st.session_state.user_plan = "pro"
                return True, response.json()["message"]
            return False, AUTHClient._handle_error(response)
        except Exception as e:
            return False, f"Erro: {e}"

    @staticmethod
    def check_and_render_access(resource: str, resource_name: str) -> bool:
        # Copiar a implementação anterior, ela estava segura do ponto de vista de UI
        if not AUTHClient.is_authenticated():
            st.info(f"🔒 Para usar o **{resource_name}**, você precisa estar logado.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button(
                    "🔐 Fazer Login", key=f"login_{resource}", width="stretch"
                ):
                    st.switch_page("pages/9_Login.py")  # Ajuste o caminho se necessário
            with c2:
                if st.button("📝 Criar Conta", key=f"reg_{resource}", width="stretch"):
                    st.switch_page("pages/10_Registro.py")
            return False
        if resource not in AUTHClient.LIMITS:
            return True

        limit = AUTHClient.LIMITS[resource]

        if AUTHClient.is_pro():
            st.success("✅ **Você é PRO:** Acesso total liberado")
            return True

        if limit == 0:
            AUTHClient._render_exclusive_message(resource, resource_name)
            return False

        rerun = st.session_state.get("rerun_count", 0)
        cache_key = f"rate_check_{resource}"
        cached = st.session_state.get(cache_key)

        if cached and cached.get("rerun") == rerun:
            allowed = cached["allowed"]
            current_usage = cached["usage"]
            final_limit = cached.get("limit", limit)
        else:
            allowed, _, current_usage, server_limit = AUTHClient.check_rate_limit(
                resource
            )
            final_limit = server_limit if server_limit > 0 else limit

            st.session_state[cache_key] = {
                "rerun": rerun,
                "allowed": allowed,
                "usage": current_usage,
                "limit": final_limit,
            }
        limit = final_limit
        if allowed:
            remaining = max(0, limit - current_usage)
            color = "orange" if remaining <= 1 else "blue"
            st.caption(
                f":{color}[ℹ️ **Plano Gratuito:** {remaining} de {limit} usos restantes.]"
            )
            return True
        else:
            AUTHClient._render_blocked_message(resource, resource_name, limit)
            return False

    @staticmethod
    def is_authenticated() -> bool:
        return st.session_state.get("authenticated", False)

    @staticmethod
    def get_plan() -> str:
        return (
            st.session_state.get("user_plan", "free")
            if AUTHClient.is_authenticated()
            else "guest"
        )

    @staticmethod
    def is_pro() -> bool:
        return AUTHClient.get_plan() == "pro"

    @staticmethod
    def _handle_error(response) -> str:
        try:
            return response.json().get("detail", "Erro desconhecido")
        except:
            return f"Erro HTTP {response.status_code}"

    @staticmethod
    def _render_pro_message():
        st.success("✅ **Você é PRO:** Acesso total liberado")

    @staticmethod
    def _render_exclusive_message(resource: str, resource_name: str):
        """Renderiza bloqueio de recurso exclusivo PRO"""
        st.warning(
            f"👑 **{resource_name}** é exclusivo para assinantes PRO.",
            icon="🔒",
        )
        st.markdown(
            """
<div style="background-color: #fefce8; padding: 15px; border-radius: 8px; border: 1px solid #fde047; margin-bottom: 15px;">
    <p style="margin:0; color: #854d0e;">
    Usuários gratuitos têm acesso ao Validador.
    Ferramentas avançadas exigem poder computacional extra.
    </p>
</div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "🚀 Desbloquear Agora (R$ 19,90/mês)",
            type="primary",
            width="stretch",
            key=f"excl_upg_{resource}",
        ):
            st.switch_page("pages/8_Planos.py")

    @staticmethod
    def _render_blocked_message(resource: str, resource_name: str, limit: int):
        st.warning(
            f"⚠️ **Limite diário atingido ({limit} usos/dia)**\n\n"
            f"Você já usou o {resource_name} hoje. "
            f"Volte amanhã ou faça upgrade.",
            icon="🔒",
        )

        if st.button(
            "🚀 Virar Ilimitado",
            type="primary",
            width="stretch",
            key=f"limit_upg_{resource}",
        ):
            st.switch_page("pages/8_Planos.py")

    @staticmethod
    def upgrade_to_pro() -> Tuple[bool, str]:
        try:
            response = requests.post(
                f"{API_URL}/auth/upgrade",
                headers=AUTHClient._get_headers(),
                timeout=10,
            )

            if response.status_code == 200:
                st.session_state.user_plan = "pro"

                # ✅ Atualiza arquivo local
                token = st.session_state.get("access_token")
                email = st.session_state.user_email

                logger.info(f"⭐ Upgrade para PRO: {email}")
                return True, response.json()["message"]

            return False, AUTHClient._handle_error(response)
        except Exception as e:
            logger.error(f"❌ Erro no upgrade: {e}")
            return False, f"Erro: {e}"

    @staticmethod
    def is_authenticated() -> bool:
        return st.session_state.get("authenticated", False)

    @staticmethod
    def get_plan() -> str:
        return (
            st.session_state.get("user_plan", "free")
            if AUTHClient.is_authenticated()
            else "guest"
        )

    @staticmethod
    def is_pro() -> bool:
        return AUTHClient.get_plan() == "pro"
