# app/core/statistics/basic.py
"""
Funções básicas de estatística para análise de sorteios de loteria.

Este módulo contém funções para cálculo de frequências, atrasos,
tabela de inteligência e outras análises básicas.
"""

import pandas as pd
import numpy as np
from app.core.lottery import GameConfig


# ============================================
# CONSTANTES DE CONFIGURAÇÃO ESTATÍSTICA
# ============================================

# Pesos para cálculo do score composto
WEIGHT_FREQUENCY: float = 0.40
WEIGHT_GAP: float = 0.60

# Epsilon para evitar divisão por zero
EPSILON: float = 1e-9


def compute_zscore(value: float, mean: float, std: float) -> float:
    """
    Calcula o Z-score (desvio padrão normalizado) de um valor.
    
    O Z-score indica quantos desvios-padrão um valor está da média.
    Usa EPSILON para evitar divisão por zero.
    
    Parameters
    ----------
    value : float
        Valor observado.
    mean : float
        Média da distribuição.
    std : float
        Desvio padrão da distribuição.
    
    Returns
    -------
    float
        Z-score calculado.
    
    Examples
    --------
    >>> compute_zscore(15, 10, 2)
    2.5
    >>> compute_zscore(10, 10, 0)  # std=0, usa EPSILON
    0.0
    """
    return (value - mean) / (std + EPSILON)


def _flatten_draws(df: pd.DataFrame, config: GameConfig) -> np.ndarray:
    """
    Flatten all draw columns into a 1D array.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with lottery draws.
    config : GameConfig
        Game configuration.
    
    Returns
    -------
    np.ndarray
        Flattened array of all drawn numbers.
    """
    return df[config.draw_cols].values.flatten()


def get_numeros_quentes_frios(df: pd.DataFrame, config: GameConfig) -> pd.Series:
    """
    Retorna contagem de frequência de todos os números.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    pd.Series
        Série com frequência de cada número, ordenada decrescentemente.
    """
    if df.empty:
        return pd.Series()
    todos = _flatten_draws(df, config)
    return pd.Series(todos).value_counts().sort_values(ascending=False)


def get_historico_jogos(df: pd.DataFrame, config: GameConfig) -> set[tuple]:
    """
    SET de jogos já sorteados para lookup O(1).
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    set[tuple]
        Conjunto de tuplas ordenadas representando cada jogo sorteado.
    """
    if df.empty:
        return set()
    jogos = df[config.draw_cols].values
    return set(tuple(sorted(jogo)) for jogo in jogos)


def verificar_historico(numeros: list[int], df: pd.DataFrame, config: GameConfig, alvos: list[int] | None = None) -> dict[int, list[str]]:
    """
    Verifica quantos acertos o jogo teria com sorteios históricos.
    
    Parameters
    ----------
    numeros : list[int]
        Lista de números do jogo a verificar.
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    alvos : list[int] | None, optional
        Lista de quantidades de acertos a verificar. 
        Se None, usa [k, k-1, k-2] onde k é o tamanho do sorteio.
    
    Returns
    -------
    dict[int, list[str]]
        Dicionário mapeando quantidade de acertos para lista de concursos.
    """
    meus = set(numeros)
    if alvos is None:
        alvos = [config.k, config.k - 1, config.k - 2]

    res = {a: [] for a in alvos}
    for idx, row in df.iterrows():
        sorteio = set(row[config.draw_cols].values)
        acertos = len(meus.intersection(sorteio))
        if acertos in res:
            res[acertos].append(f"Conc. {idx}")
    return res


def get_reis_da_sequencia(df: pd.DataFrame, config: GameConfig) -> list[int]:
    """
    Identifica números que mais formam pares consecutivos.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    list[int]
        Lista de números que mais aparecem em sequências consecutivas.
    """
    if df.empty:
        return []

    todos_pares = []
    for _, row in df.iterrows():
        sorteio = sorted(row[config.draw_cols].values)
        for i in range(len(sorteio) - 1):
            if sorteio[i + 1] == sorteio[i] + 1:
                todos_pares.append((sorteio[i], sorteio[i + 1]))

    if not todos_pares:
        return []

    freq_pares = pd.Series(todos_pares).value_counts().head(15)
    numeros = set()
    for par in freq_pares.index:
        numeros.add(par[0])
        numeros.add(par[1])

    return sorted(list(numeros))


def calcular_atrasos(df: pd.DataFrame, config: GameConfig) -> pd.Series:
    """
    Adiciona normalização por tamanho da base.
    Gap relativo = Gap absoluto / Total de jogos.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    pd.Series
        Série com atraso de cada número desde o último sorteio,
        ordenada decrescentemente.
    """
    if df.empty:
        return pd.Series()

    ultimo_concurso = df.index.max()
    total_concursos = len(df)

    stacked = df[config.draw_cols].stack().reset_index()
    stacked.columns = ["Concurso", "Col", "Numero"]
    ultima_aparicao = stacked.groupby("Numero")["Concurso"].max()

    atrasos = {}
    for n in range(1, config.n_numbers + 1):
        if n in ultima_aparicao:
            gap_absoluto = ultimo_concurso - ultima_aparicao[n]
            atrasos[n] = gap_absoluto
        else:
            atrasos[n] = ultimo_concurso

    return pd.Series(atrasos).sort_values(ascending=False)


def get_tabela_inteligencia(df: pd.DataFrame, config: GameConfig) -> pd.DataFrame:
    """
    Calcula tabela de inteligência com frequências, atrasos e pesos.
    
    Calcula Z-scores para frequência e atraso, peso composto normalizado
    e percentis para análise estatística dos números.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    pd.DataFrame
        DataFrame com colunas:
        - Frequencia: contagem de aparições
        - Atraso: sorteios desde última aparição
        - Z_Freq: Z-score da frequência
        - Z_Gap: Z-score do atraso
        - Peso_Composto: score combinado
        - Peso_Geracao: peso normalizado para geração
        - Percentil_Freq: percentil da frequência
        - Percentil_Gap: percentil do atraso
    """
    if df.empty:
        return pd.DataFrame()

    freq = get_numeros_quentes_frios(df, config).sort_index()
    atrasos = calcular_atrasos(df, config).sort_index()

    df_stats = pd.DataFrame(index=range(1, config.n_numbers + 1))
    df_stats["Frequencia"] = freq
    df_stats["Atraso"] = atrasos
    df_stats = df_stats.fillna(0)

    # 1. Z-Scores
    mu_freq = df_stats["Frequencia"].mean()
    sigma_freq = df_stats["Frequencia"].std()
    df_stats["Z_Freq"] = compute_zscore(df_stats["Frequencia"], mu_freq, sigma_freq)

    mu_gap = df_stats["Atraso"].mean()
    sigma_gap = df_stats["Atraso"].std()
    df_stats["Z_Gap"] = compute_zscore(df_stats["Atraso"], mu_gap, sigma_gap)

    # 2. Peso Composto
    df_stats["Peso_Composto"] = df_stats["Z_Freq"] * WEIGHT_FREQUENCY + df_stats["Z_Gap"] * WEIGHT_GAP

    # 3. Normalização
    peso_min = df_stats["Peso_Composto"].min()
    peso_max = df_stats["Peso_Composto"].max()
    df_stats["Peso_Geracao"] = (
        (df_stats["Peso_Composto"] - peso_min) / (peso_max - peso_min + EPSILON)
    ) + 0.01

    # 4. Métricas adicionais
    df_stats["Percentil_Freq"] = df_stats["Frequencia"].rank(pct=True)
    df_stats["Percentil_Gap"] = df_stats["Atraso"].rank(pct=True)

    return df_stats
