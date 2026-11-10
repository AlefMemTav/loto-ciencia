"""
Modo Jogo Real.

Orquestra um torneio fechado de pacotes para quando o usuário realmente vai
apostar. O objetivo é disciplina: uma execução, uma regra fixa, relatório
auditável e comparação contra Monte Carlo equivalente.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from itertools import combinations
from math import comb
from typing import Any

import numpy as np

from app.core.generator_fast import gerar_jogos_vetorizado
from app.core.generator_objective import (
    portfolio_diagnostics,
    score_plausibility_batch,
)
from app.core.statistics.score_calibration import score_calibration_diagnostics
from app.core.strategies import estrategia_padrao, normalizar_estrategia


@dataclass(frozen=True)
class EffortProfile:
    candidate_pool_size: int
    tournament_packages: int
    monte_carlo_packages: int
    null_model_samples: int


EFFORT_PROFILES: dict[str, EffortProfile] = {
    "rapido": EffortProfile(
        candidate_pool_size=60,
        tournament_packages=60,
        monte_carlo_packages=300,
        null_model_samples=10000,
    ),
    "forte": EffortProfile(
        candidate_pool_size=90,
        tournament_packages=180,
        monte_carlo_packages=1000,
        null_model_samples=30000,
    ),
    "maximo": EffortProfile(
        candidate_pool_size=160,
        tournament_packages=800,
        monte_carlo_packages=5000,
        null_model_samples=80000,
    ),
}


def _default_seed(ctx, slug: str, quantidade: int, perfil_esforco: str) -> int:
    df = getattr(ctx, "df", None)
    draw_cols = getattr(ctx.config, "draw_cols", [])
    last_draw = []
    if df is not None and not getattr(df, "empty", True):
        available_cols = [c for c in draw_cols if c in df.columns]
        if available_cols:
            last_draw = [int(v) for v in df.iloc[-1][available_cols].tolist()]

    raw = "|".join(
        [
            "jogo_real_v1",
            str(date.today().isoformat()),
            str(slug),
            str(quantidade),
            str(perfil_esforco),
            str(len(df) if df is not None else 0),
            ",".join(map(str, last_draw)),
        ]
    )
    return int.from_bytes(sha256(raw.encode("utf-8")).digest()[:8], "big") % (2**32)


def _unique_rows(rows: list[list[int]], target: int) -> np.ndarray:
    seen: set[tuple[int, ...]] = set()
    unique: list[list[int]] = []
    for row in rows:
        t = tuple(sorted(int(n) for n in row))
        if t in seen:
            continue
        seen.add(t)
        unique.append(list(t))
        if len(unique) >= target:
            break
    return np.asarray(unique, dtype=int)


def _generate_candidate_pool(
    ctx,
    target_size: int,
    seed: int,
    estrategia_base: str,
    null_model_samples: int,
    payload_options: dict[str, Any],
) -> np.ndarray:
    collected: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    chunk_size = min(40, max(12, target_size // 4))
    max_chunks = max(6, int(np.ceil(target_size / max(1, chunk_size))) + 8)

    for chunk_idx in range(max_chunks):
        if len(seen) >= target_size:
            break
        jogos = gerar_jogos_vetorizado(
            ctx=ctx,
            quantidade=chunk_size,
            estrategia=estrategia_base,
            numeros_fixos=payload_options.get("numeros_fixos"),
            numeros_evitados=payload_options.get("numeros_evitados"),
            buffer_size=max(2000, chunk_size * 180),
            seed=seed + chunk_idx,
            temperatura=payload_options.get("temperatura"),
            usar_quentes=payload_options.get("usar_quentes", True),
            usar_atrasados=payload_options.get("usar_atrasados", True),
            usar_markov=payload_options.get("usar_markov", True),
            usar_ciclo=payload_options.get("usar_ciclo", True),
            usar_coocorrencia=payload_options.get("usar_coocorrencia", True),
            historical_signal_strength=payload_options.get(
                "historical_signal_strength", 1.0
            ),
            percentil_min=payload_options.get("percentil_min", 5.0),
            percentil_max=payload_options.get("percentil_max", 95.0),
            null_model_samples=null_model_samples,
            usar_calibracao_score=payload_options.get("usar_calibracao_score", True),
            calibration_strength=payload_options.get("calibration_strength", 1.0),
            calibration_target=payload_options.get(
                "calibration_target",
                "historico_nulo",
            ),
            candidate_multiplier=250,
        )
        for jogo in jogos:
            t = tuple(sorted(jogo))
            if t not in seen:
                seen.add(t)
                collected.append(list(t))

    if len(collected) < target_size:
        fallback = gerar_jogos_vetorizado(
            ctx=ctx,
            quantidade=max(target_size - len(collected), chunk_size),
            estrategia="pura",
            numeros_fixos=payload_options.get("numeros_fixos"),
            numeros_evitados=payload_options.get("numeros_evitados"),
            buffer_size=max(2000, chunk_size * 180),
            seed=seed + 99991,
            null_model_samples=null_model_samples,
            candidate_multiplier=250,
        )
        for jogo in fallback:
            t = tuple(sorted(jogo))
            if t not in seen:
                seen.add(t)
                collected.append(list(t))
            if len(collected) >= target_size:
                break

    return _unique_rows(collected, target_size)


def _random_games_array(
    rng: np.random.Generator,
    n_games: int,
    n_numbers: int,
    k: int,
    numeros_fixos: list[int] | None = None,
    numeros_evitados: list[int] | None = None,
) -> np.ndarray:
    fixos = sorted(set(int(n) for n in (numeros_fixos or [])))
    evitados = sorted(set(int(n) for n in (numeros_evitados or [])))
    needed = k - len(fixos)
    if needed < 0:
        raise ValueError("Quantidade de fixos maior que o tamanho do jogo.")

    available = np.asarray(
        [n for n in range(1, n_numbers + 1) if n not in set(fixos + evitados)],
        dtype=int,
    )
    if len(available) < needed:
        raise ValueError("Restrições impossibilitam gerar jogos aleatórios.")
    if needed == 0:
        return np.tile(np.asarray(fixos, dtype=int), (n_games, 1))

    random_scores = rng.random((n_games, len(available)))
    idx = np.argpartition(random_scores, needed - 1, axis=1)[:, :needed]
    drawn = available[idx]
    if fixos:
        fixed = np.tile(np.asarray(fixos, dtype=int), (n_games, 1))
        arr = np.concatenate([fixed, drawn], axis=1)
    else:
        arr = drawn
    arr.sort(axis=1)
    return arr.astype(int)


def _package_index_matrix(
    rng: np.random.Generator,
    game_scores: np.ndarray,
    quantidade: int,
    n_packages: int,
) -> np.ndarray:
    n_games = len(game_scores)
    if quantidade > n_games:
        raise ValueError("Pool de candidatos menor que a quantidade final.")

    score_std = float(game_scores.std())
    score_z = (
        np.zeros_like(game_scores)
        if score_std < 1e-9
        else (game_scores - game_scores.mean()) / score_std
    )
    logits = np.clip(score_z / 1.35, -6.0, 6.0)
    weights = np.exp(logits - logits.max())
    weights = weights / weights.sum()

    packages = np.empty((n_packages, quantidade), dtype=int)
    top_order = np.argsort(game_scores)[::-1]
    packages[0] = top_order[:quantidade]

    for i in range(1, n_packages):
        if i % 5 == 0:
            top_pool = top_order[: max(quantidade, min(n_games, quantidade * 8))]
            packages[i] = rng.choice(top_pool, size=quantidade, replace=False)
        else:
            packages[i] = rng.choice(
                n_games,
                size=quantidade,
                replace=False,
                p=weights,
            )
    return packages


def _coverage_ratio(games: np.ndarray, group_size: int) -> float:
    total_possible = len(games) * comb(games.shape[1], group_size)
    if total_possible <= 0:
        return 0.0
    seen = set()
    for row in games:
        for group in combinations(row.tolist(), group_size):
            seen.add(tuple(sorted(int(n) for n in group)))
    return len(seen) / total_possible


def _package_score(
    games: np.ndarray,
    individual_scores: np.ndarray,
    config,
    matriz_coocorrencia=None,
) -> tuple[float, dict[str, Any]]:
    diag = portfolio_diagnostics(games, config, matriz_coocorrencia)
    n_games = len(games)
    if n_games == 0:
        return -1e9, diag

    score_mean = float(np.mean(individual_scores))
    score_best = float(np.max(individual_scores))
    pair_coverage = _coverage_ratio(games, 2)
    triple_coverage = _coverage_ratio(games, 3) if config.bet_size >= 3 else 0.0

    if config.slug == "mega_sena_sorteio" and n_games >= 20:
        exposure_limit = 5
    else:
        expected_exposure = n_games * config.bet_size / max(1, config.n_numbers)
        exposure_limit = max(2, int(np.ceil(expected_exposure * 2.5)))
    over_exposure = max(0, int(diag.get("max_exposicao", 0)) - exposure_limit)
    overlap_over = max(
        0.0,
        float(diag.get("overlap_max", 0)) - config.get_overlap_limit(),
    )
    if getattr(config, "is_dense", False):
        expected_pair_reuse = (
            n_games * comb(config.bet_size, 2) / max(1, comb(config.n_numbers, 2))
        )
        pair_limit = max(4, int(np.ceil(expected_pair_reuse * 1.45)))
    else:
        pair_limit = 3
    pair_over = max(0, int(diag.get("max_repeticao_par", 0)) - pair_limit)

    score = (
        score_mean
        + (score_best * 0.12)
        + (pair_coverage * 0.80)
        + (triple_coverage * 0.55)
        - (over_exposure * 0.80)
        - (overlap_over * 0.80)
        - (pair_over * 0.60)
    )
    return float(score), diag


def _score_packages(
    packages: np.ndarray,
    games_pool: np.ndarray,
    game_scores: np.ndarray,
    config,
    matriz_coocorrencia=None,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    scores = np.zeros(len(packages), dtype=float)
    diagnostics: list[dict[str, Any]] = []
    for i, idxs in enumerate(packages):
        score, diag = _package_score(
            games_pool[idxs],
            game_scores[idxs],
            config,
            matriz_coocorrencia,
        )
        scores[i] = score
        diagnostics.append(diag)
    return scores, diagnostics


def generate_real_game_package(
    ctx,
    quantidade: int,
    perfil_esforco: str = "forte",
    estrategia_base: str | None = None,
    seed: int | None = None,
    payload_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload_options = dict(payload_options or {})
    # Sem estratégia explícita: cauda_controlada em jogo esparso, balanceada em denso.
    estrategia_base = (
        normalizar_estrategia(estrategia_base)
        if estrategia_base
        else estrategia_padrao(ctx.config)
    )
    if perfil_esforco not in EFFORT_PROFILES:
        raise ValueError("perfil_esforco deve ser rapido, forte ou maximo.")
    if quantidade < 1:
        raise ValueError("quantidade deve ser maior que zero.")
    if quantidade > 50:
        raise ValueError("Modo Jogo Real aceita no máximo 50 jogos por execução.")

    profile = EFFORT_PROFILES[perfil_esforco]
    null_model_samples = max(
        1000,
        int(payload_options.get("null_model_samples") or profile.null_model_samples),
    )
    default_target_pool = min(profile.candidate_pool_size, max(quantidade * 16, 40))
    target_pool = int(payload_options.get("candidate_pool_size") or default_target_pool)
    target_pool = max(quantidade, target_pool)
    tournament_packages = max(
        1,
        int(payload_options.get("tournament_packages") or profile.tournament_packages),
    )
    monte_carlo_packages = max(
        1,
        int(payload_options.get("monte_carlo_packages") or profile.monte_carlo_packages),
    )

    seed = int(
        seed
        if seed is not None
        else _default_seed(ctx, ctx.config.slug, quantidade, perfil_esforco)
    )
    rng = np.random.default_rng(seed)

    candidate_pool = _generate_candidate_pool(
        ctx=ctx,
        target_size=target_pool,
        seed=seed,
        estrategia_base=estrategia_base,
        null_model_samples=null_model_samples,
        payload_options=payload_options,
    )
    candidate_scores = score_plausibility_batch(
        candidate_pool,
        ctx,
        estrategia=estrategia_base,
        percentil_min=payload_options.get("percentil_min", 5.0),
        percentil_max=payload_options.get("percentil_max", 95.0),
        null_model_samples=null_model_samples,
        usar_quentes=payload_options.get("usar_quentes", True),
        usar_atrasados=payload_options.get("usar_atrasados", True),
        usar_coocorrencia=payload_options.get("usar_coocorrencia", True),
        historical_signal_strength=payload_options.get(
            "historical_signal_strength",
            1.0,
        ),
        usar_calibracao_score=payload_options.get("usar_calibracao_score", True),
        calibration_strength=payload_options.get("calibration_strength", 1.0),
        calibration_target=payload_options.get(
            "calibration_target",
            "historico_nulo",
        ),
    )

    package_idxs = _package_index_matrix(
        rng,
        candidate_scores,
        quantidade=quantidade,
        n_packages=tournament_packages,
    )
    package_scores, package_diags = _score_packages(
        package_idxs,
        candidate_pool,
        candidate_scores,
        ctx.config,
        getattr(ctx, "matriz_coocorrencia", None),
    )
    best_idx = int(np.argmax(package_scores))
    selected_idxs = package_idxs[best_idx]
    selected_games = candidate_pool[selected_idxs]

    mc_games = _random_games_array(
        rng,
        n_games=monte_carlo_packages * quantidade,
        n_numbers=ctx.config.n_numbers,
        k=ctx.config.bet_size,
        numeros_fixos=payload_options.get("numeros_fixos"),
        numeros_evitados=payload_options.get("numeros_evitados"),
    )
    mc_scores_games = score_plausibility_batch(
        mc_games,
        ctx,
        estrategia=estrategia_base,
        percentil_min=payload_options.get("percentil_min", 5.0),
        percentil_max=payload_options.get("percentil_max", 95.0),
        null_model_samples=null_model_samples,
        usar_quentes=payload_options.get("usar_quentes", True),
        usar_atrasados=payload_options.get("usar_atrasados", True),
        usar_coocorrencia=payload_options.get("usar_coocorrencia", True),
        historical_signal_strength=payload_options.get(
            "historical_signal_strength",
            1.0,
        ),
        usar_calibracao_score=payload_options.get("usar_calibracao_score", True),
        calibration_strength=payload_options.get("calibration_strength", 1.0),
        calibration_target=payload_options.get(
            "calibration_target",
            "historico_nulo",
        ),
    )
    mc_pool = mc_games.reshape(monte_carlo_packages, quantidade, ctx.config.bet_size)
    mc_score_pool = mc_scores_games.reshape(monte_carlo_packages, quantidade)
    mc_package_scores = np.zeros(monte_carlo_packages, dtype=float)
    for i in range(monte_carlo_packages):
        mc_package_scores[i], _diag = _package_score(
            mc_pool[i],
            mc_score_pool[i],
            ctx.config,
            getattr(ctx, "matriz_coocorrencia", None),
        )

    selected_score = float(package_scores[best_idx])
    percentile_mc = float(
        np.searchsorted(np.sort(mc_package_scores), selected_score, side="right")
        / max(1, monte_carlo_packages)
        * 100.0
    )
    p_empirical = float(
        (np.sum(mc_package_scores >= selected_score) + 1.0)
        / (monte_carlo_packages + 1.0)
    )
    calibration_diag = score_calibration_diagnostics(
        selected_games,
        ctx.config,
        df_historico=getattr(ctx, "df", None),
        n_samples=null_model_samples,
        target=payload_options.get("calibration_target", "historico_nulo"),
    )

    return {
        "jogos": selected_games.tolist(),
        "relatorio": {
            "modo": "jogo_real",
            "perfil_esforco": perfil_esforco,
            "estrategia_base": estrategia_base,
            "seed": seed,
            "quantidade": quantidade,
            "candidate_pool_size": int(len(candidate_pool)),
            "tournament_packages": tournament_packages,
            "monte_carlo_packages": monte_carlo_packages,
            "null_model_samples": null_model_samples,
            "score_pacote": round(selected_score, 6),
            "percentil_vs_monte_carlo": round(percentile_mc, 4),
            "p_empirico_mc_supera_ou_iguala": round(p_empirical, 6),
            "score_mc_media": round(float(np.mean(mc_package_scores)), 6),
            "score_mc_p95": round(float(np.percentile(mc_package_scores, 95)), 6),
            "ranking_torneio": int(best_idx + 1),
            "restricoes": {
                "numeros_fixos": payload_options.get("numeros_fixos") or [],
                "numeros_evitados": payload_options.get("numeros_evitados") or [],
            },
            "diagnostico_portfolio": package_diags[best_idx],
            "diagnostico_calibracao_score": calibration_diag,
        },
    }
