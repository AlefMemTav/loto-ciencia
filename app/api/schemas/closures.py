# app/api/schemas/closures.py
from pydantic import BaseModel
from typing import List, Any, Dict, Union


class ClosuresRequest(BaseModel):
    numeros_base: List[int]
    max_combinacoes: int = 1000


class ClosuresResponse(BaseModel):
    games: List[List[int]]
