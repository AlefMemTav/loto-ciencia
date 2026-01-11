# app/core/statistics/temporal.py
"""
Análises temporais de frequências e tendências.

Este módulo contém funções para análise de autocorrelação temporal,
detecção de ciclos e análise de tendências nas frequências de números
ao longo do tempo.
"""

import numpy as np
import pandas as pd
from typing import Optional, List
from scipy import stats
from app.core.lottery import GameConfig


def calcular_autocorrelacao_frequencias(
    df: pd.DataFrame,
    config: GameConfig,
    max_lag: int = 50,
    janela: int = 10
) -> dict:
    """
    Calcula autocorrelação das frequências de números ao longo do tempo.
    
    Divide o histórico em janelas e calcula a frequência de cada número
    em cada janela, depois mede a autocorrelação dessa série.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    max_lag : int, default=50
        Número máximo de lags para calcular autocorrelação.
    janela : int, default=10
        Tamanho da janela (em sorteios) para agregação.
    
    Returns
    -------
    dict
        Autocorrelações e análise de ciclos:
        - 'autocorrelacoes': array de autocorrelações por lag
        - 'lags_significativos': lags com autocorrelação significativa
        - 'ciclo_detectado': se foi detectado padrão cíclico
        - 'periodo_ciclo': período estimado do ciclo (se houver)
    """
    if df.empty or len(df) < janela * 3:
        return None
    
    n_janelas = len(df) // janela
    
    # Série temporal de frequências por janela
    frequencias_por_janela = []
    
    for i in range(n_janelas):
        inicio = i * janela
        fim = inicio + janela
        df_janela = df.iloc[inicio:fim]
        
        todos_numeros = df_janela[config.draw_cols].values.flatten()
        freq_total = len(todos_numeros)
        frequencias_por_janela.append(freq_total)
    
    serie = np.array(frequencias_por_janela)
    
    # Normaliza a série
    serie_norm = (serie - serie.mean()) / (serie.std() + 1e-9)
    
    # Calcula autocorrelações
    n = len(serie_norm)
    max_lag = min(max_lag, n // 2)
    autocorrs = []
    
    for lag in range(1, max_lag + 1):
        if lag >= n:
            break
        autocorr = np.corrcoef(serie_norm[:-lag], serie_norm[lag:])[0, 1]
        autocorrs.append(autocorr)
    
    autocorrs = np.array(autocorrs)
    
    # Limite de significância (aproximação)
    limite_sig = 1.96 / np.sqrt(n)
    
    # Encontra lags significativos
    lags_significativos = [i+1 for i, ac in enumerate(autocorrs) if abs(ac) > limite_sig]
    
    # Detecta ciclo (pico na autocorrelação)
    if len(autocorrs) > 0:
        pico_idx = np.argmax(autocorrs)
        ciclo_detectado = autocorrs[pico_idx] > limite_sig
        periodo_ciclo = pico_idx + 1 if ciclo_detectado else None
    else:
        ciclo_detectado = False
        periodo_ciclo = None
    
    return {
        'autocorrelacoes': autocorrs.tolist(),
        'lags': list(range(1, len(autocorrs) + 1)),
        'limite_significancia': round(limite_sig, 4),
        'lags_significativos': lags_significativos,
        'ciclo_detectado': ciclo_detectado,
        'periodo_ciclo': periodo_ciclo,
        'n_janelas': n_janelas,
        'tamanho_janela': janela,
    }


def detectar_tendencia_frequencia(
    df: pd.DataFrame,
    config: GameConfig,
    numero: int,
    janela: int = 50
) -> dict:
    """
    Detecta tendência na frequência de um número específico.
    
    Usa regressão linear para identificar se a frequência está
    aumentando, diminuindo ou estável ao longo do tempo.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico.
    config : GameConfig
        Configuração do jogo.
    numero : int
        Número a analisar.
    janela : int, default=50
        Tamanho da janela móvel.
    
    Returns
    -------
    dict
        Análise de tendência com coeficiente angular e p-value.
    """
    if df.empty or len(df) < janela * 2:
        return None
    
    # Calcula frequência móvel
    n_janelas = len(df) // janela
    frequencias = []
    
    for i in range(n_janelas):
        inicio = i * janela
        fim = inicio + janela
        df_janela = df.iloc[inicio:fim]
        
        count = sum(
            1 for _, row in df_janela.iterrows()
            if numero in row[config.draw_cols].values
        )
        frequencias.append(count / janela)
    
    if len(frequencias) < 3:
        return None
    
    # Regressão linear
    x = np.arange(len(frequencias))
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, frequencias)
    
    # Interpretação
    if p_value < 0.05:
        if slope > 0:
            tendencia = "📈 Frequência aumentando"
        else:
            tendencia = "📉 Frequência diminuindo"
    else:
        tendencia = "➡️ Frequência estável"
    
    return {
        'numero': numero,
        'slope': round(slope, 6),
        'r_squared': round(r_value ** 2, 4),
        'p_value': round(p_value, 4),
        'tendencia': tendencia,
        'frequencias_janela': frequencias,
    }
