"""
Modelo nulo combinatório para jogos de loteria.

Gera amostras uniformes do espaço combinatório de cada modalidade e cacheia
distribuições ordenadas de métricas. Isso permite consultas de percentil em
tempo quase constante depois da primeira construção.
"""

from __future__ import annotations

from dataclasses import dataclass
import os

import numpy as np

from app.core.lottery import GameConfig
from app.core.ticket_features import extract_ticket_features_batch


NULL_MODEL_VERSION = "comb-null-v1"
DEFAULT_NULL_MODEL_SAMPLES = int(os.getenv("LOTOSCIENCE_NULL_MODEL_SAMPLES", "50000"))
DEFAULT_NULL_MODEL_SEED = 20260607
_CACHE: dict[tuple, "NullModel"] = {}


@dataclass(frozen=True)
class NullModel:
    game_slug: str
    version: str
    n_samples: int
    metrics: dict[str, np.ndarray]

    def percentile(self, metric: str, value: float) -> float | None:
        arr = self.metrics.get(metric)
        if arr is None or len(arr) == 0:
            return None
        idx = np.searchsorted(arr, value, side="right")
        return round(float(idx * 100.0 / len(arr)), 3)

    def percentiles(self, metric: str, values: np.ndarray) -> np.ndarray:
        arr = self.metrics.get(metric)
        if arr is None or len(arr) == 0:
            return np.full(len(values), 50.0, dtype=float)
        idx = np.searchsorted(arr, values, side="right")
        return idx.astype(float) * 100.0 / len(arr)


def _cache_key(config: GameConfig, n_samples: int) -> tuple:
    layout = config.layout
    return (
        config.slug,
        config.n_numbers,
        config.bet_size,
        config.k,
        layout.rows if layout else 0,
        layout.cols if layout else 0,
        NULL_MODEL_VERSION,
        int(n_samples),
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
    remaining = n_samples
    while remaining > 0:
        batch = min(batch_size, remaining)
        keys = rng.random((batch, n_numbers))
        idx = np.argpartition(keys, k - 1, axis=1)[:, :k]
        games = pool[idx]
        games.sort(axis=1)
        chunks.append(games)
        remaining -= batch
    return np.vstack(chunks)


def build_null_model(config: GameConfig, n_samples: int | None = None) -> NullModel:
    n = int(n_samples or DEFAULT_NULL_MODEL_SAMPLES)
    key = _cache_key(config, n)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached

    slug_seed = sum((i + 1) * ord(ch) for i, ch in enumerate(config.slug))
    seed = DEFAULT_NULL_MODEL_SEED + slug_seed
    rng = np.random.default_rng(seed)
    games = _sample_uniform_games(rng, config.n_numbers, config.bet_size, n)
    features = extract_ticket_features_batch(games, config)
    metrics = {
        name: np.sort(values.astype(float))
        for name, values in features.items()
        if len(values) > 0
    }
    model = NullModel(
        game_slug=config.slug,
        version=NULL_MODEL_VERSION,
        n_samples=n,
        metrics=metrics,
    )
    _CACHE[key] = model
    return model


def get_null_model(config: GameConfig, n_samples: int | None = None) -> NullModel:
    return build_null_model(config, n_samples=n_samples)
