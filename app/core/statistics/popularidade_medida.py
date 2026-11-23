# app/core/statistics/popularidade_medida.py
"""
Popularidade MEDIDA dos números, a partir dos ganhadores reais de cada concurso.

Ideia: o número de ganhadores de uma faixa baixa (ex.: quadra da Mega-Sena)
depende de quão populares eram, entre os apostadores, os números sorteados.
Como o sorteio é aleatório, os números sorteados são independentes do volume de
apostas, então dá para estimar o peso de cada número por regressão:

    log(ganhadores / arrecadado) ~ números sorteados + controles

O modelo prevê, para um jogo qualquer, quantos ganhadores a faixa teria se
aquele jogo fosse o sorteado. Mede RISCO DE DIVIDIR O PRÊMIO, não chance de acerto.

O modelo só é usado se passar numa validação cruzada temporal (ganho sobre um
modelo só com os controles). Sem dados em data/detalhes/ ou sem ganho
comprovado, devolve None e o sistema funciona sem ele.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from scipy import linalg as sp_linalg

from app.core.ticket_features import extract_ticket_features_batch

SLUG_PARA_API = {
    "mega_sena_sorteio": "megasena",
    "quina_sorteio": "quina",
    "loto_facil_sorteio": "lotofacil",
    "loto_mania_sorteio": "lotomania",
}

PASTA_DETALHES = os.path.join("data", "detalhes")
MIN_CONCURSOS = 300
MEDIANA_MIN_GANHADORES = 300  # para o ruído de contagem (Poisson) ficar pequeno
R2_MINIMO = 0.02
# Corte de popularidade: nos jogos em que o modelo explica bem os ganhadores
# (R2 de CV temporal estrita com limpeza causal de arrecadação + Huber-IRLS + estrutura 2D
# + interações de 2ª ordem por pares: Quina ~0,79, Mega-Sena ~0,70, Lotofácil ~0,58, Lotomania ~0,38).
# Valor = razão de ganhadores prevista (1,0 = jogo médio) que deixa de fora
# os ~85-90% de jogos mais populares dentro da faixa estrutural 5-95.
# Na Lotomania (aposta de 50 números para 20 sorteados), a proteção anti-divisão
# atua via score contínuo reescalonado (k/m = 0,4) + espelho de 0 acertos (J^c).
LIMIAR_RAZAO_GANHADORES = {
    "mega_sena_sorteio": 0.75,
    "quina_sorteio": 0.80,
    "loto_facil_sorteio": 0.75,
}
LAMBDAS = (1.0, 10.0, 100.0, 1000.0)
STRUCT_LAMBDAS = (10.0, 100.0, 1000.0)
PAIR_LAMBDAS = (30.0, 100.0, 500.0, 2000.0)
MAX_DUAL_PAIRS_WINDOW = 2200
N_AMOSTRAS_NULO = 4000
N_BLOCOS_CV = 6

STRUCT_FEATURE_KEYS = (
    "soma",
    "pares",
    "span",
    "max_sequencia",
    "entropia_gaps",
    "max_linha",
    "max_coluna",
    "max_quadrante",
    "max_final_repetido",
    "max_dezena_repetida",
    "compressibilidade_simples",
    "moldura",
    "cruz",
    "xis",
    "cantos",
    "diag_principal",
    "diag_secundaria",
    "multiplos_5",
    "finais_unicos",
    "simetria_reflexao",
    "std_linhas",
)


def _extract_struct_raw(jogos: np.ndarray, config: Any) -> np.ndarray:
    arr = np.sort(np.asarray(jogos, dtype=int), axis=1)
    feats = extract_ticket_features_batch(arr, config)
    cols = [feats[key].astype(float) for key in STRUCT_FEATURE_KEYS]
    n_num = int(getattr(config, "n_numbers", 0))
    if n_num > 31:
        cols.append((arr <= 31).sum(axis=1).astype(float))

    # Sub-faixas de calendário (meses 1..12 vs dias 13..31)
    cols.append((arr <= 12).sum(axis=1).astype(float))
    cols.append(((arr >= 13) & (arr <= 31)).sum(axis=1).astype(float))

    # Diferenças 1D e progressões aritméticas consecutivas
    k_curr = arr.shape[1]
    if k_curr >= 2:
        diffs = np.diff(arr, axis=1)
        cols.append((diffs == 1).sum(axis=1).astype(float))
        cols.append((diffs == 2).sum(axis=1).astype(float))
        if k_curr >= 3:
            cols.append((diffs[:, :-1] == diffs[:, 1:]).sum(axis=1).astype(float))
        else:
            cols.append(np.zeros(len(arr), dtype=float))

        # Geometria 2D de adjacência física no volante
        layout = getattr(config, "layout", None)
        n_cols = int(getattr(layout, "cols", 0) or 10)
        rows = (arr - 1) // n_cols
        cols_2d = (arr - 1) % n_cols
        i_idx, j_idx = np.triu_indices(k_curr, k=1)
        dr = np.abs(rows[:, i_idx] - rows[:, j_idx])
        dc = np.abs(cols_2d[:, i_idx] - cols_2d[:, j_idx])
        cols.append(((dr + dc) == 1).sum(axis=1).astype(float))  # adj_ortho
        cols.append(((dr == 1) & (dc == 1)).sum(axis=1).astype(float))  # adj_diag
        cols.append((dr == 0).sum(axis=1).astype(float))  # same_row_pairs
        cols.append((dc == 0).sum(axis=1).astype(float))  # same_col_pairs

    return np.column_stack(cols)


def _fit_struct_params(x_raw: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mu1 = x_raw.mean(axis=0)
    sd1_raw = x_raw.std(axis=0)
    sd1 = np.where(sd1_raw > 1e-9, sd1_raw, 0.0)
    z1 = np.divide(x_raw - mu1, sd1, out=np.zeros_like(x_raw, dtype=float), where=sd1 > 0.0)
    z2_raw = z1 ** 2
    mu2 = z2_raw.mean(axis=0)
    sd2_raw = z2_raw.std(axis=0)
    sd2 = np.where(sd2_raw > 1e-9, sd2_raw, 0.0)
    return (mu1, sd1, mu2, sd2)


def _apply_struct_params(
    x_raw: np.ndarray, params: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]
) -> np.ndarray:
    mu1, sd1, mu2, sd2 = params
    z1 = np.divide(x_raw - mu1, sd1, out=np.zeros_like(x_raw, dtype=float), where=sd1 > 0.0)
    z2 = np.divide(
        (z1 ** 2) - mu2,
        sd2,
        out=np.zeros_like(z1, dtype=float),
        where=sd2 > 0.0,
    )
    return np.column_stack([z1, z2])


def carregar_detalhes(config, pasta: str = PASTA_DETALHES) -> pd.DataFrame | None:
    """Lê data/detalhes/<loteria>_detalhes.csv (indexado por Concurso) ou None."""
    chave = SLUG_PARA_API.get(config.slug)
    if chave is None:
        return None
    caminho = os.path.join(pasta, f"{chave}_detalhes.csv")
    if not os.path.exists(caminho):
        return None
    try:
        det = pd.read_csv(caminho)
    except Exception:
        return None
    if "Concurso" not in det.columns:
        return None
    det = det.dropna(subset=["Concurso"]).copy()
    det["Concurso"] = det["Concurso"].astype(int)
    return det.drop_duplicates("Concurso").set_index("Concurso").sort_index()


def _escolher_faixa(det: pd.DataFrame) -> int | None:
    """Faixa de maior prêmio cuja mediana de ganhadores seja alta o bastante."""
    faixas = []
    for c in det.columns:
        if c.startswith("faixa") and c.endswith("_ganhadores"):
            faixas.append(int(c[5 : c.index("_")]))
    for f in sorted(faixas):
        mediana = pd.to_numeric(det[f"faixa{f}_ganhadores"], errors="coerce").median()
        if pd.notna(mediana) and mediana >= MEDIANA_MIN_GANHADORES:
            return f
    return None


def filtrar_arrecadacao_valida_causal(
    arrecadado: np.ndarray | pd.Series,
    game_price: float = 3.0,
    min_apostas_fisicas: float = 1000.0,
    fracao_min_mediana_causal: float = 0.01,
) -> np.ndarray:
    """
    Filtro estritamente causal contra registros corrompidos de `valorArrecadado`
    (ex.: Concurso 994 da Mega-Sena gravado com R$ 0,01 na API da Caixa).

    Usa apenas um piso físico mínimo (`min_apostas_fisicas * game_price`) e,
    a partir de 10 concursos válidos anteriores, exige pelo menos `fracao_min_mediana_causal`
    da mediana móvel passada (zero vazamento de futuro).
    """
    arr = pd.to_numeric(pd.Series(arrecadado), errors="coerce").to_numpy(dtype=float)
    piso_fisico = max(1000.0, float(min_apostas_fisicas) * max(float(game_price), 1.0))
    valido = np.zeros(len(arr), dtype=bool)
    historico_ok: list[float] = []

    for i, val in enumerate(arr):
        if not np.isfinite(val) or val < piso_fisico:
            continue
        if len(historico_ok) >= 10:
            janela = historico_ok[-50:]
            med = float(np.median(janela))
            if val < fracao_min_mediana_causal * med:
                continue
        valido[i] = True
        historico_ok.append(float(val))
    return valido


def _ridge(
    x: np.ndarray,
    y: np.ndarray,
    lam: float,
    n_penalizados: int,
    penalties: np.ndarray | None = None,
    weights: np.ndarray | None = None,
) -> np.ndarray:
    """Ridge (OLS ou WLS com decaimento exponencial) com intercepto livre."""
    xi = np.column_stack([np.ones(len(x)), x])
    pen = np.zeros(xi.shape[1])
    if penalties is not None:
        pen[1 : 1 + len(penalties)] = penalties
    else:
        pen[1 : 1 + n_penalizados] = lam
    if weights is not None:
        w = np.asarray(weights, dtype=float)
        w = w / max(float(w.mean()), 1e-12)
        xtw = xi.T * w
        return np.linalg.solve(xtw @ xi + np.diag(pen), xtw @ y)
    return np.linalg.solve(xi.T @ xi + np.diag(pen), xi.T @ y)


def _ridge_huber(
    x: np.ndarray,
    y: np.ndarray,
    penalties: np.ndarray,
    weights: np.ndarray | None = None,
    n_iter: int = 3,
    huber_k: float = 1.5,
) -> np.ndarray:
    """
    Ridge robusto via IRLS com função de perda Huber.
    Amortece automaticamente outliers de rateio/API sem sacrificar eficiência em dados limpos.
    """
    w_base = (
        np.ones(len(y), dtype=float)
        if weights is None
        else np.asarray(weights, dtype=float)
    )
    beta = _ridge(x, y, 0.0, 0, penalties=penalties, weights=w_base)
    for _ in range(n_iter):
        res = y - _prever(x, beta)
        mad = float(np.median(np.abs(res - np.median(res))))
        escala = max(1.4826 * mad, 1e-4)
        delta = huber_k * escala
        abs_r = np.abs(res)
        w_huber = np.where(abs_r <= delta, 1.0, delta / np.maximum(abs_r, 1e-12))
        beta = _ridge(x, y, 0.0, 0, penalties=penalties, weights=w_base * w_huber)
    return beta


def _prever(x: np.ndarray, beta: np.ndarray) -> np.ndarray:
    return beta[0] + x @ beta[1:]


def _causal_rolling_median(y_raw: np.ndarray, window: int = 50) -> np.ndarray:
    """Mediana móvel estritamente causal (usa apenas [max(0, t-window), t-1]) para remover saltos de preço."""
    if len(y_raw) == 0:
        return np.array([], dtype=float)
    s = pd.Series(y_raw, dtype=float)
    med = s.rolling(window=window, min_periods=1).median().shift(1)
    med.iloc[0] = float(y_raw[0])
    return med.to_numpy(dtype=float)


def _complement_games_batch(candidatos: np.ndarray, n_numeros: int) -> np.ndarray:
    """Devolve o bilhete espelho J^c = {1..N} \\ J para cada linha de `candidatos`."""
    m_rows, k_bet = candidatos.shape
    mask = np.ones((m_rows, n_numeros), dtype=bool)
    mask[np.arange(m_rows)[:, None], candidatos - 1] = False
    pool = np.broadcast_to(np.arange(1, n_numeros + 1), (m_rows, n_numeros))
    return pool[mask].reshape(m_rows, n_numeros - k_bet)


def _fit_pair_kernel_alpha(
    x_num_tr: np.ndarray,
    res_tr: np.ndarray,
    lam_pair: float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Ajusta o kernel dual exato de interações de 2ª ordem K_par(a, b) = C(|S_a ∩ S_b|, 2)
    sobre os resíduos do modelo linear+estrutural.
    Usa janela recente máxima `MAX_DUAL_PAIRS_WINDOW` para manter execução leve em notebooks.
    """
    if len(res_tr) > MAX_DUAL_PAIRS_WINDOW:
        x_sub = x_num_tr[-MAX_DUAL_PAIRS_WINDOW:]
        r_sub = res_tr[-MAX_DUAL_PAIRS_WINDOW:]
    else:
        x_sub = x_num_tr
        r_sub = res_tr

    ov = x_sub @ x_sub.T
    k_mat = ov * (ov - 1.0) * 0.5
    k_mat[np.diag_indices_from(k_mat)] += float(lam_pair)
    c_fac, lower = sp_linalg.cho_factor(k_mat, overwrite_a=True, check_finite=False)
    alpha = sp_linalg.cho_solve((c_fac, lower), r_sub, check_finite=False)
    return alpha, x_sub


def _pair_matrix_from_dual(alpha: np.ndarray, x_sub: np.ndarray) -> np.ndarray:
    """
    Converte os coeficientes duais `alpha` na matriz simétrica W (N x N, diagonal 0)
    tal que x^T W x = sum_{s} alpha_s * C(|S_x ∩ S_s|, 2) exatamente para qualquer bilhete x.
    """
    m_mat = (x_sub.T * alpha) @ x_sub
    np.fill_diagonal(m_mat, 0.0)
    return 0.5 * m_mat


def _score_pairs_batch(
    candidatos: np.ndarray,
    pair_matrix: np.ndarray,
    n_numeros: int,
) -> np.ndarray:
    """Calcula x^T W x vetorizado para um lote de candidatos (B, bet_size)."""
    m_rows = len(candidatos)
    if m_rows == 0:
        return np.array([], dtype=float)
    g = np.zeros((m_rows, n_numeros), dtype=float)
    g[np.arange(m_rows)[:, None], candidatos - 1] = 1.0
    return np.einsum("ij,ij->i", g @ pair_matrix, g)


@dataclass
class ModeloPopularidade:
    faixa: int
    n_concursos: int
    r2_cv: float
    lam: float
    pesos: np.ndarray  # por número (índice 0 = número 1), centrado na média
    k: int
    n_numeros: int
    media_nula: float = 0.0
    config: Any = None
    struct_coefs: np.ndarray | None = None
    struct_params: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None = None
    media_log_estrutural: float = 0.0
    meia_vida_wls: float | None = None
    normalizacao_regime: str = "mediana_movel_causal"
    pair_matrix: np.ndarray | None = None
    media_log_pares: float = 0.0
    lam_pares: float | None = None
    usa_huber: bool = False
    n_outliers_filtrados: int = 0
    cal_slope: float = 1.0
    r2_recente: float | None = None
    cal_slope_recente: float | None = None
    drift_alerta: bool = False
    conformal_q90_log: float | None = None
    _nulos: dict = field(repr=False, default_factory=dict)
    _struct_por_tamanho: dict = field(repr=False, default_factory=dict)

    def _has_struct(self, bet_size: int) -> bool:
        return (
            bet_size > 0
            and self.config is not None
            and self.struct_coefs is not None
            and self.struct_params is not None
        )

    def _get_struct_calibration(
        self, bet_size: int
    ) -> tuple[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray], float, float]:
        if bet_size == self.k:
            return self.struct_params, self.media_log_estrutural, 1.0
        if bet_size not in self._struct_por_tamanho:
            rng_m = np.random.default_rng(2000 + bet_size)
            pool = np.arange(1, self.n_numeros + 1)
            keys = rng_m.random((N_AMOSTRAS_NULO // 2, self.n_numeros))
            idx = np.argpartition(keys, bet_size - 1, axis=1)[:, :bet_size]
            amostras_m = np.sort(pool[idx], axis=1)
            raw_m = _extract_struct_raw(amostras_m, self.config)
            prm_m = _fit_struct_params(raw_m)
            xs_m = _apply_struct_params(raw_m, prm_m)
            media_m = float((xs_m @ self.struct_coefs).mean())
            scale_m = float(self.k) / float(max(1, bet_size))
            self._struct_por_tamanho[bet_size] = (prm_m, media_m, scale_m)
        return self._struct_por_tamanho[bet_size]

    def _single_side_log_score(self, candidatos: np.ndarray) -> np.ndarray:
        bet_size = int(candidatos.shape[1])
        ball_scale = float(self.k) / float(max(1, bet_size))
        score = self.pesos[candidatos - 1].sum(axis=1) * ball_scale
        if self._has_struct(bet_size):
            prm_m, media_m, scale_m = self._get_struct_calibration(bet_size)
            x_struct = _apply_struct_params(
                _extract_struct_raw(candidatos, self.config),
                prm_m,
            )
            score = score + ((x_struct @ self.struct_coefs) - media_m) * scale_m
        if self.pair_matrix is not None and bet_size >= 2:
            # Escala exata pela razão esperada de pares sorteados C(k,2)/C(m,2)
            pair_scale = float(self.k * (self.k - 1)) / float(
                max(1, bet_size * (bet_size - 1))
            )
            raw_pair = _score_pairs_batch(candidatos, self.pair_matrix, self.n_numeros)
            score = score + (raw_pair * pair_scale - self.media_log_pares)
        return score * float(self.cal_slope)

    def _log_score_batch(self, candidatos: np.ndarray) -> np.ndarray:
        score = self._single_side_log_score(candidatos)
        bet_size = int(candidatos.shape[1])
        # Lotomania (50 de 100): protege simultaneamente as faixas principais (15..20 acertos,
        # 97,5% do EV rateado) e a faixa de 0 acertos (2,5% do EV rateado, cujo rateio é
        # dividido com quem jogou o bilhete-espelho J^c = {1..100} \ J).
        if self.n_numeros == 100 and bet_size == 50:
            espelho = _complement_games_batch(candidatos, self.n_numeros)
            score_espelho = self._single_side_log_score(espelho)
            score = 0.975 * score + 0.025 * score_espelho
        return score

    def _nulo(self, m: int) -> np.ndarray:
        if m not in self._nulos:
            rng = np.random.default_rng(1000 + m)
            pool = np.arange(1, self.n_numeros + 1)
            keys = rng.random((N_AMOSTRAS_NULO // 2, self.n_numeros))
            idx = np.argpartition(keys, m - 1, axis=1)[:, :m]
            amostras = np.sort(pool[idx], axis=1)
            self._nulos[m] = np.sort(self._log_score_batch(amostras))
        return self._nulos[m]

    def percentil_batch(self, candidatos: np.ndarray) -> np.ndarray:
        """Percentil (0-100) de popularidade de cada jogo frente a jogos aleatórios."""
        candidatos = np.asarray(candidatos, dtype=int)
        if candidatos.size == 0:
            return np.array([], dtype=float)
        valores = self._log_score_batch(candidatos)
        nulo = self._nulo(candidatos.shape[1])
        return 100.0 * np.searchsorted(nulo, valores, side="right") / len(nulo)

    def razao_ganhadores_batch(self, candidatos: np.ndarray) -> np.ndarray:
        """Razão de ganhadores prevista de cada jogo (1,0 = jogo médio)."""
        candidatos = np.asarray(candidatos, dtype=int)
        if candidatos.size == 0:
            return np.array([], dtype=float)
        return np.exp(self._log_score_batch(candidatos))

    def avaliar(self, numeros) -> dict:
        """Popularidade de um jogo: percentil, razão de ganhadores e banda conformal 90%."""
        arr = np.array([sorted(numeros)], dtype=int)
        percentil = float(self.percentil_batch(arr)[0])
        razao = None
        razao_low = None
        razao_high = None
        bet_size_cfg = (
            getattr(self.config, "bet_size", self.k) if self.config is not None else self.k
        )
        if len(numeros) in {self.k, bet_size_cfg}:
            log_val = float(self._log_score_batch(arr)[0])
            razao = float(np.exp(log_val))
            if self.conformal_q90_log is not None and np.isfinite(self.conformal_q90_log):
                scale_q = float(self.k) / float(max(1, len(numeros)))
                q_eff = float(self.conformal_q90_log) * scale_q
                razao_low = float(np.exp(log_val - q_eff))
                razao_high = float(np.exp(log_val + q_eff))
        out = {"percentil": percentil, "razao_ganhadores": razao}
        if razao_low is not None:
            out["razao_ic90_low"] = razao_low
            out["razao_ic90_high"] = razao_high
        return out

    def diagnostico_modelo(self) -> dict[str, Any]:
        """Resumo de calibração, interações e monitoramento de deriva temporal."""
        return {
            "faixa": self.faixa,
            "n_concursos": self.n_concursos,
            "n_outliers_filtrados": self.n_outliers_filtrados,
            "r2_cv": round(float(self.r2_cv), 4),
            "r2_recente": round(float(self.r2_recente), 4)
            if self.r2_recente is not None
            else None,
            "cal_slope": round(float(self.cal_slope), 4),
            "cal_slope_recente": round(float(self.cal_slope_recente), 4)
            if self.cal_slope_recente is not None
            else None,
            "drift_alerta": bool(self.drift_alerta),
            "usa_huber": bool(self.usa_huber),
            "usa_interacoes_pares": bool(self.pair_matrix is not None),
            "lam_pares": self.lam_pares,
            "conformal_q90_log": round(float(self.conformal_q90_log), 4)
            if self.conformal_q90_log is not None
            else None,
        }


def _fit_linear_step(
    x_tr: np.ndarray,
    y_tr: np.ndarray,
    pen: np.ndarray,
    hl: float | None,
    usa_huber: bool,
) -> np.ndarray:
    w_tr = (
        0.5 ** ((len(y_tr) - 1 - np.arange(len(y_tr), dtype=float)) / hl)
        if hl is not None
        else None
    )
    if usa_huber:
        return _ridge_huber(x_tr, y_tr, penalties=pen, weights=w_tr)
    return _ridge(x_tr, y_tr, 0.0, 0, penalties=pen, weights=w_tr)


def treinar_modelo_popularidade(
    df: pd.DataFrame, detalhes: pd.DataFrame | None, config
) -> ModeloPopularidade | None:
    """
    Ajusta o modelo com os concursos presentes em `df` E em `detalhes`
    (só usa o que está no df, então não vaza o futuro em backtests).

    Pipeline causal completo:
    1. Limpeza causal de registros corrompidos de `valorArrecadado` (ex.: R$ 0,01).
    2. Pesos por número + métricas estruturais 1D/2D e quadráticas + normalização causal
       por mediana móvel + WLS exponencial + opção robusta Huber-IRLS via CV temporal.
    3. Termo opcional de interações de 2ª ordem por pares (γ_ij) via kernel dual exato
       sobre os resíduos do modelo linear+estrutural (só ativado se melhorar a CV temporal).
    4. Calibração de slope out-of-sample, quantil conformal 90% e monitor de deriva recente.

    Devolve None se não houver dados suficientes ou se a validação cruzada
    temporal não mostrar ganho real sobre o modelo só com controles.
    """
    if df is None or df.empty or detalhes is None or detalhes.empty:
        return None

    idx = df.index.intersection(detalhes.index)
    if len(idx) < MIN_CONCURSOS:
        return None
    idx = idx.sort_values()
    det = detalhes.loc[idx]
    sorteios = df.loc[idx, config.draw_cols].to_numpy()

    faixa = _escolher_faixa(det)
    if faixa is None:
        return None

    if "valorArrecadado" not in det.columns:
        return None
    ganhadores_s = pd.to_numeric(det[f"faixa{faixa}_ganhadores"], errors="coerce")
    arrecadado_s = pd.to_numeric(det["valorArrecadado"], errors="coerce")
    arr_ok_causal = filtrar_arrecadacao_valida_causal(
        arrecadado_s,
        game_price=float(getattr(config, "game_price", 3.0)),
    )
    ok_basico = (ganhadores_s.notna() & arrecadado_s.notna() & (arrecadado_s > 0)).to_numpy()
    ok = ok_basico & arr_ok_causal
    n_outliers_filtrados = int(ok_basico.sum() - ok.sum())
    if ok.sum() < MIN_CONCURSOS:
        return None

    ganhadores = ganhadores_s.to_numpy()[ok]
    arrecadado = arrecadado_s.to_numpy()[ok]
    sorteios = sorteios[ok]
    t = len(ganhadores)
    n = config.n_numbers

    y_raw = np.log((ganhadores + 0.5) / arrecadado * 1e6)
    med_causal = _causal_rolling_median(y_raw, window=50)
    y_norm = y_raw - med_causal

    log_arr = np.log(arrecadado)
    tempo = np.arange(t, dtype=float)
    x_num = np.zeros((t, n))
    x_num[np.repeat(np.arange(t), config.k), (sorteios - 1).ravel()] = 1.0
    x_struct_raw = _extract_struct_raw(sorteios, config)

    # Folds temporais estritamente causais (inclusive padronização dos controles por fold)
    limites = np.linspace(0, t, N_BLOCOS_CV + 1).astype(int)
    targets_specs = [
        ("mediana_movel_causal", y_norm),
        ("log_arrecadado_linear", y_raw),
    ]
    half_lives: tuple[float | None, ...] = (None, 500.0, 1000.0)

    melhor = None
    melhor_spec = ("mediana_movel_causal", y_norm, None, False)
    melhor_fold_data = None

    for norm_name, y_target in targets_specs:
        fold_data = []
        for f in range(1, N_BLOCOS_CV):
            tr = slice(0, limites[f])
            te = slice(limites[f], limites[f + 1])
            la_tr_mu, la_tr_sd = float(log_arr[tr].mean()), float(log_arr[tr].std()) or 1.0
            tp_tr_mu, tp_tr_sd = float(tempo[tr].mean()), float(tempo[tr].std()) or 1.0
            ctrl_tr = np.column_stack(
                [(log_arr[tr] - la_tr_mu) / la_tr_sd, (tempo[tr] - tp_tr_mu) / tp_tr_sd]
            )
            ctrl_te = np.column_stack(
                [(log_arr[te] - la_tr_mu) / la_tr_sd, (tempo[te] - tp_tr_mu) / tp_tr_sd]
            )
            prm = _fit_struct_params(x_struct_raw[tr])
            xs_tr = _apply_struct_params(x_struct_raw[tr], prm)
            xs_te = _apply_struct_params(x_struct_raw[te], prm)
            x_tr = np.column_stack([x_num[tr], xs_tr, ctrl_tr])
            x_te = np.column_stack([x_num[te], xs_te, ctrl_te])
            beta_base = _ridge(ctrl_tr, y_target[tr], 0.0, 0)
            pred_base = _prever(ctrl_te, beta_base)
            e_base = float(((y_target[te] - pred_base) ** 2).sum())
            fold_data.append(
                (tr, te, x_tr, y_target[tr], x_te, y_target[te], pred_base, e_base, xs_tr.shape[1])
            )

        sse_base_total = sum(fd[7] for fd in fold_data)
        grid_lambdas = [
            (lam_num, lam_str, hl)
            for lam_num in LAMBDAS
            for lam_str in STRUCT_LAMBDAS
            for hl in half_lives
            if lam_str >= lam_num
        ]
        for lam_num, lam_str, hl in grid_lambdas:
            sse_modelo = 0.0
            folds_melhor = 0
            folds = len(fold_data)
            for _, _, x_tr, y_tr, x_te, y_te, _, e_base, n_str in fold_data:
                pen = np.zeros(x_tr.shape[1])
                pen[:n] = lam_num
                pen[n : n + n_str] = lam_str
                beta = _fit_linear_step(x_tr, y_tr, pen, hl, usa_huber=False)
                e_mod = float(((y_te - _prever(x_te, beta)) ** 2).sum())
                sse_modelo += e_mod
                folds_melhor += int(e_mod < e_base)
            r2 = 1.0 - sse_modelo / sse_base_total if sse_base_total > 0 else 0.0
            if melhor is None or r2 > melhor[0]:
                melhor = (r2, lam_num, lam_str, folds_melhor, folds)
                melhor_spec = (norm_name, y_target, hl, False)
                melhor_fold_data = (fold_data, sse_base_total)

    if melhor is None or melhor_fold_data is None:
        return None

    r2, lam_num, lam_str, folds_melhor, folds = melhor
    norm_name, y_best, hl_best, usa_huber = melhor_spec
    fold_data, sse_base_total = melhor_fold_data

    # Avalia Huber-IRLS na especificação vencedora (proteção contra outliers com custo mínimo)
    sse_huber = 0.0
    folds_melhor_huber = 0
    for _, _, x_tr, y_tr, x_te, y_te, _, e_base, n_str in fold_data:
        pen = np.zeros(x_tr.shape[1])
        pen[:n] = lam_num
        pen[n : n + n_str] = lam_str
        beta_h = _fit_linear_step(x_tr, y_tr, pen, hl_best, usa_huber=True)
        e_h = float(((y_te - _prever(x_te, beta_h)) ** 2).sum())
        sse_huber += e_h
        folds_melhor_huber += int(e_h < e_base)
    r2_huber = 1.0 - sse_huber / sse_base_total if sse_base_total > 0 else 0.0
    if r2_huber > r2 + 0.002 and folds_melhor_huber >= folds_melhor:
        r2 = r2_huber
        folds_melhor = folds_melhor_huber
        usa_huber = True

    if r2 < R2_MINIMO or folds_melhor <= folds // 2:
        return None

    # Calcula previsões OOF do modelo linear+estrutural vencedor e resíduos de treino por fold
    oof_preds_lin: list[np.ndarray] = []
    oof_y_true: list[np.ndarray] = []
    oof_base_preds: list[np.ndarray] = []
    fold_train_res: list[tuple[slice, slice, np.ndarray, np.ndarray]] = []
    for tr, te, x_tr, y_tr, x_te, y_te, pred_base, _, n_str in fold_data:
        pen = np.zeros(x_tr.shape[1])
        pen[:n] = lam_num
        pen[n : n + n_str] = lam_str
        beta_f = _fit_linear_step(x_tr, y_tr, pen, hl_best, usa_huber=usa_huber)
        p_tr = _prever(x_tr, beta_f)
        p_te = _prever(x_te, beta_f)
        oof_preds_lin.append(p_te)
        oof_y_true.append(y_te)
        oof_base_preds.append(pred_base)
        fold_train_res.append((tr, te, y_tr - p_tr, p_te))

    # Avalia interações de 2ª ordem (pares γ_ij) via kernel dual exato sobre os últimos 2 folds
    # (onde há histórico suficiente para pares) e só ativa se houver ganho comprovado em CV.
    best_lam_pair: float | None = None
    best_pair_oof: list[np.ndarray] | None = None
    r2_with_pairs = r2

    if t >= 600 and len(fold_train_res) >= 2:
        sse_lin_all = sum(
            float(((yt - yp) ** 2).sum()) for yt, yp in zip(oof_y_true, oof_preds_lin)
        )
        # Pré-calcula matrizes de sobreposição por fold uma única vez
        pair_fold_cache = []
        for idx_f, (tr, te, res_tr, p_te) in enumerate(fold_train_res):
            x_tr_sub = x_num[tr]
            r_tr_sub = res_tr
            if len(r_tr_sub) > MAX_DUAL_PAIRS_WINDOW:
                x_tr_sub = x_tr_sub[-MAX_DUAL_PAIRS_WINDOW:]
                r_tr_sub = r_tr_sub[-MAX_DUAL_PAIRS_WINDOW:]
            ov_tr = x_tr_sub @ x_tr_sub.T
            k_tr_base = ov_tr * (ov_tr - 1.0) * 0.5
            ov_te = x_num[te] @ x_tr_sub.T
            k_te = ov_te * (ov_te - 1.0) * 0.5
            pair_fold_cache.append((k_tr_base, r_tr_sub, k_te, p_te, oof_y_true[idx_f]))

        best_sse_pair = sse_lin_all
        for lp in PAIR_LAMBDAS:
            sse_p = 0.0
            preds_p_fold: list[np.ndarray] = []
            try:
                for k_tr_base, r_tr_sub, k_te, p_te, y_te in pair_fold_cache:
                    k_reg = k_tr_base.copy()
                    k_reg[np.diag_indices_from(k_reg)] += lp
                    c_fac, lower = sp_linalg.cho_factor(
                        k_reg, overwrite_a=True, check_finite=False
                    )
                    alpha_f = sp_linalg.cho_solve(
                        (c_fac, lower), r_tr_sub, check_finite=False
                    )
                    p_comb = p_te + k_te @ alpha_f
                    sse_p += float(((y_te - p_comb) ** 2).sum())
                    preds_p_fold.append(p_comb)
            except sp_linalg.LinAlgError:
                continue

            r2_p = 1.0 - sse_p / sse_base_total if sse_base_total > 0 else 0.0
            if sse_p < best_sse_pair and (r2_p - r2) >= 0.002:
                best_sse_pair = sse_p
                best_lam_pair = float(lp)
                r2_with_pairs = r2_p
                best_pair_oof = preds_p_fold

    oof_preds_final = best_pair_oof if best_pair_oof is not None else oof_preds_lin
    r2_final = r2_with_pairs if best_lam_pair is not None else r2

    # Calibração de slope OOF, monitor de drift recente e quantil conformal 90%
    y_oof_all = np.concatenate(oof_y_true)
    p_oof_all = np.concatenate(oof_preds_final)
    b_oof_all = np.concatenate(oof_base_preds)

    # Sinal puramente dos números/estrutura = (p_oof - b_oof) vs (y_oof - b_oof)
    sig_hat = p_oof_all - b_oof_all
    sig_obs = y_oof_all - b_oof_all
    var_sig = float(np.var(sig_hat))
    if var_sig > 1e-8:
        raw_slope = float(np.cov(sig_hat, sig_obs, ddof=0)[0, 1] / var_sig)
    else:
        raw_slope = 1.0
    # Só comprime/calibra quando há descalibração relevante fora de [0.95, 1.05]
    cal_slope = float(np.clip(raw_slope, 0.55, 1.15)) if abs(raw_slope - 1.0) > 0.05 else 1.0

    # Monitor de drift nos últimos ~180 concursos OOF (ou último fold)
    n_rec = min(len(y_oof_all), max(120, len(oof_y_true[-1])))
    y_rec = y_oof_all[-n_rec:]
    p_rec = p_oof_all[-n_rec:]
    b_rec = b_oof_all[-n_rec:]
    sse_rec_base = float(((y_rec - b_rec) ** 2).sum())
    sse_rec_mod = float(((y_rec - p_rec) ** 2).sum())
    r2_recente = 1.0 - sse_rec_mod / sse_rec_base if sse_rec_base > 1e-9 else 0.0

    sig_hat_rec = p_rec - b_rec
    sig_obs_rec = y_rec - b_rec
    var_sig_rec = float(np.var(sig_hat_rec))
    cal_slope_recente = (
        float(np.cov(sig_hat_rec, sig_obs_rec, ddof=0)[0, 1] / var_sig_rec)
        if var_sig_rec > 1e-8
        else 1.0
    )
    drift_alerta = bool(
        (r2_final > 0.10 and r2_recente < 0.5 * r2_final) or cal_slope_recente < 0.65
    )

    # Quantil conformal finito 90% sobre os resíduos absolutos OOF recentes
    abs_res_rec = np.abs(y_rec - p_rec)
    m_conf = len(abs_res_rec)
    if m_conf >= 20:
        q_level = min(1.0, float(np.ceil(0.90 * (m_conf + 1))) / float(m_conf))
        conformal_q90_log = float(np.quantile(abs_res_rec, q_level))
    else:
        conformal_q90_log = None

    # Ajuste final com todos os concursos disponíveis em `df`
    controles = np.column_stack(
        [
            (log_arr - log_arr.mean()) / (log_arr.std() or 1.0),
            (tempo - tempo.mean()) / (tempo.std() or 1.0),
        ]
    )
    prm_full = _fit_struct_params(x_struct_raw)
    xs_full = _apply_struct_params(x_struct_raw, prm_full)
    n_str = xs_full.shape[1]
    x_full = np.column_stack([x_num, xs_full, controles])
    pen_full = np.zeros(x_full.shape[1])
    pen_full[:n] = lam_num
    pen_full[n : n + n_str] = lam_str
    beta = _fit_linear_step(x_full, y_best, pen_full, hl_best, usa_huber=usa_huber)

    pesos = beta[1 : 1 + n]
    pesos = pesos - pesos.mean()
    struct_coefs = beta[1 + n : 1 + n + n_str]

    pair_matrix: np.ndarray | None = None
    media_log_pares = 0.0
    if best_lam_pair is not None:
        try:
            res_full = y_best - _prever(x_full, beta)
            alpha_full, x_sub_full = _fit_pair_kernel_alpha(x_num, res_full, best_lam_pair)
            pair_matrix = _pair_matrix_from_dual(alpha_full, x_sub_full)
        except sp_linalg.LinAlgError:
            pair_matrix = None
            best_lam_pair = None

    # Centra a contribuição estrutural e de pares no nulo para que 1,0 = jogo médio
    rng_null = np.random.default_rng(1000 + config.k)
    pool = np.arange(1, n + 1)
    keys_null = rng_null.random((N_AMOSTRAS_NULO // 2, n))
    amostras_null = np.sort(
        pool[np.argpartition(keys_null, config.k - 1, axis=1)[:, : config.k]],
        axis=1,
    )
    null_struct = _apply_struct_params(_extract_struct_raw(amostras_null, config), prm_full)
    media_log_estrutural = float((null_struct @ struct_coefs).mean())
    if pair_matrix is not None:
        media_log_pares = float(_score_pairs_batch(amostras_null, pair_matrix, n).mean())

    return ModeloPopularidade(
        faixa=faixa,
        n_concursos=t,
        r2_cv=float(r2_final),
        lam=float(lam_num),
        pesos=pesos,
        k=config.k,
        n_numeros=n,
        config=config,
        struct_coefs=struct_coefs,
        struct_params=prm_full,
        media_log_estrutural=media_log_estrutural,
        meia_vida_wls=hl_best,
        normalizacao_regime=norm_name,
        pair_matrix=pair_matrix,
        media_log_pares=media_log_pares,
        lam_pares=best_lam_pair,
        usa_huber=usa_huber,
        n_outliers_filtrados=n_outliers_filtrados,
        cal_slope=cal_slope,
        r2_recente=float(r2_recente),
        cal_slope_recente=float(cal_slope_recente),
        drift_alerta=drift_alerta,
        conformal_q90_log=conformal_q90_log,
    )

