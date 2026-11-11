# app/core/statistics/ordem_saida.py
"""
Análise da ORDEM DE SAÍDA das bolas.

Usa as colunas D1..Dk na ordem em que as bolas foram sorteadas (não ordenadas).
Serve a dois propósitos:

1. Auditoria do sorteio: cada número sai em posições uniformes do sorteio?
   (testes com correção de Benjamini-Hochberg para múltiplos testes)
2. Pontuação de jogos (preferência): quão "precoce" ou "tardio" é o conjunto de
   números de um jogo na ordem histórica de saída, comparado com jogos
   aleatórios. Não altera a probabilidade de acerto: o prêmio independe da ordem.

Cuidado com os dados: em algumas planilhas (ex.: Quina) as linhas mais antigas
vêm em ordem crescente, não na ordem de saída. Essas linhas são detectadas e
descartadas antes de qualquer cálculo.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from app.core.statistics.multiple_testing import (
    benjamini_hochberg as _benjamini_hochberg,
)

N_AMOSTRAS_NULO = 4000
ALFA = 0.05


def mascara_ordem_de_saida(df: pd.DataFrame, config) -> np.ndarray:
    """
    Marca (True) as linhas que estão na ordem real de saída.

    Supõe que o df esteja em ordem cronológica (mais antigo primeiro) e que
    no máximo um bloco INICIAL (o mais antigo) esteja ordenado de forma crescente.
    O ponto de corte é o que minimiza as linhas incoerentes: crescentes depois do
    corte ou não crescentes antes dele. Em dados aleatórios, a chance de uma linha
    sair estritamente crescente por acaso é 1/k!, então o corte só aparece quando
    há mesmo um bloco ordenado.
    """
    n = len(df)
    if n == 0:
        return np.zeros(0, dtype=bool)

    vals = df[config.draw_cols].to_numpy()
    crescente = (np.diff(vals, axis=1) > 0).all(axis=1).astype(int)

    # custo(c) = linhas não crescentes em [0, c) + linhas crescentes em [c, n)
    nao_cresc_ate = np.concatenate([[0], np.cumsum(1 - crescente)])
    cresc_total = crescente.sum()
    cresc_ate = np.concatenate([[0], np.cumsum(crescente)])
    custo = nao_cresc_ate + (cresc_total - cresc_ate)

    corte = int(np.argmin(custo))
    mascara = np.ones(n, dtype=bool)
    mascara[:corte] = False
    return mascara


def posicoes_normalizadas(df: pd.DataFrame, config, mascara=None) -> np.ndarray:
    """
    Matriz (linhas_validas, n_numeros) com a posição de saída de cada número,
    normalizada em [0, 1] (0 = primeira bola, 1 = última). NaN se não saiu.
    """
    if mascara is None:
        mascara = mascara_ordem_de_saida(df, config)
    vals = df[config.draw_cols].to_numpy()[mascara]
    t, k = vals.shape
    n = config.n_numbers
    pos = np.full((t, n), np.nan)
    linhas = np.repeat(np.arange(t), k)
    colunas = (vals - 1).ravel()
    pos[linhas, colunas] = np.tile(np.arange(k) / max(1, k - 1), t)
    return pos


@dataclass
class PerfilPosicional:
    n_numeros: int
    k: int
    n_linhas_validas: int
    n_linhas_ignoradas: int
    n_obs: np.ndarray
    media: np.ndarray  # posição média normalizada de cada número (esperado 0,5)
    desvio: np.ndarray  # media - 0,5 (0 se o número nunca saiu)
    z: np.ndarray
    p_valor: np.ndarray
    p_ajustado: np.ndarray
    p_primeira_bola: float
    p_ultima_bola: float
    nulo: np.ndarray = field(repr=False, default_factory=lambda: np.zeros(0))
    _nulos_por_tamanho: dict = field(repr=False, default_factory=dict)

    @property
    def n_significativos(self) -> int:
        return int((self.p_ajustado < ALFA).sum())

    def conclusao(self) -> str:
        sig = self.n_significativos
        extremos = min(self.p_primeira_bola, self.p_ultima_bola) < ALFA / 2
        if sig == 0 and not extremos:
            return "sem evidência de desvio na ordem de saída"
        partes = []
        if sig:
            partes.append(f"{sig} número(s) com posição média fora do esperado (FDR 5%)")
        if extremos:
            partes.append("primeira/última bola fora da uniformidade")
        return "possível desvio: " + "; ".join(partes)


def _chi2_uniforme(contagens: np.ndarray) -> float:
    esperado = contagens.sum() / len(contagens)
    if esperado <= 0:
        return 1.0
    chi2 = float(((contagens - esperado) ** 2 / esperado).sum())
    return float(1.0 - stats.chi2.cdf(chi2, df=len(contagens) - 1))


def calcular_perfil_posicional(
    df: pd.DataFrame, config, n_amostras: int = N_AMOSTRAS_NULO, seed: int = 0
) -> PerfilPosicional | None:
    """Perfil posicional do histórico. None se houver poucas linhas válidas."""
    if df is None or df.empty:
        return None

    mascara = mascara_ordem_de_saida(df, config)
    n_validas = int(mascara.sum())
    k = config.k
    n = config.n_numbers
    if n_validas < 50 or k < 2:
        return None

    pos = posicoes_normalizadas(df, config, mascara)
    n_obs = (~np.isnan(pos)).sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        media = np.nanmean(pos, axis=0)

    # sob a hipótese nula, dado que o número saiu, sua posição é uniforme em k posições
    var_pos = (k + 1) / (12.0 * (k - 1))
    with np.errstate(invalid="ignore", divide="ignore"):
        z = (media - 0.5) / np.sqrt(var_pos / np.maximum(n_obs, 1))
    z = np.where(n_obs > 0, z, 0.0)
    p = 2.0 * stats.norm.sf(np.abs(z))
    p = np.where(n_obs > 0, p, 1.0)
    desvio = np.where(n_obs > 0, media - 0.5, 0.0)

    vals = df[config.draw_cols].to_numpy()[mascara]
    primeira = np.bincount(vals[:, 0] - 1, minlength=n)
    ultima = np.bincount(vals[:, -1] - 1, minlength=n)

    rng = np.random.default_rng(seed)
    amostras = np.array(
        [rng.choice(n, size=k, replace=False) for _ in range(n_amostras)]
    )
    nulo = np.sort(desvio[amostras].mean(axis=1))

    return PerfilPosicional(
        n_numeros=n,
        k=k,
        n_linhas_validas=n_validas,
        n_linhas_ignoradas=len(df) - n_validas,
        n_obs=n_obs,
        media=np.nan_to_num(media, nan=0.5),
        desvio=desvio,
        z=z,
        p_valor=p,
        p_ajustado=_benjamini_hochberg(p),
        p_primeira_bola=_chi2_uniforme(primeira),
        p_ultima_bola=_chi2_uniforme(ultima),
        nulo=nulo,
        _nulos_por_tamanho={k: nulo},
    )


def _nulo_para_tamanho(perfil: PerfilPosicional, m: int) -> np.ndarray:
    if m not in perfil._nulos_por_tamanho:
        rng = np.random.default_rng(m)
        amostras = np.array(
            [
                rng.choice(perfil.n_numeros, size=m, replace=False)
                for _ in range(N_AMOSTRAS_NULO // 2)
            ]
        )
        perfil._nulos_por_tamanho[m] = np.sort(perfil.desvio[amostras].mean(axis=1))
    return perfil._nulos_por_tamanho[m]


def percentil_posicional_batch(candidatos: np.ndarray, perfil: PerfilPosicional) -> np.ndarray:
    """
    Percentil (0-100) da tendência posicional de cada jogo (linhas de `candidatos`)
    frente a jogos aleatórios do mesmo tamanho. Perto de 0: números que costumam
    sair cedo; perto de 100: números que costumam sair tarde.
    """
    candidatos = np.asarray(candidatos)
    if candidatos.size == 0:
        return np.array([], dtype=float)
    valores = perfil.desvio[candidatos - 1].mean(axis=1)
    nulo = _nulo_para_tamanho(perfil, candidatos.shape[1])
    return 100.0 * np.searchsorted(nulo, valores, side="right") / len(nulo)


def percentil_posicional(numeros, perfil: PerfilPosicional) -> float:
    return float(percentil_posicional_batch(np.array([sorted(numeros)]), perfil)[0])


def auditar_ordem_saida(df: pd.DataFrame, config) -> dict:
    """Resumo da auditoria da ordem de saída (para relatórios e decisão)."""
    perfil = calcular_perfil_posicional(df, config)
    if perfil is None:
        return {"disponivel": False, "motivo": "poucas linhas na ordem real de saída"}
    return {
        "disponivel": True,
        "linhas_validas": perfil.n_linhas_validas,
        "linhas_ignoradas": perfil.n_linhas_ignoradas,
        "testes": int(config.n_numbers),
        "significativos_fdr": perfil.n_significativos,
        "menor_p": float(perfil.p_valor.min()),
        "menor_p_ajustado": float(perfil.p_ajustado.min()),
        "p_primeira_bola": perfil.p_primeira_bola,
        "p_ultima_bola": perfil.p_ultima_bola,
        "conclusao": perfil.conclusao(),
    }
