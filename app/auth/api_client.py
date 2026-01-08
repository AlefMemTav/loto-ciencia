# app/auth/api_client.py
"""
Cliente para API LotoScience com cookies HttpOnly automáticos.
Rate limiting apenas para usuários autenticados (free/pro).
"""

import requests
import streamlit as st
from typing import Optional, Tuple
import os

API_BASE_URL = os.getenv("API_URL", "http://localhost:8000")


class APIClient:
    """Cliente para API LotoScience"""

    # Sessão persistente para manter cookies
    _session = requests.Session()

    @staticmethod
    def init():
        """
        ✅ Verifica autenticação em TODA navegação de página.
        Cookies HttpOnly são enviados automaticamente!
        """
        # SEMPRE verifica com o backend (cookies são persistentes)
        try:
            response = APIClient._session.get(
                f"{API_BASE_URL}/auth/me",
                timeout=5,
                # ✅ Garante que os cookies sejam enviados
                allow_redirects=False,
            )

            if response.status_code == 200:
                data = response.json()
                # ✅ Sincroniza session_state com o backend
                st.session_state.authenticated = True
                st.session_state.user_email = data["email"]
                st.session_state.user_plan = data["plan"]
                st.session_state.last_auth_check = st.session_state.get(
                    "rerun_count", 0
                )
                return True
            else:
                # ❌ Cookie inválido/expirado - limpa estado
                APIClient._clear_session_state()
                return False

        except Exception as e:
            # Erro de conexão - mantém estado se já autenticado
            # (para funcionar offline depois de login)
            if not st.session_state.get("authenticated", False):
                APIClient._clear_session_state()
            return False

    @staticmethod
    def _clear_session_state():
        """Limpa estado de autenticação"""
        st.session_state.authenticated = False
        st.session_state.user_email = None
        st.session_state.user_plan = None

    @staticmethod
    def _handle_error(response: requests.Response) -> str:
        """Extrai mensagem de erro"""
        try:
            return response.json().get("detail", "Erro desconhecido")
        except:
            return f"Erro HTTP {response.status_code}"

    # ===== AUTENTICAÇÃO =====

    @staticmethod
    def register(email: str, password: str) -> Tuple[bool, str, Optional[dict]]:
        """Registra novo usuário (backend define cookie automaticamente)"""
        try:
            response = APIClient._session.post(
                f"{API_BASE_URL}/auth/register",
                json={"email": email, "password": password},
                timeout=10,
            )

            if response.status_code == 201:
                data = response.json()
                # Cookie já foi definido pelo backend!
                # Atualiza session_state
                st.session_state.authenticated = True
                st.session_state.user_email = data["user"]["email"]
                st.session_state.user_plan = data["user"]["plan"]
                return True, data["message"], data
            else:
                return False, APIClient._handle_error(response), None

        except Exception as e:
            return False, f"Erro de conexão: {e}", None

    @staticmethod
    def login(email: str, password: str) -> Tuple[bool, str, Optional[dict]]:
        """Faz login (backend define cookie automaticamente)"""
        try:
            response = APIClient._session.post(
                f"{API_BASE_URL}/auth/login",
                json={"email": email, "password": password},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                # ✅ Cookie HttpOnly já foi setado pelo backend!

                # Atualiza session_state
                st.session_state.authenticated = True
                st.session_state.user_email = data["user"]["email"]
                st.session_state.user_plan = data["user"]["plan"]

                return True, data["message"], data
            else:
                error = response.json().get("detail", "Erro desconhecido")
                return False, error, None

        except Exception as e:
            return False, f"Erro de conexão: {e}", None

    @staticmethod
    def logout():
        """Faz logout (backend remove cookie)"""
        try:
            APIClient._session.post(f"{API_BASE_URL}/auth/logout", timeout=5)
        except:
            pass

        # Limpa session_state
        APIClient._clear_session_state()

    @staticmethod
    def get_profile() -> Optional[dict]:
        """Retorna perfil do usuário (cookie enviado automaticamente)"""
        try:
            response = APIClient._session.get(f"{API_BASE_URL}/auth/me", timeout=10)
            return response.json() if response.status_code == 200 else None
        except:
            return None

    # ===== RATE LIMITING (apenas autenticado) =====

    @staticmethod
    def check_rate_limit(resource: str) -> Tuple[bool, str]:
        """Verifica rate limit (APENAS consulta, não marca como usado)"""
        if not APIClient.is_authenticated():
            return False, "🔒 Login necessário"

        try:
            response = APIClient._session.post(
                f"{API_BASE_URL}/auth/check-rate-limit/{resource}", timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return data["allowed"], data["message"]
            else:
                return False, APIClient._handle_error(response)

        except Exception as e:
            return False, f"Erro: {e}"

    @staticmethod
    def mark_resource_used(resource: str) -> Tuple[bool, str]:
        """
        ✅ MARCA recurso como usado (chame APÓS validar/gerar).
        """
        if not APIClient.is_authenticated():
            return False, "Login necessário"

        try:
            response = APIClient._session.post(
                f"{API_BASE_URL}/auth/use-resource/{resource}", timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return True, data["message"]
            else:
                return False, APIClient._handle_error(response)

        except Exception as e:
            return False, f"Erro: {e}"

    # ===== PLANOS =====

    @staticmethod
    def upgrade_to_pro() -> Tuple[bool, str]:
        """Faz upgrade para Pro (cookie enviado automaticamente)"""
        try:
            response = APIClient._session.post(
                f"{API_BASE_URL}/auth/upgrade", timeout=10
            )

            if response.status_code == 200:
                # Atualiza session_state
                st.session_state.user_plan = "pro"
                data = response.json()
                return True, data["message"]
            else:
                return False, APIClient._handle_error(response)

        except Exception as e:
            return False, f"Erro: {e}"

    # ===== HELPERS =====

    @staticmethod
    def is_authenticated() -> bool:
        return st.session_state.get("authenticated", False)

    @staticmethod
    def get_plan() -> str:
        if not APIClient.is_authenticated():
            return "guest"
        return st.session_state.get("user_plan", "free")

    @staticmethod
    def is_pro() -> bool:
        return APIClient.get_plan() == "pro"
