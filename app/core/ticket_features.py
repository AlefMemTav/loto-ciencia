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


def _max_bucket_count_batch(values: np.ndarray, n_bins: int) -> np.ndarray:
    m = len(values)
    if m == 0 or values.shape[1] == 0:
        return np.zeros(m, dtype=float)
    if int(values.min()) >= 0 and int(values.max()) < n_bins:
        offsets = np.arange(m, dtype=np.int64)[:, None] * n_bins
        flat = (values.astype(np.int64, copy=False) + offsets).ravel()
        counts = np.bincount(flat, minlength=m * n_bins).reshape(m, n_bins)
        return counts.max(axis=1).astype(float)
    return np.array(
        [np.unique(row, return_counts=True)[1].max() for row in values],
        dtype=float,
    )


def extract_ticket_features_batch(
    candidates: np.ndarray, config: GameConfig
) -> dict[str, np.ndarray]:
    """Extrai métricas vetorizadas para muitos jogos já ordenados."""
    if len(candidates) == 0:
        return {}

    arr = np.asarray(candidates, dtype=int)
    m, k = arr.shape
    gaps = np.diff(arr, axis=1) if k >= 2 else np.empty((m, 0), dtype=int)

    soma = arr.sum(axis=1).astype(float)
    pares = (arr % 2 == 0).sum(axis=1).astype(float)
    span = (arr[:, -1] - arr[:, 0]).astype(float) if k >= 2 else np.zeros(m, dtype=float)

    g = gaps.shape[1]
    if g > 0:
        min_gap = gaps.min(axis=1).astype(float)
        max_gap = gaps.max(axis=1).astype(float)
        gap_medio = gaps.mean(axis=1).astype(float)

        sorted_gaps = np.sort(gaps, axis=1)
        run_starts_mask = np.ones((m, g), dtype=bool)
        if g > 1:
            run_starts_mask[:, 1:] = sorted_gaps[:, 1:] != sorted_gaps[:, :-1]
        unique_gaps = run_starts_mask.sum(axis=1).astype(float)
        gap_variety = unique_gaps / max(1, g)

        flat_starts = np.flatnonzero(run_starts_mask.ravel())
        run_lengths = np.diff(np.append(flat_starts, m * g))
        run_rows = flat_starts // g
        probs = run_lengths.astype(float) / float(g)
        entropia_gaps = np.bincount(
            run_rows,
            weights=-probs * np.log2(probs),
            minlength=m,
        ).astype(float)

        padded = np.zeros((m, g + 2), dtype=np.int8)
        padded[:, 1:-1] = (gaps == 1)
        transitions = np.diff(padded, axis=1)
        seq_starts = np.flatnonzero(transitions.ravel() == 1)
        seq_ends = np.flatnonzero(transitions.ravel() == -1)
        max_sequencia = np.ones(m, dtype=float)
        if len(seq_starts) > 0:
            np.maximum.at(
                max_sequencia,
                seq_starts // (g + 1),
                1.0 + (seq_ends - seq_starts).astype(float),
            )
    else:
        min_gap = np.zeros(m, dtype=float)
        max_gap = np.zeros(m, dtype=float)
        gap_medio = np.zeros(m, dtype=float)
        gap_variety = np.zeros(m, dtype=float)
        entropia_gaps = np.zeros(m, dtype=float)
        max_sequencia = np.ones(m, dtype=float) if k >= 1 else np.zeros(m, dtype=float)

    finais = arr % 10
    max_final_repetido = _max_bucket_count_batch(finais, 10)

    meio = config.n_numbers // 2
    superior = (arr <= meio).sum(axis=1).astype(float)
    inferior = k - superior

    faixa = ((arr - 1) // 10).astype(int)
    n_dezenas_bins = max(1, (config.n_numbers + 9) // 10)
    max_dezena_repetida = _max_bucket_count_batch(faixa, n_dezenas_bins)

    layout = config.layout
    if layout and layout.rows > 0 and layout.cols > 0:
        rows = ((arr - 1) // layout.cols).astype(int)
        cols = ((arr - 1) % layout.cols).astype(int)
        max_linha = _max_bucket_count_batch(rows, layout.rows)
        max_coluna = _max_bucket_count_batch(cols, layout.cols)
        quad_ids = (rows >= (layout.rows // 2)).astype(int) * 2 + (
            cols >= (layout.cols // 2)
        ).astype(int)
        max_quadrante = _max_bucket_count_batch(quad_ids, 4)
    else:
        max_linha = np.zeros(m, dtype=float)
        max_coluna = np.zeros(m, dtype=float)
        max_quadrante = np.zeros(m, dtype=float)

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
