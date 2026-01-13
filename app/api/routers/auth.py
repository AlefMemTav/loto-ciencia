# app/api/routers/auth.py
from fastapi import APIRouter, HTTPException, Header, Depends
from app.core.security import decode_token
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


@router.post("/login")
def login(user: UserLogin):
    db_user = auth_service.get_user_by_email(user.email)
    if not db_user or not verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(401, "Credenciais inválidas")

    token = create_access_token(
        {"sub": db_user["email"], "plan": db_user["plan"], "user_id": db_user["id"]}
    )

    return {
        "message": "Login realizado!",
        "access_token": token,
        "token_type": "bearer",
        "user": {"email": db_user["email"], "plan": db_user["plan"]},
    }


@router.post("/register", status_code=201)
def register(user: UserRegister):
    if len(user.password) < 6:
        raise HTTPException(400, "Senha muito curta")
    if auth_service.get_user_by_email(user.email):
        raise HTTPException(400, "E-mail já cadastrado")

    new_user = auth_service.create_user(user.email, hash_password(user.password))
    token = create_access_token({"sub": user.email, "plan": "free"})

    return {
        "message": "Conta criada!",
        "access_token": token,
        "token_type": "bearer",
        "user": new_user,
    }


def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Token ausente ou inválido")

    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)

    if not payload or not payload.get("sub"):
        raise HTTPException(401, "Token inválido ou expirado")

    return payload


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
def check_rate_limit(resource: str, user: dict = Depends(get_current_user)):
    if resource not in SERVER_LIMITS:
        raise HTTPException(400, "Recurso inválido")

    if user["plan"] == "pro":
        return {"allowed": True, "message": "✅ PRO: Ilimitado", "usage": 0, "limit": 0}

    limit = SERVER_LIMITS[resource]
    if limit == 0:
        return {
            "allowed": False,
            "message": "👑 Recurso exclusivo PRO",
            "usage": 0,
            "limit": 0,
        }

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

    if user["plan"] == "pro":
        return {"allowed": True, "message": "✅ PRO: Ilimitado", "usage": 0, "limit": 0}

    auth_service.register_usage(user["sub"], resource)
    usage_count = auth_service.get_usage_count(user["sub"], resource)
    limit = SERVER_LIMITS[resource]

    return {
        "allowed": True,
        "message": "✅ Uso registrado",
        "usage": usage_count,
        "limit": limit,
    }


@router.post("/upgrade")
def upgrade(user: dict = Depends(get_current_user)):
    auth_service.upgrade_user(user["sub"])
    return {"message": "Upgrade para PRO realizado!", "plan": "pro"}
