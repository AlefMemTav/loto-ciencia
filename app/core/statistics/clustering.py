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


def extrair_features_jogos_batch(
    jogos: List[List[int]] | np.ndarray,
    config: GameConfig,
) -> np.ndarray:
    """
    Extrai a matriz (M, 9) de features numéricas de um lote de jogos de forma vetorizada.
    """
    if len(jogos) == 0:
        return np.empty((0, 9), dtype=float)

    try:
        arr = np.asarray(jogos, dtype=int)
    except ValueError:
        return np.array([extrair_features_jogo(list(j), config) for j in jogos], dtype=float)

    if arr.ndim != 2 or arr.shape[1] == 0:
        return np.array([extrair_features_jogo(list(j), config) for j in jogos], dtype=float)

    arr = np.sort(arr, axis=1)
    m, n = arr.shape
    soma = arr.sum(axis=1, dtype=float)
    media = soma / n
    prop_pares = (arr % 2 == 0).sum(axis=1, dtype=float) / n
    metade = config.n_numbers // 2
    prop_baixos = (arr <= metade).sum(axis=1, dtype=float) / n

    if n > 1:
        diffs = np.diff(arr, axis=1)
        gap_medio = diffs.mean(axis=1)
        gap_std = diffs.std(axis=1)
        sequencias = (diffs == 1).sum(axis=1, dtype=float)
    else:
        gap_medio = np.zeros(m, dtype=float)
        gap_std = np.zeros(m, dtype=float)
        sequencias = np.zeros(m, dtype=float)

    finais = arr % 10
    digits = np.arange(10, dtype=int)[None, None, :]
    finais_unicos = np.sum(np.any(finais[:, :, None] == digits, axis=1), axis=1, dtype=float)
    prop_finais_unicos = finais_unicos / n
    amplitude_rel = (arr[:, -1] - arr[:, 0]).astype(float) / max(1, config.n_numbers)

    return np.column_stack(
        [
            soma,
            media,
            prop_pares,
            prop_baixos,
            gap_medio,
            gap_std,
            sequencias,
            prop_finais_unicos,
            amplitude_rel,
        ]
    )


# Índices das 7 features linearmente independentes (exclui col 1 = media = soma/n
# e col 4 = gap_medio = amplitude/(n-1), que tornavam a matriz de covariância singular).
INDEPENDENT_FEATURE_INDICES: Tuple[int, ...] = (0, 2, 3, 5, 6, 7, 8)
INDEPENDENT_FEATURE_NAMES: List[str] = [
    "soma",
    "prop_pares",
    "prop_baixos",
    "gap_std",
    "sequencias",
    "prop_finais_unicos",
    "amplitude_relativa",
]


def calcular_referencia_mahalanobis(features_ind: np.ndarray) -> dict:
    """Calcula média, inversa regularizada da covariância e quantis de distância de Mahalanobis."""
    arr = np.asarray(features_ind, dtype=float)
    mu = arr.mean(axis=0)
    cov = np.cov(arr, rowvar=False)
    if cov.ndim == 0:
        cov = np.array([[float(cov)]], dtype=float)
    # Regularização mínima proporcional à variância média para estabilidade numérica
    reg = max(1e-6, 1e-5 * float(np.trace(cov)) / max(1, cov.shape[0]))
    cov_reg = cov + np.eye(cov.shape[0]) * reg
    cov_inv = np.linalg.pinv(cov_reg)
    diff = arr - mu
    dm = np.sqrt(np.maximum(0.0, np.einsum("ij,jk,ik->i", diff, cov_inv, diff)))
    return {
        "mahal_mu": [round(float(x), 6) for x in mu],
        "mahal_cov_inv": [[round(float(v), 8) for v in row] for row in cov_inv],
        "mahal_media": round(float(np.mean(dm)), 4) if len(dm) else 0.0,
        "mahal_p90": round(float(np.percentile(dm, 90)), 4) if len(dm) else 3.5,
        "mahal_p95": round(float(np.percentile(dm, 95)), 4) if len(dm) else 4.0,
        "mahal_quantis": (
            [round(float(q), 6) for q in np.quantile(dm, np.linspace(0.0, 1.0, 21))]
            if len(dm)
            else []
        ),
    }


def clusterizar_jogos_kmeans(
    jogos: List[List[int]],
    config: GameConfig,
    n_clusters: int = 5,
    random_state: int = 42
) -> dict:
    """
    Agrupa jogos similares usando K-Means sobre as 7 features linearmente independentes
    (eliminando a colinearidade exata de `media = soma/n` e `gap_medio = amplitude/(n-1)`)
    e calcula a referência de distância de Mahalanobis multivariada para diagnóstico descritivo.
    """
    if len(jogos) < n_clusters:
        return {'erro': 'Número de jogos insuficiente para clusterização'}

    # Extrai as 9 features completas (para relatório legível) e seleciona as 7 independentes
    features_full = extrair_features_jogos_batch(jogos, config)
    idx_ind = list(INDEPENDENT_FEATURE_INDICES)
    features_ind = features_full[:, idx_ind]

    # Normaliza apenas as 7 features independentes (elimina peso duplo de soma/amplitude)
    scaler = StandardScaler()
    features_norm = scaler.fit_transform(features_ind)
    safe_scale = np.where(scaler.scale_ > 1e-9, scaler.scale_, 1.0)

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

    # Características médias por cluster (9 nomes legíveis) e centróides no espaço Z (7 independentes)
    centroides = {}
    centroides_norm = {}
    feature_names = [
        'soma', 'media', 'prop_pares', 'prop_baixos',
        'gap_medio', 'gap_std', 'sequencias',
        'prop_finais_unicos', 'amplitude_relativa'
    ]

    for i in range(n_clusters):
        mask = labels == i
        if np.sum(mask) > 0:
            centro_full = features_full[mask].mean(axis=0)
            centro_norm = features_norm[mask].mean(axis=0)
            centroides[i] = {name: round(float(val), 3) for name, val in zip(feature_names, centro_full)}
            centroides_norm[i] = [round(float(val), 6) for val in centro_norm]
        else:
            centro_norm = kmeans.cluster_centers_[i]
            centro_ind = centro_norm * safe_scale + scaler.mean_
            # Reconstrói as 2 features derivadas para compatibilidade do relatório
            k_len = max(1, len(jogos[0]))
            soma_c = float(centro_ind[0])
            amp_rel_c = float(centro_ind[6])
            centro_full = np.array([
                soma_c,
                soma_c / k_len,
                float(centro_ind[1]),
                float(centro_ind[2]),
                (amp_rel_c * config.n_numbers) / max(1, k_len - 1),
                float(centro_ind[3]),
                float(centro_ind[4]),
                float(centro_ind[5]),
                amp_rel_c,
            ])
            centroides[i] = {name: round(float(val), 3) for name, val in zip(feature_names, centro_full)}
            centroides_norm[i] = [round(float(val), 6) for val in centro_norm]

    assigned_centers = np.array(
        [centroides_norm[int(lbl)] for lbl in labels],
        dtype=float,
    )
    dists_norm = np.linalg.norm(features_norm - assigned_centers, axis=1)
    dist_media = float(np.mean(dists_norm)) if len(dists_norm) else 0.0
    dist_std = float(np.std(dists_norm)) if len(dists_norm) else 0.0
    dist_p90 = float(np.percentile(dists_norm, 90)) if len(dists_norm) else 3.5
    dist_p95 = float(np.percentile(dists_norm, 95)) if len(dists_norm) else 4.0
    dist_quantis = (
        [round(float(q), 6) for q in np.quantile(dists_norm, np.linspace(0.0, 1.0, 21))]
        if len(dists_norm)
        else []
    )

    mahal_ref = calcular_referencia_mahalanobis(features_ind)

    return {
        'labels': labels.tolist(),
        'n_clusters': n_clusters,
        'silhouette_score': round(silhouette, 4),
        'distribuicao': distribuicao,
        'centroides': centroides,
        'centroides_norm': centroides_norm,
        'scaler_mean': [round(float(x), 6) for x in scaler.mean_],
        'scaler_scale': [round(float(x), 6) for x in safe_scale],
        'feature_indices': idx_ind,
        'independent_feature_names': list(INDEPENDENT_FEATURE_NAMES),
        'dist_media': round(dist_media, 4),
        'dist_std': round(dist_std, 4),
        'dist_p90': round(dist_p90, 4),
        'dist_p95': round(dist_p95, 4),
        'distancias_quantis': dist_quantis,
        'feature_names': feature_names,
        'k_referencia': int(len(jogos[0])) if jogos else int(config.k),
        **mahal_ref,
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
    
    # Extrai e normaliza apenas as 7 features independentes
    features = extrair_features_jogos_batch(jogos, config)[
        :, list(INDEPENDENT_FEATURE_INDICES)
    ]
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
    Encontra o número ótimo de clusters usando o método Elbow e Silhouette
    sobre as 7 features linearmente independentes.
    """
    features = extrair_features_jogos_batch(jogos, config)[
        :, list(INDEPENDENT_FEATURE_INDICES)
    ]
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
