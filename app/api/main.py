# app/api/main.py
from fastapi import FastAPI
from app.api.routers import games, stats, generator, validator, closures

app = FastAPI(title="LotoScience API", version="v1")
app.include_router(games.router, prefix="/v1")
app.include_router(stats.router, prefix="/v1")
app.include_router(generator.router, prefix="/v1")
app.include_router(validator.router, prefix="/v1")
app.include_router(closures.router, prefix="/v1")
