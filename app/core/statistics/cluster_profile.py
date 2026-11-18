# app/core/statistics/cluster_profile.py
"""
Interpretação de clusters baseada em features dinâmicas.
"""

import numpy as np
from typing import Dict, List, Any
from app.core.lottery import GameConfig
from app.core.statistics.clustering import (
    extrair_features_jogo,
    extrair_features_jogos_batch,
)
from app.core.logger import logger


def assign_clusters_batch(
    candidates: np.ndarray | List[List[int]],
    config: GameConfig,
    clusters_cache: dict | None = None,
) -> np.ndarray:
    """
    Atribui cada jogo de um lote (M, k) a um arquétipo estrutural (cluster ID)
    de forma 100% vetorizada no espaço Z padronizado.
    """
    arr = np.asarray(candidates, dtype=int)
    if arr.ndim != 2 or len(arr) == 0:
        return np.empty(0, dtype=int)

    features = extrair_features_jogos_batch(arr, config)
    if (
        clusters_cache
        and isinstance(clusters_cache, dict)
        and "scaler_mean" in clusters_cache
        and "scaler_scale" in clusters_cache
        and "centroides_norm" in clusters_cache
        and getattr(config, "bet_size", config.k) == config.k
    ):
        scaler_mean = np.asarray(clusters_cache["scaler_mean"], dtype=float)
        scaler_scale = np.asarray(clusters_cache["scaler_scale"], dtype=float)
        scaler_scale = np.where(np.abs(scaler_scale) > 1e-9, scaler_scale, 1.0)
        c_dict = clusters_cache["centroides_norm"]
        if c_dict and len(scaler_mean) == features.shape[1]:
            cids = sorted(c_dict.keys(), key=lambda x: int(x))
            centers = np.asarray([c_dict[c] for c in cids], dtype=float)
            z = (features - scaler_mean[None, :]) / scaler_scale[None, :]
            dists = np.linalg.norm(z[:, None, :] - centers[None, :, :], axis=2)
            nearest = np.argmin(dists, axis=1)
            cid_arr = np.asarray([int(c) for c in cids], dtype=int)
            return cid_arr[nearest]

    # Fallback determinístico por quantis teóricos/empíricos de soma e gap_medio (6 arquétipos: 0..5)
    k = arr.shape[1]
    n_num = config.n_numbers
    mean_sum = k * (n_num + 1) / 2.0
    std_sum = max(
        1.0,
        float(np.sqrt(k * (n_num - k) * (n_num + 1) / 12.0)),
    )
    sum_z = (features[:, 0] - mean_sum) / std_sum
    sum_bin = np.where(sum_z < -0.45, 0, np.where(sum_z > 0.45, 2, 1))
    mean_gap = (n_num + 1) / float(k + 1)
    gap_bin = np.where(features[:, 4] < mean_gap, 0, 1)
    return (sum_bin * 2 + gap_bin).astype(int)


def interpretar_cluster_por_centroide(
    cluster_id: int, centroide: dict, config: GameConfig, todos_centroides: dict
) -> dict:
    """
    Interpreta cluster baseado em CARACTERÍSTICAS DO CENTRÓIDE,
    comparando-o com os outros clusters existentes.
    """
    # 1. Extrai features do centróide atual
    soma = centroide.get("soma", 0)
    gap_medio = centroide.get("gap_medio", 0)
    prop_pares = centroide.get("prop_pares", 0.5)
    amplitude = centroide.get("amplitude_relativa", 0.5)
    sequencias = centroide.get("sequencias", 0)

    # 2. Cria contexto RELATIVO (rankeia este cluster contra os outros)
    # Ex: Onde a soma deste cluster se encaixa? (Baixa, Média, Alta)
    todas_somas = sorted([c.get("soma", 0) for c in todos_centroides.values()])
    todos_gaps = sorted([c.get("gap_medio", 0) for c in todos_centroides.values()])

    # Encontra o índice (rank)
    try:
        soma_rank = todas_somas.index(soma)  # 0=Menor, 1=Médio, 2=Maior
        gap_rank = todos_gaps.index(gap_medio)
    except ValueError:
        # Fallback de segurança caso float precision falhe
        soma_rank = 1
        gap_rank = 1

    total_clusters = len(todos_centroides)

    # ============================================
    # INTERPRETAÇÃO BASEADA EM DADOS (FACTUAL)
    # ============================================
    caracteristicas = []

    # A. Análise de SOMA
    if soma_rank == 0:
        caracteristicas.append("soma baixa")
        tag_soma = "Baixo"
    elif soma_rank == total_clusters - 1:
        caracteristicas.append("soma alta")
        tag_soma = "Alto"
    else:
        caracteristicas.append("soma média")
        tag_soma = "Médio"

    # B. Análise de GAPS (Espaçamento)
    if gap_rank == 0:
        caracteristicas.append("números concentrados")
        tag_gap = "Concentrado"
    elif gap_rank == total_clusters - 1:
        caracteristicas.append("números espalhados")
        tag_gap = "Espalhado"
    else:
        caracteristicas.append("distribuição padrão")
        tag_gap = "Padrão"

    # C. Análise de PARES
    if prop_pares < 0.35:
        caracteristicas.append("foco em ímpares")
    elif prop_pares > 0.65:
        caracteristicas.append("foco em pares")
    else:
        caracteristicas.append("pares equilibrados")

    # D. Análise de SEQUÊNCIAS
    if sequencias >= 2.5:
        caracteristicas.append("presença de sequências")

    # ============================================
    # NOMEAÇÃO DINÂMICA (UX)
    # ============================================

    # Define ícone e nome baseados na combinação Soma + Gap
    if tag_soma == "Baixo" and tag_gap == "Concentrado":
        nome = "Compacto-Inicial"
        icone = "🔵"
        desc_ux = "Jogo focado nos números iniciais do volante."

    elif tag_soma == "Alto" and tag_gap == "Espalhado":
        nome = "Expansivo-Final"
        icone = "🔴"
        desc_ux = "Jogo agressivo que busca cobrir o final do volante."

    elif tag_soma == "Médio" and tag_gap == "Padrão":
        nome = "Equilibrado (Típico)"
        icone = "🟢"
        desc_ux = "O padrão mais comum nos sorteios históricos."

    elif tag_soma == "Alto" and tag_gap == "Concentrado":
        nome = "Compacto-Final"
        icone = "🟠"
        desc_ux = "Concentração de números altos."

    else:
        # Híbridos
        nome = f"Perfil Misto ({tag_soma}/{tag_gap})"
        icone = "⚪"
        desc_ux = "Combinação de características variadas."

    # ============================================
    # MONTAGEM DO RESULTADO
    # ============================================
    return {
        "nome": nome,
        "icone": icone,
        "descricao_curta": desc_ux,
        "caracteristicas": caracteristicas,
        "tags_tecnicas": {"soma": tag_soma, "gap": tag_gap},
        "metricas_centroide": {
            "soma": round(soma, 1),
            "gap": round(gap_medio, 1),
            "rank_soma": f"{soma_rank + 1}/{total_clusters}",
        },
    }


def analisar_perfil_cluster(
    numeros: List[int],
    df_historico: Any,
    config: GameConfig,
    n_amostras_historico: int = 300,
    clusters_cache: dict = None,
) -> Dict:
    """
    Analisa o perfil do jogo comparando-o com os clusters históricos cacheados
    no espaço Z padronizado (9 features estruturais) e avalia outlier pelo P95 empírico.
    """
    if not clusters_cache:
        return {"disponivel": False, "erro": "Cache de IA não inicializado"}

    try:
        features_jogo = extrair_features_jogo(numeros, config)
        centroides = clusters_cache["centroides"]
        labels_historicos = clusters_cache["labels"]

        menor_distancia = float("inf")
        cluster_vencedor = -1
        usou_espaco_z = False

        if (
            "scaler_mean" in clusters_cache
            and "scaler_scale" in clusters_cache
            and "centroides_norm" in clusters_cache
        ):
            scaler_mean = np.asarray(clusters_cache["scaler_mean"], dtype=float)
            scaler_scale = np.asarray(clusters_cache["scaler_scale"], dtype=float)
            scaler_scale = np.where(np.abs(scaler_scale) > 1e-9, scaler_scale, 1.0)
            centroides_norm = clusters_cache["centroides_norm"]

            if len(scaler_mean) == len(features_jogo) and centroides_norm:
                usou_espaco_z = True
                z_jogo = (features_jogo - scaler_mean) / scaler_scale
                for cid, centro_norm in centroides_norm.items():
                    cid_key = cid if cid in centroides else int(cid)
                    c_vec = np.asarray(centro_norm, dtype=float)
                    distancia = float(np.linalg.norm(z_jogo - c_vec))
                    if distancia < menor_distancia:
                        menor_distancia = distancia
                        cluster_vencedor = cid_key

        if not usou_espaco_z:
            for cid, centroide_feat in centroides.items():
                dist_soma = (features_jogo[0] - centroide_feat["soma"]) ** 2
                dist_gap = (features_jogo[4] - centroide_feat["gap_medio"]) ** 2
                distancia = float(np.sqrt(dist_soma + (dist_gap * 10)))
                if distancia < menor_distancia:
                    menor_distancia = distancia
                    cluster_vencedor = cid

        centroide_vencedor = centroides[cluster_vencedor]
        interpretacao = interpretar_cluster_por_centroide(
            cluster_vencedor, centroide_vencedor, config, centroides
        )

        from collections import Counter

        contagem = Counter(labels_historicos)
        total = max(1, len(labels_historicos))
        pct_cluster = (contagem[cluster_vencedor] / total) * 100

        if usou_espaco_z:
            limiar_outlier = float(clusters_cache.get("dist_p95", 3.8))
            quantis = clusters_cache.get("distancias_quantis") or []
            if quantis:
                pos = int(np.searchsorted(quantis, menor_distancia, side="right"))
                tipicidade_pct = round(max(0.0, 100.0 * (1.0 - pos / max(1, len(quantis)))), 1)
            else:
                tipicidade_pct = round(
                    max(0.0, min(100.0, 100.0 * (1.0 - menor_distancia / max(1e-6, limiar_outlier * 1.4)))),
                    1,
                )
        else:
            limiar_outlier = 50.0
            tipicidade_pct = round(max(0.0, min(100.0, 100.0 - menor_distancia)), 1)

        is_outlier = bool(menor_distancia > limiar_outlier)

        return {
            "disponivel": True,
            "cluster_id": int(cluster_vencedor) if isinstance(cluster_vencedor, (int, np.integer)) else cluster_vencedor,
            "nome_cluster": interpretacao["nome"],
            "icone": interpretacao["icone"],
            "descricao": interpretacao["descricao_curta"],
            "caracteristicas": interpretacao["caracteristicas"],
            "percentual_historico": round(pct_cluster, 1),
            "tipicidade_percentil": tipicidade_pct,
            "espaco_padronizado_z": usou_espaco_z,
            "limiar_outlier_p95": round(limiar_outlier, 4),
            "features_jogo": {
                "soma": int(features_jogo[0]),
                "gap": round(float(features_jogo[4]), 1),
                "prop_pares": round(float(features_jogo[2]), 3),
                "prop_baixos": round(float(features_jogo[3]), 3),
                "sequencias": int(features_jogo[6]),
                "amplitude_relativa": round(float(features_jogo[8]), 3),
            },
            "metricas_cluster": interpretacao["metricas_centroide"],
            "is_outlier": is_outlier,
            "debug_distancia": round(float(menor_distancia), 4),
        }

    except Exception as e:
        logger.error(f"Erro na análise de perfil: {e}")
        return {"disponivel": False, "erro": str(e)}
