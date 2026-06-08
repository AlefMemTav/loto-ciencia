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
    seed: Optional[int] = None
    temperatura: Optional[float] = None
    validar_resultado: bool = True
    usar_quentes: bool = True
    usar_atrasados: bool = True
    usar_markov: bool = True
    usar_ciclo: bool = True
    usar_coocorrencia: bool = True
    frequencia_recente: bool = True
    historical_signal_strength: float = 1.0
    percentil_min: float = 5.0
    percentil_max: float = 95.0
    null_model_samples: Optional[int] = None


class GeneratedGame(BaseModel):
    numbers: List[int]
    validation: Optional[Dict[str, Any]] = None  # opcional: valida junto


class GenerateResponse(BaseModel):
    games: List[GeneratedGame]
    meta: Dict[str, Any]
