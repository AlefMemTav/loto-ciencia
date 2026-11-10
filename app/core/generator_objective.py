"""
Objetivo próprio do gerador.

O gerador usa esta função para priorizar jogos plausíveis e diversos sem
chamar o validador nem perseguir o score exibido ao usuário.
"""

from __future__ import annotations

from itertools import combinations
from math import comb
import numpy as np

from app.core.statistics.popularidade_medida import LIMIAR_RAZAO_GANHADORES
from app.core.strategies import CAUDA_CONTROLADA, normalizar_estrategia
from app.core.ticket_features import extract_ticket_features_batch
from app.core.statistics.feature_percentiles import batch_feature_percentiles
from app.core.statistics.score_calibration import (
    BUCKET_LABELS,
    bucket_indices,
    get_score_calibration_model,
    score_structural_batch,
    score_structural_from_percentiles,
)


TAIL_CONTROLLED = CAUDA_CONTROLADA
PENALIDADE_CORTE_POPULARIDADE = 100.0
TAIL_STRATEGIES = {TAIL_CONTROLLED}


def score_plausibility_batch(
    candidates: np.ndarray,
    ctx,
    estrategia: str = "balanceada",
    percentil_min: float = 5.0,
    percentil_max: float = 95.0,
    null_model_samples: int | None = None,
    usar_quentes: bool = False,
    usar_atrasados: bool = False,
    usar_coocorrencia: bool = True,
    historical_signal_strength: float = 1.0,
    usar_calibracao_score: bool = True,
    calibration_strength: float = 1.0,
    calibration_target: str = "historico_nulo",
    usar_ordem_saida: bool = True,
    ordem_strength: float = 1.0,
    usar_popularidade_medida: bool = True,
    popularidade_strength: float = 1.0,
    usar_corte_popularidade: bool = True,
) -> np.ndarray:
    """
    Score vetorial de plausibilidade para candidatos já ordenados.

    Maior é melhor. O score combina sinais suaves e independentes do validador:
    aderência a distribuições esperadas, baixa compressibilidade, baixa
    popularidade humana e uso controlado de sinais históricos.
    """
    if len(candidates) == 0:
        return np.array([], dtype=float)

    estrategia = normalizar_estrategia(estrategia)
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

    def _bounds_for(metric: str) -> tuple[float, float]:
        if estrategia == TAIL_CONTROLLED and metric in {"soma", "span", "gap_medio"}:
            return 4.0, 96.0
        return percentil_min, percentil_max

    def _central_score(
        pct: np.ndarray, weight: float, metric: str
    ) -> np.ndarray:
        lower, upper = _bounds_for(metric)
        center = 1.0 - np.abs(pct - 50.0) / 50.0
        outside_low = np.maximum(0.0, lower - pct) / max(1.0, lower)
        outside_high = np.maximum(0.0, pct - upper) / max(1.0, 100.0 - upper)
        return (center * weight) - ((outside_low + outside_high) * weight * 1.8)

    for metric, weight in central_weights.items():
        pct = percentiles.get(metric)
        if pct is not None:
            scores += _central_score(pct, weight, metric)

    for metric, weight in high_bad_weights.items():
        pct = percentiles.get(metric)
        if pct is not None:
            scores -= np.maximum(0.0, pct - percentil_max) * weight / 5.0

    for metric, weight in low_bad_weights.items():
        pct = percentiles.get(metric)
        if pct is not None:
            scores -= np.maximum(0.0, percentil_min - pct) * weight / 5.0

    if usar_calibracao_score:
        calibration_strength = float(np.clip(calibration_strength, 0.0, 2.0))
        if calibration_strength > 0:
            structural_scores = score_structural_from_percentiles(
                features,
                percentiles,
                len(candidates),
            )
            model = get_score_calibration_model(
                config,
                df_historico=getattr(ctx, "df", None),
                n_samples=null_model_samples,
                target=calibration_target,
            )
            buckets = bucket_indices(structural_scores)
            target_probs = np.clip(model.target_probabilities, 1e-6, 1.0)
            uniform = 1.0 / len(BUCKET_LABELS)
            prior = np.clip(np.log(target_probs[buckets] / uniform), -1.5, 1.5)
            scores += prior * 0.35 * calibration_strength

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
            if estrategia == TAIL_CONTROLLED:
                scores += (
                    np.clip(cooc_z, -1.0, 2.0)
                    * 0.25
                    * historical_signal_strength
                )
                scores -= (
                    np.maximum(0.0, cooc_z - 2.0)
                    * 0.45
                    * historical_signal_strength
                )
            else:
                scores += (
                    np.clip(cooc_z, -1.5, 1.5)
                    * 0.35
                    * historical_signal_strength
                )

    # Popularidade medida com ganhadores reais (risco de dividir o prêmio).
    modelo_pop = getattr(ctx, "modelo_popularidade", None)
    if usar_popularidade_medida and modelo_pop is not None:
        pop_pct = modelo_pop.percentil_batch(candidates)
        forca = float(np.clip(popularidade_strength, 0.0, 3.0))
        scores -= np.maximum(0.0, pop_pct - 60.0) / 40.0 * 2.0 * forca

        # Corte: jogos acima do limiar de razão de ganhadores (Mega e Quina) levam
        # penalidade grande, mas finita. Assim saem da seleção enquanto houver
        # alternativas, e o gerador ainda fecha o pacote se os fixos/evitados
        # deixarem poucos candidatos.
        limiar = LIMIAR_RAZAO_GANHADORES.get(getattr(config, "slug", ""))
        if usar_corte_popularidade and limiar is not None and k == modelo_pop.k:
            scores -= PENALIDADE_CORTE_POPULARIDADE * (
                modelo_pop.razao_ganhadores_batch(candidates) > limiar
            )

    # Ordem de saída das bolas: preferência leve contra extremos (cedo/tarde).
    perfil_pos = getattr(ctx, "perfil_posicional", None)
    if usar_ordem_saida and usar_historico and perfil_pos is not None:
        from app.core.statistics.ordem_saida import percentil_posicional_batch

        pos_pct = percentil_posicional_batch(candidates, perfil_pos)
        forca = float(np.clip(ordem_strength, 0.0, 3.0))
        scores -= np.maximum(0.0, np.abs(pos_pct - 50.0) - 45.0) / 5.0 * 0.4 * forca

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
    ctx=None,
    usar_calibracao_score: bool = True,
    calibration_strength: float = 1.0,
    calibration_target: str = "historico_nulo",
    null_model_samples: int | None = None,
) -> list[list[int]]:
    """Seleciona os melhores candidatos preservando diversidade do portfólio."""
    if rng is None:
        rng = np.random.default_rng()

    estrategia = normalizar_estrategia(estrategia)
    if len(candidates) == 0:
        return []

    finite_mask = np.isfinite(scores)
    candidates = candidates[finite_mask]
    scores = scores[finite_mask]
    if len(candidates) == 0:
        return []

    if estrategia in TAIL_STRATEGIES:
        return _select_tail_controlled_portfolio(
            candidates=candidates,
            scores=scores,
            config=config,
            quantidade=quantidade,
            rng=rng,
            ctx=ctx,
            usar_calibracao_score=usar_calibracao_score,
            calibration_strength=calibration_strength,
            calibration_target=calibration_target,
            null_model_samples=null_model_samples,
        )

    noise_scale = {
        "balanceada": 0.85,
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
        for idx, row in enumerate(ordered):
            if len(selected) >= quantidade:
                break
            t = tuple(row.tolist())
            if t in seen:
                continue
            _add(row)

    return [row.tolist() for row in selected[:quantidade]]


def _pair_keys(row: np.ndarray) -> list[tuple[int, int]]:
    nums = [int(n) for n in row.tolist()]
    return [tuple(pair) for pair in combinations(nums, 2)]


def _group_keys(row: np.ndarray, size: int) -> list[tuple[int, ...]]:
    nums = [int(n) for n in row.tolist()]
    return [tuple(group) for group in combinations(nums, size)]


def _cooccurrence_z(candidates: np.ndarray, ctx) -> np.ndarray:
    if ctx is None:
        return np.zeros(len(candidates), dtype=float)

    matriz = getattr(ctx, "matriz_coocorrencia", None)
    n = getattr(getattr(ctx, "config", None), "n_numbers", None)
    if (
        matriz is None
        or not hasattr(matriz, "shape")
        or n is None
        or matriz.shape != (n, n)
    ):
        return np.zeros(len(candidates), dtype=float)

    from app.core.generator_fast import _calcular_scores_coocorrencia_batch

    cooc = _calcular_scores_coocorrencia_batch(candidates - 1, matriz)
    std = cooc.std()
    if std < 1e-9:
        return np.zeros_like(cooc, dtype=float)
    return (cooc - cooc.mean()) / std


def _select_tail_controlled_portfolio(
    candidates: np.ndarray,
    scores: np.ndarray,
    config,
    quantidade: int,
    rng: np.random.Generator,
    ctx=None,
    usar_calibracao_score: bool = True,
    calibration_strength: float = 1.0,
    calibration_target: str = "historico_nulo",
    null_model_samples: int | None = None,
) -> list[list[int]]:
    """
    Seleciona o portfólio como conjunto (estratégia cauda_controlada).

    Preserva plausibilidade individual, mas adiciona ganho marginal por cluster
    controlado e penaliza redundância que não aumenta cobertura real do pacote.
    """
    noise_scale = 0.65
    base_cooc_weight = 0.20
    noise = rng.gumbel(0.0, noise_scale, size=len(scores))
    score_std = scores.std()
    score_z = (
        np.zeros_like(scores)
        if score_std < 1e-9
        else (scores - scores.mean()) / score_std
    )
    cooc_z = _cooccurrence_z(candidates, ctx)
    base_rank = score_z + np.clip(cooc_z, -1.0, 2.0) * base_cooc_weight + noise
    order = np.argsort(base_rank)[::-1]

    pool_size = min(len(order), max(quantidade * 350, 1200))
    order = order[:pool_size]
    ordered = candidates[order]
    ordered_score_z = score_z[order]
    ordered_cooc_z = cooc_z[order]
    calibration_bucket_idx = None
    calibration_target_probs = None
    calibration_counts = None
    calibration_strength = float(np.clip(calibration_strength, 0.0, 2.0))
    if usar_calibracao_score and calibration_strength > 0:
        from app.core.statistics.score_calibration import (
            bucket_indices,
            get_score_calibration_model,
        )

        calibration_scores = score_structural_batch(
            ordered,
            config,
            n_samples=null_model_samples,
        )
        model = get_score_calibration_model(
            config,
            df_historico=getattr(ctx, "df", None),
            n_samples=null_model_samples,
            target=calibration_target,
        )
        calibration_bucket_idx = bucket_indices(calibration_scores)
        calibration_target_probs = model.target_probabilities
        calibration_counts = np.zeros(len(BUCKET_LABELS), dtype=float)

    selected: list[np.ndarray] = []
    seen: set[tuple[int, ...]] = set()
    exposure: dict[int, int] = {}
    pair_exposure: dict[tuple[int, int], int] = {}

    dense_game = bool(getattr(config, "is_dense", False))
    overlap_limit = config.get_overlap_limit()
    expected_exposure = quantidade * config.bet_size / max(1, config.n_numbers)
    soft_target = max(2, int(np.ceil(expected_exposure * 1.25)))
    hard_cap = max(2, int(np.ceil(expected_exposure * 2.50)))
    if getattr(config, "slug", "") == "mega_sena_sorteio" and quantidade >= 20:
        hard_cap = 5
    total_pairs = max(1, comb(config.n_numbers, 2))
    expected_pair_reuse = quantidade * comb(config.bet_size, 2) / total_pairs
    if dense_game:
        pair_hard_cap = max(4, int(np.ceil(expected_pair_reuse * 1.35)))
    else:
        pair_hard_cap = 3

    def _would_break_hard_caps(row: np.ndarray) -> bool:
        if any(exposure.get(int(n), 0) >= hard_cap for n in row):
            return True
        return any(
            pair_exposure.get(pair, 0) >= pair_hard_cap for pair in _pair_keys(row)
        )

    def _calibration_marginal(idx: int) -> float:
        if (
            calibration_bucket_idx is None
            or calibration_target_probs is None
            or calibration_counts is None
        ):
            return 0.0
        bucket = int(calibration_bucket_idx[idx])
        selected_now = len(selected)
        expected_next = calibration_target_probs[bucket] * max(1, selected_now + 1)
        under = max(0.0, expected_next - calibration_counts[bucket])
        over = max(0.0, calibration_counts[bucket] + 1.0 - expected_next - 0.75)
        if quantidade <= 2:
            return under * 0.08 * calibration_strength
        return (under * 0.16 - over * 0.24) * calibration_strength

    def _overlap_penalty(row: np.ndarray) -> float:
        """Penalidade infinita (1e6) se o jogo repete demais com um já escolhido."""
        if not selected:
            return 0.0
        s = set(row.tolist())
        for prev in selected:
            if len(s.intersection(set(prev.tolist()))) > overlap_limit:
                return 1e6
        return 0.0

    def _marginal_score(idx: int, row: np.ndarray) -> float:
        pairs = _pair_keys(row)
        exposure_penalty = sum(
            max(0, exposure.get(int(n), 0) + 1 - soft_target) for n in row
        ) * 0.06
        pair_penalty = sum(
            max(0, pair_exposure.get(pair, 0) - 1) for pair in pairs
        ) * 0.01
        cluster_bonus = np.clip(ordered_cooc_z[idx], -1.0, 2.0) * 0.18
        return (
            ordered_score_z[idx]
            + cluster_bonus
            + _calibration_marginal(idx)
            - exposure_penalty
            - pair_penalty
            - _overlap_penalty(row)
        )

    def _register(idx: int, row: np.ndarray) -> None:
        selected.append(row)
        seen.add(tuple(row.tolist()))
        for n in row:
            nn = int(n)
            exposure[nn] = exposure.get(nn, 0) + 1
        for pair in _pair_keys(row):
            pair_exposure[pair] = pair_exposure.get(pair, 0) + 1
        if calibration_counts is not None and calibration_bucket_idx is not None:
            calibration_counts[int(calibration_bucket_idx[idx])] += 1

    remaining = set(range(len(ordered)))
    while len(selected) < quantidade and remaining:
        best_idx = None
        best_score = -np.inf
        for idx in list(remaining):
            row = ordered[idx]
            t = tuple(row.tolist())
            if t in seen or _would_break_hard_caps(row):
                remaining.discard(idx)
                continue
            marginal = _marginal_score(idx, row)
            if marginal > best_score:
                best_score = marginal
                best_idx = idx

        if best_idx is None:
            break

        remaining.discard(best_idx)
        _register(best_idx, ordered[best_idx].copy())

    if len(selected) < quantidade:
        for idx, row in enumerate(ordered):
            if len(selected) >= quantidade:
                break
            t = tuple(row.tolist())
            if t in seen or _would_break_hard_caps(row):
                continue
            _register(idx, row.copy())

    return [row.tolist() for row in selected[:quantidade]]


def portfolio_diagnostics(
    games: list[list[int]] | np.ndarray,
    config,
    matriz_coocorrencia=None,
) -> dict:
    """Resume concentração e diversidade de um pacote de jogos."""
    if games is None or len(games) == 0:
        return {}

    arr = np.asarray(games, dtype=int)
    if arr.ndim != 2:
        return {}

    exposure = {str(n): 0 for n in range(1, config.n_numbers + 1)}
    for row in arr:
        for n in row:
            exposure[str(int(n))] += 1
    used_counts = np.array([v for v in exposure.values() if v > 0], dtype=float)
    top_dezenas = sorted(
        ((int(k), int(v)) for k, v in exposure.items() if v > 0),
        key=lambda item: (-item[1], item[0]),
    )[:10]

    overlaps = []
    pair_counts: dict[tuple[int, int], int] = {}
    triple_counts: dict[tuple[int, int, int], int] = {}
    quad_counts: dict[tuple[int, int, int, int], int] = {}
    for i, row in enumerate(arr):
        row_set = set(row.tolist())
        for other in arr[i + 1 :]:
            overlaps.append(len(row_set.intersection(set(other.tolist()))))
        for pair in _pair_keys(row):
            pair_counts[pair] = pair_counts.get(pair, 0) + 1
        if config.bet_size >= 3:
            for triple in _group_keys(row, 3):
                triple_counts[triple] = triple_counts.get(triple, 0) + 1
        if config.bet_size >= 4:
            for quad in _group_keys(row, 4):
                quad_counts[quad] = quad_counts.get(quad, 0) + 1

    repeated_pairs = [count for count in pair_counts.values() if count > 1]
    repeated_triples = [count for count in triple_counts.values() if count > 1]
    repeated_quads = [count for count in quad_counts.values() if count > 1]
    features = extract_ticket_features_batch(arr, config)
    feature_summary = {}
    for metric in ("soma", "span", "pares", "gap_medio"):
        vals = features.get(metric)
        if vals is None or len(vals) == 0:
            continue
        feature_summary[metric] = {
            "media": round(float(np.mean(vals)), 4),
            "desvio": round(float(np.std(vals)), 4),
            "min": round(float(np.min(vals)), 4),
            "max": round(float(np.max(vals)), 4),
        }

    cooc_media = 0.0
    if (
        matriz_coocorrencia is not None
        and hasattr(matriz_coocorrencia, "shape")
        and matriz_coocorrencia.shape == (config.n_numbers, config.n_numbers)
    ):
        from app.core.generator_fast import _calcular_scores_coocorrencia_batch

        cooc_scores = _calcular_scores_coocorrencia_batch(arr - 1, matriz_coocorrencia)
        cooc_media = float(np.mean(cooc_scores)) if len(cooc_scores) else 0.0

    return {
        "exposicao_dezenas": exposure,
        "top_dezenas": [{"dezena": n, "vezes": v} for n, v in top_dezenas],
        "max_exposicao": int(max(exposure.values()) if exposure else 0),
        "media_exposicao_usadas": round(float(np.mean(used_counts)), 4)
        if len(used_counts)
        else 0.0,
        "desvio_exposicao_usadas": round(float(np.std(used_counts)), 4)
        if len(used_counts)
        else 0.0,
        "overlap_medio": round(float(np.mean(overlaps)), 4) if overlaps else 0.0,
        "overlap_max": int(max(overlaps) if overlaps else 0),
        "pares_repetidos": int(len(repeated_pairs)),
        "pares_repetidos_acima_2": int(
            sum(1 for count in repeated_pairs if count > 2)
        ),
        "max_repeticao_par": int(max(pair_counts.values()) if pair_counts else 0),
        "trincas_repetidas": int(len(repeated_triples)),
        "max_repeticao_trinca": int(
            max(triple_counts.values()) if triple_counts else 0
        ),
        "quadras_repetidas": int(len(repeated_quads)),
        "max_repeticao_quadra": int(max(quad_counts.values()) if quad_counts else 0),
        "coocorrencia_media": round(cooc_media, 4),
        "dispersao_features": feature_summary,
    }
