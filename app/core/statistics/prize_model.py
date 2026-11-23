"""Financial diagnostics for lottery backtests.

The historical spreadsheets bundled with the project only contain drawn
numbers, not paid prizes per contest.  This module therefore works with an
explicit prize table: fixed tiers are provided where they are stable enough to
be useful, and variable tiers can be supplied by CLI overrides.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import comb
from typing import Any

import numpy as np
import pandas as pd

from app.core.lottery import GameConfig


DEFAULT_PRIZE_TABLES: dict[str, dict[int, float]] = {
    # Official fixed-tier prizes for the current Lotofácil base game (R$ 3,50).
    # The 14/15 tiers are variable and intentionally left out unless supplied.
    "loto_facil_sorteio": {11: 7.0, 12: 14.0, 13: 35.0},
}

TIER_HITS_BY_SLUG: dict[str, dict[int, int]] = {
    "mega_sena_sorteio": {1: 6, 2: 5, 3: 4},
    "quina_sorteio": {1: 5, 2: 4, 3: 3, 4: 2},
    "loto_facil_sorteio": {1: 15, 2: 14, 3: 13, 4: 12, 5: 11},
    "loto_mania_sorteio": {1: 20, 2: 19, 3: 18, 4: 17, 5: 16, 6: 15, 7: 0},
}

# Fração líquida média da arrecadação destinada à faixa 1 em concursos regulares (fallback estatutário)
DEFAULT_FRESH_F1_RATIO_BY_SLUG: dict[str, float] = {
    "mega_sena_sorteio": 0.1226,
    "quina_sorteio": 0.1073,
    "loto_facil_sorteio": 0.0783,
    "loto_mania_sorteio": 0.1379,
}


def _parse_bool_series(series: pd.Series) -> np.ndarray:
    """Converte série booleana/numérica/string ('True'/'False'/'1'/'0') com segurança."""
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).to_numpy(dtype=bool)
    if pd.api.types.is_numeric_dtype(series):
        return (pd.to_numeric(series, errors="coerce").fillna(0.0) != 0.0).to_numpy(dtype=bool)
    s = series.fillna("").astype(str).str.strip().str.lower()
    return s.isin({"true", "1", "1.0", "sim", "s", "t", "yes"}).to_numpy(dtype=bool)


def filtrar_detalhes_causais(
    detalhes_df: pd.DataFrame | None,
    df_historico: pd.DataFrame | None,
) -> pd.DataFrame:
    """
    Restringe `detalhes_df` estritamente aos concursos presentes em `df_historico`
    para impedir vazamento temporal em backtests walk-forward.
    """
    if detalhes_df is None:
        return pd.DataFrame()
    if df_historico is None:
        return detalhes_df
    if getattr(detalhes_df, "empty", True):
        return detalhes_df
    if getattr(df_historico, "empty", True):
        return detalhes_df.iloc[0:0]
    if "Concurso" in detalhes_df.columns:
        concursos = set(df_historico.index.tolist())
        return detalhes_df[detalhes_df["Concurso"].isin(concursos)]
    idx_comum = detalhes_df.index.intersection(df_historico.index)
    return detalhes_df.loc[idx_comum]


@dataclass(frozen=True)
class FinancialDiagnostics:
    cost: float
    gross_return: float
    net_return: float
    roi: float
    profit_factor: float
    prize_table: dict[str, float]
    paid_hits: dict[str, int]
    n_bets: int
    n_draws: int
    stake_per_bet: float
    mode: str


def parse_prize_table(values: list[str] | None) -> dict[int, float]:
    table: dict[int, float] = {}
    for raw in values or []:
        if "=" not in raw:
            raise ValueError(f"Premio invalido '{raw}'. Use acertos=valor, ex: 14=1500.")
        key, value = raw.split("=", 1)
        try:
            hits = int(key.strip())
            amount = float(value.strip().replace(",", "."))
        except ValueError as exc:
            raise ValueError(f"Premio invalido '{raw}'. Use acertos=valor.") from exc
        if hits < 0 or amount < 0:
            raise ValueError(f"Premio invalido '{raw}'. Acertos/valor devem ser positivos.")
        table[hits] = amount
    return table


def resolve_prize_table(
    config: GameConfig,
    overrides: dict[int, float] | None = None,
    include_defaults: bool = True,
) -> dict[int, float]:
    table: dict[int, float] = {}
    if include_defaults:
        table.update(DEFAULT_PRIZE_TABLES.get(config.slug, {}))
    table.update(overrides or {})
    return {int(k): float(v) for k, v in sorted(table.items()) if float(v) > 0}


def hypergeometric_hit_probability(
    n_numbers: int, k_draw: int, k_bet: int, hits: int
) -> float:
    """Exact hypergeometric probability P(H = hits) for a single ticket."""
    if hits < 0 or hits > min(k_draw, k_bet):
        return 0.0
    rem_draw = k_draw - hits
    rem_pool = n_numbers - k_bet
    if rem_draw < 0 or rem_draw > rem_pool:
        return 0.0
    total = comb(n_numbers, k_draw)
    if total <= 0:
        return 0.0
    return float(comb(k_bet, hits) * comb(rem_pool, rem_draw)) / float(total)


def poisson_retention_factor(lam: float | np.ndarray, r: float | np.ndarray = 1.0) -> float | np.ndarray:
    """
    Expected prize fraction E[1 / (1 + W)] when other winners follow W ~ Poisson(r * lam).
    Equals (1 - exp(-mu)) / mu where mu = r * lam, with smooth limit 1 - mu/2 as mu -> 0.
    """
    mu = np.asarray(lam, dtype=float) * np.asarray(r, dtype=float)
    scalar = mu.ndim == 0
    mu_arr = np.atleast_1d(np.maximum(mu, 0.0))
    out = np.ones_like(mu_arr, dtype=float)
    small = (mu_arr > 0.0) & (mu_arr < 1e-6)
    large = mu_arr >= 1e-6
    out[small] = 1.0 - 0.5 * mu_arr[small] + (mu_arr[small] ** 2) / 6.0
    out[large] = -np.expm1(-mu_arr[large]) / mu_arr[large]
    return float(out[0]) if scalar else out


def poisson_ev_elasticity(lam: float | np.ndarray, r: float | np.ndarray = 1.0) -> float | np.ndarray:
    """
    Absolute elasticity |d log E[share] / d log r| = 1 - mu / (exp(mu) - 1) for mu = r * lam.
    Approaches 0 when mu -> 0 (no dilution) and 1 when mu >> 1 (full parimutuel dilution).
    """
    mu = np.asarray(lam, dtype=float) * np.asarray(r, dtype=float)
    scalar = mu.ndim == 0
    mu_arr = np.atleast_1d(np.maximum(mu, 0.0))
    out = np.zeros_like(mu_arr, dtype=float)
    small = (mu_arr > 0.0) & (mu_arr < 1e-5)
    large = (mu_arr >= 1e-5) & (mu_arr < 500.0)
    huge = mu_arr >= 500.0
    out[small] = 0.5 * mu_arr[small] - (mu_arr[small] ** 2) / 12.0
    out[large] = 1.0 - mu_arr[large] / np.expm1(mu_arr[large])
    out[huge] = 1.0
    out = np.clip(out, 0.0, 1.0)
    return float(out[0]) if scalar else out


# Razão histórica típica (est_prev / arr_real) em concursos especiais (fallback regulatório)
DEFAULT_SPECIAL_EST_TO_ARR_RATIO_BY_SLUG: dict[str, float] = {
    "mega_sena_sorteio": 0.30,
    "quina_sorteio": 0.52,
    "loto_facil_sorteio": 0.33,
    "loto_mania_sorteio": 0.35,
}


def _detectar_concurso_especial_ex_ante(
    acum_prox_v: float,
    acum_esp_v: float,
    est_prox_v: float = 0.0,
    med_arr_recente: float = 0.0,
) -> bool:
    """
    Detector estritamente ex-ante (usa apenas colunas disponíveis em t-1) de concurso especial
    (Mega da Virada, Quina de São João, Lotofácil da Independência).
    Nos dados reais da Caixa, na véspera do concurso especial vale:
    `valorAcumuladoProximoConcurso == valorAcumuladoConcursoEspecial > 0` com salto
    forte na estimativa de prêmio (`est_prox >= 1.5 * acum_prox` e `>= 3x` arrecadação típica).
    """
    if acum_prox_v <= 0.0 or acum_esp_v <= 0.0 or est_prox_v <= 0.0:
        return False
    exata_igualdade = bool(np.isclose(acum_prox_v, acum_esp_v, rtol=1e-4, atol=0.05))
    salto_estimativa = est_prox_v >= 1.45 * acum_prox_v
    if exata_igualdade and salto_estimativa:
        if med_arr_recente <= 0.0 or est_prox_v >= 2.5 * med_arr_recente:
            return True
    if (
        med_arr_recente > 0.0
        and est_prox_v >= max(1.5e8, 6.0 * med_arr_recente)
        and acum_prox_v >= 0.85 * acum_esp_v
        and salto_estimativa
    ):
        return True
    return False


def estimar_ev_concurso_ex_ante(
    config: GameConfig,
    detalhes_df: pd.DataFrame | None = None,
    razao_popularidade: float = 1.0,
    agio_bolao: float = 0.0,
    janela_treino: int = 150,
    conformal_q90_log_pop: float = 0.0,
) -> dict[str, Any]:
    """
    Causal ex-ante expected value gatekeeper with Poisson crowd dilution,
    dedicated special-contest regime handling, and split-conformal EV bounds.

    Uses only information available at contest t-1 (`valorEstimadoProximoConcurso`,
    `valorAcumuladoProximoConcurso`, `valorAcumuladoConcursoEspecial`, `acumulou`,
    and `valorArrecadado`) to predict the expected net return per unit stake at contest t.
    """
    price = float(config.game_price)
    r_eff = max(float(razao_popularidade), 1e-3)
    q_pop = max(0.0, float(conformal_q90_log_pop))
    fator_bolao = 1.0 / max(1.0, 1.0 + max(0.0, float(agio_bolao)))
    tier_map = TIER_HITS_BY_SLUG.get(config.slug, {})
    fixed_tiers = DEFAULT_PRIZE_TABLES.get(config.slug, {})

    ev_fixo = sum(
        hypergeometric_hit_probability(config.n_numbers, config.k, config.bet_size, h) * val
        for h, val in fixed_tiers.items()
    )
    ev_fixo_ratio = (ev_fixo / price) * fator_bolao if price > 0 else 0.0

    if detalhes_df is None:
        from app.core.statistics.popularidade_medida import carregar_detalhes

        detalhes_df = carregar_detalhes(config)

    if detalhes_df is None or getattr(detalhes_df, "empty", True):
        return {
            "disponivel": False,
            "ev_por_real_aleatorio": round(ev_fixo_ratio, 4),
            "ev_por_real_ajustado": round(ev_fixo_ratio, 4),
            "ev_fixo_por_real": round(ev_fixo_ratio, 4),
            "ev_rateado_por_real": 0.0,
            "ganho_relativo_antipopular": 0.0,
            "elasticidade_antipopular": 0.0,
            "concurso_especial_detectado": False,
            "recomendacao_aposta": "INDISPONIVEL",
        }

    from app.core.statistics.popularidade_medida import filtrar_arrecadacao_valida_causal

    df = detalhes_df.copy()
    if "Concurso" in df.columns:
        df = df.sort_values("Concurso")
    else:
        df = df.sort_index()

    arr_col = pd.to_numeric(df.get("valorArrecadado"), errors="coerce")
    arr_valido = filtrar_arrecadacao_valida_causal(arr_col, game_price=price)
    df = df[arr_col.notna() & (arr_col > 0) & arr_valido].copy()
    if len(df) < 30:
        return {
            "disponivel": False,
            "ev_por_real_aleatorio": round(ev_fixo_ratio, 4),
            "ev_por_real_ajustado": round(ev_fixo_ratio, 4),
            "ev_fixo_por_real": round(ev_fixo_ratio, 4),
            "ev_rateado_por_real": 0.0,
            "ganho_relativo_antipopular": 0.0,
            "elasticidade_antipopular": 0.0,
            "concurso_especial_detectado": False,
            "recomendacao_aposta": "INDISPONIVEL",
        }

    # Extrai histórico completo causal para calibrar razão de concursos especiais (raros: ~1/ano)
    arr_all = pd.to_numeric(df["valorArrecadado"], errors="coerce").to_numpy(dtype=float)
    est_all = pd.to_numeric(
        df.get("valorEstimadoProximoConcurso", pd.Series(0.0, index=df.index)),
        errors="coerce",
    ).fillna(0.0).to_numpy(dtype=float)
    acum_prox_all = pd.to_numeric(
        df.get("valorAcumuladoProximoConcurso", pd.Series(0.0, index=df.index)),
        errors="coerce",
    ).fillna(0.0).to_numpy(dtype=float)
    acum_esp_all = pd.to_numeric(
        df.get("valorAcumuladoConcursoEspecial", pd.Series(0.0, index=df.index)),
        errors="coerce",
    ).fillna(0.0).to_numpy(dtype=float)
    f1_w_all = pd.to_numeric(
        df.get("faixa1_ganhadores", pd.Series(0.0, index=df.index)), errors="coerce"
    ).fillna(0.0).to_numpy(dtype=float)
    f1_p_all = pd.to_numeric(
        df.get("faixa1_premio", pd.Series(0.0, index=df.index)), errors="coerce"
    ).fillna(0.0).to_numpy(dtype=float)

    med_arr_all = float(np.median(arr_all[-min(50, len(arr_all)) :]))
    is_esp_prev_all = np.array(
        [
            _detectar_concurso_especial_ex_ante(
                acum_prox_all[i], acum_esp_all[i], est_all[i], med_arr_all
            )
            for i in range(len(arr_all))
        ],
        dtype=bool,
    )
    esp_ratios_hist = []
    esp_cal_f1_hist = []
    for i in range(len(arr_all) - 1):
        if is_esp_prev_all[i] and est_all[i] > 0.0 and arr_all[i + 1] > 0.0:
            r_ea = float(est_all[i] / arr_all[i + 1])
            if 0.10 <= r_ea <= 1.20:
                esp_ratios_hist.append(r_ea)
            if f1_w_all[i + 1] > 0.0 and f1_p_all[i + 1] > 0.0:
                c_f1 = float((f1_w_all[i + 1] * f1_p_all[i + 1]) / est_all[i])
                if 0.50 <= c_f1 <= 1.50:
                    esp_cal_f1_hist.append(c_f1)

    default_esp_ratio = DEFAULT_SPECIAL_EST_TO_ARR_RATIO_BY_SLUG.get(config.slug, 0.35)
    esp_ratios_rec = esp_ratios_hist[-4:]
    esp_cal_f1_rec = esp_cal_f1_hist[-4:]
    if len(esp_ratios_rec) >= 2:
        ratio_est_arr_esp = float(np.clip(np.median(esp_ratios_rec), 0.18, 0.70))
    elif len(esp_ratios_rec) == 1:
        ratio_est_arr_esp = float(
            np.clip(0.5 * esp_ratios_rec[0] + 0.5 * default_esp_ratio, 0.18, 0.70)
        )
    else:
        ratio_est_arr_esp = default_esp_ratio

    cal_f1_esp = (
        float(np.clip(np.median(esp_cal_f1_rec), 0.75, 1.20))
        if len(esp_cal_f1_rec) >= 2
        else 1.0
    )

    sub = df.iloc[-max(35, int(janela_treino) + 1) :].copy()
    arr = pd.to_numeric(sub["valorArrecadado"], errors="coerce").to_numpy(dtype=float)
    est_prox = pd.to_numeric(
        sub.get("valorEstimadoProximoConcurso", pd.Series(0.0, index=sub.index)),
        errors="coerce",
    ).fillna(0.0).to_numpy(dtype=float)
    acum_prox = pd.to_numeric(
        sub.get("valorAcumuladoProximoConcurso", pd.Series(0.0, index=sub.index)),
        errors="coerce",
    ).fillna(0.0).to_numpy(dtype=float)
    acum_esp = pd.to_numeric(
        sub.get("valorAcumuladoConcursoEspecial", pd.Series(0.0, index=sub.index)),
        errors="coerce",
    ).fillna(0.0).to_numpy(dtype=float)
    f1_w = pd.to_numeric(
        sub.get("faixa1_ganhadores", pd.Series(0.0, index=sub.index)), errors="coerce"
    ).fillna(0.0).to_numpy(dtype=float)
    f1_p = pd.to_numeric(
        sub.get("faixa1_premio", pd.Series(0.0, index=sub.index)), errors="coerce"
    ).fillna(0.0).to_numpy(dtype=float)

    if "acumulou" in sub.columns:
        is_acum = _parse_bool_series(sub["acumulou"]).astype(float)
    elif "acumulado" in sub.columns:
        is_acum = _parse_bool_series(sub["acumulado"]).astype(float)
    else:
        is_acum = ((acum_prox > 0.0) | (f1_w == 0.0)).astype(float)

    med_arr_sub = float(np.median(arr))
    is_esp_sub = np.array(
        [
            _detectar_concurso_especial_ex_ante(
                acum_prox[i], acum_esp[i], est_prox[i], med_arr_sub
            )
            for i in range(len(arr))
        ],
        dtype=bool,
    )

    # Estimativa causal da fração líquida fresca da faixa 1 sobre a arrecadação (apenas regulares)
    pool_f1_real = np.where(f1_w > 0, f1_w * f1_p, np.maximum(est_prox, acum_prox))
    default_fresh = DEFAULT_FRESH_F1_RATIO_BY_SLUG.get(config.slug, 0.11)
    valid_fresh = (
        (f1_w[1:] > 0)
        & (pool_f1_real[1:] > acum_prox[:-1])
        & (arr[1:] > 0)
        & (~is_esp_sub[:-1])
    )
    if int(np.sum(valid_fresh)) >= 3:
        fresh_f1_ratio = float(
            np.clip(
                np.median(
                    (pool_f1_real[1:][valid_fresh] - acum_prox[:-1][valid_fresh])
                    / arr[1:][valid_fresh]
                ),
                0.04,
                0.22,
            )
        )
    else:
        fresh_f1_ratio = default_fresh

    # Protege log_est_ratio quando valorEstimadoProximoConcurso == 0 em históricos antigos
    est_safe = np.where(est_prox > 0.0, est_prox, np.maximum(acum_prox, fresh_f1_ratio * arr))

    # Treino causal da regressão de arrecadação em transições REGULARES (s-1) -> s
    log_arr_prev = np.log(np.maximum(arr[:-1], 1.0))
    log_est_ratio = np.log(np.maximum(est_safe[:-1], 1.0) / np.maximum(arr[:-1], 1.0))
    x_tr_all = np.column_stack(
        [np.ones(len(log_arr_prev)), log_arr_prev, log_est_ratio, is_acum[:-1]]
    )
    y_tr_all = np.log(np.maximum(arr[1:], 1.0))
    reg_mask = ~is_esp_sub[:-1]
    if int(np.sum(reg_mask)) < 20:
        reg_mask = np.ones(len(y_tr_all), dtype=bool)
    x_tr = x_tr_all[reg_mask]
    y_tr = y_tr_all[reg_mask]
    pen = np.diag([0.0, 1e-2, 1e-2, 1e-2])
    beta_arr = np.linalg.solve(x_tr.T @ x_tr + pen, x_tr.T @ y_tr)

    # Split-Conformal causal para erro log-arrecadação fora da amostra (90%)
    n_reg = len(y_tr)
    if n_reg >= 24:
        split_c = max(12, n_reg // 2)
        beta_split = np.linalg.solve(
            x_tr[:split_c].T @ x_tr[:split_c] + pen,
            x_tr[:split_c].T @ y_tr[:split_c],
        )
        res_conf = np.abs(y_tr[split_c:] - x_tr[split_c:] @ beta_split)
        m_c = len(res_conf)
        q_lvl = min(1.0, float(np.ceil(0.90 * (m_c + 1))) / float(m_c))
        q90_log_arr = float(np.clip(np.quantile(res_conf, q_lvl), 0.03, 0.85))
    else:
        q90_log_arr = 0.25

    # Calibration ratio between realized Faixa 1 pool at s and est_prox at s-1 (regular)
    valid_cal = (f1_w[1:] > 0) & (est_prox[:-1] > 0) & (~is_esp_sub[:-1])
    if int(np.sum(valid_cal)) >= 5:
        cal_f1 = float(
            np.clip(np.median(pool_f1_real[1:][valid_cal] / est_prox[:-1][valid_cal]), 0.65, 1.15)
        )
    else:
        cal_f1 = 0.95

    # Secondary parimutuel pool ratios (relative to revenue)
    sec_pool_ratios: dict[int, float] = {}
    for f_idx, h_val in tier_map.items():
        if f_idx == 1 or h_val in fixed_tiers:
            continue
        fw = pd.to_numeric(sub.get(f"faixa{f_idx}_ganhadores"), errors="coerce").fillna(0.0).to_numpy(dtype=float)
        fp = pd.to_numeric(sub.get(f"faixa{f_idx}_premio"), errors="coerce").fillna(0.0).to_numpy(dtype=float)
        valid_f = (fw > 0) & (arr > 0)
        if np.any(valid_f):
            sec_pool_ratios[f_idx] = float(np.median((fw[valid_f] * fp[valid_f]) / arr[valid_f]))
        else:
            sec_pool_ratios[f_idx] = 0.0

    def _eval_ev_with_arr(
        arr_val: float,
        est_prev_v: float,
        acum_prev_v: float,
        is_special_v: bool,
        r_val: float,
    ) -> tuple[float, float, float, float]:
        arr_safe = max(float(arr_val), price)
        n_bets_hat = max(arr_safe / max(price, 0.01), 1.0)
        p1 = hypergeometric_hit_probability(
            config.n_numbers, config.k, config.bet_size, tier_map[1]
        )
        lam1 = n_bets_hat * p1
        if is_special_v and est_prev_v > 0.0:
            pool1_hat = max(est_prev_v * cal_f1_esp, acum_prev_v)
        else:
            pool1_hat = max(est_prev_v * cal_f1, acum_prev_v + fresh_f1_ratio * arr_safe)

        ev_var = p1 * pool1_hat * float(poisson_retention_factor(lam1, r_val))
        weighted_elast = ev_var * float(poisson_ev_elasticity(lam1, r_val))

        for f_idx, h_val in tier_map.items():
            if f_idx == 1 or h_val in fixed_tiers:
                continue
            pf = hypergeometric_hit_probability(
                config.n_numbers, config.k, config.bet_size, h_val
            )
            lam_f = n_bets_hat * pf
            pool_f = sec_pool_ratios.get(f_idx, 0.0) * arr_safe
            ev_f = pf * pool_f * float(poisson_retention_factor(lam_f, r_val))
            ev_var += ev_f
            weighted_elast += ev_f * float(poisson_ev_elasticity(lam_f, r_val))

        ev_tot = (ev_fixo + ev_var) / max(price, 0.01) * fator_bolao
        ev_var_ratio = (ev_var / max(price, 0.01)) * fator_bolao
        elast = float(weighted_elast / max(ev_fixo + ev_var, 1e-12))
        return ev_tot, ev_var_ratio, elast, pool1_hat

    def _predict_arr(
        arr_prev_v: float,
        est_prev_v: float,
        acum_prev_v: float,
        is_acum_v: float,
        is_special_v: bool,
    ) -> float:
        if is_special_v and est_prev_v > 0.0:
            return float(max(est_prev_v / ratio_est_arr_esp, arr_prev_v))
        est_prev_safe = (
            est_prev_v
            if est_prev_v > 0.0
            else max(acum_prev_v, fresh_f1_ratio * arr_prev_v)
        )
        x_now = np.array(
            [
                1.0,
                np.log(max(arr_prev_v, 1.0)),
                np.log(max(est_prev_safe, 1.0) / max(arr_prev_v, 1.0)),
                float(is_acum_v),
            ]
        )
        return float(np.exp(np.clip(x_now @ beta_arr, 10.0, 23.0)))

    def _eval_from_prev_signals(
        arr_prev_v: float,
        est_prev_v: float,
        acum_prev_v: float,
        is_acum_v: float,
        is_special_v: bool,
        r_val: float,
    ) -> tuple[float, float, float, float, float]:
        arr_hat = _predict_arr(
            arr_prev_v, est_prev_v, acum_prev_v, is_acum_v, is_special_v
        )
        ev_tot, ev_var_ratio, elast, pool1_hat = _eval_ev_with_arr(
            arr_hat, est_prev_v, acum_prev_v, is_special_v, r_val
        )
        return ev_tot, ev_var_ratio, elast, arr_hat, pool1_hat

    # Evaluate trailing historical ex-ante distribution to set causal quantile thresholds
    hist_evs = []
    for i in range(len(arr) - 1):
        ev_i, _, _, _, _ = _eval_from_prev_signals(
            arr[i], est_prox[i], acum_prox[i], is_acum[i], bool(is_esp_sub[i]), r_eff
        )
        hist_evs.append(ev_i)
    hist_arr = np.asarray(hist_evs, dtype=float)
    tau_80 = float(np.percentile(hist_arr, 80)) if len(hist_arr) > 0 else 0.45
    tau_90 = float(np.percentile(hist_arr, 90)) if len(hist_arr) > 0 else 0.55

    # Evaluate next contest t from the last recorded contest t-1
    is_special_now = bool(is_esp_sub[-1])
    ev_adj, ev_var_adj, elast_now, arr_hat_now, pool1_hat_now = _eval_from_prev_signals(
        arr[-1], est_prox[-1], acum_prox[-1], is_acum[-1], is_special_now, r_eff
    )
    ev_rand, _, _, _, _ = _eval_from_prev_signals(
        arr[-1], est_prox[-1], acum_prox[-1], is_acum[-1], is_special_now, 1.0
    )

    # Banda conformal 90% do EV propagando incerteza de arrecadação e popularidade
    q_arr_eff = max(q90_log_arr, 0.30) if is_special_now else q90_log_arr
    arr_high_90 = arr_hat_now * float(np.exp(q_arr_eff))
    arr_low_90 = arr_hat_now * float(np.exp(-q_arr_eff))
    r_high_90 = r_eff * float(np.exp(q_pop))
    r_low_90 = max(1e-3, r_eff * float(np.exp(-q_pop)))
    ev_low_90, _, _, _ = _eval_ev_with_arr(
        arr_high_90, est_prox[-1], acum_prox[-1], is_special_now, r_high_90
    )
    ev_high_90, _, _, _ = _eval_ev_with_arr(
        arr_low_90, est_prox[-1], acum_prox[-1], is_special_now, r_low_90
    )
    ev_ic90_low = min(ev_low_90, ev_adj, ev_high_90)
    ev_ic90_high = max(ev_low_90, ev_adj, ev_high_90)

    pct_hist = (
        float(100.0 * np.mean(hist_arr <= ev_adj)) if len(hist_arr) > 0 else 50.0
    )
    ganho_rel = (ev_adj / max(ev_rand, 1e-9)) - 1.0 if ev_rand > 0 else 0.0

    if ev_adj >= 1.0:
        rec = "APOSTAR_EV_POSITIVO"
    elif ev_adj >= tau_90:
        rec = "APOSTAR_ACUMULADO_TOP10"
    elif ev_adj >= tau_80:
        rec = "APOSTAR_SELETIVO_TOP20"
    else:
        rec = "PULAR_CONCURSO"

    ultimo_conc = (
        int(sub["Concurso"].iloc[-1])
        if "Concurso" in sub.columns
        else int(sub.index[-1])
    )

    return {
        "disponivel": True,
        "concurso_referencia": ultimo_conc,
        "acumulado_anterior": bool(is_acum[-1] > 0.5),
        "concurso_especial_detectado": is_special_now,
        "premio_estimado_proximo": round(float(est_prox[-1]), 2),
        "acumulado_concurso_especial": round(float(acum_esp[-1]), 2),
        "arrecadacao_estimada": round(float(arr_hat_now), 2),
        "pool_faixa1_estimado": round(float(pool1_hat_now), 2),
        "fresh_f1_ratio_estimado": round(float(fresh_f1_ratio), 4),
        "razao_est_arr_especial": round(float(ratio_est_arr_esp), 4),
        "razao_popularidade_usada": round(float(r_eff), 4),
        "agio_bolao": round(float(agio_bolao), 4),
        "ev_por_real_aleatorio": round(float(ev_rand), 4),
        "ev_por_real_ajustado": round(float(ev_adj), 4),
        "ev_por_real_ic90_low": round(float(ev_ic90_low), 4),
        "ev_por_real_ic90_high": round(float(ev_ic90_high), 4),
        "ev_positivo_conformal": bool(ev_ic90_low >= 1.0),
        "conformal_q90_log_arr": round(float(q_arr_eff), 4),
        "ev_fixo_por_real": round(float(ev_fixo_ratio), 4),
        "ev_rateado_por_real": round(float(ev_var_adj), 4),
        "ganho_relativo_antipopular": round(float(ganho_rel), 4),
        "elasticidade_antipopular": round(float(elast_now), 4),
        "percentil_historico_ev": round(float(pct_hist), 2),
        "limiar_top20": round(float(tau_80), 4),
        "limiar_top10": round(float(tau_90), 4),
        "recomendacao_aposta": rec,
    }


def calcular_kelly_fracionado(
    config: GameConfig,
    ev_por_real: float,
    pool1_estimado: float,
    banca: float,
    fracao_kelly: float = 0.25,
    teto_banca: float = 0.05,
    agio_bolao: float = 0.0,
) -> dict[str, Any]:
    """
    Dimensionamento conservador de aposta via critério de Kelly fracionado ajustado
    pela variância hipergeométrica do prêmio principal (com teto de exposição da banca).

    Retorna aposta 0 sempre que `ev_por_real <= 1.0` ou `banca <= 0`.
    """
    custo_jogo = float(config.game_price) * max(1.0, 1.0 + max(0.0, float(agio_bolao)))
    if banca <= 0.0 or ev_por_real <= 1.0 or pool1_estimado <= 0.0 or custo_jogo <= 0.0:
        return {
            "ev_por_real": round(float(ev_por_real), 4),
            "f_kelly_puro": 0.0,
            "f_kelly_fracionado": 0.0,
            "aposta_sugerida": 0.0,
            "jogos_sugeridos": 0,
            "motivo": "EV líquido <= 1,00 (sem vantagem matemática para alocar banca)"
            if ev_por_real <= 1.0
            else "Parâmetros insuficientes",
        }

    tier_map = TIER_HITS_BY_SLUG.get(config.slug, {})
    h1 = tier_map.get(1, config.k)
    p1 = hypergeometric_hit_probability(config.n_numbers, config.k, config.bet_size, h1)
    # Aproximação de segunda ordem da variância do retorno por R$ 1 apostado dominada pela faixa 1
    retorno_unitario_f1 = float(pool1_estimado) / custo_jogo
    var_retorno = max(p1 * (retorno_unitario_f1 ** 2) - (float(ev_por_real) ** 2), 1e-6)
    f_puro = max(0.0, (float(ev_por_real) - 1.0) / var_retorno)
    f_frac = min(max(0.0, float(teto_banca)), max(0.0, float(fracao_kelly)) * f_puro)
    aposta = float(banca) * f_frac
    jogos = int(aposta // custo_jogo)
    return {
        "ev_por_real": round(float(ev_por_real), 4),
        "f_kelly_puro": float(f_puro),
        "f_kelly_fracionado": float(f_frac),
        "aposta_sugerida": round(float(aposta), 2),
        "jogos_sugeridos": jogos,
        "custo_unitario_efetivo": round(custo_jogo, 2),
        "motivo": "EV positivo: alocação limitada por Kelly fracionado e teto de banca",
    }


def comparar_ev_modalidades(
    detalhes_por_slug: dict[str, pd.DataFrame | None] | None = None,
    razoes_por_slug: dict[str, float] | None = None,
    conformal_pop_por_slug: dict[str, float] | None = None,
    agio_bolao: float = 0.0,
    banca: float | None = None,
    modo_estrito: bool = False,
) -> dict[str, Any]:
    """
    Compara simultaneamente o retorno esperado líquido ex-ante entre todas as modalidades
    suportadas (Mega-Sena, Quina, Lotofácil e Lotomania) e recomenda onde (ou se) apostar.
    """
    from app.core.lottery import GAMES

    det_map = detalhes_por_slug or {}
    raz_map = razoes_por_slug or {}
    q_map = conformal_pop_por_slug or {}

    ranking: list[dict[str, Any]] = []
    for slug, cfg in GAMES.items():
        det_df = det_map.get(slug)
        razao = float(raz_map.get(slug, 1.0))
        q_pop = float(q_map.get(slug, 0.0))
        ev_info = estimar_ev_concurso_ex_ante(
            cfg,
            detalhes_df=det_df,
            razao_popularidade=razao,
            agio_bolao=agio_bolao,
            conformal_q90_log_pop=q_pop,
        )
        item: dict[str, Any] = {
            "slug": slug,
            "nome": cfg.name,
            **ev_info,
        }
        if banca is not None and ev_info.get("disponivel"):
            item["kelly"] = calcular_kelly_fracionado(
                cfg,
                ev_por_real=float(ev_info["ev_por_real_ajustado"]),
                pool1_estimado=float(ev_info.get("pool_faixa1_estimado", 0.0)),
                banca=float(banca),
                agio_bolao=agio_bolao,
            )
        ranking.append(item)

    ranking.sort(
        key=lambda r: (
            bool(r.get("disponivel", False)),
            float(r.get("ev_por_real_ajustado", 0.0)),
        ),
        reverse=True,
    )

    melhor = next((r for r in ranking if r.get("disponivel")), None)
    if melhor is None:
        decisao = "INDISPONIVEL"
        melhor_slug = None
    elif float(melhor["ev_por_real_ajustado"]) >= 1.0:
        decisao = "APOSTAR_EV_POSITIVO"
        melhor_slug = melhor["slug"]
    elif modo_estrito:
        decisao = "NAO_JOGAR_MODO_ESTRITO"
        melhor_slug = None
    else:
        decisao = str(melhor.get("recomendacao_aposta", "PULAR_CONCURSO"))
        melhor_slug = melhor["slug"] if decisao != "PULAR_CONCURSO" else None

    return {
        "melhor_modalidade": melhor_slug,
        "decisao_global": decisao,
        "ranking": ranking,
    }



def financial_diagnostics(
    games: list[list[int]] | np.ndarray,
    gabarito: np.ndarray,
    config: GameConfig,
    prize_table: dict[int, float] | None = None,
) -> FinancialDiagnostics:
    arr = np.asarray(games, dtype=int)
    draws = np.asarray(gabarito, dtype=int)
    if arr.size == 0 or draws.size == 0:
        n_bets = int(len(arr)) if arr.ndim > 1 else 0
        n_draws = int(len(draws)) if draws.ndim > 1 else 0
        cost = n_bets * n_draws * float(config.game_price)
        return FinancialDiagnostics(
            cost=round(float(cost), 2),
            gross_return=0.0,
            net_return=round(float(-cost), 2),
            roi=0.0,
            profit_factor=0.0,
            prize_table={str(k): v for k, v in sorted((prize_table or {}).items())},
            paid_hits={},
            n_bets=n_bets,
            n_draws=n_draws,
            stake_per_bet=float(config.game_price),
            mode="prize_table",
        )

    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    if draws.ndim == 1:
        draws = draws.reshape(1, -1)

    table = {int(k): float(v) for k, v in (prize_table or {}).items()}
    paid_hits = {int(k): 0 for k in table}
    gross = 0.0

    n_max = int(config.n_numbers)
    valid_bounds = (
        int(arr.min()) >= 1
        and int(arr.max()) <= n_max
        and int(draws.min()) >= 1
        and int(draws.max()) <= n_max
    )
    if valid_bounds and table:
        b_games = np.zeros((len(arr), n_max), dtype=np.int16)
        b_games[np.arange(len(arr))[:, None], arr - 1] = 1
        b_draws = np.zeros((len(draws), n_max), dtype=np.int16)
        b_draws[np.arange(len(draws))[:, None], draws - 1] = 1
        if np.all(b_games.sum(axis=1) == arr.shape[1]) and np.all(
            b_draws.sum(axis=1) == draws.shape[1]
        ):
            hits_matrix = b_games @ b_draws.T
            for h_key, prize in table.items():
                if prize > 0:
                    cnt = int(np.sum(hits_matrix == h_key))
                    if cnt > 0:
                        paid_hits[h_key] = cnt
                        gross += cnt * prize
        else:
            valid_bounds = False

    if not valid_bounds and table:
        for game in arr:
            game_set = set(int(n) for n in game.tolist())
            for draw in draws:
                hits = len(game_set.intersection(int(n) for n in draw.tolist()))
                prize = table.get(hits, 0.0)
                if prize > 0:
                    paid_hits[hits] = paid_hits.get(hits, 0) + 1
                    gross += prize

    n_bets = int(len(arr))
    n_draws = int(len(draws))
    cost = float(n_bets * n_draws * config.game_price)
    net = gross - cost
    profit_factor = gross / cost if cost > 0 else 0.0
    roi = net / cost if cost > 0 else 0.0
    return FinancialDiagnostics(
        cost=round(cost, 2),
        gross_return=round(float(gross), 2),
        net_return=round(float(net), 2),
        roi=round(float(roi), 6),
        profit_factor=round(float(profit_factor), 6),
        prize_table={str(k): round(float(v), 2) for k, v in sorted(table.items())},
        paid_hits={str(k): int(v) for k, v in sorted(paid_hits.items()) if v > 0},
        n_bets=n_bets,
        n_draws=n_draws,
        stake_per_bet=round(float(config.game_price), 2),
        mode="prize_table",
    )


def diagnostics_to_dict(diag: FinancialDiagnostics) -> dict[str, Any]:
    return {
        "custo_total": diag.cost,
        "receita_bruta": diag.gross_return,
        "lucro_liquido": diag.net_return,
        "roi": diag.roi,
        "fator_retorno": diag.profit_factor,
        "tabela_premios": diag.prize_table,
        "hits_pagos": diag.paid_hits,
        "n_jogos": diag.n_bets,
        "n_concursos": diag.n_draws,
        "preco_aposta": diag.stake_per_bet,
        "modo": diag.mode,
    }
