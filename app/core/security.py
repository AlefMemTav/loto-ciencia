# app/core/security.py
import os
import jwt
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

# Configurações
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

COOKIE_SETTINGS = {
    "httponly": True,
    "secure": os.getenv("ENV", "development") == "production",
    "samesite": "lax",
    "max_age": 30 * 24 * 60 * 60,
    "path": "/",
    "domain": None,
}


def hash_password(password: str) -> str:
    """Hash SHA-256 da senha"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password


def create_access_token(data: dict) -> str:
    """Cria JWT token com expiração"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except (jwt.ExpiredSignatureError, jwt.JWTError):
        return None
