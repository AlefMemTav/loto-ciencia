# app/ui/services/auth_client.py

"""
Cliente para API LotoScience com cookies HttpOnly automáticos.
Rate limiting + UI de controle de acesso inline.
"""

import requests
import streamlit as st
from typing import Optional, Tuple
import os

API_BASE_URL = os.getenv("API_URL", "http://localhost:8000")


class AUTHClient:
    """Cliente para API LotoScience"""

    # Sessão persistente para manter cookies
    _session = requests.Session()

    # ========================================
    # ✅ CONFIGURAÇÕES DE LIMITES (para UI)
    # ========================================
    # 0 = Exclusivo PRO (Bloqueado para Free)
    # >0 = Limite diário para Free
    LIMITS = {
        "validator": 3,
        "generator": 1,
        "closures": 0,  # 0 significa Exclusivo PRO
        "bolao": 0,  # Exemplo: Bolão também exclusivo
    }

    @staticmethod
    def init():
        """
        ✅ Verifica autenticação em TODA navegação de página.
        Cookies HttpOnly são enviados automaticamente!
        """
        # SEMPRE verifica com o backend (cookies são persistentes)
        try:
            response = AUTHClient._session.get(
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
                AUTHClient._clear_session_state()
                return False

        except Exception as e:
            # Erro de conexão - mantém estado se já autenticado
            # (para funcionar offline depois de login)
            if not st.session_state.get("authenticated", False):
                AUTHClient._clear_session_state()
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
            response = AUTHClient._session.post(
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
                return False, AUTHClient._handle_error(response), None

        except Exception as e:
            return False, f"Erro de conexão: {e}", None

    @staticmethod
    def login(email: str, password: str) -> Tuple[bool, str, Optional[dict]]:
        """Faz login (backend define cookie automaticamente)"""
        try:
            response = AUTHClient._session.post(
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
            AUTHClient._session.post(f"{API_BASE_URL}/auth/logout", timeout=5)
        except:
            pass

        # Limpa session_state
        AUTHClient._clear_session_state()

    @staticmethod
    def get_profile() -> Optional[dict]:
        """Retorna perfil do usuário (cookie enviado automaticamente)"""
        try:
            response = AUTHClient._session.get(f"{API_BASE_URL}/auth/me", timeout=10)
            return response.json() if response.status_code == 200 else None
        except:
            return None

    # ===== RATE LIMITING =====

    @staticmethod
    def check_rate_limit(resource: str) -> Tuple[bool, str, int]:
        """Retorna (allowed, message, current_usage)"""
        if AUTHClient.is_pro():
            return True, "Acesso Ilimitado", 0

        try:
            response = AUTHClient._session.get(
                f"{API_BASE_URL}/auth/check_limit?resource={resource}", timeout=2
            )
            data = response.json()
            return (
                data.get("allowed", False),
                data.get("message", ""),
                data.get("usage", 0),
                data.get("limit", 0),
            )
        except:
            return False, "Erro de conexão", 999

    @staticmethod
    def mark_resource_used(resource: str) -> Tuple[bool, str]:
        """
        ✅ MARCA recurso como usado e LIMPA O CACHE local para atualizar UI.
        """
        if not AUTHClient.is_authenticated():
            return False, "Login necessário"
        try:
            response = AUTHClient._session.post(
                f"{API_BASE_URL}/auth/use-resource/{resource}", timeout=10
            )
            if response.status_code == 200:
                data = response.json()

                cache_key = f"rate_check_{resource}"
                if cache_key in st.session_state:
                    del st.session_state[cache_key]

                return True, data["message"]
            else:
                return False, AUTHClient._handle_error(response)
        except Exception as e:
            return False, f"Erro: {e}"

    @staticmethod
    def check_and_render_access(resource: str, resource_name: str) -> bool:
        """
        Verifica acesso e renderiza UI de bloqueio.
        """
        # 1. Caso: Visitante (Não Logado)
        if not AUTHClient.is_authenticated():
            st.info(f"🔒 Para usar o **{resource_name}**, você precisa estar logado.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button(
                    "🔐 Fazer Login", key=f"login_{resource}", use_container_width=True
                ):
                    st.switch_page("pages/6_Login.py")
            with c2:
                if st.button(
                    "📝 Criar Conta Grátis",
                    key=f"reg_{resource}",
                    use_container_width=True,
                ):
                    st.switch_page("pages/7_Registro.py")
            return False

        if resource not in AUTHClient.LIMITS:
            return True

        # Limite padrão (hardcoded)
        limit = AUTHClient.LIMITS[resource]

        # 2. Caso: Usuário PRO (Libera tudo)
        if AUTHClient.is_pro():
            AUTHClient._render_pro_message()
            return True

        # 3. Caso: Recurso Exclusivo (Limite 0 para Free)
        if limit == 0:
            AUTHClient._render_exclusive_message(resource_name)
            return False

        # 4. Caso: Usuário Free com Limite Diário
        rerun = st.session_state.get("rerun_count", 0)
        cache_key = f"rate_check_{resource}"
        cached = st.session_state.get(cache_key)

        # Lógica de Cache e Busca
        if cached and cached.get("rerun") == rerun:
            # ✅ CAMINHO DO CACHE: Recupera tudo do cache
            allowed = cached["allowed"]
            current_usage = cached["usage"]
            # Recupera o limite salvo ou usa o padrão se não existir
            final_limit = cached.get("limit", limit)
        else:
            # 🔄 CAMINHO DA API: Busca dados novos
            allowed, _, current_usage, server_limit = AUTHClient.check_rate_limit(
                resource
            )

            # Prioriza limite do servidor; se for 0, usa o local
            final_limit = server_limit if server_limit > 0 else limit

            st.session_state[cache_key] = {
                "rerun": rerun,
                "allowed": allowed,
                "usage": current_usage,
                "limit": final_limit,
            }

        # Atualiza a variável 'limit' para usar o valor mais correto (local ou servidor)
        limit = final_limit

        if allowed:
            remaining = max(0, limit - current_usage)
            AUTHClient._render_available_message(resource_name, limit, remaining)
            return True
        else:
            AUTHClient._render_blocked_message(resource_name, limit)

        return False

    # ===== MENSAGENS UI =====

    @staticmethod
    def _render_pro_message():
        st.success("✅ **Você é PRO:** Acesso total liberado")

    @staticmethod
    def _render_exclusive_message(resource_name: str):
        """Renderiza bloqueio de recurso exclusivo PRO"""
        st.warning(
            f"👑 **{resource_name}** é exclusivo para assinantes PRO.",
            icon="🔒",
        )
        st.markdown(
            """
            <div style="background-color: #fefce8; padding: 15px; border-radius: 8px; border: 1px solid #fde047; margin-bottom: 15px;">
                <p style="margin:0; color: #854d0e;">
                Usuários gratuitos têm acesso ao Validador e Gerador básico.
                Ferramentas avançadas exigem poder computacional extra.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button(
                "🚀 Desbloquear Agora (R$ 19,90/mês)",
                type="primary",
                use_container_width=True,
                key=f"excl_upg_{resource_name}",
            ):
                st.switch_page("pages/8_Planos.py")

    @staticmethod
    def _render_blocked_message(resource_name: str, limit: int):
        st.warning(
            f"⚠️ **Limite diário atingido ({limit} usos/dia)**\n\n"
            f"Você já usou o {resource_name} hoje. "
            f"Volte amanhã ou faça upgrade.",
            icon="🔒",
        )
        if st.button(
            "🚀 Virar Ilimitado",
            type="primary",
            use_container_width=True,
            key=f"limit_upg_{resource_name}",
        ):
            st.switch_page("pages/8_Planos.py")

    @staticmethod
    def _render_available_message(resource_name: str, limit: int, remaining: int):
        color = "orange" if remaining <= 1 else "blue"
        st.caption(
            f":{color}[ℹ️ **Plano Gratuito:** {remaining} de {limit} usos restantes hoje.]"
        )

    # ===== HELPERS =====

    @staticmethod
    def upgrade_to_pro() -> Tuple[bool, str]:
        """Faz upgrade para Pro (cookie enviado automaticamente)"""
        try:
            response = AUTHClient._session.post(
                f"{API_BASE_URL}/auth/upgrade", timeout=10
            )
            if response.status_code == 200:
                # Atualiza session_state
                st.session_state.user_plan = "pro"
                return True, response.json()["message"]
            else:
                return False, AUTHClient._handle_error(response)
        except Exception as e:
            return False, f"Erro: {e}"

    # ===== HELPERS =====

    @staticmethod
    def is_authenticated() -> bool:
        return st.session_state.get("authenticated", False)

    @staticmethod
    def get_plan() -> str:
        if not AUTHClient.is_authenticated():
            return "guest"
        return st.session_state.get("user_plan", "free")

    @staticmethod
    def is_pro() -> bool:
        return AUTHClient.get_plan() == "pro"
