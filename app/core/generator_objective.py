"""
Objetivo próprio do gerador.

O gerador usa esta função para priorizar jogos plausíveis e diversos sem
chamar o validador nem perseguir o score exibido ao usuário.
"""

from __future__ import annotations

import numpy as np

from app.core.ticket_features import extract_ticket_features_batch
from app.core.statistics.feature_percentiles import batch_feature_percentiles


def score_plausibility_batch(
    candidates: np.ndarray,
    ctx,
    estrategia: str = "balanceada",
    percentil_min: float = 5.0,
    percentil_max: float = 95.0,
    null_model_samples: int | None = None,
    usar_quentes: bool = True,
    usar_atrasados: bool = True,
    usar_coocorrencia: bool = True,
    historical_signal_strength: float = 1.0,
) -> np.ndarray:
    """
    Score vetorial de plausibilidade para candidatos já ordenados.

    Maior é melhor. O score combina sinais suaves e independentes do validador:
    aderência a distribuições esperadas, baixa compressibilidade, baixa
    popularidade humana e uso controlado de sinais históricos.
    """
    if len(candidates) == 0:
        return np.array([], dtype=float)

    config = ctx.config
    n = config.n_numbers
    k = candidates.shape[1]
    usar_historico = estrategia != "pura"

    scores = np.zeros(len(candidates), dtype=float)
    features, percentiles, _model = batch_feature_percentiles(
        candidates,
        config,
        n_samples=null_model_samples,
    )

    central_weights = {
        "soma": 1.8,
        "pares": 1.3,
        "span": 1.4,
        "gap_medio": 1.0,
        "gap_variety": 0.8,
        "entropia_gaps": 0.8,
        "max_quadrante": 0.7,
    }
    high_bad_weights = {
        "max_final_repetido": 1.0,
        "max_dezena_repetida": 0.8,
        "max_linha": 0.8,
        "max_coluna": 0.7,
        "max_sequencia": 1.4,
    }
    low_bad_weights = {
        "min_gap": 1.1,
        "compressibilidade_simples": 1.7,
    }

    def _central_score(pct: np.ndarray, weight: float) -> np.ndarray:
        center = 1.0 - np.abs(pct - 50.0) / 50.0
        outside_low = np.maximum(0.0, percentil_min - pct) / max(1.0, percentil_min)
        outside_high = np.maximum(0.0, pct - percentil_max) / max(
            1.0, 100.0 - percentil_max
        )
        return (center * weight) - ((outside_low + outside_high) * weight * 1.8)

    for metric, weight in central_weights.items():
        pct = percentiles.get(metric)
        if pct is not None:
            scores += _central_score(pct, weight)

    for metric, weight in high_bad_weights.items():
        pct = percentiles.get(metric)
        if pct is not None:
            scores -= np.maximum(0.0, pct - percentil_max) * weight / 5.0

    for metric, weight in low_bad_weights.items():
        pct = percentiles.get(metric)
        if pct is not None:
            scores -= np.maximum(0.0, percentil_min - pct) * weight / 5.0

    lucky = np.array([3, 7, 9, 11, 13, 21, 27, 33])
    lucky = lucky[lucky <= n]
    if len(lucky) > 0:
        lucky_count = np.isin(candidates, lucky).sum(axis=1)
        scores[lucky_count >= max(4, int(candidates.shape[1] * 0.35))] -= 1.5

    indices = candidates - 1
    if usar_historico:
        historical_signal_strength = float(np.clip(historical_signal_strength, 0.0, 2.0))
        # Sinais históricos controlados: úteis para intenção de acerto, mas capados.
        tabela = getattr(ctx, "tabela", None)
        if tabela is not None and not getattr(tabela, "empty", True):
            z_freq = np.nan_to_num(tabela["Z_Freq"].to_numpy(dtype=float), nan=0.0)
            z_gap = np.nan_to_num(tabela["Z_Gap"].to_numpy(dtype=float), nan=0.0)
            if len(z_freq) >= n and len(z_gap) >= n:
                if usar_quentes:
                    freq_signal = np.clip(z_freq[:n][indices].mean(axis=1), -2.0, 2.0)
                    scores += freq_signal * 0.30 * historical_signal_strength
                if usar_atrasados:
                    gap_signal = np.clip(z_gap[:n][indices].mean(axis=1), -2.0, 2.0)
                    scores += gap_signal * 0.22 * historical_signal_strength

        matriz = getattr(ctx, "matriz_coocorrencia", None)
        if (
            usar_coocorrencia
            and matriz is not None
            and hasattr(matriz, "shape")
            and matriz.shape == (n, n)
        ):
            from app.core.generator_fast import _calcular_scores_coocorrencia_batch

            cooc = _calcular_scores_coocorrencia_batch(indices, matriz)
            std = cooc.std()
            cooc_z = np.zeros_like(cooc) if std < 1e-9 else (cooc - cooc.mean()) / std
            scores += np.clip(cooc_z, -1.5, 1.5) * 0.35 * historical_signal_strength

    historico = getattr(ctx, "historico_set", None) or set()
    if k == config.k and historico:
        for i, row in enumerate(candidates):
            if tuple(row.tolist()) in historico:
                scores[i] = -np.inf

    return np.nan_to_num(scores, nan=-1e9, neginf=-1e9, posinf=1e9)


def select_diverse_portfolio(
    candidates: np.ndarray,
    scores: np.ndarray,
    config,
    quantidade: int,
    rng: np.random.Generator | None = None,
    estrategia: str = "balanceada",
) -> list[list[int]]:
    """Seleciona os melhores candidatos preservando diversidade do portfólio."""
    if rng is None:
        rng = np.random.default_rng()

    if len(candidates) == 0:
        return []

    finite_mask = np.isfinite(scores)
    candidates = candidates[finite_mask]
    scores = scores[finite_mask]
    if len(candidates) == 0:
        return []

    noise_scale = {
        "conservadora": 0.55,
        "balanceada": 0.85,
        "agressiva": 1.00,
        "pura": 1.40,
    }.get(estrategia, 0.85)
    adjusted_scores = scores + rng.gumbel(0.0, noise_scale, size=len(scores))
    order = np.argsort(adjusted_scores)[::-1]
    ordered = candidates[order]

    selected: list[np.ndarray] = []
    seen: set[tuple[int, ...]] = set()
    exposure: dict[int, int] = {}
    feature_exposure: dict[tuple, int] = {}
    overlap_limit = config.get_overlap_limit()
    expected_exposure = quantidade * config.bet_size / max(1, config.n_numbers)
    if config.is_sparse:
        exposure_limit = max(1, int(np.ceil(expected_exposure * 2.5)))
    else:
        exposure_limit = max(2, int(np.ceil(expected_exposure * 1.5)))

    def _fits_exposure(row: np.ndarray, limit: int) -> bool:
        return all(exposure.get(int(n), 0) < limit for n in row)

    feature_values = extract_ticket_features_batch(ordered, config)

    def _feature_key(idx: int) -> tuple:
        return (
            int(feature_values["soma"][idx] // 15),
            int(feature_values["pares"][idx]),
            int(feature_values["span"][idx] // 8),
            int(feature_values["gap_medio"][idx] // 3),
        )

    def _fits_feature_exposure(idx: int, limit: int) -> bool:
        return feature_exposure.get(_feature_key(idx), 0) < limit

    def _add(row: np.ndarray) -> None:
        selected.append(row.copy())
        seen.add(tuple(row.tolist()))
        for n in row:
            nn = int(n)
            exposure[nn] = exposure.get(nn, 0) + 1

    for idx, row in enumerate(ordered):
        if len(selected) >= quantidade:
            break
        t = tuple(row.tolist())
        if t in seen:
            continue
        if not _fits_exposure(row, exposure_limit):
            continue
        if not _fits_feature_exposure(idx, 1):
            continue
        s = set(t)
        if all(
            len(s.intersection(set(prev.tolist()))) <= overlap_limit
            for prev in selected
        ):
            _add(row)
            key = _feature_key(idx)
            feature_exposure[key] = feature_exposure.get(key, 0) + 1

    # Se restrições/fixos tornarem a diversidade impossível, completa com os mais
    # plausíveis ainda únicos. Isso evita falhar quando muitos números são fixados.
    if len(selected) < quantidade:
        relaxed_limit = exposure_limit + 1
        for idx, row in enumerate(ordered):
            if len(selected) >= quantidade:
                break
            t = tuple(row.tolist())
            if t in seen:
                continue
            if not _fits_exposure(row, relaxed_limit):
                continue
            if not _fits_feature_exposure(idx, 2):
                continue
            _add(row)
            key = _feature_key(idx)
            feature_exposure[key] = feature_exposure.get(key, 0) + 1

    if len(selected) < quantidade:
        for row in ordered:
            if len(selected) >= quantidade:
                break
            t = tuple(row.tolist())
            if t in seen:
                continue
            _add(row)

    return [row.tolist() for row in selected[:quantidade]]
