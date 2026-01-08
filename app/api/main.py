# app/api/main.py
"""
FastAPI Backend para LotoScience.
Serve APIs de autenticação, rate limiting e dados.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from app.api.auth import router as auth_router

# ===== CONFIGURAÇÃO =====
ENV = os.getenv("ENV", "development")
STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")

app = FastAPI(
    title="LotoScience API",
    description="Backend para análise de jogos de loteria",
    version="1.0.0",
    docs_url="/docs" if ENV == "development" else None,  # Desativa docs em prod
)

# ===== CORS (permite Streamlit acessar com cookies) =====
allowed_origins = [
    "http://localhost:8501",  # Streamlit local
    "http://127.0.0.1:8501",  # Streamlit local (alternativo)
    STREAMLIT_URL,  # Streamlit produção (variável de ambiente)
]

# Remove duplicatas e None
allowed_origins = list(set(filter(None, allowed_origins)))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,  # ✅ IMPORTANTE: permite enviar/receber cookies
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# ===== MIDDLEWARE DE LOGGING =====
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log de todas as requisições"""
    print(f"📨 {request.method} {request.url.path}")
    response = await call_next(request)
    print(f"✅ {response.status_code}")
    return response


# ===== ROTAS =====
app.include_router(auth_router)


@app.get("/")
def root():
    """Health check"""
    return {
        "message": "LotoScience API",
        "status": "running",
        "version": "1.0.0",
        "environment": ENV,
    }


@app.get("/health")
def health_check():
    """Health check para monitoramento"""
    return {"status": "healthy"}


# ===== ERROR HANDLERS =====
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={"detail": "Rota não encontrada"})


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor"})


# ===== STARTUP/SHUTDOWN =====
@app.on_event("startup")
async def startup_event():
    print("🚀 LotoScience API iniciada!")
    print(f"📍 Ambiente: {ENV}")
    print(f"🔒 CORS habilitado para: {allowed_origins}")


@app.on_event("shutdown")
async def shutdown_event():
    print("👋 LotoScience API encerrada!")
