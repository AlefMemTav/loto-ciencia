# app/core/statistics/clustering.py
"""
Clusterização estatística de jogos de loteria.

Este módulo contém funções para agrupamento de padrões de jogos
usando algoritmos de machine learning (K-Means e DBSCAN).
"""

import numpy as np
import pandas as pd
from typing import Optional, List, Tuple
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from app.core.lottery import GameConfig


def extrair_features_jogo(numeros: List[int], config: GameConfig) -> np.ndarray:
    """
    Extrai features numéricas de um jogo para clusterização.
    
    Parameters
    ----------
    numeros : List[int]
        Lista de números do jogo.
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    np.ndarray
        Vetor de features do jogo.
    """
    numeros = sorted(numeros)
    n = len(numeros)
    
    # Features básicas
    soma = sum(numeros)
    media = soma / n
    
    # Pares e ímpares
    pares = sum(1 for x in numeros if x % 2 == 0)
    impares = n - pares
    
    # Distribuição espacial
    metade = config.n_numbers // 2
    baixos = sum(1 for x in numeros if x <= metade)
    altos = n - baixos
    
    # Gaps entre números consecutivos
    gaps = [numeros[i+1] - numeros[i] for i in range(n-1)]
    gap_medio = np.mean(gaps) if gaps else 0
    gap_std = np.std(gaps) if gaps else 0
    
    # Sequências consecutivas
    sequencias = sum(1 for g in gaps if g == 1)
    
    # Finais (último dígito)
    finais = [x % 10 for x in numeros]
    finais_unicos = len(set(finais))
    
    # Dispersão
    amplitude = numeros[-1] - numeros[0]
    
    return np.array([
        soma,
        media,
        pares / n,  # proporção de pares
        baixos / n,  # proporção de baixos
        gap_medio,
        gap_std,
        sequencias,
        finais_unicos / n,
        amplitude / config.n_numbers,
    ])


def clusterizar_jogos_kmeans(
    jogos: List[List[int]],
    config: GameConfig,
    n_clusters: int = 5,
    random_state: int = 42
) -> dict:
    """
    Agrupa jogos similares usando K-Means.
    
    Parameters
    ----------
    jogos : List[List[int]]
        Lista de jogos (cada jogo é uma lista de números).
    config : GameConfig
        Configuração do jogo.
    n_clusters : int, default=5
        Número de clusters desejados.
    random_state : int, default=42
        Seed para reprodutibilidade.
    
    Returns
    -------
    dict
        Resultado da clusterização:
        - 'labels': cluster de cada jogo
        - 'centroides': características médias de cada cluster
        - 'silhouette': score de silhouette
        - 'distribuicao': contagem de jogos por cluster
    """
    if len(jogos) < n_clusters:
        return {'erro': 'Número de jogos insuficiente para clusterização'}
    
    # Extrai features
    features = np.array([extrair_features_jogo(j, config) for j in jogos])
    
    # Normaliza
    scaler = StandardScaler()
    features_norm = scaler.fit_transform(features)
    
    # K-Means
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    labels = kmeans.fit_predict(features_norm)
    
    # Silhouette score
    if len(set(labels)) > 1:
        silhouette = silhouette_score(features_norm, labels)
    else:
        silhouette = 0.0
    
    # Distribuição por cluster
    distribuicao = {i: int(np.sum(labels == i)) for i in range(n_clusters)}
    
    # Características médias por cluster (desnormalizadas)
    centroides = {}
    feature_names = [
        'soma', 'media', 'prop_pares', 'prop_baixos', 
        'gap_medio', 'gap_std', 'sequencias', 
        'prop_finais_unicos', 'amplitude_relativa'
    ]
    
    for i in range(n_clusters):
        mask = labels == i
        if np.sum(mask) > 0:
            centro = features[mask].mean(axis=0)
            centroides[i] = {name: round(float(val), 3) for name, val in zip(feature_names, centro)}
    
    return {
        'labels': labels.tolist(),
        'n_clusters': n_clusters,
        'silhouette_score': round(silhouette, 4),
        'distribuicao': distribuicao,
        'centroides': centroides,
        'feature_names': feature_names,
    }


def clusterizar_jogos_dbscan(
    jogos: List[List[int]],
    config: GameConfig,
    eps: float = 0.5,
    min_samples: int = 5
) -> dict:
    """
    Agrupa jogos usando DBSCAN (detecta outliers automaticamente).
    
    DBSCAN não requer número pré-definido de clusters e identifica
    jogos atípicos como ruído (outliers).
    
    Parameters
    ----------
    jogos : List[List[int]]
        Lista de jogos.
    config : GameConfig
        Configuração do jogo.
    eps : float, default=0.5
        Distância máxima entre pontos do mesmo cluster.
    min_samples : int, default=5
        Número mínimo de pontos para formar um cluster.
    
    Returns
    -------
    dict
        Resultado com clusters e outliers identificados.
    """
    if len(jogos) < min_samples:
        return {'erro': 'Número de jogos insuficiente'}
    
    # Extrai e normaliza features
    features = np.array([extrair_features_jogo(j, config) for j in jogos])
    scaler = StandardScaler()
    features_norm = scaler.fit_transform(features)
    
    # DBSCAN
    dbscan = DBSCAN(eps=eps, min_samples=min_samples)
    labels = dbscan.fit_predict(features_norm)
    
    # Identifica outliers (label = -1)
    outliers = [i for i, label in enumerate(labels) if label == -1]
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    
    # Distribuição
    distribuicao = {}
    for label in set(labels):
        if label == -1:
            distribuicao['outliers'] = int(np.sum(labels == -1))
        else:
            distribuicao[f'cluster_{label}'] = int(np.sum(labels == label))
    
    return {
        'labels': labels.tolist(),
        'n_clusters': n_clusters,
        'n_outliers': len(outliers),
        'indices_outliers': outliers,
        'jogos_outliers': [jogos[i] for i in outliers],
        'distribuicao': distribuicao,
        'eps': eps,
        'min_samples': min_samples,
    }


def encontrar_numero_otimo_clusters(
    jogos: List[List[int]],
    config: GameConfig,
    k_min: int = 2,
    k_max: int = 10
) -> dict:
    """
    Encontra o número ótimo de clusters usando o método Elbow e Silhouette.
    
    Parameters
    ----------
    jogos : List[List[int]]
        Lista de jogos.
    config : GameConfig
        Configuração do jogo.
    k_min : int, default=2
        Número mínimo de clusters a testar.
    k_max : int, default=10
        Número máximo de clusters a testar.
    
    Returns
    -------
    dict
        Análise com inércias, silhouettes e k ótimo sugerido.
    """
    features = np.array([extrair_features_jogo(j, config) for j in jogos])
    scaler = StandardScaler()
    features_norm = scaler.fit_transform(features)
    
    k_max = min(k_max, len(jogos) - 1)
    
    inercias = []
    silhouettes = []
    
    for k in range(k_min, k_max + 1):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(features_norm)
        
        inercias.append(float(kmeans.inertia_))
        
        if len(set(labels)) > 1:
            sil = silhouette_score(features_norm, labels)
        else:
            sil = 0.0
        silhouettes.append(float(sil))
    
    # K ótimo pelo silhouette
    k_otimo = k_min + np.argmax(silhouettes)
    
    return {
        'k_range': list(range(k_min, k_max + 1)),
        'inercias': inercias,
        'silhouettes': silhouettes,
        'k_otimo_silhouette': int(k_otimo),
        'melhor_silhouette': round(max(silhouettes), 4),
    }
