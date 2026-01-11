# app/core/statistics/basic.py
"""
Funções básicas de estatística para análise de sorteios de loteria.

Este módulo contém funções para cálculo de frequências, atrasos,
tabela de inteligência e outras análises básicas.
"""

import pandas as pd
import numpy as np
import math
from collections import Counter
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


def calcular_min_gap_e_span(numeros: list[int], config: GameConfig) -> dict:
    """
    Calcula o menor gap entre números consecutivos e o span total.
    
    Otimizado para calcular ambas as métricas em um único passo.
    
    Parameters
    ----------
    numeros : list[int]
        Lista de números do jogo.
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    dict
        - 'min_gap': menor distância entre números consecutivos
        - 'max_gap': maior distância entre números consecutivos
        - 'span': amplitude total (max - min)
        - 'span_relativo': span / (n_numbers - 1)
        - 'gaps': lista de gaps entre números consecutivos
        - 'sequencias': quantidade de gaps iguais a 1 (números em sequência)
        - 'taxa_sequencias': proporção de gaps iguais a 1 em relação ao total de gaps
        - 'compactacao': se o jogo está muito compacto
    
    Examples
    --------
    >>> calcular_min_gap_e_span([1, 2, 3, 10, 20, 30], config)
    {'min_gap': 1, 'max_gap': 10, 'span': 29, ...}
    """
    if len(numeros) < 2:
        return {'erro': 'Jogo precisa de pelo menos 2 números'}
    
    numeros_sorted = sorted(numeros)
    
    # Calcula gaps em um único passo
    gaps = [numeros_sorted[i+1] - numeros_sorted[i] for i in range(len(numeros_sorted)-1)]
    
    min_gap = min(gaps)
    max_gap = max(gaps)
    span = numeros_sorted[-1] - numeros_sorted[0]
    span_relativo = span / (config.n_numbers - 1)
    
    # Análise de compactação
    # Se min_gap = 1 para muitos pares, jogo está compacto
    sequencias = sum(1 for g in gaps if g == 1)
    taxa_sequencias = sequencias / len(gaps)
    
    compactacao = "extrema" if taxa_sequencias > 0.6 else \
                  "alta" if taxa_sequencias > 0.4 else \
                  "normal"
    
    return {
        'min_gap': min_gap,
        'max_gap': max_gap,
        'span': span,
        'span_relativo': round(span_relativo, 3),
        'gaps': gaps,
        'sequencias': sequencias,
        'taxa_sequencias': round(taxa_sequencias, 3),
        'compactacao': compactacao,
    }


def calcular_entropia_faixas(
    numeros: list[int],
    config: GameConfig,
    n_faixas: int = 10
) -> dict:
    """
    Calcula entropia da distribuição de números por faixas do volante.
    
    Divide o volante em n_faixas e mede a uniformidade da distribuição
    dos números escolhidos entre essas faixas.
    
    Parameters
    ----------
    numeros : list[int]
        Lista de números do jogo.
    config : GameConfig
        Configuração do jogo.
    n_faixas : int, default=10
        Número de faixas para dividir o volante.
    
    Returns
    -------
    dict
        - 'entropia': entropia calculada
        - 'entropia_maxima': entropia máxima possível
        - 'entropia_normalizada': entropia / entropia_maxima
        - 'distribuicao': contagem por faixa
        - 'faixas_vazias': número de faixas sem números
        - 'n_faixas': número total de faixas consideradas
        - 'conclusao': interpretação qualitativa da distribuição
        - 'penalidade': valor numérico de penalidade associado à distribuição
    """
    # Tamanho de cada faixa
    tamanho_faixa = config.n_numbers / n_faixas
    
    # Conta números por faixa
    contagem = Counter()
    for num in numeros:
        faixa = min(int((num - 1) / tamanho_faixa), n_faixas - 1)
        contagem[faixa] += 1
    
    # Calcula entropia
    total = len(numeros)
    entropia = 0.0
    
    for faixa in range(n_faixas):
        count = contagem.get(faixa, 0)
        if count > 0:
            p = count / total
            entropia -= p * math.log2(p)
    
    # Entropia máxima (distribuição uniforme)
    # Depende de quantas faixas podem ser ocupadas dado k números
    faixas_ocupaveis = min(n_faixas, len(numeros))
    entropia_maxima = math.log2(faixas_ocupaveis) if faixas_ocupaveis > 0 else 0
    
    entropia_norm = entropia / entropia_maxima if entropia_maxima > 0 else 0
    
    faixas_vazias = n_faixas - len(contagem)
    
    # Interpretação
    if entropia_norm < 0.5:
        conclusao = "⚠️ Alta concentração em poucas faixas"
        penalidade = 10
    elif entropia_norm < 0.7:
        conclusao = "ℹ️ Concentração moderada"
        penalidade = 5
    else:
        conclusao = "✅ Boa distribuição entre faixas"
        penalidade = 0
    
    return {
        'entropia': round(entropia, 3),
        'entropia_maxima': round(entropia_maxima, 3),
        'entropia_normalizada': round(entropia_norm, 3),
        'distribuicao': dict(contagem),
        'faixas_vazias': faixas_vazias,
        'n_faixas': n_faixas,
        'conclusao': conclusao,
        'penalidade': penalidade,
    }
