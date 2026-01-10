# app/api/schemas/auth.py
from pydantic import BaseModel, EmailStr
from typing import Optional


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
