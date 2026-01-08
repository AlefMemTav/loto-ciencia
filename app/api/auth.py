# app/api/auth.py
"""
Sistema de autenticação completo com JWT, cookies HttpOnly seguros e rate limiting.
"""
from fastapi import APIRouter, HTTPException, Response, Request, Depends, status
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from typing import Optional
import jwt
import hashlib
import os
from pathlib import Path
import sqlite3
from datetime import timedelta, timezone

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ===== CONFIGURAÇÕES =====
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/users.db")
DB_PATH = Path("data/users.db")
DB_PATH.parent.mkdir(exist_ok=True)

# Configuração de cookies
COOKIE_SETTINGS = {
    "httponly": True,
    "secure": os.getenv("ENV", "development") == "production",
    "samesite": "lax",
    "max_age": 30 * 24 * 60 * 60,  # ✅ 30 dias em segundos
    "path": "/",
    "domain": None,  # ✅ Permite funcionar em localhost e produção
}


# ===== MODELS =====
class UserRegister(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    email: str
    plan: str
    created_at: str


class RateLimitCheck(BaseModel):
    allowed: bool
    message: str
    remaining_today: Optional[int] = None


# ===== DATABASE =====
def get_db_connection():
    """Retorna conexão SQLite"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Inicializa banco de dados"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            plan TEXT DEFAULT 'free',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            upgraded_at TIMESTAMP,
            validator_last_used DATE,
            generator_last_used DATE,
            validator_count_today INTEGER DEFAULT 0,
            generator_count_today INTEGER DEFAULT 0
        )
    """
    )

    # Usuário demo (Pro)
    demo_hash = hashlib.sha256("demo123".encode()).hexdigest()
    try:
        cursor.execute(
            "INSERT INTO users (email, password_hash, plan) VALUES (?, ?, ?)",
            ("demo@lotoscience.com", demo_hash, "pro"),
        )
    except:
        pass  # Já existe

    conn.commit()
    conn.close()


# Inicializa DB ao importar
init_db()


# ===== HELPERS =====
def hash_password(password: str) -> str:
    """Hash SHA-256 da senha"""
    return hashlib.sha256(password.encode()).hexdigest()


def create_access_token(data: dict) -> str:
    """Cria JWT token com expiração de 30 dias (timezone-aware UTC)"""

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def get_user_from_db(email: str) -> Optional[dict]:
    """Busca usuário no banco"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "email": row[1],
        "password_hash": row[2],
        "plan": row[3],
        "created_at": row[4],
        "upgraded_at": row[5],
        "validator_last_used": row[6],
        "generator_last_used": row[7],
        "validator_count_today": row[8] if len(row) > 8 else 0,
        "generator_count_today": row[9] if len(row) > 9 else 0,
    }


def get_current_user_from_cookie(request: Request) -> dict:
    """Dependency: extrai usuário do cookie JWT"""
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=401, detail="Não autenticado. Faça login primeiro."
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401, detail="Sessão expirada. Faça login novamente."
        )
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")


# ===== ROTAS PÚBLICAS =====


@router.post("/register", status_code=201)
def register(user: UserRegister, response: Response):
    """
    Registra novo usuário no plano FREE.
    Define cookie HttpOnly automaticamente.
    """
    # Valida senha
    if len(user.password) < 6:
        raise HTTPException(
            status_code=400, detail="Senha deve ter pelo menos 6 caracteres"
        )

    # Verifica se já existe
    existing = get_user_from_db(user.email)
    if existing:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    # Cria usuário
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (email, password_hash, plan) VALUES (?, ?, ?)",
        (user.email, hash_password(user.password), "free"),
    )
    conn.commit()
    conn.close()

    # Gera token JWT
    access_token = create_access_token(data={"sub": user.email, "plan": "free"})

    # ✅ Define cookie HttpOnly seguro
    response.set_cookie(key="access_token", value=access_token, **COOKIE_SETTINGS)

    return {
        "message": "Conta criada com sucesso!",
        "user": {
            "email": user.email,
            "plan": "free",
            "created_at": datetime.now().isoformat(),
        },
    }


@router.post("/login")
def login(user: UserLogin, response: Response):
    """
    Faz login e define cookie HttpOnly.
    Cookie é enviado automaticamente em todas as requisições.
    """
    db_user = get_user_from_db(user.email)

    if not db_user:
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")

    if db_user["password_hash"] != hash_password(user.password):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")

    # Gera token JWT
    access_token = create_access_token(
        data={
            "sub": db_user["email"],
            "plan": db_user["plan"],
            "user_id": db_user["id"],
        }
    )

    # ✅ Define cookie HttpOnly seguro
    response.set_cookie(key="access_token", value=access_token, **COOKIE_SETTINGS)

    return {
        "message": "Login realizado com sucesso!",
        "user": {
            "email": db_user["email"],
            "plan": db_user["plan"],
            "created_at": db_user["created_at"],
        },
    }


@router.post("/logout")
def logout(response: Response):
    """Remove cookie de autenticação"""
    response.delete_cookie(key="access_token", path="/")
    return {"message": "Logout realizado com sucesso"}


# ===== ROTAS PROTEGIDAS =====


@router.get("/me", response_model=UserResponse)
def get_profile(current_user: dict = Depends(get_current_user_from_cookie)):
    """Retorna perfil do usuário autenticado (via cookie)"""
    email = current_user["sub"]
    db_user = get_user_from_db(email)

    if not db_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    return {
        "email": db_user["email"],
        "plan": db_user["plan"],
        "created_at": db_user["created_at"],
    }


@router.post("/upgrade", status_code=200)
def upgrade_to_pro(current_user: dict = Depends(get_current_user_from_cookie)):
    """
    Upgrade para plano PRO.
    ⚠️ MVP: upgrade manual. Integre com Stripe em produção.
    """
    email = current_user["sub"]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET plan = 'pro', upgraded_at = ? WHERE email = ?",
        (datetime.now().isoformat(), email),
    )
    conn.commit()
    conn.close()

    return {
        "message": "Upgrade para PRO realizado com sucesso!",
        "plan": "pro",
    }


@router.post("/check-rate-limit/{resource}", response_model=RateLimitCheck)
def check_rate_limit(
    resource: str, current_user: dict = Depends(get_current_user_from_cookie)
):
    """
    ✅ APENAS VERIFICA se pode usar (NÃO marca como usado).
    - Free: 1 uso/dia
    - Pro: ilimitado
    """
    if resource not in ["validator", "generator"]:
        raise HTTPException(
            status_code=400, detail="Recurso inválido. Use 'validator' ou 'generator'"
        )

    email = current_user["sub"]
    plan = current_user["plan"]

    # Pro sempre pode
    if plan == "pro":
        return {
            "allowed": True,
            "message": "✅ Plano PRO: uso ilimitado",
            "remaining_today": None,
        }

    # Free: verifica limite diário (SEM MARCAR)
    db_user = get_user_from_db(email)
    today = datetime.now().date().isoformat()
    field_last_used = f"{resource}_last_used"
    last_used = db_user.get(field_last_used)

    # Se já usou hoje
    if last_used == today:
        return {
            "allowed": False,
            "message": "⛔ Limite diário atingido. Faça upgrade para PRO para uso ilimitado.",
            "remaining_today": 0,
        }

    # Ainda não usou hoje
    return {
        "allowed": True,
        "message": "✅ Você tem 1 uso disponível hoje (plano Free)",
        "remaining_today": 1,
    }


@router.post("/use-resource/{resource}", response_model=RateLimitCheck)
def use_resource(
    resource: str, current_user: dict = Depends(get_current_user_from_cookie)
):
    """
    ✅ MARCA como usado (chame isso APÓS o usuário realmente usar).
    """
    if resource not in ["validator", "generator"]:
        raise HTTPException(
            status_code=400, detail="Recurso inválido. Use 'validator' ou 'generator'"
        )

    email = current_user["sub"]
    plan = current_user["plan"]

    # Pro não precisa marcar (ilimitado)
    if plan == "pro":
        return {
            "allowed": True,
            "message": "✅ Plano PRO: uso ilimitado",
            "remaining_today": None,
        }

    # Free: marca como usado
    today = datetime.now().date().isoformat()
    field_last_used = f"{resource}_last_used"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE users SET {field_last_used} = ?, {resource}_count_today = 1 WHERE email = ?",
        (today, email),
    )
    conn.commit()
    conn.close()

    return {
        "allowed": True,
        "message": f"✅ Uso do {resource} registrado. Próximo uso disponível amanhã.",
        "remaining_today": 0,
    }


@router.delete("/account", status_code=204)
def delete_account(current_user: dict = Depends(get_current_user_from_cookie)):
    """Deleta conta do usuário (GDPR compliance)"""
    email = current_user["sub"]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE email = ?", (email,))
    conn.commit()
    conn.close()

    return None


@router.post("/check-rate-limit-guest/{resource}")
def check_rate_limit_guest(resource: str, request: dict):
    """
    Verifica rate limit para GUESTS (não autenticados).
    Usa browser_id para rastrear uso entre reloads.
    """
    if resource not in ["validator", "generator"]:
        raise HTTPException(
            status_code=400, detail="Recurso inválido. Use 'validator' ou 'generator'"
        )

    browser_id = request.get("browser_id", "unknown")

    if not browser_id or browser_id == "unknown":
        # Se não tem browser_id, bloqueia por segurança
        return {
            "allowed": False,
            "message": "⛔ Não foi possível identificar seu navegador. Por favor, recarregue a página.",
        }

    # Busca no banco se o guest já usou hoje
    conn = get_db_connection()
    cursor = conn.cursor()

    # Cria tabela de guests se não existir
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS guest_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            browser_id TEXT NOT NULL,
            resource TEXT NOT NULL,
            used_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(browser_id, resource, used_date)
        )
    """
    )
    conn.commit()

    today = datetime.now().date().isoformat()

    cursor.execute(
        "SELECT * FROM guest_usage WHERE browser_id = ? AND resource = ? AND used_date = ?",
        (browser_id, resource, today),
    )
    usage = cursor.fetchone()
    conn.close()

    if usage:
        return {
            "allowed": False,
            "message": f"⛔ Limite diário atingido (1/{resource} por dia). Crie uma conta para continuar.",
            "remaining_today": 0,
        }

    return {
        "allowed": True,
        "message": f"ℹ️ Modo Guest: você pode usar o {resource} 1x por dia. Crie uma conta gratuita!",
        "remaining_today": 1,
    }


@router.post("/use-resource-guest/{resource}")
def use_resource_guest(resource: str, request: dict):
    """
    Marca recurso como usado para GUEST.
    Salva no banco de dados para persistir entre reloads.
    """
    if resource not in ["validator", "generator"]:
        raise HTTPException(
            status_code=400, detail="Recurso inválido. Use 'validator' ou 'generator'"
        )

    browser_id = request.get("browser_id", "unknown")

    if not browser_id or browser_id == "unknown":
        return {
            "allowed": False,
            "message": "Erro ao registrar uso: browser_id inválido",
        }

    today = datetime.now().date().isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Insere ou ignora (UNIQUE constraint previne duplicatas)
    try:
        cursor.execute(
            """INSERT OR IGNORE INTO guest_usage (browser_id, resource, used_date) 
               VALUES (?, ?, ?)""",
            (browser_id, resource, today),
        )
        conn.commit()
        rows_affected = cursor.rowcount
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail=f"Erro ao registrar uso: {e}")

    conn.close()

    if rows_affected > 0:
        return {
            "allowed": True,
            "message": f"✅ Uso do {resource} registrado. Próximo uso disponível amanhã.",
            "remaining_today": 0,
        }
    else:
        # Já estava registrado
        return {
            "allowed": True,
            "message": f"Uso já estava registrado para hoje.",
            "remaining_today": 0,
        }


# OPCIONAL: Adicione uma rota de limpeza para remover registros antigos (rodar periodicamente)
@router.delete("/admin/cleanup-guest-usage", include_in_schema=False)
def cleanup_old_guest_usage(days_old: int = 7):
    """
    Remove registros de guest usage mais antigos que X dias.
    Evita crescimento infinito do banco.
    """

    cutoff_date = (datetime.now().date() - timedelta(days=days_old)).isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM guest_usage WHERE used_date < ?", (cutoff_date,))
    rows_deleted = cursor.rowcount
    conn.commit()
    conn.close()

    return {
        "message": f"Limpeza concluída: {rows_deleted} registros removidos.",
        "cutoff_date": cutoff_date,
    }


# ===== ROTAS ADMIN =====


@router.get("/admin/stats", include_in_schema=False)
def admin_stats():
    """Estatísticas gerais (adicione autenticação admin real em produção)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM users")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) as total FROM users WHERE plan = 'pro'")
    pro_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) as total FROM users WHERE plan = 'free'")
    free_users = cursor.fetchone()[0]

    conn.close()

    return {
        "total_users": total,
        "pro_users": pro_users,
        "free_users": free_users,
        "conversion_rate": round((pro_users / total * 100), 2) if total > 0 else 0,
    }
