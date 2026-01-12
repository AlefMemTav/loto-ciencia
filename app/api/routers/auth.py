# app/api/routers/auth.py
from fastapi import APIRouter, HTTPException, Query, Response, Request, Depends
from datetime import datetime

# Novos Imports
from app.api.schemas.auth import UserRegister, UserLogin, UserResponse, RateLimitCheck
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    COOKIE_SETTINGS,
)
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

SERVER_LIMITS = {
    "validator": 3,
    "generator": 1,
    "closures": 0,
    "bolao": 0,
}


# Dependency para pegar usuário do cookie
def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(401, "Não autenticado")

    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(401, "Token inválido")
    return payload


# ===== ROTAS =====


@router.post("/register", status_code=201)
def register(user: UserRegister, response: Response):
    if len(user.password) < 6:
        raise HTTPException(400, "Senha muito curta")

    if auth_service.get_user_by_email(user.email):
        raise HTTPException(400, "E-mail já cadastrado")

    new_user = auth_service.create_user(user.email, hash_password(user.password))

    token = create_access_token({"sub": user.email, "plan": "free"})
    response.set_cookie(key="access_token", value=token, **COOKIE_SETTINGS)

    return {"message": "Conta criada!", "user": new_user}


@router.post("/login")
def login(user: UserLogin, response: Response):
    db_user = auth_service.get_user_by_email(user.email)

    if not db_user or not verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(401, "Credenciais inválidas")

    token = create_access_token(
        {"sub": db_user["email"], "plan": db_user["plan"], "user_id": db_user["id"]}
    )
    response.set_cookie(key="access_token", value=token, **COOKIE_SETTINGS)

    return {
        "message": "Login realizado!",
        "user": {"email": db_user["email"], "plan": db_user["plan"]},
    }


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logout realizado"}


@router.get("/me", response_model=UserResponse)
def get_profile(user: dict = Depends(get_current_user)):
    db_user = auth_service.get_user_by_email(user["sub"])
    if not db_user:
        raise HTTPException(404, "Usuário não encontrado")
    return {
        "email": db_user["email"],
        "plan": db_user["plan"],
        "created_at": db_user["created_at"],
    }


@router.get("/check_limit", response_model=RateLimitCheck)
def check_rate_limit(
    resource: str = Query(
        ..., description="Recurso a verificar (validator, generator)"
    ),
    user: dict = Depends(get_current_user),
):
    """
    Verifica limites e retorna contagem atual.
    Usado pela UI para mostrar 'X de Y usos restantes'.
    """
    if resource not in SERVER_LIMITS:
        raise HTTPException(400, "Recurso inválido")

    # 1. Usuário PRO: Ilimitado
    if user["plan"] == "pro":
        return {
            "allowed": True,
            "message": "✅ PRO: Ilimitado",
            "usage": 0,  # Uso não conta para Pro
        }

    # 2. Usuário Free
    limit = SERVER_LIMITS[resource]

    # Se limite é 0, é feature exclusiva Pro
    if limit == 0:
        return {"allowed": False, "message": "👑 Recurso exclusivo PRO", "usage": 0}

    # Busca quantos usos ele já fez hoje
    # (Precisamos adicionar esse método no AuthService, veja abaixo)
    usage_count = auth_service.get_usage_count(user["sub"], resource)

    is_allowed = usage_count < limit

    return {
        "allowed": is_allowed,
        "message": "✅ Uso autorizado" if is_allowed else "⛔ Limite diário atingido",
        "usage": usage_count,
        "limit": limit,
    }


@router.post("/use-resource/{resource}", response_model=RateLimitCheck)
def use_resource(resource: str, user: dict = Depends(get_current_user)):
    if resource not in SERVER_LIMITS:
        raise HTTPException(400, "Recurso inválido")

    # Se for PRO, retorna padrão
    if user["plan"] == "pro":
        return {"allowed": True, "message": "✅ PRO: Ilimitado", "usage": 0, "limit": 0}

    # 1. Registra o uso no banco
    auth_service.register_usage(user["sub"], resource)

    # 2. Busca os dados atualizados para retornar ao frontend
    usage_count = auth_service.get_usage_count(user["sub"], resource)
    limit = SERVER_LIMITS[resource]

    return {
        "allowed": True,
        "message": "✅ Uso registrado",
        "usage": usage_count,  # Retorna o valor novo (ex: 1)
        "limit": limit,  # Retorna o limite (ex: 3)
    }


# Rota de Upgrade
@router.post("/upgrade")
def upgrade(user: dict = Depends(get_current_user)):
    auth_service.upgrade_user(user["sub"])
    return {"message": "Upgrade para PRO realizado!", "plan": "pro"}


# --- Guest Routes ---


@router.post("/check-rate-limit-guest/{resource}")
def check_guest(resource: str, req: dict):
    bid = req.get("browser_id")
    if not bid:
        return {"allowed": False, "message": "Browser ID required"}

    if auth_service.check_guest_usage(bid, resource):
        return {"allowed": True, "message": "✅ Modo Guest: 1 uso disponível"}
    return {"allowed": False, "message": "⛔ Limite guest atingido"}


@router.post("/use-resource-guest/{resource}")
def use_guest(resource: str, req: dict):
    bid = req.get("browser_id")
    if auth_service.register_guest_usage(bid, resource):
        return {"allowed": True, "message": "✅ Uso guest registrado"}
    return {"allowed": True, "message": "Uso já computado"}
