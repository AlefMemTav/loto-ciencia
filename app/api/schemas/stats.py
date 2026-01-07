# app/api/schemas/stats.py
from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class PoissonFinalItem(BaseModel):
    digito: int
    observado: int
    esperado: float
    desvio: float
    tipo: str
    p_value: float
    interpretacao: str


class Chi2Out(BaseModel):
    chi2_stat: float
    p_chi: float
    ks_stat: float
    p_ks: float
    status: str
    confianca: str
    n_amostras: int


class IntervaloConfiancaOut(BaseModel):
    media: float
    mediana: float
    desvio: float
    ic_50: List[float]
    ic_80: List[float]
    ic_95: List[float]
    min_historico: int
    max_historico: int


class CoefVariacaoOut(BaseModel):
    coeficiente_variacao: float
    interpretacao: str
    freq_max: int
    freq_min: int
    amplitude: int


class AtrasosItem(BaseModel):
    numero: int
    atraso: int


class FrequenciaItem(BaseModel):
    numero: int
    frequencia: int


class InteligenciaItem(BaseModel):
    numero: int
    Frequencia: int
    Atraso: int
    Z_Freq: float
    Z_Gap: float
    Peso_Composto: float
    Peso_Geracao: float
    Percentil_Freq: Optional[float] = None
    Percentil_Gap: Optional[float] = None
