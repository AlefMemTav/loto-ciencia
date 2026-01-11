# app/core/statistics/advanced.py
"""
Funções avançadas de estatística para análise de sorteios de loteria.

Este módulo contém funções para análises estatísticas avançadas incluindo:
- Matriz de co-ocorrência entre números
- Cadeias de Markov (transições entre sorteios)
- Teste de Runs (Wald-Wolfowitz)
- Índice de Dispersão (Variance-to-Mean Ratio)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple
from math import comb
from collections import Counter
from scipy.stats import norm, chi2

from app.core.lottery import GameConfig


# ============================================
# 1. MATRIZ DE CO-OCORRÊNCIA
# ============================================


def matriz_coocorrencia_numeros(df: pd.DataFrame, config: GameConfig) -> np.ndarray:
    """
    Calcula matriz de co-ocorrência normalizada entre números.
    
    Mede quantas vezes cada par de números apareceu junto nos sorteios,
    normalizado pela frequência esperada sob independência.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    np.ndarray
        Matriz NxN onde N = config.n_numbers.
        Valores > 1 indicam co-ocorrência acima do esperado.
        Valores < 1 indicam co-ocorrência abaixo do esperado.
    
    Examples
    --------
    >>> matriz = matriz_coocorrencia_numeros(df, MEGASENA)
    >>> matriz[6, 12]  # Co-ocorrência entre números 7 e 13
    1.23  # 23% acima do esperado
    """
    if df.empty:
        return np.zeros((config.n_numbers, config.n_numbers))
    
    n = config.n_numbers
    matriz = np.zeros((n, n))
    
    # Conta co-ocorrências
    for _, row in df.iterrows():
        nums = row[config.draw_cols].values
        for i in nums:
            for j in nums:
                if i != j:
                    matriz[i-1][j-1] += 1
    
    # Normaliza pela frequência esperada
    n_sorteios = len(df)
    k = config.k
    
    # Probabilidade esperada de dois números específicos saírem juntos
    # P(A e B) = C(n-2, k-2) / C(n, k)
    prob_esperada = comb(n - 2, k - 2) / comb(n, k)
    esperado = n_sorteios * prob_esperada
    
    # Evita divisão por zero
    matriz_normalizada = matriz / (esperado + 1e-9)
    
    return matriz_normalizada


def get_pares_mais_frequentes(df: pd.DataFrame, config: GameConfig, top_n: int = 20) -> list[dict]:
    """
    Retorna os pares de números que mais co-ocorrem historicamente.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    top_n : int, optional
        Número de pares a retornar (default: 20).
    
    Returns
    -------
    list[dict]
        Lista de dicts com 'par', 'ocorrencias', 'razao' (vs esperado).
    
    Examples
    --------
    >>> pares = get_pares_mais_frequentes(df, MEGASENA, top_n=10)
    >>> pares[0]
    {'par': (10, 23), 'ocorrencias': 45, 'razao': 1.35}
    """
    if df.empty:
        return []
    
    contador_pares = Counter()
    
    for _, row in df.iterrows():
        nums = sorted(row[config.draw_cols].values)
        for i in range(len(nums)):
            for j in range(i + 1, len(nums)):
                contador_pares[(nums[i], nums[j])] += 1
    
    # Calcula esperado
    n_sorteios = len(df)
    prob_esperada = comb(config.n_numbers - 2, config.k - 2) / comb(config.n_numbers, config.k)
    esperado = n_sorteios * prob_esperada
    
    # Monta resultado
    resultado = []
    for par, ocorrencias in contador_pares.most_common(top_n):
        resultado.append({
            'par': par,
            'ocorrencias': ocorrencias,
            'razao': round(ocorrencias / esperado, 3)
        })
    
    return resultado


def get_pares_que_se_repelem(df: pd.DataFrame, config: GameConfig, top_n: int = 20) -> list[dict]:
    """
    Retorna os pares de números que menos co-ocorrem (se "repelem").
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    top_n : int, optional
        Número de pares a retornar (default: 20).
    
    Returns
    -------
    list[dict]
        Lista de dicts com 'par', 'ocorrencias', 'razao' (vs esperado).
    """
    if df.empty:
        return []
    
    contador_pares = Counter()
    
    # Inicializa todos os pares possíveis com 0
    for i in range(1, config.n_numbers + 1):
        for j in range(i + 1, config.n_numbers + 1):
            contador_pares[(i, j)] = 0
    
    # Conta ocorrências
    for _, row in df.iterrows():
        nums = sorted(row[config.draw_cols].values)
        for i in range(len(nums)):
            for j in range(i + 1, len(nums)):
                contador_pares[(nums[i], nums[j])] += 1
    
    # Calcula esperado
    n_sorteios = len(df)
    prob_esperada = comb(config.n_numbers - 2, config.k - 2) / comb(config.n_numbers, config.k)
    esperado = n_sorteios * prob_esperada
    
    # Ordena do menor para o maior
    pares_ordenados = sorted(contador_pares.items(), key=lambda x: x[1])
    
    resultado = []
    for par, ocorrencias in pares_ordenados[:top_n]:
        resultado.append({
            'par': par,
            'ocorrencias': ocorrencias,
            'razao': round(ocorrencias / esperado, 3) if esperado > 0 else 0
        })
    
    return resultado


# ============================================
# 2. CADEIAS DE MARKOV
# ============================================


def calcular_matriz_transicao(df: pd.DataFrame, config: GameConfig) -> np.ndarray:
    """
    Calcula matriz de transição de Markov entre números.
    
    M[i,j] = P(número j sai no sorteio t+1 | número i saiu no sorteio t)
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios (ordenado cronologicamente).
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    np.ndarray
        Matriz NxN de probabilidades de transição.
    
    Notes
    -----
    Em uma loteria verdadeiramente aleatória, todas as linhas deveriam
    convergir para a mesma distribuição uniforme. Desvios significativos
    podem indicar padrões ou problemas na aleatoriedade.
    
    Examples
    --------
    >>> matriz = calcular_matriz_transicao(df, MEGASENA)
    >>> matriz[6, 13]  # P(14 sair | 7 saiu no anterior)
    0.105
    """
    if df.empty or len(df) < 2:
        return np.zeros((config.n_numbers, config.n_numbers))
    
    n = config.n_numbers
    matriz_contagem = np.zeros((n, n))
    
    # Conta transições
    for i in range(1, len(df)):
        anterior = set(df.iloc[i-1][config.draw_cols].values)
        atual = set(df.iloc[i][config.draw_cols].values)
        
        for a in anterior:
            for b in atual:
                matriz_contagem[a-1][b-1] += 1
    
    # Normaliza por linha (soma de cada linha = 1)
    soma_linhas = matriz_contagem.sum(axis=1, keepdims=True)
    matriz_prob = matriz_contagem / (soma_linhas + 1e-9)
    
    return matriz_prob


def analisar_transicoes_anomalas(df: pd.DataFrame, config: GameConfig, threshold_zscore: float = 2.5) -> list[dict]:
    """
    Identifica transições com frequência anormalmente alta ou baixa.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    threshold_zscore : float, optional
        Limiar de Z-score para considerar anomalia (default: 2.5).
    
    Returns
    -------
    list[dict]
        Lista de transições anômalas com 'de', 'para', 'observado', 
        'esperado', 'zscore', 'tipo'.
    
    Examples
    --------
    >>> anomalias = analisar_transicoes_anomalas(df, MEGASENA)
    >>> anomalias[0]
    {'de': 7, 'para': 14, 'observado': 45, 'esperado': 30.2, 
     'zscore': 2.7, 'tipo': 'excesso'}
    """
    if df.empty or len(df) < 2:
        return []
    
    n = config.n_numbers
    k = config.k
    n_transicoes = len(df) - 1
    
    # Conta transições
    matriz_contagem = np.zeros((n, n))
    for i in range(1, len(df)):
        anterior = set(df.iloc[i-1][config.draw_cols].values)
        atual = set(df.iloc[i][config.draw_cols].values)
        for a in anterior:
            for b in atual:
                matriz_contagem[a-1][b-1] += 1
    
    # Esperado: cada número sai com probabilidade k/n
    # Transições esperadas de i para j = n_transicoes * k * (k/n)
    esperado_por_celula = n_transicoes * k * (k / n)
    
    # Calcula Z-scores
    # Assumindo distribuição aproximadamente Poisson para contagens
    std_esperado = np.sqrt(esperado_por_celula)
    
    anomalias = []
    for i in range(n):
        for j in range(n):
            observado = matriz_contagem[i, j]
            zscore = (observado - esperado_por_celula) / (std_esperado + 1e-9)
            
            if abs(zscore) >= threshold_zscore:
                anomalias.append({
                    'de': i + 1,
                    'para': j + 1,
                    'observado': int(observado),
                    'esperado': round(esperado_por_celula, 2),
                    'zscore': round(zscore, 2),
                    'tipo': 'excesso' if zscore > 0 else 'deficit'
                })
    
    # Ordena por Z-score absoluto (mais anômalo primeiro)
    anomalias.sort(key=lambda x: abs(x['zscore']), reverse=True)
    
    return anomalias


# ============================================
# 3. TESTE DE RUNS (WALD-WOLFOWITZ)
# ============================================


def teste_runs_numero(df: pd.DataFrame, numero: int, config: GameConfig) -> dict:
    """
    Aplica teste de runs (Wald-Wolfowitz) para um número específico.
    
    Verifica se a sequência de "saiu/não saiu" de um número é aleatória.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    numero : int
        Número a ser testado (1 a n_numbers).
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    dict
        Resultado com 'numero', 'n_runs', 'n_runs_esperado', 
        'zscore', 'p_value', 'aleatorio' (bool).
    
    Notes
    -----
    - H0: A sequência é aleatória
    - H1: A sequência não é aleatória
    - Se p_value < 0.05, rejeitamos H0 (sequência não é aleatória)
    
    Examples
    --------
    >>> resultado = teste_runs_numero(df, 7, MEGASENA)
    >>> resultado
    {'numero': 7, 'n_runs': 523, 'n_runs_esperado': 512.3,
     'zscore': 0.67, 'p_value': 0.503, 'aleatorio': True}
    """
    if df.empty:
        return {'numero': numero, 'erro': 'DataFrame vazio'}
    
    # Cria sequência binária: 1 se saiu, 0 se não saiu
    sequencia = []
    for _, row in df.iterrows():
        if numero in row[config.draw_cols].values:
            sequencia.append(1)
        else:
            sequencia.append(0)
    
    if len(sequencia) < 10:
        return {'numero': numero, 'erro': 'Sequência muito curta'}
    
    # Conta runs
    n_runs = 1
    for i in range(1, len(sequencia)):
        if sequencia[i] != sequencia[i-1]:
            n_runs += 1
    
    # Conta 1s e 0s
    n1 = sum(sequencia)
    n0 = len(sequencia) - n1
    
    if n1 == 0 or n0 == 0:
        return {'numero': numero, 'erro': 'Número nunca saiu ou sempre saiu'}
    
    # Esperado e variância sob H0
    n = n1 + n0
    runs_esperado = (2 * n1 * n0) / n + 1
    runs_var = (2 * n1 * n0 * (2 * n1 * n0 - n)) / (n**2 * (n - 1))
    
    if runs_var <= 0:
        return {'numero': numero, 'erro': 'Variância inválida'}
    
    runs_std = np.sqrt(runs_var)
    
    # Z-score
    zscore = (n_runs - runs_esperado) / runs_std
    
    # P-value (bilateral)
    p_value = 2 * (1 - norm.cdf(abs(zscore)))
    
    return {
        'numero': numero,
        'n_aparicoes': n1,
        'n_ausencias': n0,
        'n_runs': n_runs,
        'n_runs_esperado': round(runs_esperado, 2),
        'zscore': round(zscore, 3),
        'p_value': round(p_value, 4),
        'aleatorio': bool(p_value >= 0.05)
    }


def teste_runs_todos_numeros(df: pd.DataFrame, config: GameConfig) -> dict:
    """
    Aplica teste de runs para todos os números do jogo.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    dict
        Resultado com 'resultados' (lista), 'numeros_nao_aleatorios',
        'percentual_aleatorios', 'resumo'.
    
    Examples
    --------
    >>> resultado = teste_runs_todos_numeros(df, MEGASENA)
    >>> resultado['percentual_aleatorios']
    96.7  # 96.7% dos números passaram no teste
    """
    resultados = []
    nao_aleatorios = []
    
    for numero in range(1, config.n_numbers + 1):
        res = teste_runs_numero(df, numero, config)
        resultados.append(res)
        
        if 'erro' not in res and not res['aleatorio']:
            nao_aleatorios.append(numero)
    
    # Filtra resultados válidos
    validos = [r for r in resultados if 'erro' not in r]
    aleatorios = [r for r in validos if r['aleatorio']]
    
    percentual = (len(aleatorios) / len(validos) * 100) if validos else 0
    
    return {
        'resultados': resultados,
        'numeros_nao_aleatorios': nao_aleatorios,
        'percentual_aleatorios': round(percentual, 1),
        'resumo': f"{len(aleatorios)}/{len(validos)} números passaram no teste de aleatoriedade"
    }


# ============================================
# 4. ÍNDICE DE DISPERSÃO (VMR)
# ============================================


def indice_dispersao(df: pd.DataFrame, config: GameConfig) -> dict:
    """
    Calcula o Índice de Dispersão (Variance-to-Mean Ratio - VMR).
    
    O VMR compara a variância com a média das frequências.
    - VMR ≈ 1: Distribuição Poisson (aleatório)
    - VMR > 1: Superdispersão (alguns números saem muito mais que outros)
    - VMR < 1: Subdispersão (frequências muito uniformes)
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    dict
        Resultado com 'vmr', 'variancia', 'media', 'interpretacao',
        'chi2_stat', 'p_value'.
    
    Notes
    -----
    O teste estatístico usa Chi² para verificar se VMR difere de 1.
    
    Examples
    --------
    >>> resultado = indice_dispersao(df, MEGASENA)
    >>> resultado
    {'vmr': 1.02, 'variancia': 45.3, 'media': 44.4,
     'interpretacao': 'Distribuição compatível com aleatoriedade',
     'chi2_stat': 61.2, 'p_value': 0.43}
    """
    if df.empty:
        return {'erro': 'DataFrame vazio'}
    
    from app.core.statistics import get_numeros_quentes_frios
    
    freq = get_numeros_quentes_frios(df, config)
    
    if freq.empty:
        return {'erro': 'Frequências vazias'}
    
    media = freq.mean()
    variancia = freq.var()
    
    if media == 0:
        return {'erro': 'Média zero'}
    
    vmr = variancia / media
    
    # Teste Chi² para VMR
    # Sob H0 (Poisson), (n-1) * VMR ~ Chi²(n-1)
    n = len(freq)
    chi2_stat = (n - 1) * vmr
    p_value = 1 - chi2.cdf(chi2_stat, n - 1) if vmr > 1 else chi2.cdf(chi2_stat, n - 1)
    
    # Interpretação
    if 0.9 <= vmr <= 1.1:
        interpretacao = "✅ Distribuição compatível com aleatoriedade (Poisson)"
    elif vmr > 1.1:
        if vmr > 1.5:
            interpretacao = "⚠️ Superdispersão significativa (alguns números muito frequentes)"
        else:
            interpretacao = "ℹ️ Leve superdispersão (variação acima do esperado)"
    else:
        if vmr < 0.5:
            interpretacao = "⚠️ Subdispersão significativa (frequências muito uniformes)"
        else:
            interpretacao = "ℹ️ Leve subdispersão (variação abaixo do esperado)"
    
    return {
        'vmr': round(vmr, 4),
        'variancia': round(variancia, 2),
        'media': round(media, 2),
        'interpretacao': interpretacao,
        'chi2_stat': round(chi2_stat, 2),
        'p_value': round(p_value, 4),
        'dispersao_normal': bool(0.9 <= vmr <= 1.1)
    }
