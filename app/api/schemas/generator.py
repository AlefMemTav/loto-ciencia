# app/api/schemas/generator.py
from pydantic import BaseModel
from typing import List, Optional, Literal, Any, Dict

Strategy = Literal["balanceada", "conservadora", "agressiva", "pura"]


class GenerateRequest(BaseModel):
    quantidade: int = 1
    estrategia: Strategy = "balanceada"
    garantir_diversidade: bool = True
    numeros_fixos: Optional[List[int]] = None
    numeros_evitados: Optional[List[int]] = None


class GeneratedGame(BaseModel):
    numbers: List[int]
    validation: Optional[Dict[str, Any]] = None  # opcional: valida junto


class GenerateResponse(BaseModel):
    games: List[GeneratedGame]
    meta: Dict[str, Any]
