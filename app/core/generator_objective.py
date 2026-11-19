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
    usar_coocorrencia: bool = False,
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
        "moldura": 0.8,
        "cruz": 0.5,
    }
    high_bad_weights = {
        "max_final_repetido": 1.0,
        "max_dezena_repetida": 0.8,
        "max_linha": 0.8,
        "max_coluna": 0.7,
        "max_sequencia": 1.4,
        "diag_principal": 0.7,
        "diag_secundaria": 0.7,
        "simetria_reflexao": 0.7,
        "gap_regularidade": 0.9,
    }
    low_bad_weights = {
        "min_gap": 1.1,
        "compressibilidade_simples": 1.7,
        "finais_unicos": 0.7,
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
                null_model=_model,
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
        elast = getattr(ctx, "elasticidade_antipopular", None)
        if elast is not None:
            forca *= float(np.clip(1.0 + 0.50 * (float(elast) - 0.50), 0.75, 1.35))
        scores -= np.maximum(0.0, pop_pct - 60.0) / 40.0 * 2.0 * forca

        # Corte: jogos acima do limiar de razão de ganhadores (Mega, Quina e Lotofácil) levam
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

    if k == config.k:
        recent_bin = None
        draws_bin = getattr(ctx, "draws_bin", None)
        if draws_bin is not None and len(draws_bin) > 0:
            recent_bin = draws_bin[-10:]
        else:
            df_hist = getattr(ctx, "df", None)
            if (
                df_hist is not None
                and not getattr(df_hist, "empty", True)
                and all(col in df_hist.columns for col in config.draw_cols)
            ):
                from app.core.statistics.basic import build_draws_binary_matrix

                recent_bin, _ = build_draws_binary_matrix(df_hist.tail(10), config)

        if recent_bin is not None and len(recent_bin) > 0 and recent_bin.shape[1] == n:
            valid_idx = np.clip(indices, 0, n - 1)
            recent_hits = (
                recent_bin.astype(np.int16, copy=False).T[valid_idx].sum(axis=1)
            )
            max_recent_hits = recent_hits.max(axis=1)
            near_clone = max_recent_hits >= (config.k - 1)
            if np.any(near_clone):
                pen_clone = 2.5 if getattr(config, "is_dense", False) else 3.5
                scores[near_clone] -= pen_clone

    historico = getattr(ctx, "historico_set", None) or set()
    if k == config.k and historico:
        for i, row in enumerate(candidates):
            if tuple(row.tolist()) in historico:
                scores[i] = -np.inf

    return np.nan_to_num(scores, nan=-1e9, neginf=-1e9, posinf=1e9)


def _refine_coverage_preserving_buckets(
    selected: list[np.ndarray],
    selected_pool_idxs: list[int],
    ordered: np.ndarray,
    ordered_scores: np.ndarray,
    config,
    calibration_bucket_idx: np.ndarray | None,
    overlap_limit: int,
    max_exposure_cap: int | None = None,
    max_pair_cap: int | None = None,
) -> list[np.ndarray]:
    """
    Busca local 1-opt/2-opt que preserva exatamente as cotas de calibração de score
    e o corte de popularidade, reduzindo a variância de exposição e sobreposição máxima
    (especialmente relevante em jogos densos com faixas fixas como Lotofácil).
    """
    m = len(selected)
    if m < 3 or len(ordered) <= m or len(selected_pool_idxs) != m:
        return selected

    n_num = int(config.n_numbers)
    k = int(config.bet_size)
    is_dense = bool(getattr(config, "is_dense", False))
    w_exp = 0.45 if is_dense else 0.12
    w_ov = 0.55 if is_dense else 0.35

    arr = np.asarray(selected, dtype=int).copy()
    if int(arr.min()) < 1 or int(arr.max()) > n_num:
        return selected

    b_mat = np.zeros((m, n_num), dtype=np.int16)
    b_mat[np.arange(m)[:, None], arr - 1] = 1
    if not np.all(b_mat.sum(axis=1) == k):
        return selected

    used_tuples = {tuple(row.tolist()) for row in arr}
    sel_scores = np.array([float(ordered_scores[i]) for i in selected_pool_idxs], dtype=float)
    sel_buckets = (
        np.array([int(calibration_bucket_idx[i]) for i in selected_pool_idxs], dtype=int)
        if calibration_bucket_idx is not None
        else np.zeros(m, dtype=int)
    )

    # Candidatos alternativos limpos (aprovados no corte de popularidade) agrupados por bucket
    max_cand = min(len(ordered), max(m * 16, 120))
    bucket_pools: dict[int, list[int]] = {}
    for idx in range(max_cand):
        if float(ordered_scores[idx]) <= -50.0:
            continue
        b_id = int(calibration_bucket_idx[idx]) if calibration_bucket_idx is not None else 0
        bucket_pools.setdefault(b_id, []).append(idx)

    exp_target = m * k / float(max(1, n_num))
    exp_counts = b_mat.sum(axis=0).astype(float)

    def _cov_cost(b_curr: np.ndarray, exp_c: np.ndarray) -> float:
        g = b_curr @ b_curr.T
        ov_sq = float(np.sum(g * g) - m * (k ** 2))
        exp_var = float(np.sum((exp_c - exp_target) ** 2))
        return w_ov * ov_sq + w_exp * exp_var

    curr_cost = _cov_cost(b_mat, exp_counts)

    for pos in range(m):
        b_id = int(sel_buckets[pos])
        pool_idxs = bucket_pools.get(b_id, [])
        if not pool_idxs:
            continue
        old_row = arr[pos]
        old_vec = b_mat[pos].copy()
        exp_without = exp_counts - old_vec
        other_b = np.delete(b_mat, pos, axis=0)

        for cand_idx in pool_idxs[:24]:
            cand_row = ordered[cand_idx]
            cand_t = tuple(cand_row.tolist())
            if cand_t in used_tuples:
                continue
            # Não aceita troca que derrube significativamente o score de plausibilidade individual
            if float(ordered_scores[cand_idx]) < sel_scores[pos] - 0.65:
                continue
            cand_vec = np.zeros(n_num, dtype=np.int16)
            cand_vec[cand_row - 1] = 1
            if int(cand_vec.sum()) != k:
                continue
            overlaps = other_b @ cand_vec
            if int(overlaps.max()) > overlap_limit:
                continue
            new_exp = exp_without + cand_vec
            if max_exposure_cap is not None and int(new_exp.max()) > max_exposure_cap:
                continue
            if max_pair_cap is not None and k >= 2:
                sub_b = other_b[:, cand_row - 1]
                pair_mat = sub_b.T @ sub_b
                np.fill_diagonal(pair_mat, 0)
                if int(pair_mat.max()) + 1 > max_pair_cap:
                    continue
            b_mat[pos] = cand_vec
            new_cost = _cov_cost(b_mat, new_exp)
            if new_cost + 1e-6 < curr_cost:
                used_tuples.discard(tuple(old_row.tolist()))
                used_tuples.add(cand_t)
                arr[pos] = cand_row.copy()
                old_row = arr[pos]
                old_vec = cand_vec
                exp_counts = new_exp
                curr_cost = new_cost
                sel_scores[pos] = float(ordered_scores[cand_idx])
            else:
                b_mat[pos] = old_vec

    return [row.copy() for row in arr]


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

    finite_mask = np.isfinite(scores) & (scores > -1e8)
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
    pool_limit = min(len(order), max(quantidade * 180, 1200))
    ordered = candidates[order[:pool_limit]]
    ordered_raw_scores = scores[order[:pool_limit]]

    calibration_bucket_idx = None
    bucket_quotas = None
    bucket_counts = np.zeros(len(BUCKET_LABELS), dtype=int)
    calibration_strength = float(np.clip(calibration_strength, 0.0, 2.0))
    if usar_calibracao_score and calibration_strength > 0 and estrategia != "pura":
        from app.core.statistics.score_calibration import (
            bucket_indices,
            get_score_calibration_model,
        )

        cal_scores = score_structural_batch(
            ordered,
            config,
            n_samples=null_model_samples,
        )
        cal_model = get_score_calibration_model(
            config,
            df_historico=getattr(ctx, "df", None),
            n_samples=null_model_samples,
            target=calibration_target,
        )
        calibration_bucket_idx = bucket_indices(cal_scores)
        raw_quotas = cal_model.target_probabilities * quantidade
        bucket_quotas = np.floor(raw_quotas).astype(int)
        rem = int(max(0, quantidade - int(bucket_quotas.sum())))
        if rem > 0:
            rem_order = np.argsort(raw_quotas - bucket_quotas)[::-1][:rem]
            bucket_quotas[rem_order] += 1

    from app.core.statistics.cluster_profile import assign_clusters_batch

    ordered_archetypes = assign_clusters_batch(
        ordered,
        config,
        getattr(ctx, "clusters_historicos", None) or getattr(ctx, "clusters_info", None),
    )
    n_arch_unique = max(1, len(np.unique(ordered_archetypes)))
    arch_limit = max(1, int(np.ceil(quantidade / n_arch_unique)) + 1)
    archetype_counts: dict[int, int] = {}

    selected: list[np.ndarray] = []
    selected_pool_idxs: list[int] = []
    seen: set[tuple[int, ...]] = set()
    exposure: dict[int, int] = {}
    feature_exposure: dict[tuple, int] = {}
    overlap_limit = config.get_overlap_limit()
    expected_exposure = quantidade * config.bet_size / max(1, config.n_numbers)
    if config.is_sparse:
        exposure_limit = max(1, int(np.ceil(expected_exposure * 2.5)))
    elif getattr(config, "is_dense", False):
        # Em jogos densos dominados por faixas fixas (Lotofácil), exposição quase-uniforme
        # maximiza P(>= 1 prêmio) e reduz a variância do retorno fixo em ~15%.
        exposure_limit = max(2, int(np.ceil(expected_exposure * 1.25)))
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

    def _fits_bucket_quota(idx: int, slack: int = 0) -> bool:
        if calibration_bucket_idx is None or bucket_quotas is None:
            return True
        b = int(calibration_bucket_idx[idx])
        return int(bucket_counts[b]) < int(bucket_quotas[b]) + slack

    def _add(idx: int, row: np.ndarray) -> None:
        selected.append(row.copy())
        selected_pool_idxs.append(int(idx))
        seen.add(tuple(row.tolist()))
        for n in row:
            nn = int(n)
            exposure[nn] = exposure.get(nn, 0) + 1
        key = _feature_key(idx)
        feature_exposure[key] = feature_exposure.get(key, 0) + 1
        if calibration_bucket_idx is not None:
            bucket_counts[int(calibration_bucket_idx[idx])] += 1
        arch_id = int(ordered_archetypes[idx])
        archetype_counts[arch_id] = archetype_counts.get(arch_id, 0) + 1

    # Passo 1: respeita cota exata de bucket de calibração, limite de arquétipo, exposição e overlap
    for idx, row in enumerate(ordered):
        if len(selected) >= quantidade:
            break
        t = tuple(row.tolist())
        if t in seen:
            continue
        if not _fits_bucket_quota(idx, slack=0):
            continue
        if not _fits_exposure(row, exposure_limit):
            continue
        if not _fits_feature_exposure(idx, 1):
            continue
        arch_id = int(ordered_archetypes[idx])
        if archetype_counts.get(arch_id, 0) >= arch_limit:
            continue
        s = set(t)
        if all(
            len(s.intersection(set(prev.tolist()))) <= overlap_limit
            for prev in selected
        ):
            _add(idx, row)

    # Passo 2: relaxa feature_exposure e arquétipo mantendo cota de bucket (slack=0 ou 1) e overlap
    if len(selected) < quantidade:
        for slack in (0, 1):
            if len(selected) >= quantidade:
                break
            for idx, row in enumerate(ordered):
                if len(selected) >= quantidade:
                    break
                t = tuple(row.tolist())
                if t in seen:
                    continue
                if not _fits_bucket_quota(idx, slack=slack):
                    continue
                if not _fits_exposure(row, exposure_limit + slack):
                    continue
                if not _fits_feature_exposure(idx, 2):
                    continue
                s = set(t)
                if all(
                    len(s.intersection(set(prev.tolist()))) <= overlap_limit
                    for prev in selected
                ):
                    _add(idx, row)

    # Passo 3: se restrições/fixos tornarem a diversidade estrita impossível, relaxa cota de bucket
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
            _add(idx, row)

    if len(selected) < quantidade:
        for idx, row in enumerate(ordered):
            if len(selected) >= quantidade:
                break
            t = tuple(row.tolist())
            if t in seen:
                continue
            _add(idx, row)

    if len(selected) < quantidade and pool_limit < len(order):
        for raw_idx in order[pool_limit:]:
            if len(selected) >= quantidade:
                break
            row = candidates[raw_idx]
            t = tuple(row.tolist())
            if t in seen:
                continue
            selected.append(row.copy())
            seen.add(t)

    if len(selected) == quantidade and len(selected_pool_idxs) == quantidade:
        selected = _refine_coverage_preserving_buckets(
            selected[:quantidade],
            selected_pool_idxs[:quantidade],
            ordered,
            ordered_raw_scores,
            config,
            calibration_bucket_idx,
            overlap_limit,
        )

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
    clean_mask = scores > -50.0
    if np.any(clean_mask):
        clean_mean = float(scores[clean_mask].mean())
        clean_std = float(scores[clean_mask].std())
    else:
        clean_mean = float(scores.mean())
        clean_std = float(scores.std())
    score_z = (
        np.zeros_like(scores)
        if clean_std < 1e-9
        else (scores - clean_mean) / clean_std
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
    bucket_quotas = None
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
        raw_quotas = calibration_target_probs * quantidade
        bucket_quotas = np.floor(raw_quotas).astype(int)
        rem = int(max(0, quantidade - int(bucket_quotas.sum())))
        if rem > 0:
            rem_order = np.argsort(raw_quotas - bucket_quotas)[::-1][:rem]
            bucket_quotas[rem_order] += 1

    from app.core.statistics.cluster_profile import assign_clusters_batch

    ordered_archetypes = assign_clusters_batch(
        ordered,
        config,
        getattr(ctx, "clusters_historicos", None) or getattr(ctx, "clusters_info", None),
    )
    n_archetypes = max(1, len(np.unique(ordered_archetypes)))
    archetype_counts: dict[int, int] = {}

    selected: list[np.ndarray] = []
    selected_pool_idxs: list[int] = []
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
        quota_adjust = 0.0
        if bucket_quotas is not None:
            if calibration_counts[bucket] < bucket_quotas[bucket]:
                quota_adjust = 0.35
            elif calibration_counts[bucket] >= bucket_quotas[bucket] + 1:
                quota_adjust = -0.95
            elif calibration_counts[bucket] >= bucket_quotas[bucket]:
                quota_adjust = -0.45
        return (under * 0.22 - over * 0.32 + quota_adjust) * calibration_strength

    def _archetype_marginal(idx: int) -> float:
        arch_id = int(ordered_archetypes[idx])
        count = archetype_counts.get(arch_id, 0)
        expected_arch = (len(selected) + 1) / float(n_archetypes)
        if count < expected_arch:
            return 0.10
        return -0.05 * max(0.0, count - expected_arch)

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
            + _archetype_marginal(idx)
            - exposure_penalty
            - pair_penalty
            - _overlap_penalty(row)
        )

    def _register(idx: int, row: np.ndarray) -> None:
        selected.append(row)
        selected_pool_idxs.append(idx)
        seen.add(tuple(row.tolist()))
        for n in row:
            nn = int(n)
            exposure[nn] = exposure.get(nn, 0) + 1
        for pair in _pair_keys(row):
            pair_exposure[pair] = pair_exposure.get(pair, 0) + 1
        if calibration_counts is not None and calibration_bucket_idx is not None:
            calibration_counts[int(calibration_bucket_idx[idx])] += 1
        arch_id = int(ordered_archetypes[idx])
        archetype_counts[arch_id] = archetype_counts.get(arch_id, 0) + 1

    non_cut_indices = [i for i in range(len(ordered)) if ordered_score_z[i] > -10.0]
    if len(non_cut_indices) >= quantidade:
        remaining = set(non_cut_indices)
    else:
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

    # Fallback progressivo: relaxa pair_hard_cap/hard_cap priorizando candidatos aprovados no corte
    if len(selected) < quantidade:
        candidate_indices = (
            non_cut_indices + [i for i in range(len(ordered)) if ordered_score_z[i] <= -10.0]
            if non_cut_indices
            else list(range(len(ordered)))
        )
        for slack in (1, 2, 4):
            if len(selected) >= quantidade:
                break
            for idx in candidate_indices:
                if len(selected) >= quantidade:
                    break
                row = ordered[idx]
                t = tuple(row.tolist())
                if t in seen:
                    continue
                if _overlap_penalty(row) > 0:
                    continue
                if any(exposure.get(int(n), 0) >= hard_cap + slack for n in row):
                    continue
                if any(
                    pair_exposure.get(pair, 0) >= pair_hard_cap + slack * 2
                    for pair in _pair_keys(row)
                ):
                    continue
                _register(idx, row.copy())

    if len(selected) < quantidade:
        candidate_indices = (
            non_cut_indices + [i for i in range(len(ordered)) if ordered_score_z[i] <= -10.0]
            if non_cut_indices
            else list(range(len(ordered)))
        )
        for idx in candidate_indices:
            if len(selected) >= quantidade:
                break
            row = ordered[idx]
            t = tuple(row.tolist())
            if t in seen:
                continue
            _register(idx, row.copy())

    if len(selected) == quantidade and len(selected_pool_idxs) == quantidade:
        selected = _refine_coverage_preserving_buckets(
            selected[:quantidade],
            selected_pool_idxs[:quantidade],
            ordered,
            scores[order],
            config,
            calibration_bucket_idx,
            overlap_limit,
            max_exposure_cap=hard_cap,
            max_pair_cap=pair_hard_cap,
        )

    return [row.tolist() for row in selected[:quantidade]]


def portfolio_diagnostics(
    games: list[list[int]] | np.ndarray,
    config,
    matriz_coocorrencia=None,
    include_higher_order: bool = True,
    include_dispersao: bool = True,
    clusters_cache: dict | None = None,
) -> dict:
    """Resume concentração, diversidade combinatória e arquétipos estruturais de um pacote."""
    if games is None or len(games) == 0:
        return {}

    arr = np.asarray(games, dtype=int)
    if arr.ndim != 2:
        return {}

    m, k = arr.shape
    n_numbers = int(config.n_numbers)
    in_bounds = arr.size > 0 and int(arr.min()) >= 1 and int(arr.max()) <= n_numbers

    used_fast_path = False
    if in_bounds:
        B = np.zeros((m, n_numbers), dtype=np.int32)
        B[np.arange(m)[:, None], arr - 1] = 1
        if np.all(B.sum(axis=1) == k):
            used_fast_path = True
            exposure_counts = B.sum(axis=0)
            exposure = {str(n): int(exposure_counts[n - 1]) for n in range(1, n_numbers + 1)}

            if m >= 2:
                G = B @ B.T
                overlaps_arr = G[np.triu_indices(m, k=1)]
                overlap_medio = round(float(np.mean(overlaps_arr)), 4)
                overlap_max = int(np.max(overlaps_arr))
            else:
                overlap_medio = 0.0
                overlap_max = 0

            P = B.T @ B
            pi, pj = np.triu_indices(n_numbers, k=1)
            pair_vals = P[pi, pj]
            nz_pairs = pair_vals[pair_vals > 0]
            pares_repetidos = int(np.sum(nz_pairs > 1))
            pares_repetidos_acima_2 = int(np.sum(nz_pairs > 2))
            max_repeticao_par = int(np.max(nz_pairs)) if nz_pairs.size else 0

            trincas_repetidas = 0
            max_repeticao_trinca = 1 if (include_higher_order and config.bet_size >= 3 and k >= 3 and m >= 1) else 0
            quadras_repetidas = 0
            max_repeticao_quadra = 1 if (include_higher_order and config.bet_size >= 4 and k >= 4 and m >= 1) else 0

            if include_higher_order and config.bet_size >= 3 and k >= 3 and m >= 2:
                for a in np.flatnonzero(exposure_counts[: max(0, n_numbers - 2)] >= 2):
                    mask_a = B[:, a] == 1
                    Ra = B[mask_a, a + 1 :]
                    Pa = Ra.T @ Ra
                    np.fill_diagonal(Pa, 0)
                    rep_a = int(np.count_nonzero(Pa > 1)) // 2
                    if rep_a > 0:
                        trincas_repetidas += rep_a
                        max_repeticao_trinca = max(max_repeticao_trinca, int(Pa.max()))

                    if config.bet_size >= 4 and k >= 4 and a < n_numbers - 3:
                        bs = np.flatnonzero(P[a, a + 1 : n_numbers - 2] >= 2) + (a + 1)
                        for b in bs:
                            Rab = B[mask_a & (B[:, b] == 1), b + 1 :]
                            Qab = Rab.T @ Rab
                            np.fill_diagonal(Qab, 0)
                            rep_ab = int(np.count_nonzero(Qab > 1)) // 2
                            if rep_ab > 0:
                                quadras_repetidas += rep_ab
                                max_repeticao_quadra = max(max_repeticao_quadra, int(Qab.max()))

    if not used_fast_path:
        exposure = {str(n): 0 for n in range(1, n_numbers + 1)}
        for row in arr:
            for n in row:
                key = str(int(n))
                exposure[key] = exposure.get(key, 0) + 1

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
            if include_higher_order and config.bet_size >= 3:
                for triple in _group_keys(row, 3):
                    triple_counts[triple] = triple_counts.get(triple, 0) + 1
            if include_higher_order and config.bet_size >= 4:
                for quad in _group_keys(row, 4):
                    quad_counts[quad] = quad_counts.get(quad, 0) + 1

        repeated_pairs = [count for count in pair_counts.values() if count > 1]
        repeated_triples = [count for count in triple_counts.values() if count > 1]
        repeated_quads = [count for count in quad_counts.values() if count > 1]
        overlap_medio = round(float(np.mean(overlaps)), 4) if overlaps else 0.0
        overlap_max = int(max(overlaps) if overlaps else 0)
        pares_repetidos = int(len(repeated_pairs))
        pares_repetidos_acima_2 = int(sum(1 for count in repeated_pairs if count > 2))
        max_repeticao_par = int(max(pair_counts.values()) if pair_counts else 0)
        trincas_repetidas = int(len(repeated_triples))
        max_repeticao_trinca = int(max(triple_counts.values()) if triple_counts else 0)
        quadras_repetidas = int(len(repeated_quads))
        max_repeticao_quadra = int(max(quad_counts.values()) if quad_counts else 0)

    used_counts = np.array([v for v in exposure.values() if v > 0], dtype=float)
    top_dezenas = sorted(
        ((int(key), int(v)) for key, v in exposure.items() if v > 0),
        key=lambda item: (-item[1], item[0]),
    )[:10]

    feature_summary = {}
    if include_dispersao:
        features = extract_ticket_features_batch(arr, config)
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

    from app.core.statistics.cluster_profile import assign_clusters_batch

    arch_ids = assign_clusters_batch(arr, config, clusters_cache)
    if len(arch_ids) > 0:
        uniq_arch, arch_counts = np.unique(arch_ids, return_counts=True)
        arch_probs = arch_counts / float(len(arch_ids))
        raw_entropy = float(-np.sum(arch_probs * np.log(np.maximum(arch_probs, 1e-12))))
        max_k = (
            max(2, int(clusters_cache.get("n_clusters", 5)))
            if isinstance(clusters_cache, dict) and "n_clusters" in clusters_cache
            else 6
        )
        entropia_arquetipos = round(min(1.0, raw_entropy / float(np.log(max_k))), 4)
        arquetipos_unicos = int(len(uniq_arch))
        distribuicao_arquetipos = {
            str(int(cid)): int(cnt) for cid, cnt in zip(uniq_arch, arch_counts)
        }
    else:
        entropia_arquetipos = 0.0
        arquetipos_unicos = 0
        distribuicao_arquetipos = {}

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
        "overlap_medio": overlap_medio,
        "overlap_max": overlap_max,
        "pares_repetidos": pares_repetidos,
        "pares_repetidos_acima_2": pares_repetidos_acima_2,
        "max_repeticao_par": max_repeticao_par,
        "trincas_repetidas": trincas_repetidas,
        "max_repeticao_trinca": max_repeticao_trinca,
        "quadras_repetidas": quadras_repetidas,
        "max_repeticao_quadra": max_repeticao_quadra,
        "coocorrencia_media": round(cooc_media, 4),
        "arquetipos_unicos": arquetipos_unicos,
        "entropia_arquetipos": entropia_arquetipos,
        "distribuicao_arquetipos": distribuicao_arquetipos,
        "dispersao_features": feature_summary,
    }
