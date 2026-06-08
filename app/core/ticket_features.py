"""
Métricas compartilhadas de bilhetes.

Este módulo não decide se um jogo é "bom" ou "ruim". Ele só extrai sinais
objetivos que podem ser usados pelo gerador e pelo validador sem acoplar
geração ao score final do validador.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
from typing import Iterable

import numpy as np

from app.core.lottery import GameConfig


@dataclass(frozen=True)
class TicketFeatures:
    numbers: list[int]
    soma: int
    pares: int
    impares: int
    span: int
    span_relativo: float
    sequencias: int
    max_sequencia: int
    max_final_repetido: int
    unique_gaps: int
    entropia_gaps: float
    superior: int
    inferior: int
    qtd_sortudos: int
    compressibilidade_simples: float


def _entropy(values: Iterable[int]) -> float:
    vals = list(values)
    if not vals:
        return 0.0

    counts = Counter(vals)
    total = len(vals)
    entropy = 0.0
    for count in counts.values():
        p = count / total
        entropy -= p * math.log2(p)
    return entropy


def extract_ticket_features(numbers: list[int], config: GameConfig) -> TicketFeatures:
    nums = sorted(numbers)
    k = len(nums)
    gaps = [nums[i + 1] - nums[i] for i in range(k - 1)] if k >= 2 else []

    max_seq = 1 if k else 0
    current_seq = 1
    for gap in gaps:
        if gap == 1:
            current_seq += 1
            max_seq = max(max_seq, current_seq)
        else:
            current_seq = 1

    finais = [n % 10 for n in nums]
    max_final = max(Counter(finais).values()) if finais else 0
    meio = config.n_numbers // 2
    superior = sum(1 for n in nums if n <= meio)
    inferior = k - superior
    span = nums[-1] - nums[0] if k >= 2 else 0
    span_rel = span / max(1, config.n_numbers - 1)
    sortudos = {7, 3, 13, 21, 33, 11, 27, 9}

    # Índice simples e barato: quanto menor, mais o jogo parece uma fórmula.
    # Ele não substitui o índice completo do validador.
    entropy_norm = _entropy(gaps) / math.log2(max(2, len(gaps))) if gaps else 0.0
    gap_variety = len(set(gaps)) / max(1, len(gaps))
    seq_penalty = min(1.0, max(0, max_seq - 2) / max(1, k - 2))
    final_penalty = min(1.0, max(0, max_final - 2) / max(1, k - 2))
    compressibilidade = max(
        0.0,
        min(
            1.0,
            (entropy_norm * 0.55)
            + (gap_variety * 0.35)
            - seq_penalty * 0.2
            - final_penalty * 0.1,
        ),
    )

    return TicketFeatures(
        numbers=nums,
        soma=sum(nums),
        pares=sum(1 for n in nums if n % 2 == 0),
        impares=sum(1 for n in nums if n % 2 != 0),
        span=span,
        span_relativo=span_rel,
        sequencias=sum(1 for gap in gaps if gap == 1),
        max_sequencia=max_seq,
        max_final_repetido=max_final,
        unique_gaps=len(set(gaps)),
        entropia_gaps=_entropy(gaps),
        superior=superior,
        inferior=inferior,
        qtd_sortudos=len(set(nums) & sortudos),
        compressibilidade_simples=round(compressibilidade, 4),
    )


def extract_ticket_features_batch(
    candidates: np.ndarray, config: GameConfig
) -> dict[str, np.ndarray]:
    """Extrai métricas vetorizadas para muitos jogos já ordenados."""
    if len(candidates) == 0:
        return {}

    arr = np.asarray(candidates, dtype=int)
    k = arr.shape[1]
    gaps = np.diff(arr, axis=1) if k >= 2 else np.empty((len(arr), 0), dtype=int)

    soma = arr.sum(axis=1).astype(float)
    pares = (arr % 2 == 0).sum(axis=1).astype(float)
    span = (arr[:, -1] - arr[:, 0]).astype(float) if k >= 2 else np.zeros(len(arr))

    if gaps.shape[1] > 0:
        min_gap = gaps.min(axis=1).astype(float)
        max_gap = gaps.max(axis=1).astype(float)
        gap_medio = gaps.mean(axis=1).astype(float)
        unique_gaps = np.array([len(np.unique(row)) for row in gaps], dtype=float)
        gap_variety = unique_gaps / max(1, gaps.shape[1])
        entropia_gaps = np.array([_entropy(row.tolist()) for row in gaps], dtype=float)
        max_sequencia = np.ones(len(arr), dtype=float)
        for i, row in enumerate(gaps):
            run = 1
            best = 1
            for gap in row:
                if gap == 1:
                    run += 1
                    best = max(best, run)
                else:
                    run = 1
            max_sequencia[i] = best
    else:
        min_gap = np.zeros(len(arr), dtype=float)
        max_gap = np.zeros(len(arr), dtype=float)
        gap_medio = np.zeros(len(arr), dtype=float)
        gap_variety = np.zeros(len(arr), dtype=float)
        entropia_gaps = np.zeros(len(arr), dtype=float)
        max_sequencia = np.zeros(len(arr), dtype=float)

    finais = arr % 10
    max_final_repetido = np.array(
        [np.unique(row, return_counts=True)[1].max() for row in finais],
        dtype=float,
    )

    meio = config.n_numbers // 2
    superior = (arr <= meio).sum(axis=1).astype(float)
    inferior = k - superior

    faixa = np.ceil(arr / 10).astype(int)
    max_dezena_repetida = np.array(
        [np.unique(row, return_counts=True)[1].max() for row in faixa],
        dtype=float,
    )

    layout = config.layout
    if layout and layout.rows > 0 and layout.cols > 0:
        rows = ((arr - 1) // layout.cols).astype(int)
        cols = ((arr - 1) % layout.cols).astype(int)
        max_linha = np.array(
            [np.unique(row, return_counts=True)[1].max() for row in rows],
            dtype=float,
        )
        max_coluna = np.array(
            [np.unique(row, return_counts=True)[1].max() for row in cols],
            dtype=float,
        )
        quad_ids = (rows >= (layout.rows // 2)).astype(int) * 2 + (
            cols >= (layout.cols // 2)
        ).astype(int)
        max_quadrante = np.array(
            [np.unique(row, return_counts=True)[1].max() for row in quad_ids],
            dtype=float,
        )
    else:
        max_linha = np.zeros(len(arr), dtype=float)
        max_coluna = np.zeros(len(arr), dtype=float)
        max_quadrante = np.zeros(len(arr), dtype=float)

    entropy_norm = np.divide(
        entropia_gaps,
        math.log2(max(2, max(1, k - 1))),
        out=np.zeros_like(entropia_gaps),
        where=True,
    )
    seq_penalty = np.minimum(1.0, np.maximum(0.0, max_sequencia - 2) / max(1, k - 2))
    final_penalty = np.minimum(
        1.0, np.maximum(0.0, max_final_repetido - 2) / max(1, k - 2)
    )
    compressibilidade = np.clip(
        (entropy_norm * 0.55)
        + (gap_variety * 0.35)
        - seq_penalty * 0.2
        - final_penalty * 0.1,
        0.0,
        1.0,
    )

    return {
        "soma": soma,
        "pares": pares,
        "span": span,
        "min_gap": min_gap,
        "max_gap": max_gap,
        "gap_medio": gap_medio,
        "gap_variety": gap_variety,
        "entropia_gaps": entropia_gaps,
        "max_sequencia": max_sequencia,
        "max_final_repetido": max_final_repetido,
        "superior": superior,
        "inferior": inferior,
        "max_dezena_repetida": max_dezena_repetida,
        "max_linha": max_linha,
        "max_coluna": max_coluna,
        "max_quadrante": max_quadrante,
        "compressibilidade_simples": compressibilidade,
    }
