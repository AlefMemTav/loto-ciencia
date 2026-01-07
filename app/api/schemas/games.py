# app/api/schemas/games.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class GameSummary(BaseModel):
    slug: str
    name: str


class BoardLayoutOut(BaseModel):
    rows: int
    cols: int
    n_numbers: int


class GameConfigOut(BaseModel):
    slug: str
    name: str
    n_numbers: int
    k: int
    bet_size: int
    odds_text: str
    game_price: float
    how_to_play: str
    layout: BoardLayoutOut


class ContextOut(BaseModel):
    slug: str
    total_concursos: int
    ultimo_concurso: int
    freq_top: List[Dict[str, Any]]  # ex.: [{"numero": 10, "freq": 120}, ...]
    poisson_finais: List[Dict[str, Any]]  # lista já sai pronta do core
