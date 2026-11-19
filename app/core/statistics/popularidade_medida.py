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
# (R2 de CV temporal estrita com normalização causal + WLS + estrutura 2D:
# Quina ~0,78, Lotofácil ~0,55, Lotomania ~0,38, Mega-Sena ~0,38).
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
STRUCT_LAMBDAS = (100.0, 1000.0)
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
        return score

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
        """Popularidade de um jogo: percentil e razão de ganhadores vs. jogo médio."""
        arr = np.array([sorted(numeros)], dtype=int)
        percentil = float(self.percentil_batch(arr)[0])
        razao = None
        bet_size_cfg = getattr(self.config, "bet_size", self.k) if self.config is not None else self.k
        if len(numeros) in {self.k, bet_size_cfg}:
            razao = float(self.razao_ganhadores_batch(arr)[0])
        return {"percentil": percentil, "razao_ganhadores": razao}


def treinar_modelo_popularidade(
    df: pd.DataFrame, detalhes: pd.DataFrame | None, config
) -> ModeloPopularidade | None:
    """
    Ajusta o modelo com os concursos presentes em `df` E em `detalhes`
    (só usa o que está no df, então não vaza o futuro em backtests).
    Combina pesos por número com métricas estruturais 1D/2D e quadráticas do bilhete,
    normalização causal por mediana móvel contra saltos de preço e WLS exponencial.
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
    ganhadores = pd.to_numeric(det[f"faixa{faixa}_ganhadores"], errors="coerce")
    arrecadado = pd.to_numeric(det["valorArrecadado"], errors="coerce")
    ok = (ganhadores.notna() & arrecadado.notna() & (arrecadado > 0)).to_numpy()
    if ok.sum() < MIN_CONCURSOS:
        return None

    ganhadores = ganhadores.to_numpy()[ok]
    arrecadado = arrecadado.to_numpy()[ok]
    sorteios = sorteios[ok]
    t = len(ganhadores)
    n = config.n_numbers

    y_raw = np.log((ganhadores + 0.5) / arrecadado * 1e6)
    med_causal = _causal_rolling_median(y_raw, window=50)
    y_norm = y_raw - med_causal

    # Controles (reduzem ruído de regime; os números sorteados são independentes deles)
    log_arr = np.log(arrecadado)
    tempo = np.arange(t, dtype=float)
    controles = np.column_stack(
        [
            (log_arr - log_arr.mean()) / (log_arr.std() or 1.0),
            (tempo - tempo.mean()) / (tempo.std() or 1.0),
        ]
    )
    x_num = np.zeros((t, n))
    x_num[np.repeat(np.arange(t), config.k), (sorteios - 1).ravel()] = 1.0
    x_struct_raw = _extract_struct_raw(sorteios, config)

    # Pré-calcula folds temporais sem vazamento para ambos os alvos (bruto e normalizado por mediana móvel causal)
    limites = np.linspace(0, t, N_BLOCOS_CV + 1).astype(int)
    targets_specs = [
        ("mediana_movel_causal", y_norm),
        ("log_arrecadado_linear", y_raw),
    ]
    half_lives: tuple[float | None, ...] = (None, 1000.0)

    melhor = None
    melhor_spec = ("mediana_movel_causal", y_norm, None)

    for norm_name, y_target in targets_specs:
        fold_data = []
        for f in range(1, N_BLOCOS_CV):
            tr = slice(0, limites[f])
            te = slice(limites[f], limites[f + 1])
            prm = _fit_struct_params(x_struct_raw[tr])
            xs_tr = _apply_struct_params(x_struct_raw[tr], prm)
            xs_te = _apply_struct_params(x_struct_raw[te], prm)
            x_tr = np.column_stack([x_num[tr], xs_tr, controles[tr]])
            x_te = np.column_stack([x_num[te], xs_te, controles[te]])
            beta_base = _ridge(controles[tr], y_target[tr], 0.0, 0)
            e_base = float(((y_target[te] - _prever(controles[te], beta_base)) ** 2).sum())
            fold_data.append((x_tr, y_target[tr], x_te, y_target[te], e_base, xs_tr.shape[1]))

        sse_base_total = sum(fd[4] for fd in fold_data)
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
            for x_tr, y_tr, x_te, y_te, e_base, n_str in fold_data:
                pen = np.zeros(x_tr.shape[1])
                pen[:n] = lam_num
                pen[n : n + n_str] = lam_str
                w_tr = (
                    0.5 ** ((len(y_tr) - 1 - np.arange(len(y_tr), dtype=float)) / hl)
                    if hl is not None
                    else None
                )
                beta = _ridge(x_tr, y_tr, 0.0, 0, penalties=pen, weights=w_tr)
                e_mod = float(((y_te - _prever(x_te, beta)) ** 2).sum())
                sse_modelo += e_mod
                folds_melhor += int(e_mod < e_base)
            r2 = 1.0 - sse_modelo / sse_base_total if sse_base_total > 0 else 0.0
            if melhor is None or r2 > melhor[0]:
                melhor = (r2, lam_num, lam_str, folds_melhor, folds)
                melhor_spec = (norm_name, y_target, hl)

    r2, lam_num, lam_str, folds_melhor, folds = melhor
    norm_name, y_best, hl_best = melhor_spec
    if r2 < R2_MINIMO or folds_melhor <= folds // 2:
        return None

    prm_full = _fit_struct_params(x_struct_raw)
    xs_full = _apply_struct_params(x_struct_raw, prm_full)
    n_str = xs_full.shape[1]
    x_full = np.column_stack([x_num, xs_full, controles])
    pen_full = np.zeros(x_full.shape[1])
    pen_full[:n] = lam_num
    pen_full[n : n + n_str] = lam_str
    w_full = (
        0.5 ** ((t - 1 - np.arange(t, dtype=float)) / hl_best)
        if hl_best is not None
        else None
    )
    beta = _ridge(x_full, y_best, 0.0, 0, penalties=pen_full, weights=w_full)

    pesos = beta[1 : 1 + n]
    pesos = pesos - pesos.mean()
    struct_coefs = beta[1 + n : 1 + n + n_str]

    # Centra a contribuição estrutural no nulo para que 1,0 = jogo médio
    rng_null = np.random.default_rng(1000 + config.k)
    pool = np.arange(1, n + 1)
    keys_null = rng_null.random((N_AMOSTRAS_NULO // 2, n))
    amostras_null = np.sort(
        pool[np.argpartition(keys_null, config.k - 1, axis=1)[:, : config.k]],
        axis=1,
    )
    null_struct = _apply_struct_params(_extract_struct_raw(amostras_null, config), prm_full)
    media_log_estrutural = float((null_struct @ struct_coefs).mean())

    return ModeloPopularidade(
        faixa=faixa,
        n_concursos=t,
        r2_cv=float(r2),
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
    )
