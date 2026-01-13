# app/ui/services/auth_client.py
import requests
import streamlit as st
from typing import Optional, Tuple
import os
import json
from pathlib import Path
import hashlib
import uuid
from app.core.logger import logger


try:
    from streamlit_cookies_controller import CookieController

    controller = CookieController()
    COOKIES_AVAILABLE = True
except ImportError:
    logger.warning(
        "streamlit-cookies-controller não instalado - sessão não persistirá após F5"
    )
    COOKIES_AVAILABLE = False
    controller = None


API_BASE_URL = os.getenv("API_URL", "http://localhost:8000")


import tempfile


def _get_sessions_dir() -> Path:
    """
    Retorna diretório de sessões baseado no ambiente:
    - Desenvolvimento: tempdir (limpo automaticamente)
    - Docker/Produção: /app/data/sessions (persistente)
    """
    if os.getenv("ENVIRONMENT") == "production":
        sessions_dir = Path("/app/data/sessions")
    else:
        sessions_dir = Path(tempfile.gettempdir()) / ".lotoscience_sessions"

    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir


SESSIONS_DIR = _get_sessions_dir()


def _get_browser_id() -> str:
    """
    ✅ Retorna ID único do navegador com isolamento correto.
    - Cookie persiste após F5
    - Session ID diferencia abas do mesmo navegador
    """
    # 1. Verifica se já calculamos nesta execução
    if "browser_id" in st.session_state:
        return st.session_state.browser_id

    # 2. Pega session_id do Streamlit (diferente para cada aba)
    streamlit_session_id = None
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        ctx = get_script_run_ctx()
        if ctx and ctx.session_id:
            streamlit_session_id = ctx.session_id
    except:
        pass

    # 3. Tenta ler cookie do navegador (persiste após F5)
    cookie_id = None
    if COOKIES_AVAILABLE:
        try:
            cookie_id = controller.get("lotoscience_browser_id")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao ler cookie: {e}")

    # 4. Se NÃO tem cookie, cria um novo UUID e salva
    if not cookie_id:
        cookie_id = str(uuid.uuid4())
        if COOKIES_AVAILABLE:
            try:
                controller.set("lotoscience_browser_id", cookie_id)
                logger.info(f"🆕 Novo cookie criado: {cookie_id[:8]}...")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao salvar cookie: {e}")

    # 5. Combina cookie (persistente) + session_id (diferencia abas)
    if streamlit_session_id:
        # Para abas diferentes do MESMO navegador
        browser_id = f"{cookie_id}_{streamlit_session_id}"
        logger.debug(
            f"🔗 Browser ID: cookie {cookie_id[:8]}... + session {streamlit_session_id[:8]}..."
        )
    else:
        # Fallback: só o cookie
        browser_id = cookie_id
        logger.debug(f"🍪 Browser ID: {cookie_id[:8]}...")

    st.session_state.browser_id = browser_id
    return browser_id


def _get_session_file() -> Path:
    """
    ✅ Retorna arquivo baseado APENAS no cookie (não no session_id).
    Isso permite que o F5 encontre o mesmo arquivo.
    """
    browser_id = _get_browser_id()

    # ✅ CRÍTICO: Extrai apenas a parte do cookie (antes do "_")
    cookie_part = browser_id.split("_")[0]  # Pega só "abc123" de "abc123_xyz789"

    # Hash para nome de arquivo seguro
    filename = hashlib.md5(cookie_part.encode()).hexdigest()
    filepath = SESSIONS_DIR / f"{filename}.json"
    logger.debug(f"📁 Session file: {filepath.name} (cookie: {cookie_part[:8]}...)")
    return filepath


class AUTHClient:
    """Cliente para API LotoScience com persistência real após F5"""

    LIMITS = {
        "validator": 3,
        "generator": 1,
        "closures": 0,
        "bolao": 0,
    }

    @staticmethod
    def _save_session(token: str, email: str, plan: str):
        """Salva sessão em arquivo baseado no browser_id"""
        try:
            session_file = _get_session_file()
            session_file.write_text(
                json.dumps({"access_token": token, "email": email, "plan": plan})
            )
            logger.info(f"✅ Sessão salva: {email} -> {session_file.name}")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar sessão: {e}")

    @staticmethod
    def _load_session() -> Optional[dict]:
        """Carrega sessão do arquivo baseado no browser_id"""
        try:
            session_file = _get_session_file()
            if session_file.exists():
                data = json.loads(session_file.read_text())
                logger.debug(
                    f"✅ Sessão carregada: {data.get('email')} <- {session_file.name}"
                )
                return data
            else:
                logger.debug(f"ℹ️ Arquivo de sessão não existe: {session_file.name}")
        except Exception as e:
            logger.error(f"❌ Erro ao carregar sessão: {e}")
        return None

    @staticmethod
    def _delete_session():
        """Remove arquivo de sessão"""
        try:
            session_file = _get_session_file()
            if session_file.exists():
                session_file.unlink()
                logger.info(f"🗑️ Sessão removida: {session_file.name}")
        except Exception as e:
            logger.error(f"❌ Erro ao deletar sessão: {e}")

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
        # 1️⃣ Já está autenticado (navegação interna)
        if st.session_state.get("authenticated", False):
            logger.debug("✅ Já autenticado via session_state")
            return True

        # 2️⃣ Tenta carregar do arquivo persistente (baseado em browser_id)
        browser_id = _get_browser_id()
        logger.debug(
            f"🔍 Tentando restaurar sessão para browser_id: {browser_id[:8]}..."
        )

        saved = AUTHClient._load_session()

        if saved and saved.get("access_token"):
            token = saved["access_token"]
            logger.debug(f"✅ Token recuperado: {token[:20]}...")

            # Valida token com backend
            try:
                response = requests.get(
                    f"{API_BASE_URL}/auth/me",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=5,
                )

                if response.status_code == 200:
                    data = response.json()

                    # ✅ Restaura session_state
                    st.session_state.access_token = token
                    st.session_state.authenticated = True
                    st.session_state.user_email = data["email"]
                    st.session_state.user_plan = data["plan"]

                    logger.info(f"✅✅ Sessão restaurada após F5: {data['email']}")
                    return True
                else:
                    logger.warning(f"❌ Token inválido: HTTP {response.status_code}")
                    AUTHClient._delete_session()

            except Exception as e:
                logger.error(f"❌ Erro ao validar token: {e}")
                AUTHClient._delete_session()
        else:
            logger.debug("ℹ️ Nenhuma sessão salva encontrada")

        return False

    @staticmethod
    def _clear_session_state():
        """Limpa estado de autenticação"""
        st.session_state.authenticated = False
        st.session_state.user_email = None
        st.session_state.user_plan = None
        st.session_state.access_token = None
        AUTHClient._delete_session()
        logger.info("🧹 Session state e arquivo limpos")

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

                # ✅ Salva em arquivo (persiste após F5)
                AUTHClient._save_session(
                    token, data["user"]["email"], data["user"]["plan"]
                )

                logger.info(f"📝 Registro bem-sucedido: {data['user']['email']}")
                return True, data["message"], data

            return False, AUTHClient._handle_error(response), None
        except Exception as e:
            logger.error(f"❌ Erro no registro: {e}")
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

                # ✅ Salva em arquivo (persiste após F5)
                AUTHClient._save_session(
                    token, data["user"]["email"], data["user"]["plan"]
                )

                logger.info(f"🔐 Login bem-sucedido: {data['user']['email']}")
                return True, data["message"], data

            return False, response.json().get("detail", "Erro de login"), None
        except Exception as e:
            logger.error(f"❌ Erro no login: {e}")
            return False, f"Erro de conexão: {e}", None

    @staticmethod
    def logout():
        email = st.session_state.get("user_email", "desconhecido")
        logger.info(f"🚪 Logout: {email}")
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
            logger.error(f"❌ Erro ao verificar rate limit: {e}")
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
            logger.error(f"❌ Erro ao marcar recurso: {e}")
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
