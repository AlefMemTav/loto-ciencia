# app/core/statistics/monte_carlo.py
"""
Análises estatísticas via Bootstrap e Monte Carlo.

Este módulo contém funções para estimação de intervalos de confiança
através de reamostragem bootstrap e simulação Monte Carlo para
probabilidades de acertos.
"""

import numpy as np
from typing import Optional
import pandas as pd
from app.core.lottery import GameConfig


def bootstrap_ic_soma(
    df: pd.DataFrame,
    config: GameConfig,
    n_iteracoes: int = 10000,
    nivel_confianca: float = 0.95,
    random_state: Optional[int] = None
) -> dict:
    """
    Estima intervalos de confiança da soma dos números via bootstrap.
    
    O método bootstrap reamostra os sorteios históricos com reposição
    para construir uma distribuição empírica da estatística de interesse.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo (Mega-Sena, Quina, etc.).
    n_iteracoes : int, default=10000
        Número de reamostras bootstrap.
    nivel_confianca : float, default=0.95
        Nível de confiança do intervalo (0.95 = 95%).
    random_state : int, optional
        Seed para reprodutibilidade.
    
    Returns
    -------
    dict
        Dicionário contendo:
        - 'media_bootstrap': média das médias bootstrap
        - 'std_bootstrap': desvio padrão bootstrap
        - 'ic_lower': limite inferior do IC
        - 'ic_upper': limite superior do IC
        - 'nivel_confianca': nível de confiança usado
        - 'n_iteracoes': número de iterações realizadas
    
    Examples
    --------
    >>> resultado = bootstrap_ic_soma(df, config, n_iteracoes=5000)
    >>> print(f"IC 95%: [{resultado['ic_lower']}, {resultado['ic_upper']}]")
    """
    if df.empty:
        return None
    
    if random_state is not None:
        np.random.seed(random_state)
    
    # Calcula somas dos sorteios históricos
    somas = df[config.draw_cols].sum(axis=1).values
    n_sorteios = len(somas)
    
    # Bootstrap: reamostragem com reposição
    medias_bootstrap = np.zeros(n_iteracoes)
    for i in range(n_iteracoes):
        amostra = np.random.choice(somas, size=n_sorteios, replace=True)
        medias_bootstrap[i] = amostra.mean()
    
    # Calcula percentis para o intervalo de confiança
    alpha = 1 - nivel_confianca
    ic_lower = np.percentile(medias_bootstrap, (alpha / 2) * 100)
    ic_upper = np.percentile(medias_bootstrap, (1 - alpha / 2) * 100)
    
    return {
        'media_bootstrap': float(np.mean(medias_bootstrap)),
        'std_bootstrap': float(np.std(medias_bootstrap)),
        'ic_lower': float(ic_lower),
        'ic_upper': float(ic_upper),
        'nivel_confianca': nivel_confianca,
        'n_iteracoes': n_iteracoes,
        'mediana_bootstrap': float(np.median(medias_bootstrap)),
    }


def monte_carlo_probabilidade_acerto(
    df: pd.DataFrame,
    config: GameConfig,
    numeros_apostados: list[int],
    n_simulacoes: int = 100000,
    random_state: Optional[int] = None
) -> dict:
    """
    Simula probabilidade de acertos via Monte Carlo.
    
    Gera sorteios aleatórios e conta quantos acertos seriam obtidos
    com os números apostados.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico (usado para validação).
    config : GameConfig
        Configuração do jogo.
    numeros_apostados : list[int]
        Lista de números da aposta.
    n_simulacoes : int, default=100000
        Número de simulações Monte Carlo.
    random_state : int, optional
        Seed para reprodutibilidade.
    
    Returns
    -------
    dict
        Distribuição de probabilidades de acertos.
    """
    if random_state is not None:
        np.random.seed(random_state)
    
    aposta = set(numeros_apostados)
    universo = list(range(1, config.n_numbers + 1))
    
    contagem_acertos = {i: 0 for i in range(config.k + 1)}
    
    for _ in range(n_simulacoes):
        sorteio = set(np.random.choice(universo, size=config.k, replace=False))
        acertos = len(aposta & sorteio)
        if acertos <= config.k:
            contagem_acertos[acertos] += 1
    
    probabilidades = {k: v / n_simulacoes for k, v in contagem_acertos.items()}
    
    return {
        'distribuicao_acertos': contagem_acertos,
        'probabilidades': probabilidades,
        'n_simulacoes': n_simulacoes,
        'esperanca_acertos': sum(k * p for k, p in probabilidades.items()),
    }
