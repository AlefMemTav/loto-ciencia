# app/ui/services/auth_client.py
import requests
import streamlit as st
from typing import Optional, Tuple
import os
import json
from pathlib import Path
from app.core.logger import logger

API_BASE_URL = os.getenv("API_URL", "http://localhost:8000")

TOKEN_FILE = Path.home() / ".lotoscience" / "session.json"
TOKEN_FILE.parent.mkdir(exist_ok=True)


class AUTHClient:
    """Cliente para API LotoScience com persistência via arquivo local"""

    LIMITS = {
        "validator": 3,
        "generator": 1,
        "closures": 0,
        "bolao": 0,
    }

    @staticmethod
    def _save_session(token: str, email: str, plan: str):
        """Salva sessão em arquivo local (substitui cookies)"""
        try:
            TOKEN_FILE.write_text(
                json.dumps({"access_token": token, "email": email, "plan": plan})
            )
            logger.info(f"Sessão salva para {email}")
        except Exception as e:
            logger.error(f"Erro ao salvar sessão: {e}")

    @staticmethod
    def _load_session() -> Optional[dict]:
        """Carrega sessão do arquivo local"""
        try:
            if TOKEN_FILE.exists():
                data = json.loads(TOKEN_FILE.read_text())
                logger.debug(f"Sessão carregada do arquivo: {data.get('email')}")
                return data
        except Exception as e:
            logger.error(f"Erro ao carregar sessão: {e}")
        return None

    @staticmethod
    def _delete_session():
        """Remove arquivo de sessão"""
        try:
            if TOKEN_FILE.exists():
                TOKEN_FILE.unlink()
                logger.info("Arquivo de sessão removido")
        except Exception as e:
            logger.error(f"Erro ao deletar sessão: {e}")

    @staticmethod
    def _get_headers():
        """Retorna headers com token de autenticação"""
        token = st.session_state.get("access_token")
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    @staticmethod
    def init():
        """
        ✅ Restaura autenticação após F5
        """
        logger.debug("=" * 50)
        logger.debug("🔄 AUTHClient.init() chamado")
        logger.debug(
            f"authenticated em session_state: {st.session_state.get('authenticated', False)}"
        )

        # 1️⃣ Já está autenticado (navegação interna)
        if st.session_state.get("authenticated", False):
            logger.debug("✅ Já autenticado via session_state")
            return True

        # 2️⃣ Tenta carregar do arquivo local
        logger.debug("🔍 Tentando restaurar de arquivo local...")
        saved = AUTHClient._load_session()

        if saved and saved.get("access_token"):
            token = saved["access_token"]
            logger.debug(f"✅ Token recuperado: {token[:20]}...")

            # Valida token com backend
            try:
                logger.debug("🌐 Validando token com backend...")
                response = requests.get(
                    f"{API_BASE_URL}/auth/me",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=5,
                )

                logger.debug(f"📡 Backend respondeu: HTTP {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    logger.debug(f"✅ Backend validou: {data['email']}")

                    # ✅ Restaura session_state
                    st.session_state.access_token = token
                    st.session_state.authenticated = True
                    st.session_state.user_email = data["email"]
                    st.session_state.user_plan = data["plan"]

                    logger.info(
                        f"✅✅ Sessão restaurada com sucesso para {data['email']}"
                    )
                    return True
                else:
                    logger.warning(f"❌ Backend rejeitou token: {response.text[:100]}")
                    AUTHClient._delete_session()

            except Exception as e:
                logger.error(f"❌ ERRO ao validar token: {e}")
                AUTHClient._delete_session()
        else:
            logger.debug("❌ Nenhuma sessão salva encontrada")

        logger.debug("❌ init() falhou - usuário não autenticado")
        logger.debug("=" * 50)
        return False

    @staticmethod
    def _clear_session_state():
        """Limpa estado de autenticação"""
        st.session_state.authenticated = False
        st.session_state.user_email = None
        st.session_state.user_plan = None
        st.session_state.access_token = None
        AUTHClient._delete_session()
        logger.info("Session state e arquivo de sessão limpos")

    @staticmethod
    def _handle_error(response) -> str:
        try:
            return response.json().get("detail", "Erro desconhecido")
        except:
            return f"Erro HTTP {response.status_code}"

    # ===== ACTIONS =====

    @staticmethod
    def register(email: str, password: str) -> Tuple[bool, str, Optional[dict]]:
        try:
            response = requests.post(
                f"{API_BASE_URL}/auth/register",
                json={"email": email, "password": password},
                timeout=10,
            )

            if response.status_code == 201:
                data = response.json()
                token = data["access_token"]

                # Salva em session_state
                st.session_state.access_token = token
                st.session_state.authenticated = True
                st.session_state.user_email = data["user"]["email"]
                st.session_state.user_plan = data["user"]["plan"]

                AUTHClient._save_session(
                    token, data["user"]["email"], data["user"]["plan"]
                )

                logger.info(f"Registro bem-sucedido: {data['user']['email']}")
                return True, data["message"], data

            return False, AUTHClient._handle_error(response), None
        except Exception as e:
            logger.error(f"Erro no registro: {e}")
            return False, f"Erro de conexão: {e}", None

    @staticmethod
    def login(email: str, password: str) -> Tuple[bool, str, Optional[dict]]:
        try:
            response = requests.post(
                f"{API_BASE_URL}/auth/login",
                json={"email": email, "password": password},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                token = data["access_token"]

                # Salva em session_state
                st.session_state.access_token = token
                st.session_state.authenticated = True
                st.session_state.user_email = data["user"]["email"]
                st.session_state.user_plan = data["user"]["plan"]

                AUTHClient._save_session(
                    token, data["user"]["email"], data["user"]["plan"]
                )

                logger.info(f"Login bem-sucedido: {data['user']['email']}")
                return True, data["message"], data

            return False, response.json().get("detail", "Erro de login"), None
        except Exception as e:
            logger.error(f"Erro no login: {e}")
            return False, f"Erro de conexão: {e}", None

    @staticmethod
    def logout():
        logger.info(f"Logout: {st.session_state.get('user_email')}")
        AUTHClient._clear_session_state()

    @staticmethod
    def get_profile() -> Optional[dict]:
        try:
            response = requests.get(
                f"{API_BASE_URL}/auth/me",
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
                f"{API_BASE_URL}/auth/check_limit",
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
            logger.error(f"Erro ao verificar rate limit: {e}")
            return False, "Erro de conexão", 999, 0

    @staticmethod
    def mark_resource_used(resource: str) -> Tuple[bool, str]:
        if not AUTHClient.is_authenticated():
            return False, "Login necessário"

        try:
            response = requests.post(
                f"{API_BASE_URL}/auth/use-resource/{resource}",
                headers=AUTHClient._get_headers(),
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                cache_key = f"rate_check_{resource}"
                if cache_key in st.session_state:
                    del st.session_state[cache_key]
                return True, data["message"]

            return False, AUTHClient._handle_error(response)
        except Exception as e:
            logger.error(f"Erro ao marcar recurso: {e}")
            return False, f"Erro: {e}"

    @staticmethod
    def check_and_render_access(resource: str, resource_name: str) -> bool:
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
    Usuários gratuitos têm acesso ao Validador e Gerador básico.
    Ferramentas avançadas exigem poder computacional extra.
    </p>
</div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "🚀 Desbloquear Agora (R$ 19,90/mês)",
            type="primary",
            use_container_width=True,
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
            use_container_width=True,
            key=f"limit_upg_{resource}",
        ):
            st.switch_page("pages/8_Planos.py")

    @staticmethod
    def upgrade_to_pro() -> Tuple[bool, str]:
        try:
            response = requests.post(
                f"{API_BASE_URL}/auth/upgrade",
                headers=AUTHClient._get_headers(),
                timeout=10,
            )

            if response.status_code == 200:
                st.session_state.user_plan = "pro"

                # ✅ Atualiza arquivo local
                token = st.session_state.get("access_token")
                email = st.session_state.user_email
                if token and email:
                    AUTHClient._save_session(token, email, "pro")

                logger.info(f"Upgrade para PRO: {email}")
                return True, response.json()["message"]

            return False, AUTHClient._handle_error(response)
        except Exception as e:
            logger.error(f"Erro no upgrade: {e}")
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
