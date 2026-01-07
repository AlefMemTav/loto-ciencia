# app/api/schemas/validator.py
from pydantic import BaseModel, conlist
from typing import Any, Dict, List


class ValidateRequest(BaseModel):
    numbers: conlist(int, min_length=1)


class ValidateResponse(BaseModel):
    score: int
    status: str
    risco_divisao: str
    ja_saiu: bool
    msgs: List[str]
    metricas: Dict[str, Any]
