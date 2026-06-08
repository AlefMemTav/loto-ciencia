"""Percentis combinatórios de métricas de bilhetes."""

from __future__ import annotations

import numpy as np

from app.core.lottery import GameConfig
from app.core.ticket_features import (
    extract_ticket_features,
    extract_ticket_features_batch,
)
from app.core.statistics.null_model import get_null_model


PRIMARY_PERCENTILE_METRICS = [
    "soma",
    "pares",
    "span",
    "min_gap",
    "gap_medio",
    "gap_variety",
    "entropia_gaps",
    "max_final_repetido",
    "max_dezena_repetida",
    "max_linha",
    "max_coluna",
    "max_quadrante",
    "compressibilidade_simples",
]


def batch_feature_percentiles(
    candidates: np.ndarray,
    config: GameConfig,
    n_samples: int | None = None,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], object]:
    features = extract_ticket_features_batch(candidates, config)
    model = get_null_model(config, n_samples=n_samples)
    percentiles = {
        metric: model.percentiles(metric, values)
        for metric, values in features.items()
        if metric in model.metrics
    }
    return features, percentiles, model


def summarize_feature_percentiles(
    numbers: list[int],
    config: GameConfig,
    n_samples: int | None = None,
    rare_low: float = 5.0,
    rare_high: float = 95.0,
) -> dict:
    features = extract_ticket_features(numbers, config)
    model = get_null_model(config, n_samples=n_samples)

    values = {
        "soma": features.soma,
        "pares": features.pares,
        "span": features.span,
        "min_gap": 0 if len(features.numbers) < 2 else min(np.diff(features.numbers)),
        "gap_medio": 0
        if len(features.numbers) < 2
        else float(np.mean(np.diff(features.numbers))),
        "gap_variety": features.unique_gaps / max(1, len(features.numbers) - 1),
        "entropia_gaps": features.entropia_gaps,
        "max_final_repetido": features.max_final_repetido,
        "compressibilidade_simples": features.compressibilidade_simples,
    }

    percentis = {}
    caudas = {}
    for metric, value in values.items():
        pct = model.percentile(metric, float(value))
        if pct is None:
            continue
        percentis[metric] = pct
        if pct <= rare_low:
            caudas[metric] = "baixa"
        elif pct >= rare_high:
            caudas[metric] = "alta"

    return {
        "percentis_combinatorios": percentis,
        "caudas_raras": caudas,
        "modelo_nulo_version": model.version,
        "n_amostras_modelo_nulo": model.n_samples,
    }
