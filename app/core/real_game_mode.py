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
            usar_quentes=payload_options.get("usar_quentes", False),
            usar_atrasados=payload_options.get("usar_atrasados", False),
            usar_markov=payload_options.get("usar_markov", False),
            usar_ciclo=payload_options.get("usar_ciclo", False),
            usar_coocorrencia=payload_options.get("usar_coocorrencia", False),
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

    clean_mask = (game_scores > -50.0) & np.isfinite(game_scores)
    clean_count = int(np.sum(clean_mask))
    if clean_count >= quantidade:
        clean_mean = float(game_scores[clean_mask].mean())
        clean_std = float(game_scores[clean_mask].std())
    else:
        clean_mean = float(game_scores.mean())
        clean_std = float(game_scores.std())

    score_z = (
        np.zeros_like(game_scores)
        if clean_std < 1e-9
        else (game_scores - clean_mean) / clean_std
    )
    logits = np.clip(score_z / 1.35, -18.0, 6.0)
    weights = np.exp(logits - logits.max())
    if clean_count >= quantidade:
        weights = np.where(clean_mask, weights, 0.0)
    w_sum = float(weights.sum())
    if w_sum > 0 and int(np.count_nonzero(weights > 0)) >= quantidade:
        weights = weights / w_sum
    else:
        weights = np.full(n_games, 1.0 / n_games, dtype=float)

    packages = np.empty((n_packages, quantidade), dtype=int)
    top_order = np.argsort(game_scores)[::-1]
    packages[0] = top_order[:quantidade]

    pool_cap = clean_count if clean_count >= quantidade else n_games
    for i in range(1, n_packages):
        if i % 5 == 0:
            top_pool = top_order[: max(quantidade, min(pool_cap, quantidade * 8))]
            packages[i] = rng.choice(top_pool, size=quantidade, replace=False)
        else:
            packages[i] = rng.choice(
                n_games,
                size=quantidade,
                replace=False,
                p=weights,
            )
    return packages


def _unique_group_count(
    games: np.ndarray, group_size: int, n_numbers: int | None = None
) -> int:
    arr = np.asarray(games, dtype=int)
    if arr.ndim != 2 or len(arr) == 0:
        return 0

    if group_size in (2, 3):
        n_max = int(n_numbers) if n_numbers is not None else int(arr.max())
        if arr.min() >= 1 and int(arr.max()) <= n_max:
            m, k = arr.shape
            B = np.zeros((m, n_max), dtype=np.int32)
            B[np.arange(m)[:, None], arr - 1] = 1
            if np.all(B.sum(axis=1) == k):
                if group_size == 2:
                    P = B.T @ B
                    np.fill_diagonal(P, 0)
                    return int(np.count_nonzero(P)) // 2
                col_counts = B.sum(axis=0)
                unique = 0
                for a in np.flatnonzero(col_counts[: max(0, n_max - 2)] > 0):
                    Ra = B[B[:, a] == 1, a + 1 :]
                    if Ra.shape[1] < 2:
                        continue
                    Pa = Ra.T @ Ra
                    np.fill_diagonal(Pa, 0)
                    unique += int(np.count_nonzero(Pa)) // 2
                return unique

    seen = set()
    for row in arr:
        for group in combinations(row.tolist(), group_size):
            seen.add(tuple(sorted(int(n) for n in group)))
    return len(seen)


def _coverage_ratio(
    games: np.ndarray, group_size: int, n_numbers: int | None = None
) -> float:
    arr = np.asarray(games, dtype=int)
    if arr.ndim != 2 or len(arr) == 0:
        return 0.0
    total_possible = len(arr) * comb(arr.shape[1], group_size)
    if total_possible <= 0:
        return 0.0
    return _unique_group_count(arr, group_size, n_numbers=n_numbers) / total_possible


def _universe_coverage_ratio(
    games: np.ndarray, group_size: int, n_numbers: int
) -> float:
    arr = np.asarray(games, dtype=int)
    if arr.ndim != 2 or len(arr) == 0:
        return 0.0
    total_universe = comb(max(1, int(n_numbers)), group_size)
    if total_universe <= 0:
        return 0.0
    return min(1.0, _unique_group_count(arr, group_size, n_numbers=n_numbers) / total_universe)


def _fast_js_divergence(p: np.ndarray, q: np.ndarray) -> float:
    p_arr = np.asarray(p, dtype=float)
    q_arr = np.asarray(q, dtype=float)
    p_arr = p_arr / max(1e-12, float(p_arr.sum()))
    q_arr = q_arr / max(1e-12, float(q_arr.sum()))
    m = 0.5 * (p_arr + q_arr)
    mask_p = p_arr > 0
    mask_q = q_arr > 0
    kl_pm = float(np.sum(p_arr[mask_p] * np.log2(p_arr[mask_p] / np.maximum(m[mask_p], 1e-12))))
    kl_qm = float(np.sum(q_arr[mask_q] * np.log2(q_arr[mask_q] / np.maximum(m[mask_q], 1e-12))))
    return max(0.0, 0.5 * (kl_pm + kl_qm))


def _package_score(
    games: np.ndarray,
    individual_scores: np.ndarray,
    config,
    matriz_coocorrencia=None,
    clusters_cache: dict | None = None,
    pkg_buckets: np.ndarray | None = None,
    target_bucket_probs: np.ndarray | None = None,
) -> tuple[float, dict[str, Any]]:
    diag = portfolio_diagnostics(
        games,
        config,
        matriz_coocorrencia,
        include_higher_order=False,
        include_dispersao=False,
        clusters_cache=clusters_cache,
    )
    n_games = len(games)
    if n_games == 0:
        return -1e9, diag

    score_mean = float(np.mean(individual_scores))
    score_best = float(np.max(individual_scores))
    pair_non_redundancy = _coverage_ratio(games, 2, n_numbers=config.n_numbers)
    triple_non_redundancy = (
        _coverage_ratio(games, 3, n_numbers=config.n_numbers)
        if config.bet_size >= 3
        else 0.0
    )
    universe_pair_cov = _universe_coverage_ratio(games, 2, config.n_numbers)
    arch_entropy = float(diag.get("entropia_arquetipos", 0.0))

    if config.slug == "mega_sena_sorteio" and n_games >= 20:
        exposure_limit = 5
    else:
        expected_exposure = n_games * config.bet_size / max(1, config.n_numbers)
        exposure_limit = max(2, int(np.ceil(expected_exposure * 2.5)))
    over_exposure = max(0, int(diag.get("max_exposicao", 0)) - exposure_limit)
    exposure_std = float(diag.get("desvio_exposicao_usadas", 0.0))
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

    js_penalty = 0.0
    if pkg_buckets is not None and target_bucket_probs is not None and len(pkg_buckets) > 0:
        counts = np.bincount(pkg_buckets, minlength=len(target_bucket_probs)).astype(float)
        js_div = _fast_js_divergence(counts, target_bucket_probs)
        js_penalty = js_div * 2.50

    score = (
        score_mean
        + (score_best * 0.12)
        + (pair_non_redundancy * 1.40)
        + (triple_non_redundancy * 0.90)
        + (universe_pair_cov * 1.20)
        + (arch_entropy * 0.25)
        - (exposure_std * 0.15)
        - (over_exposure * 1.20)
        - (overlap_over * 1.50)
        - (pair_over * 0.90)
        - js_penalty
    )
    return float(score), diag


def _score_packages(
    packages: np.ndarray,
    games_pool: np.ndarray,
    game_scores: np.ndarray,
    config,
    matriz_coocorrencia=None,
    clusters_cache: dict | None = None,
    candidate_buckets: np.ndarray | None = None,
    target_bucket_probs: np.ndarray | None = None,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    scores = np.zeros(len(packages), dtype=float)
    diagnostics: list[dict[str, Any]] = []
    for i, idxs in enumerate(packages):
        pkg_buckets = candidate_buckets[idxs] if candidate_buckets is not None else None
        score, diag = _package_score(
            games_pool[idxs],
            game_scores[idxs],
            config,
            matriz_coocorrencia,
            clusters_cache=clusters_cache,
            pkg_buckets=pkg_buckets,
            target_bucket_probs=target_bucket_probs,
        )
        scores[i] = score
        diagnostics.append(diag)
    return scores, diagnostics


def _refine_package_1opt(
    selected_idxs: np.ndarray,
    best_score: float,
    games_pool: np.ndarray,
    game_scores: np.ndarray,
    config,
    rng: np.random.Generator,
    matriz_coocorrencia=None,
    max_evals: int = 80,
    clusters_cache: dict | None = None,
    candidate_buckets: np.ndarray | None = None,
    target_bucket_probs: np.ndarray | None = None,
) -> tuple[np.ndarray, float]:
    """Refinamento local 1-opt sobre o melhor pacote do torneio."""
    current = selected_idxs.copy()
    n_selected = len(current)
    n_pool = len(games_pool)
    if n_selected == 0 or n_pool <= n_selected:
        return current, best_score

    used = set(int(i) for i in current.tolist())
    top_order = np.argsort(game_scores)[::-1]
    clean_order = [int(i) for i in top_order if game_scores[int(i)] > -50.0]
    base_order = clean_order if len(clean_order) > n_selected else [int(i) for i in top_order]
    replacements = [i for i in base_order if i not in used][: max(16, n_selected * 4)]
    if not replacements:
        return current, best_score

    evals = 0
    for pos in range(n_selected):
        if evals >= max_evals:
            break
        n_try = min(len(replacements), max(4, max_evals // max(1, n_selected)))
        sample_cands = rng.choice(replacements, size=n_try, replace=False)
        for cand_idx in sample_cands:
            cand_i = int(cand_idx)
            if cand_i in used:
                continue
            trial = current.copy()
            old_i = int(trial[pos])
            trial[pos] = cand_i
            pkg_buckets = candidate_buckets[trial] if candidate_buckets is not None else None
            trial_score, _ = _package_score(
                games_pool[trial],
                game_scores[trial],
                config,
                matriz_coocorrencia,
                clusters_cache=clusters_cache,
                pkg_buckets=pkg_buckets,
                target_bucket_probs=target_bucket_probs,
            )
            evals += 1
            if trial_score > best_score + 1e-9:
                used.discard(old_i)
                used.add(cand_i)
                current = trial
                best_score = trial_score
                replacements = [r for r in replacements if r != cand_i]
                replacements.append(old_i)
            if evals >= max_evals:
                break

    return current, best_score


def _compute_post_selection_historical_coverage(
    selected_games: np.ndarray,
    ctx,
) -> dict[str, Any]:
    """
    Diagnóstico pós-seleção neutro de cobertura histórica do pacote selecionado.
    Compara a distribuição de acertos máximos por concurso contra a expectativa hipergeométrica.
    """
    draws_bin = getattr(ctx, "draws_bin", None)
    config = getattr(ctx, "config", None)
    if (
        draws_bin is None
        or config is None
        or not hasattr(draws_bin, "shape")
        or len(draws_bin) == 0
        or len(selected_games) == 0
    ):
        return {"disponivel": False}

    n_draws, n_numbers = draws_bin.shape
    m_games, bet_k = selected_games.shape
    if int(selected_games.min()) < 1 or int(selected_games.max()) > n_numbers:
        return {"disponivel": False}

    B_sel = np.zeros((m_games, n_numbers), dtype=np.int16)
    B_sel[np.arange(m_games)[:, None], selected_games - 1] = 1
    hits_matrix = draws_bin.astype(np.int16, copy=False) @ B_sel.T
    max_hits = hits_matrix.max(axis=1)

    draw_k = int(config.k)
    total_comb = max(1, comb(n_numbers, draw_k))

    if draw_k <= 6:
        tiers = [t for t in (3, 4, 5, 6) if t <= min(draw_k, bet_k)]
    elif draw_k == 15:
        tiers = [t for t in (11, 12, 13, 14, 15) if t <= min(draw_k, bet_k)]
    elif draw_k == 20:
        tiers = [t for t in (0, 15, 16, 17, 18, 19, 20) if t <= min(draw_k, bet_k)]
    else:
        tiers = [max(1, draw_k - 2), max(1, draw_k - 1), draw_k]

    faixas: dict[str, Any] = {}
    for h in tiers:
        p_single = (
            comb(bet_k, h) * comb(max(0, n_numbers - bet_k), draw_k - h) / float(total_comb)
            if 0 <= draw_k - h <= n_numbers - bet_k
            else 0.0
        )
        obs_tickets = int(np.sum(hits_matrix == h))
        exp_tickets = float(n_draws * m_games * p_single)
        obs_concursos = int(np.sum(np.any(hits_matrix == h, axis=1)))
        p_any = 1.0 - ((1.0 - p_single) ** m_games)
        exp_concursos = float(n_draws * p_any)
        faixas[f"{h}_acertos"] = {
            "bilhetes_observados": obs_tickets,
            "bilhetes_esperados_h0": round(exp_tickets, 2),
            "concursos_atingidos": obs_concursos,
            "concursos_esperados_h0": round(exp_concursos, 2),
        }

    return {
        "disponivel": True,
        "concursos_avaliados": int(n_draws),
        "media_melhor_acerto_por_concurso": round(float(np.mean(max_hits)), 4),
        "max_acerto_historico_pacote": int(np.max(max_hits)),
        "faixas": faixas,
    }


def _compute_post_selection_antidivision(
    selected_games: np.ndarray,
    ctx,
) -> dict[str, Any]:
    """
    Diagnóstico pós-seleção de proteção contra divisão de prêmio (anti-multidão).
    """
    config = getattr(ctx, "config", None)
    modelo = getattr(ctx, "modelo_popularidade", None)
    if config is None or modelo is None or len(selected_games) == 0:
        return {"disponivel": False}

    from app.core.statistics.popularidade_medida import LIMIAR_RAZAO_GANHADORES

    razoes = np.asarray(modelo.razao_ganhadores_batch(selected_games), dtype=float)
    pop_pct = np.asarray(modelo.percentil_batch(selected_games), dtype=float)
    limiar = LIMIAR_RAZAO_GANHADORES.get(getattr(config, "slug", ""))

    # Fator esperado de retenção de prêmio condicional a Poisson(lambda = r) vs apostador médio (lambda = 1)
    base_share = 1.0 - float(np.exp(-1.0))
    safe_r = np.maximum(razoes, 1e-4)
    shares = (1.0 - np.exp(-safe_r)) / safe_r
    multiplicadores_ev = shares / base_share

    return {
        "disponivel": True,
        "limiar_corte_popularidade": round(float(limiar), 4) if limiar is not None else None,
        "jogos_acima_limiar_corte": int(np.sum(razoes > limiar)) if limiar is not None else 0,
        "razao_ganhadores_media": round(float(np.mean(razoes)), 4),
        "razao_ganhadores_min": round(float(np.min(razoes)), 4),
        "razao_ganhadores_max": round(float(np.max(razoes)), 4),
        "percentil_popularidade_medio": round(float(np.mean(pop_pct)), 2),
        "multiplicador_retencao_premio_medio": round(float(np.mean(multiplicadores_ev)), 4),
    }


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
        usar_quentes=payload_options.get("usar_quentes", False),
        usar_atrasados=payload_options.get("usar_atrasados", False),
        usar_coocorrencia=payload_options.get("usar_coocorrencia", False),
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

    clusters_cache = getattr(ctx, "clusters_historicos", None) or getattr(
        ctx, "clusters_info", None
    )
    candidate_buckets = None
    target_bucket_probs = None
    if payload_options.get("usar_calibracao_score", True) and float(
        payload_options.get("calibration_strength", 1.0)
    ) > 0:
        from app.core.generator_objective import score_structural_batch
        from app.core.statistics.score_calibration import (
            bucket_indices,
            get_score_calibration_model,
        )

        cal_scores = score_structural_batch(
            candidate_pool,
            ctx.config,
            n_samples=null_model_samples,
        )
        cal_model = get_score_calibration_model(
            ctx.config,
            df_historico=getattr(ctx, "df", None),
            n_samples=null_model_samples,
            target=payload_options.get("calibration_target", "historico_nulo"),
        )
        candidate_buckets = bucket_indices(cal_scores)
        target_bucket_probs = cal_model.target_probabilities

    package_idxs = _package_index_matrix(
        rng,
        candidate_scores,
        quantidade=quantidade,
        n_packages=tournament_packages,
    )
    package_scores, _package_diags = _score_packages(
        package_idxs,
        candidate_pool,
        candidate_scores,
        ctx.config,
        getattr(ctx, "matriz_coocorrencia", None),
        clusters_cache=clusters_cache,
        candidate_buckets=candidate_buckets,
        target_bucket_probs=target_bucket_probs,
    )
    best_idx = int(np.argmax(package_scores))
    selected_idxs, selected_score = _refine_package_1opt(
        package_idxs[best_idx],
        float(package_scores[best_idx]),
        candidate_pool,
        candidate_scores,
        ctx.config,
        rng,
        getattr(ctx, "matriz_coocorrencia", None),
        clusters_cache=clusters_cache,
        candidate_buckets=candidate_buckets,
        target_bucket_probs=target_bucket_probs,
    )
    selected_games = candidate_pool[selected_idxs]
    selected_diag = portfolio_diagnostics(
        selected_games,
        ctx.config,
        getattr(ctx, "matriz_coocorrencia", None),
        clusters_cache=clusters_cache,
    )
    selected_diag["cobertura_pares_universo"] = round(
        _universe_coverage_ratio(selected_games, 2, ctx.config.n_numbers), 6
    )
    selected_diag["cobertura_nao_redundante_pares"] = round(
        _coverage_ratio(selected_games, 2, n_numbers=ctx.config.n_numbers), 6
    )
    if ctx.config.bet_size >= 3:
        selected_diag["cobertura_nao_redundante_ternos"] = round(
            _coverage_ratio(selected_games, 3, n_numbers=ctx.config.n_numbers), 6
        )

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
        usar_quentes=payload_options.get("usar_quentes", False),
        usar_atrasados=payload_options.get("usar_atrasados", False),
        usar_coocorrencia=payload_options.get("usar_coocorrencia", False),
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
    mc_buckets_all = None
    if target_bucket_probs is not None:
        from app.core.generator_objective import score_structural_batch
        from app.core.statistics.score_calibration import bucket_indices

        mc_struct_scores = score_structural_batch(
            mc_games,
            ctx.config,
            n_samples=null_model_samples,
        )
        mc_buckets_all = bucket_indices(mc_struct_scores).reshape(
            monte_carlo_packages, quantidade
        )

    mc_pool = mc_games.reshape(monte_carlo_packages, quantidade, ctx.config.bet_size)
    mc_score_pool = mc_scores_games.reshape(monte_carlo_packages, quantidade)
    mc_package_scores = np.zeros(monte_carlo_packages, dtype=float)
    for i in range(monte_carlo_packages):
        mc_pkg_buckets = mc_buckets_all[i] if mc_buckets_all is not None else None
        mc_package_scores[i], _diag = _package_score(
            mc_pool[i],
            mc_score_pool[i],
            ctx.config,
            getattr(ctx, "matriz_coocorrencia", None),
            clusters_cache=clusters_cache,
            pkg_buckets=mc_pkg_buckets,
            target_bucket_probs=target_bucket_probs,
        )

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
    cobertura_historica_diag = _compute_post_selection_historical_coverage(
        selected_games,
        ctx,
    )
    antidivisao_diag = _compute_post_selection_antidivision(
        selected_games,
        ctx,
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
            "diagnostico_portfolio": selected_diag,
            "diagnostico_calibracao_score": calibration_diag,
            "diagnostico_cobertura_historica": cobertura_historica_diag,
            "diagnostico_antidivisao": antidivisao_diag,
        },
    }
