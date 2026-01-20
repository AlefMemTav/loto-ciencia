# app/core/statistics/cluster_profile.py
"""
Interpretação de clusters baseada em features dinâmicas.
"""

import numpy as np
from typing import Dict, List, Any
from app.core.lottery import GameConfig
from app.core.statistics.clustering import extrair_features_jogo
from app.core.logger import logger


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
    Analisa o perfil do jogo comparando-o com os clusters históricos cacheados.
    Não re-treina o modelo (para performance), apenas classifica o novo ponto.
    """
    if not clusters_cache:
        # Se não tiver cache, falha graciosamente ou implementa fallback
        return {"disponivel": False, "erro": "Cache de IA não inicializado"}

    try:
        # 1. Extrai features do jogo do usuário
        features_jogo = extrair_features_jogo(numeros, config)

        # features_jogo é um array numpy [soma, media, prop_pares...]
        # Precisamos comparar com os centróides do cache

        centroides = clusters_cache["centroides"]  # Dict {0: {features}, 1: {...}}
        labels_historicos = clusters_cache["labels"]

        # 2. Encontra o Cluster Mais Próximo (Nearest Neighbor)
        # Calcula distância Euclidiana para cada centróide
        menor_distancia = float("inf")
        cluster_vencedor = -1

        # Mapeamento de nomes de features para índices do array (conforme extrair_features_jogo)
        # 0:soma, 1:media, 2:prop_pares, 3:prop_baixos, 4:gap_medio, etc...
        # Simplificação: Vamos usar as features principais que temos no centróide

        for cid, centroide_feat in centroides.items():
            # Reconstrói vetor do centróide (aproximado) para cálculo de distância
            # Nota: O ideal seria o objeto KMeans salvo, mas vamos usar a lógica manual
            # para não depender do scikit-learn pesado na inferência

            # Compara principalmente Soma e Gap (os mais fortes)
            dist_soma = (features_jogo[0] - centroide_feat["soma"]) ** 2
            dist_gap = (features_jogo[4] - centroide_feat["gap_medio"]) ** 2

            # Distância simplificada ponderada
            distancia = np.sqrt(dist_soma + (dist_gap * 10))

            if distancia < menor_distancia:
                menor_distancia = distancia
                cluster_vencedor = cid

        # 3. Interpreta o Cluster Vencedor
        centroide_vencedor = centroides[cluster_vencedor]

        interpretacao = interpretar_cluster_por_centroide(
            cluster_vencedor, centroide_vencedor, config, centroides
        )

        # 4. Estatísticas de População
        from collections import Counter

        contagem = Counter(labels_historicos)
        total = len(labels_historicos)
        pct_cluster = (contagem[cluster_vencedor] / total) * 100

        # 5. Detecção de Outlier (Distância muito grande do centróide)
        # Limite empírico: se a distância for muito maior que a média do cluster
        is_outlier = menor_distancia > 50.0  # Valor arbitrário, ajustável

        return {
            "disponivel": True,
            "nome_cluster": interpretacao["nome"],
            "icone": interpretacao["icone"],
            "descricao": interpretacao["descricao_curta"],
            "caracteristicas": interpretacao["caracteristicas"],
            "percentual_historico": round(pct_cluster, 1),
            "features_jogo": {
                "soma": int(features_jogo[0]),
                "gap": round(features_jogo[4], 1),
            },
            "metricas_cluster": interpretacao["metricas_centroide"],
            "is_outlier": is_outlier,
            "debug_distancia": round(menor_distancia, 2),
        }

    except Exception as e:
        logger.error(f"Erro na análise de perfil: {e}")
        return {"disponivel": False, "erro": str(e)}
