# app/core/statistics/geometry.py
"""
Análises geométricas avançadas para sorteios de loteria.

Este módulo contém funções para análise de distribuições geométricas
baseadas em dados reais, substituindo heurísticas por estatística empírica.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from app.core.lottery import GameConfig
from app.core.statistics.basic import compute_zscore, EPSILON
from app.core.statistics.constants import (
    ZSCORE_EXTREME,
    ZSCORE_VERY_RARE,
    ZSCORE_RARE,
    PENALTY_EXTREME,
    PENALTY_VERY_RARE,
    PENALTY_RARE,
    PENALTY_NORMAL,
    PENALTY_SCALE_FACTOR,
    SCORE_CONVERSION_FACTOR,
)


# ============================================
# DISTRIBUIÇÕES GEOMÉTRICAS
# ============================================


@dataclass
class GeometricDistribution:
    """Distribuição empírica de um padrão geométrico"""

    mean: float
    std: float
    percentiles: dict[int, float]  # {5: val, 25: val, 50: val, 75: val, 95: val}
    z_scores: np.ndarray


def calcular_distribuicoes_geometricas(
    df: pd.DataFrame, conjuntos: dict[str, list[int]], config: GameConfig
) -> dict[str, GeometricDistribution]:
    """
    Calcula distribuições empíricas REAIS dos padrões geométricos.

    Substitui heurísticas por estatística baseada em dados.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    conjuntos : dict[str, list[int]]
        Dicionário mapeando nome do padrão para lista de números.
    config : GameConfig
        Configuração do jogo.

    Returns
    -------
    dict[str, GeometricDistribution]
        Dicionário com distribuições para cada grupo (moldura, miolo, cruz, xis, cantos).
    """
    if df.empty:
        return {}

    historico_sets = [set(row) for row in df[config.draw_cols].values]

    distribuicoes = {}

    for nome, numeros_grupo in conjuntos.items():
        set_grupo = set(numeros_grupo)

        # Conta quantos números de cada grupo apareceram em CADA sorteio
        contagens = np.array([len(sorteio & set_grupo) for sorteio in historico_sets])

        # Estatísticas descritivas
        mean = contagens.mean()
        std = contagens.std()

        # Percentis empíricos
        percentiles = {
            5: np.percentile(contagens, 5),
            25: np.percentile(contagens, 25),
            50: np.percentile(contagens, 50),
            75: np.percentile(contagens, 75),
            95: np.percentile(contagens, 95),
        }

        # Z-scores históricos (para detectar outliers)
        z_scores = (contagens - mean) / (std + EPSILON)

        distribuicoes[nome] = GeometricDistribution(
            mean=mean, std=std, percentiles=percentiles, z_scores=z_scores
        )

    return distribuicoes


def avaliar_jogo_geometria_estatistica(
    numeros: list[int],
    conjuntos: dict[str, list[int]],
    distribuicoes: dict[str, GeometricDistribution],
    config: GameConfig,
) -> dict:
    """
    Avalia geometria usando PROBABILIDADE EMPÍRICA ao invés de heurísticas.

    Parameters
    ----------
    numeros : list[int]
        Lista de números do jogo a avaliar.
    conjuntos : dict[str, list[int]]
        Dicionário mapeando nome do padrão para lista de números.
    distribuicoes : dict[str, GeometricDistribution]
        Distribuições empíricas calculadas.
    config : GameConfig
        Configuração do jogo.

    Returns
    -------
    dict
        Dicionário com:
        - score_geom: score geométrico (0-100)
        - detalhes: análise por padrão com z_score, p_value e categoria
        - penalidade: penalidade total acumulada

        Cada detalhe contém:
        - z_score: Quão anormal é cada padrão (-2 a +2 é normal)
        - p_value: Probabilidade de ver esse valor ou mais extremo
        - categoria: Normal, Raro, Muito Raro, Extremo
    """
    jogo = set(numeros)
    resultados = {}

    penalidade_total = 0.0

    for nome, numeros_grupo in conjuntos.items():
        if nome not in distribuicoes:
            continue

        dist = distribuicoes[nome]
        presentes = len(jogo & set(numeros_grupo))

        # Ajuste para jogos grandes (Lotomania: aposta 50 vs sorteio 20)
        qtd_jogada = len(numeros)
        if config.k != qtd_jogada and config.k > 0:
            fator_projecao = qtd_jogada / config.k
            mean_ajustada = dist.mean * fator_projecao
            std_ajustada = dist.std * np.sqrt(fator_projecao)
        else:
            mean_ajustada = dist.mean
            std_ajustada = dist.std

        # Z-score: quantos desvios-padrão do normal?
        z_score = compute_zscore(presentes, mean_ajustada, std_ajustada)

        # P-value empírico: qual % dos sorteios históricos foram tão extremos?
        mais_extremos = np.sum(np.abs(dist.z_scores) >= abs(z_score))
        p_value = mais_extremos / len(dist.z_scores) if len(dist.z_scores) > 0 else 1.0

        # Categorização baseada em Z-scores
        if abs(z_score) > ZSCORE_EXTREME:  # Evento de 3 sigma (0.3% de chance)
            categoria = "Extremo"
            peso = PENALTY_EXTREME
        elif abs(z_score) > ZSCORE_VERY_RARE:  # 2 sigma (5% de chance)
            categoria = "Muito Raro"
            peso = PENALTY_VERY_RARE
        elif abs(z_score) > ZSCORE_RARE:  # 1 sigma (32% de chance)
            categoria = "Raro"
            peso = PENALTY_RARE
        else:
            categoria = "Normal"
            peso = PENALTY_NORMAL

        penalidade_total += (
            peso * abs(z_score) * PENALTY_SCALE_FACTOR
        )  # Fator de escala

        resultados[nome] = {
            "presentes": presentes,
            "media_historica": round(float(mean_ajustada), 2),
            "desvio_historico": round(float(std_ajustada), 2),
            "z_score": round(float(z_score), 3),
            "p_value": round(float(p_value), 4),
            "categoria": categoria,
            "percentil_5": float(dist.percentiles[5]),
            "percentil_95": float(dist.percentiles[95]),
        }

    # Score geométrico baseado em desvios reais
    score_geom = max(0, min(100, int(100 - penalidade_total * SCORE_CONVERSION_FACTOR)))

    return {
        "score_geom": score_geom,
        "detalhes": resultados,
        "penalidade": round(float(penalidade_total), 2),
    }


def calcular_simetria_reflexao(
    numeros: list[int],
    config: GameConfig
) -> dict:
    """
    Calcula simetria por reflexão: quantos números têm seu "espelho".
    
    O espelho de n é (N + 1 - n), onde N = n_numbers.
    Ex: Em Mega-Sena (N=60), espelho de 1 é 60, de 2 é 59, etc.
    
    Jogos com alta simetria são estatisticamente raros e indicam
    padrão humano (ex: escolher 1, 60, 10, 51, etc.)
    
    Parameters
    ----------
    numeros : list[int]
        Lista de números do jogo.
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    dict
        - 'pares_simetricos': lista de pares (n, espelho)
        - 'n_pares': número de pares simétricos detectados
        - 'numeros_com_espelho': lista de números do jogo que possuem espelho
        - 'taxa_simetria': proporção de números com espelho no jogo
        - 'conclusao': interpretação
        - 'penalidade': penalidade sugerida
    
    Examples
    --------
    >>> calcular_simetria_reflexao([1, 10, 51, 60], config_mega)
    {'pares_simetricos': [(1, 60), (10, 51)], 'taxa_simetria': 1.0, ...}
    """
    N = config.n_numbers
    numeros_set = set(numeros)
    
    pares_simetricos = []
    numeros_com_espelho = set()
    
    for n in numeros:
        espelho = N + 1 - n
        if espelho in numeros_set and espelho != n and n not in numeros_com_espelho:
            pares_simetricos.append((min(n, espelho), max(n, espelho)))
            numeros_com_espelho.add(n)
            numeros_com_espelho.add(espelho)
    
    # Taxa de simetria: proporção de números que têm espelho no jogo
    taxa_simetria = len(numeros_com_espelho) / len(numeros) if numeros else 0
    
    # Interpretação
    # Probabilidade de k números terem pelo menos 1 par simétrico é baixa
    # Para Mega (6 de 60): ~3% de chance de ter 1 par
    # Ter 2+ pares é muito raro (~0.1%)
    # Para jogos maiores (LOTOFACIL 15 de 25), a chance é maior
    
    k = len(numeros)
    k_ratio = k / N  # Proporção de números selecionados
    
    # Ajuste de thresholds baseado no tamanho do jogo
    if k_ratio > 0.4:  # Jogos grandes como LOTOFACIL (15/25 = 0.6)
        # Para jogos grandes, pares simétricos são mais comuns
        # Exigir proporção alta para penalizar
        if taxa_simetria >= 0.5:  # Metade ou mais dos números têm espelho
            conclusao = "🚨 Alta simetria (múltiplos pares espelhados) - muito raro"
            penalidade = 15
        elif len(pares_simetricos) >= 2:
            conclusao = "⚠️ Alguns pares simétricos detectados"
            penalidade = 5
        elif len(pares_simetricos) == 1:
            conclusao = "ℹ️ Par simétrico detectado (aceitável para este jogo)"
            penalidade = 0
        else:
            conclusao = "✅ Sem simetria por reflexão"
            penalidade = 0
    else:  # Jogos pequenos como MEGA-SENA (6/60 = 0.1)
        # Para jogos pequenos, pares simétricos são raros
        if len(pares_simetricos) >= 2:
            conclusao = "🚨 Alta simetria (múltiplos pares espelhados) - muito raro"
            penalidade = 15
        elif len(pares_simetricos) == 1:
            conclusao = "⚠️ Par simétrico detectado"
            penalidade = 5
        else:
            conclusao = "✅ Sem simetria por reflexão"
            penalidade = 0
    
    return {
        'pares_simetricos': pares_simetricos,
        'n_pares': len(pares_simetricos),
        'numeros_com_espelho': list(numeros_com_espelho),
        'taxa_simetria': round(taxa_simetria, 3),
        'conclusao': conclusao,
        'penalidade': penalidade,
    }
