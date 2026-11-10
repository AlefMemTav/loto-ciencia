# app/core/statistics/popularidade_medida.py
"""
Popularidade MEDIDA dos números, a partir dos ganhadores reais de cada concurso.

Ideia: o número de ganhadores de uma faixa baixa (ex.: quadra da Mega-Sena)
depende de quão populares eram, entre os apostadores, os números sorteados.
Como o sorteio é aleatório, os números sorteados são independentes do volume de
apostas, então dá para estimar o peso de cada número por regressão:

    log(ganhadores / arrecadado) ~ números sorteados + controles

O modelo prevê, para um jogo qualquer, quantos ganhadores a faixa teria se
aquele jogo fosse o sorteado. Mede RISCO DE DIVIDIR O PRÊMIO, não chance de acerto.

O modelo só é usado se passar numa validação cruzada temporal (ganho sobre um
modelo só com os controles). Sem dados em data/detalhes/ ou sem ganho
comprovado, devolve None e o sistema funciona sem ele.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

SLUG_PARA_API = {
    "mega_sena_sorteio": "megasena",
    "quina_sorteio": "quina",
    "loto_facil_sorteio": "lotofacil",
    "loto_mania_sorteio": "lotomania",
}

PASTA_DETALHES = os.path.join("data", "detalhes")
MIN_CONCURSOS = 300
MEDIANA_MIN_GANHADORES = 300  # para o ruído de contagem (Poisson) ficar pequeno
R2_MINIMO = 0.02
# Corte de popularidade: só nos jogos em que o modelo explica bem os ganhadores
# (R2 de CV: Quina ~0,51, Mega ~0,18). Valor = razão de ganhadores prevista
# (1,0 = jogo médio) que deixa de fora os 90% de jogos mais populares dentro da
# faixa estrutural 5-95 (medido em 100 mil bilhetes aleatórios por jogo).
# Lotofácil (R2 ~0,022) e Lotomania (reprovada) ficam sem corte.
LIMIAR_RAZAO_GANHADORES = {
    "mega_sena_sorteio": 0.75,
    "quina_sorteio": 0.80,
}
LAMBDAS = (1.0, 10.0, 100.0, 1000.0)
N_AMOSTRAS_NULO = 4000
N_BLOCOS_CV = 6


def carregar_detalhes(config, pasta: str = PASTA_DETALHES) -> pd.DataFrame | None:
    """Lê data/detalhes/<loteria>_detalhes.csv (indexado por Concurso) ou None."""
    chave = SLUG_PARA_API.get(config.slug)
    if chave is None:
        return None
    caminho = os.path.join(pasta, f"{chave}_detalhes.csv")
    if not os.path.exists(caminho):
        return None
    try:
        det = pd.read_csv(caminho)
    except Exception:
        return None
    if "Concurso" not in det.columns:
        return None
    det = det.dropna(subset=["Concurso"]).copy()
    det["Concurso"] = det["Concurso"].astype(int)
    return det.drop_duplicates("Concurso").set_index("Concurso").sort_index()


def _escolher_faixa(det: pd.DataFrame) -> int | None:
    """Faixa de maior prêmio cuja mediana de ganhadores seja alta o bastante."""
    faixas = []
    for c in det.columns:
        if c.startswith("faixa") and c.endswith("_ganhadores"):
            faixas.append(int(c[5 : c.index("_")]))
    for f in sorted(faixas):
        mediana = pd.to_numeric(det[f"faixa{f}_ganhadores"], errors="coerce").median()
        if pd.notna(mediana) and mediana >= MEDIANA_MIN_GANHADORES:
            return f
    return None


def _ridge(x: np.ndarray, y: np.ndarray, lam: float, n_penalizados: int) -> np.ndarray:
    """Ridge com intercepto livre; penaliza só as primeiras `n_penalizados` colunas."""
    xi = np.column_stack([np.ones(len(x)), x])
    pen = np.zeros(xi.shape[1])
    pen[1 : 1 + n_penalizados] = lam
    return np.linalg.solve(xi.T @ xi + np.diag(pen), xi.T @ y)


def _prever(x: np.ndarray, beta: np.ndarray) -> np.ndarray:
    return beta[0] + x @ beta[1:]


@dataclass
class ModeloPopularidade:
    faixa: int
    n_concursos: int
    r2_cv: float
    lam: float
    pesos: np.ndarray  # por número (índice 0 = número 1), centrado na média
    k: int
    n_numeros: int
    media_nula: float = 0.0
    _nulos: dict = field(repr=False, default_factory=dict)

    def _nulo(self, m: int) -> np.ndarray:
        if m not in self._nulos:
            rng = np.random.default_rng(1000 + m)
            amostras = np.array(
                [
                    rng.choice(self.n_numeros, size=m, replace=False)
                    for _ in range(N_AMOSTRAS_NULO // 2)
                ]
            )
            self._nulos[m] = np.sort(self.pesos[amostras].mean(axis=1))
        return self._nulos[m]

    def percentil_batch(self, candidatos: np.ndarray) -> np.ndarray:
        """Percentil (0-100) de popularidade de cada jogo frente a jogos aleatórios."""
        candidatos = np.asarray(candidatos)
        if candidatos.size == 0:
            return np.array([], dtype=float)
        valores = self.pesos[candidatos - 1].mean(axis=1)
        nulo = self._nulo(candidatos.shape[1])
        return 100.0 * np.searchsorted(nulo, valores, side="right") / len(nulo)

    def razao_ganhadores_batch(self, candidatos: np.ndarray) -> np.ndarray:
        """Razão de ganhadores prevista de cada jogo (1,0 = jogo médio)."""
        candidatos = np.asarray(candidatos)
        if candidatos.size == 0:
            return np.array([], dtype=float)
        return np.exp(self.pesos[candidatos - 1].sum(axis=1))

    def avaliar(self, numeros) -> dict:
        """Popularidade de um jogo: percentil e razão de ganhadores vs. jogo médio."""
        numeros = sorted(numeros)
        percentil = float(self.percentil_batch(np.array([numeros]))[0])
        razao = None
        if len(numeros) == self.k:
            # soma dos pesos (efeito na escala log dos ganhadores) - média nula
            delta = float(self.pesos[np.array(numeros) - 1].sum())
            razao = float(np.exp(delta))
        return {"percentil": percentil, "razao_ganhadores": razao}


def treinar_modelo_popularidade(
    df: pd.DataFrame, detalhes: pd.DataFrame | None, config
) -> ModeloPopularidade | None:
    """
    Ajusta o modelo com os concursos presentes em `df` E em `detalhes`
    (só usa o que está no df, então não vaza o futuro em backtests).
    Devolve None se não houver dados suficientes ou se a validação cruzada
    temporal não mostrar ganho real sobre o modelo só com controles.
    """
    if df is None or df.empty or detalhes is None or detalhes.empty:
        return None

    idx = df.index.intersection(detalhes.index)
    if len(idx) < MIN_CONCURSOS:
        return None
    idx = idx.sort_values()
    det = detalhes.loc[idx]
    sorteios = df.loc[idx, config.draw_cols].to_numpy()

    faixa = _escolher_faixa(det)
    if faixa is None:
        return None

    if "valorArrecadado" not in det.columns:
        return None
    ganhadores = pd.to_numeric(det[f"faixa{faixa}_ganhadores"], errors="coerce")
    arrecadado = pd.to_numeric(det["valorArrecadado"], errors="coerce")
    ok = (ganhadores.notna() & arrecadado.notna() & (arrecadado > 0)).to_numpy()
    if ok.sum() < MIN_CONCURSOS:
        return None

    ganhadores = ganhadores.to_numpy()[ok]
    arrecadado = arrecadado.to_numpy()[ok]
    sorteios = sorteios[ok]
    t = len(ganhadores)
    n = config.n_numbers

    y = np.log((ganhadores + 0.5) / arrecadado * 1e6)

    # controles (reduzem ruído; os números sorteados são independentes deles)
    log_arr = np.log(arrecadado)
    tempo = np.arange(t, dtype=float)
    controles = np.column_stack(
        [
            (log_arr - log_arr.mean()) / (log_arr.std() or 1.0),
            (tempo - tempo.mean()) / (tempo.std() or 1.0),
        ]
    )
    x_num = np.zeros((t, n))
    x_num[np.repeat(np.arange(t), config.k), (sorteios - 1).ravel()] = 1.0
    x = np.column_stack([x_num, controles])

    # validação cruzada temporal (janela expansiva): ganho sobre só-controles
    limites = np.linspace(0, t, N_BLOCOS_CV + 1).astype(int)
    melhor = None
    for lam in LAMBDAS:
        sse_modelo = sse_base = 0.0
        folds_melhor = 0
        folds = 0
        for f in range(1, N_BLOCOS_CV):
            tr = slice(0, limites[f])
            te = slice(limites[f], limites[f + 1])
            beta = _ridge(x[tr], y[tr], lam, n)
            beta_base = _ridge(controles[tr], y[tr], 0.0, 0)
            e_mod = ((y[te] - _prever(x[te], beta)) ** 2).sum()
            e_base = ((y[te] - _prever(controles[te], beta_base)) ** 2).sum()
            sse_modelo += e_mod
            sse_base += e_base
            folds += 1
            folds_melhor += int(e_mod < e_base)
        r2 = 1.0 - sse_modelo / sse_base if sse_base > 0 else 0.0
        if melhor is None or r2 > melhor[0]:
            melhor = (r2, lam, folds_melhor, folds)

    r2, lam, folds_melhor, folds = melhor
    if r2 < R2_MINIMO or folds_melhor <= folds // 2:
        return None

    beta = _ridge(x, y, lam, n)
    pesos = beta[1 : 1 + n]
    pesos = pesos - pesos.mean()
    return ModeloPopularidade(
        faixa=faixa,
        n_concursos=t,
        r2_cv=float(r2),
        lam=float(lam),
        pesos=pesos,
        k=config.k,
        n_numeros=n,
    )
