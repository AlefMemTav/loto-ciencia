"""Structural score calibration against history and the combinatorial null model."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

import numpy as np

from app.core.lottery import GameConfig
from app.core.statistics.feature_percentiles import batch_feature_percentiles


SCORE_CALIBRATION_VERSION = "score-cal-v1"
DEFAULT_SCORE_CALIBRATION_SAMPLES = int(
    os.getenv("LOTOSCIENCE_SCORE_CALIBRATION_SAMPLES", "50000")
)
DEFAULT_SCORE_CALIBRATION_SEED = 20260614
BUCKET_LABELS = ("0-39", "40-54", "55-69", "70-84", "85-100")
BUCKET_EDGES = np.array([40.0, 55.0, 70.0, 85.0], dtype=float)
_SMOOTHING = 0.01
_CACHE: dict[tuple, "ScoreCalibrationModel"] = {}


@dataclass(frozen=True)
class ScoreCalibrationModel:
    game_slug: str
    version: str
    n_history: int
    n_null: int
    target: str
    history_distribution: dict[str, float]
    null_distribution: dict[str, float]
    target_distribution: dict[str, float]

    @property
    def target_probabilities(self) -> np.ndarray:
        return np.array(
            [self.target_distribution[label] / 100.0 for label in BUCKET_LABELS],
            dtype=float,
        )


def _sample_uniform_games(
    rng: np.random.Generator,
    n_numbers: int,
    k: int,
    n_samples: int,
    batch_size: int = 8192,
) -> np.ndarray:
    chunks = []
    pool = np.arange(1, n_numbers + 1)
    remaining = int(n_samples)
    while remaining > 0:
        batch = min(batch_size, remaining)
        keys = rng.random((batch, n_numbers))
        idx = np.argpartition(keys, k - 1, axis=1)[:, :k]
        games = pool[idx]
        games.sort(axis=1)
        chunks.append(games)
        remaining -= batch
    return np.vstack(chunks) if chunks else np.empty((0, k), dtype=int)


def _history_games(df_historico: Any, config: GameConfig) -> np.ndarray:
    if config.bet_size != config.k:
        return np.empty((0, config.bet_size), dtype=int)
    if df_historico is None or getattr(df_historico, "empty", True):
        return np.empty((0, config.k), dtype=int)
    cols = [col for col in config.draw_cols if col in df_historico.columns]
    if len(cols) != config.k:
        return np.empty((0, config.k), dtype=int)
    values = df_historico[cols].dropna().to_numpy(dtype=int).copy()
    if values.ndim != 2 or values.shape[1] != config.k:
        return np.empty((0, config.k), dtype=int)
    values.sort(axis=1)
    return values


def _history_signature(df_historico: Any, config: GameConfig) -> tuple:
    games = _history_games(df_historico, config)
    if len(games) == 0:
        return ("empty", 0)
    return (
        int(len(games)),
        tuple(int(n) for n in games[0].tolist()),
        tuple(int(n) for n in games[-1].tolist()),
    )


def bucket_indices(scores: np.ndarray) -> np.ndarray:
    arr = np.asarray(scores, dtype=float)
    return np.digitize(arr, BUCKET_EDGES, right=False).astype(int)


def bucket_label(score: float) -> str:
    idx = int(np.digitize([float(score)], BUCKET_EDGES, right=False)[0])
    return BUCKET_LABELS[max(0, min(idx, len(BUCKET_LABELS) - 1))]


def distribution_from_scores(scores: np.ndarray, smoothing: float = _SMOOTHING) -> dict[str, float]:
    idx = bucket_indices(scores)
    counts = np.bincount(idx, minlength=len(BUCKET_LABELS)).astype(float)
    counts = counts[: len(BUCKET_LABELS)] + float(smoothing)
    probs = counts / max(float(counts.sum()), 1.0)
    return {
        label: round(float(prob * 100.0), 6)
        for label, prob in zip(BUCKET_LABELS, probs)
    }


def _dist_to_probs(dist: dict[str, float]) -> np.ndarray:
    values = np.array([float(dist.get(label, 0.0)) for label in BUCKET_LABELS])
    total = float(values.sum())
    if total <= 0:
        return np.full(len(BUCKET_LABELS), 1.0 / len(BUCKET_LABELS))
    return values / total


def _probs_to_dist(probs: np.ndarray) -> dict[str, float]:
    probs = np.asarray(probs, dtype=float)
    probs = probs / max(float(probs.sum()), 1e-12)
    return {
        label: round(float(prob * 100.0), 6)
        for label, prob in zip(BUCKET_LABELS, probs)
    }


def score_structural_batch(
    candidates: np.ndarray,
    config: GameConfig,
    n_samples: int | None = None,
) -> np.ndarray:
    """Return a validator-independent structural score in the 0-100 range."""
    arr = np.asarray(candidates, dtype=int)
    if arr.size == 0:
        return np.array([], dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    arr = np.sort(arr, axis=1)

    features, percentiles, _model = batch_feature_percentiles(
        arr,
        config,
        n_samples=n_samples,
    )
    return score_structural_from_percentiles(features, percentiles, len(arr))


def score_structural_from_percentiles(
    features: dict[str, np.ndarray],
    percentiles: dict[str, np.ndarray],
    n_rows: int | None = None,
) -> np.ndarray:
    """Compute structural score from precomputed feature percentiles."""
    if n_rows is None:
        first = next(iter(features.values()), np.array([], dtype=float))
        n_rows = len(first)
    if n_rows == 0:
        return np.array([], dtype=float)

    weighted = np.zeros(n_rows, dtype=float)
    total_weight = 0.0

    central_weights = {
        "soma": 1.6,
        "pares": 1.2,
        "span": 1.3,
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

    for metric, weight in central_weights.items():
        pct = percentiles.get(metric)
        if pct is None:
            continue
        quality = np.clip(1.0 - np.abs(pct - 50.0) / 50.0, 0.0, 1.0)
        weighted += quality * weight
        total_weight += weight

    for metric, weight in high_bad_weights.items():
        pct = percentiles.get(metric)
        if pct is None:
            continue
        quality = 1.0 - np.clip((pct - 75.0) / 25.0, 0.0, 1.0)
        weighted += quality * weight
        total_weight += weight

    for metric, weight in low_bad_weights.items():
        pct = percentiles.get(metric)
        if pct is None:
            continue
        quality = 1.0 - np.clip((25.0 - pct) / 25.0, 0.0, 1.0)
        weighted += quality * weight
        total_weight += weight

    if total_weight <= 0:
        return np.full(n_rows, 50.0, dtype=float)

    score = weighted / total_weight * 100.0
    max_seq = features.get("max_sequencia")
    max_final = features.get("max_final_repetido")
    if max_seq is not None:
        score -= np.maximum(0.0, max_seq - 3.0) * 10.0
    if max_final is not None:
        score -= np.maximum(0.0, max_final - 3.0) * 6.0
    return np.clip(np.nan_to_num(score, nan=0.0), 0.0, 100.0)


def score_structural_single(
    numbers: list[int],
    config: GameConfig,
    n_samples: int | None = None,
) -> float:
    arr = np.array([sorted(numbers)], dtype=int)
    return round(float(score_structural_batch(arr, config, n_samples=n_samples)[0]), 4)


def get_score_calibration_model(
    config: GameConfig,
    df_historico: Any = None,
    n_samples: int | None = None,
    target: str = "historico_nulo",
) -> ScoreCalibrationModel:
    n = int(n_samples or DEFAULT_SCORE_CALIBRATION_SAMPLES)
    target = target if target in {"historico_nulo", "historico", "nulo"} else "historico_nulo"
    history_sig = _history_signature(df_historico, config)
    key = (
        config.slug,
        config.n_numbers,
        config.bet_size,
        config.k,
        SCORE_CALIBRATION_VERSION,
        n,
        target,
        history_sig,
    )
    cached = _CACHE.get(key)
    if cached is not None:
        return cached

    history_games = _history_games(df_historico, config)
    history_scores = score_structural_batch(history_games, config, n_samples=n)

    slug_seed = sum((i + 1) * ord(ch) for i, ch in enumerate(config.slug))
    rng = np.random.default_rng(DEFAULT_SCORE_CALIBRATION_SEED + slug_seed + n)
    null_games = _sample_uniform_games(rng, config.n_numbers, config.bet_size, n)
    null_scores = score_structural_batch(null_games, config, n_samples=n)

    null_dist = distribution_from_scores(null_scores)
    history_dist = (
        distribution_from_scores(history_scores)
        if len(history_scores) > 0
        else dict(null_dist)
    )
    history_probs = _dist_to_probs(history_dist)
    null_probs = _dist_to_probs(null_dist)

    if target == "historico":
        target_probs = history_probs
    elif target == "nulo":
        target_probs = null_probs
    else:
        target_probs = (history_probs * 0.70) + (null_probs * 0.30)

    model = ScoreCalibrationModel(
        game_slug=config.slug,
        version=SCORE_CALIBRATION_VERSION,
        n_history=int(len(history_scores)),
        n_null=int(len(null_scores)),
        target=target,
        history_distribution=history_dist,
        null_distribution=null_dist,
        target_distribution=_probs_to_dist(target_probs),
    )
    _CACHE[key] = model
    return model


def calibration_prior_batch(
    candidates: np.ndarray,
    config: GameConfig,
    df_historico: Any = None,
    n_samples: int | None = None,
    target: str = "historico_nulo",
) -> dict[str, Any]:
    scores = score_structural_batch(candidates, config, n_samples=n_samples)
    buckets = bucket_indices(scores)
    model = get_score_calibration_model(
        config,
        df_historico=df_historico,
        n_samples=n_samples,
        target=target,
    )
    target_probs = np.clip(model.target_probabilities, 1e-6, 1.0)
    uniform = 1.0 / len(BUCKET_LABELS)
    prior = np.log(target_probs[buckets] / uniform)
    prior = np.clip(prior, -1.5, 1.5)
    return {
        "scores": scores,
        "bucket_indices": buckets,
        "bucket_labels": [BUCKET_LABELS[int(idx)] for idx in buckets],
        "prior": prior,
        "model": model,
        "target_probabilities": target_probs,
    }


def summarize_score_calibration(
    numbers: list[int],
    config: GameConfig,
    df_historico: Any = None,
    n_samples: int | None = None,
    target: str = "historico_nulo",
) -> dict[str, Any]:
    score = score_structural_single(numbers, config, n_samples=n_samples)
    label = bucket_label(score)
    model = get_score_calibration_model(
        config,
        df_historico=df_historico,
        n_samples=n_samples,
        target=target,
    )
    return {
        "score_estrutural": score,
        "bucket": label,
        "freq_historica": model.history_distribution.get(label, 0.0),
        "freq_modelo_nulo": model.null_distribution.get(label, 0.0),
        "freq_alvo": model.target_distribution.get(label, 0.0),
        "distribuicao_historica": model.history_distribution,
        "distribuicao_modelo_nulo": model.null_distribution,
        "distribuicao_alvo": model.target_distribution,
        "modelo_version": model.version,
        "n_historico": model.n_history,
        "n_amostras_modelo_nulo": model.n_null,
        "target": model.target,
    }


def jensen_shannon_divergence(pct_a: dict[str, float], pct_b: dict[str, float]) -> float:
    p = _dist_to_probs(pct_a)
    q = _dist_to_probs(pct_b)
    m = (p + q) / 2.0
    eps = 1e-12
    kl_pm = np.sum(np.where(p > 0, p * np.log2((p + eps) / (m + eps)), 0.0))
    kl_qm = np.sum(np.where(q > 0, q * np.log2((q + eps) / (m + eps)), 0.0))
    return round(float((kl_pm + kl_qm) / 2.0), 6)


def chi_square_distance(pct_obs: dict[str, float], pct_exp: dict[str, float]) -> float:
    obs = _dist_to_probs(pct_obs)
    exp = np.clip(_dist_to_probs(pct_exp), 1e-9, 1.0)
    return round(float(np.sum(((obs - exp) ** 2) / exp)), 6)


def score_calibration_diagnostics(
    games: list[list[int]] | np.ndarray,
    config: GameConfig,
    df_historico: Any = None,
    n_samples: int | None = None,
    target: str = "historico_nulo",
) -> dict[str, Any]:
    arr = np.asarray(games, dtype=int)
    if arr.size == 0:
        return {}
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    arr.sort(axis=1)
    scores = score_structural_batch(arr, config, n_samples=n_samples)
    generated_dist = distribution_from_scores(scores, smoothing=0.0)
    model = get_score_calibration_model(
        config,
        df_historico=df_historico,
        n_samples=n_samples,
        target=target,
    )
    return {
        "score_medio": round(float(np.mean(scores)), 6),
        "score_min": round(float(np.min(scores)), 6),
        "score_max": round(float(np.max(scores)), 6),
        "distribuicao_gerada": generated_dist,
        "distribuicao_historica": model.history_distribution,
        "distribuicao_modelo_nulo": model.null_distribution,
        "distribuicao_alvo": model.target_distribution,
        "js_vs_alvo": jensen_shannon_divergence(generated_dist, model.target_distribution),
        "js_vs_historico": jensen_shannon_divergence(generated_dist, model.history_distribution),
        "js_vs_nulo": jensen_shannon_divergence(generated_dist, model.null_distribution),
        "chi_square_vs_alvo": chi_square_distance(generated_dist, model.target_distribution),
        "modelo_version": model.version,
        "n_historico": model.n_history,
        "n_amostras_modelo_nulo": model.n_null,
        "target": model.target,
    }
