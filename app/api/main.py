# app/api/main.py
"""
FastAPI Backend para LotoScience.
Serve APIs de autenticação, rate limiting e dados.
"""
import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.logger import logger
from app.api.routers.auth import router as auth_router

# Configurações de Ambiente
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DOMAIN_URL = os.getenv("DOMAIN_URL", "http://localhost:8501")

app = FastAPI(
    title="LotoScience API",
    description="Backend para análise de jogos de loteria",
    version="1.0.0",
    docs_url="/docs" if ENVIRONMENT == "development" else None,
    redoc_url=None,
)

# ===== CORS =====
allowed_origins = [
    "http://localhost:8501",
    "http://127.0.0.1:8501",
    DOMAIN_URL,
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# ===== MIDDLEWARE DE LOGGING =====
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"📨 {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"✅ {response.status_code} - {request.url.path}")
    return response


# ===== ROTAS =====
app.include_router(auth_router)


@app.get("/")
def root():
    return {"app": "LotoScience API", "status": "online", "env": ENVIRONMENT}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# ===== ERROR HANDLERS =====
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    logger.warning(f"404 Not Found: {request.url}")
    return JSONResponse(status_code=404, content={"detail": "Rota não encontrada"})


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"500 Internal Error: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor"})
