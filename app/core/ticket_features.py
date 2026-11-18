"""
Métricas compartilhadas de bilhetes.

Este módulo não decide se um jogo é "bom" ou "ruim". Ele só extrai sinais
objetivos que podem ser usados pelo gerador e pelo validador sem acoplar
geração ao score final do validador.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
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
    moldura: int = 0
    cruz: int = 0
    xis: int = 0
    cantos: int = 0
    diag_principal: int = 0
    diag_secundaria: int = 0
    multiplos_5: int = 0
    finais_unicos: int = 0
    simetria_reflexao: int = 0
    std_linhas: float = 0.0
    gap_regularidade: float = 0.0


@lru_cache(maxsize=16)
def _layout_masks(n_numbers: int, rows: int, cols: int) -> dict[str, np.ndarray] | None:
    if n_numbers <= 0 or rows <= 0 or cols <= 0:
        return None
    size = n_numbers + 1
    moldura = np.zeros(size, dtype=bool)
    cruz = np.zeros(size, dtype=bool)
    xis = np.zeros(size, dtype=bool)
    cantos = np.zeros(size, dtype=bool)
    diag_principal = np.zeros(size, dtype=bool)
    diag_secundaria = np.zeros(size, dtype=bool)

    center_r = {rows // 2} if rows % 2 != 0 else {rows // 2 - 1, rows // 2}
    center_c = {cols // 2} if cols % 2 != 0 else {cols // 2 - 1, cols // 2}
    corners = {(0, 0), (0, cols - 1), (rows - 1, 0), (rows - 1, cols - 1)}
    sq_lim = min(rows, cols)

    for n in range(1, n_numbers + 1):
        idx = n - 1
        r = idx // cols
        c = idx % cols
        if r in (0, rows - 1) or c in (0, cols - 1):
            moldura[n] = True
        if r in center_r or c in center_c:
            cruz[n] = True
        dp = r == c and r < sq_lim
        ds = (r + c) == (cols - 1)
        if dp:
            diag_principal[n] = True
        if ds:
            diag_secundaria[n] = True
        if dp or ds:
            xis[n] = True
        if (r, c) in corners:
            cantos[n] = True

    return {
        "moldura": moldura,
        "cruz": cruz,
        "xis": xis,
        "cantos": cantos,
        "diag_principal": diag_principal,
        "diag_secundaria": diag_secundaria,
    }


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
    finais_counts = Counter(finais)
    max_final = max(finais_counts.values()) if finais else 0
    finais_unicos = len(finais_counts)
    meio = config.n_numbers // 2
    superior = sum(1 for n in nums if n <= meio)
    inferior = k - superior
    span = nums[-1] - nums[0] if k >= 2 else 0
    span_rel = span / max(1, config.n_numbers - 1)
    sortudos = {7, 3, 13, 21, 33, 11, 27, 9}

    gap_counts = Counter(gaps)
    max_freq_gap = max(gap_counts.values()) if gap_counts else 0
    gap_regularidade = (max_freq_gap / len(gaps)) if gaps else 0.0

    # Índice simples e barato: quanto menor, mais o jogo parece uma fórmula.
    # Ele não substitui o índice completo do validador.
    entropy_norm = _entropy(gaps) / math.log2(max(2, len(gaps))) if gaps else 0.0
    gap_variety = len(gap_counts) / max(1, len(gaps))
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

    n_num = int(config.n_numbers)
    nums_set = {n for n in nums if 1 <= n <= n_num}
    simetria_reflexao = sum(
        1 for n in nums_set if (n_num + 1 - n) > n and (n_num + 1 - n) in nums_set
    )
    multiplos_5 = sum(1 for n in nums if n % 5 == 0)

    layout = config.layout
    masks = (
        _layout_masks(n_num, layout.rows, layout.cols)
        if layout and layout.rows > 0 and layout.cols > 0
        else None
    )
    if masks is not None:
        valid_nums = [n for n in nums if 1 <= n <= n_num]
        moldura = sum(1 for n in valid_nums if masks["moldura"][n])
        cruz = sum(1 for n in valid_nums if masks["cruz"][n])
        xis = sum(1 for n in valid_nums if masks["xis"][n])
        cantos = sum(1 for n in valid_nums if masks["cantos"][n])
        diag_principal = sum(1 for n in valid_nums if masks["diag_principal"][n])
        diag_secundaria = sum(1 for n in valid_nums if masks["diag_secundaria"][n])

        row_counts = np.zeros(layout.rows, dtype=float)
        for n in valid_nums:
            r = (n - 1) // layout.cols
            if 0 <= r < layout.rows:
                row_counts[r] += 1.0
        std_linhas = float(row_counts.std())
    else:
        moldura = 0
        cruz = 0
        xis = 0
        cantos = 0
        diag_principal = 0
        diag_secundaria = 0
        std_linhas = 0.0

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
        unique_gaps=len(gap_counts),
        entropia_gaps=_entropy(gaps),
        superior=superior,
        inferior=inferior,
        qtd_sortudos=len(set(nums) & sortudos),
        compressibilidade_simples=round(compressibilidade, 4),
        moldura=moldura,
        cruz=cruz,
        xis=xis,
        cantos=cantos,
        diag_principal=diag_principal,
        diag_secundaria=diag_secundaria,
        multiplos_5=multiplos_5,
        finais_unicos=finais_unicos,
        simetria_reflexao=simetria_reflexao,
        std_linhas=std_linhas,
        gap_regularidade=gap_regularidade,
    )


def _bucket_counts_batch(values: np.ndarray, n_bins: int) -> np.ndarray | None:
    m = len(values)
    if m == 0 or values.shape[1] == 0:
        return np.zeros((m, max(1, n_bins)), dtype=np.int64)
    if n_bins > 0 and int(values.min()) >= 0 and int(values.max()) < n_bins:
        offsets = np.arange(m, dtype=np.int64)[:, None] * n_bins
        flat = (values.astype(np.int64, copy=False) + offsets).ravel()
        return np.bincount(flat, minlength=m * n_bins).reshape(m, n_bins)
    return None


def _max_bucket_count_batch(values: np.ndarray, n_bins: int) -> np.ndarray:
    m = len(values)
    if m == 0 or values.shape[1] == 0:
        return np.zeros(m, dtype=float)
    counts = _bucket_counts_batch(values, n_bins)
    if counts is not None:
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

        max_freq_gap = np.zeros(m, dtype=float)
        if len(run_lengths) > 0:
            np.maximum.at(max_freq_gap, run_rows, run_lengths.astype(float))
        gap_regularidade = max_freq_gap / float(g)

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
        gap_regularidade = np.zeros(m, dtype=float)
        max_sequencia = np.ones(m, dtype=float) if k >= 1 else np.zeros(m, dtype=float)

    finais = arr % 10
    finais_counts = _bucket_counts_batch(finais, 10)
    if finais_counts is not None:
        max_final_repetido = finais_counts.max(axis=1).astype(float)
        finais_unicos = (finais_counts > 0).sum(axis=1).astype(float)
    else:
        max_final_repetido = _max_bucket_count_batch(finais, 10)
        finais_unicos = np.array([len(np.unique(row)) for row in finais], dtype=float)

    n_num = int(config.n_numbers)
    meio = n_num // 2
    superior = (arr <= meio).sum(axis=1).astype(float)
    inferior = k - superior
    multiplos_5 = (arr % 5 == 0).sum(axis=1).astype(float)

    half = n_num // 2
    if half > 0:
        valid_mask = (arr >= 1) & (arr <= n_num)
        occ = np.zeros((m, n_num), dtype=bool)
        if np.all(valid_mask):
            occ[np.arange(m)[:, None], arr - 1] = True
        else:
            rows_v, cols_v = np.nonzero(valid_mask)
            occ[rows_v, arr[rows_v, cols_v] - 1] = True
        simetria_reflexao = (
            occ[:, :half] & occ[:, n_num - half :][:, ::-1]
        ).sum(axis=1).astype(float)
    else:
        simetria_reflexao = np.zeros(m, dtype=float)

    faixa = ((arr - 1) // 10).astype(int)
    n_dezenas_bins = max(1, (n_num + 9) // 10)
    max_dezena_repetida = _max_bucket_count_batch(faixa, n_dezenas_bins)

    layout = config.layout
    masks = (
        _layout_masks(n_num, layout.rows, layout.cols)
        if layout and layout.rows > 0 and layout.cols > 0
        else None
    )
    if masks is not None:
        rows = ((arr - 1) // layout.cols).astype(int)
        cols = ((arr - 1) % layout.cols).astype(int)
        row_counts = _bucket_counts_batch(rows, layout.rows)
        if row_counts is not None:
            max_linha = row_counts.max(axis=1).astype(float)
            std_linhas = row_counts.std(axis=1).astype(float)
        else:
            max_linha = _max_bucket_count_batch(rows, layout.rows)
            std_linhas = np.zeros(m, dtype=float)
        max_coluna = _max_bucket_count_batch(cols, layout.cols)
        quad_ids = (rows >= (layout.rows // 2)).astype(int) * 2 + (
            cols >= (layout.cols // 2)
        ).astype(int)
        max_quadrante = _max_bucket_count_batch(quad_ids, 4)

        valid_mask_geo = (arr >= 1) & (arr <= n_num)
        arr_clipped = np.where(valid_mask_geo, arr, 0)
        moldura = masks["moldura"][arr_clipped].sum(axis=1).astype(float)
        cruz = masks["cruz"][arr_clipped].sum(axis=1).astype(float)
        xis = masks["xis"][arr_clipped].sum(axis=1).astype(float)
        cantos = masks["cantos"][arr_clipped].sum(axis=1).astype(float)
        diag_principal = masks["diag_principal"][arr_clipped].sum(axis=1).astype(float)
        diag_secundaria = masks["diag_secundaria"][arr_clipped].sum(axis=1).astype(float)
    else:
        max_linha = np.zeros(m, dtype=float)
        std_linhas = np.zeros(m, dtype=float)
        max_coluna = np.zeros(m, dtype=float)
        max_quadrante = np.zeros(m, dtype=float)
        moldura = np.zeros(m, dtype=float)
        cruz = np.zeros(m, dtype=float)
        xis = np.zeros(m, dtype=float)
        cantos = np.zeros(m, dtype=float)
        diag_principal = np.zeros(m, dtype=float)
        diag_secundaria = np.zeros(m, dtype=float)

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
        "gap_regularidade": gap_regularidade,
        "entropia_gaps": entropia_gaps,
        "max_sequencia": max_sequencia,
        "max_final_repetido": max_final_repetido,
        "finais_unicos": finais_unicos,
        "superior": superior,
        "inferior": inferior,
        "max_dezena_repetida": max_dezena_repetida,
        "max_linha": max_linha,
        "std_linhas": std_linhas,
        "max_coluna": max_coluna,
        "max_quadrante": max_quadrante,
        "moldura": moldura,
        "cruz": cruz,
        "xis": xis,
        "cantos": cantos,
        "diag_principal": diag_principal,
        "diag_secundaria": diag_secundaria,
        "multiplos_5": multiplos_5,
        "simetria_reflexao": simetria_reflexao,
        "compressibilidade_simples": compressibilidade,
    }
