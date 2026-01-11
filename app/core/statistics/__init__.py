"""
Módulo de estatísticas para análise de jogos de loteria.

Este pacote contém funções para análise estatística de sorteios,
incluindo frequências, atrasos, testes de aleatoriedade e análises geométricas.
"""

from app.core.statistics.basic import (
    compute_zscore,
    get_numeros_quentes_frios,
    get_historico_jogos,
    verificar_historico,
    get_reis_da_sequencia,
    calcular_atrasos,
    get_tabela_inteligencia,
    calcular_min_gap_e_span,
    calcular_entropia_faixas,
    WEIGHT_FREQUENCY,
    WEIGHT_GAP,
    EPSILON,
)

from app.core.statistics.distributions import (
    analise_poisson,
    calcular_chi_quadrado,
    analise_intervalo_confianca,
    calcular_coeficiente_variacao,
    testar_distribuicao_gaps_bilhete,
    calcular_order_statistics,
    detectar_motifs_gaps,
    CHI2_HIGH_CONFIDENCE,
    CHI2_MEDIUM_CONFIDENCE,
    CV_EXCELLENT,
    CV_GOOD,
    CV_ACCEPTABLE,
)

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
    QUADRANT_CONCENTRATION_THRESHOLD,
    QUADRANT_PVALUE_THRESHOLD,
)

from app.core.statistics.geometry import (
    GeometricDistribution,
    calcular_distribuicoes_geometricas,
    avaliar_jogo_geometria_estatistica,
    calcular_simetria_reflexao,
)

from app.core.statistics.similarity import (
    distancia_hamming,
    calcular_distancia_minima_historico,
    penalizar_por_similaridade,
    calcular_distribuicao_quadrantes,
    avaliar_quadrantes_estatistico,
    calcular_taxa_regressao,
    analisar_gaps_geometricos,
    analisar_gaps_todos_numeros,
)

from app.core.statistics.advanced import (
    matriz_coocorrencia_numeros,
    get_pares_mais_frequentes,
    get_pares_que_se_repelem,
    calcular_matriz_transicao,
    analisar_transicoes_anomalas,
    teste_runs_numero,
    teste_runs_todos_numeros,
    indice_dispersao,
)

from app.core.statistics.monte_carlo import (
    bootstrap_ic_soma,
    monte_carlo_probabilidade_acerto,
)

from app.core.statistics.temporal import (
    calcular_autocorrelacao_frequencias,
    detectar_tendencia_frequencia,
)

from app.core.statistics.clustering import (
    extrair_features_jogo,
    clusterizar_jogos_kmeans,
    clusterizar_jogos_dbscan,
    encontrar_numero_otimo_clusters,
)

__all__ = [
    # basic
    "compute_zscore",
    "get_numeros_quentes_frios",
    "get_historico_jogos",
    "verificar_historico",
    "get_reis_da_sequencia",
    "calcular_atrasos",
    "get_tabela_inteligencia",
    "calcular_min_gap_e_span",
    "calcular_entropia_faixas",
    "WEIGHT_FREQUENCY",
    "WEIGHT_GAP",
    "EPSILON",
    # distributions
    "analise_poisson",
    "calcular_chi_quadrado",
    "analise_intervalo_confianca",
    "calcular_coeficiente_variacao",
    "testar_distribuicao_gaps_bilhete",
    "calcular_order_statistics",
    "detectar_motifs_gaps",
    "CHI2_HIGH_CONFIDENCE",
    "CHI2_MEDIUM_CONFIDENCE",
    "CV_EXCELLENT",
    "CV_GOOD",
    "CV_ACCEPTABLE",
    # geometry
    "GeometricDistribution",
    "calcular_distribuicoes_geometricas",
    "avaliar_jogo_geometria_estatistica",
    "calcular_simetria_reflexao",
    "ZSCORE_EXTREME",
    "ZSCORE_VERY_RARE",
    "ZSCORE_RARE",
    "PENALTY_EXTREME",
    "PENALTY_VERY_RARE",
    "PENALTY_RARE",
    "PENALTY_NORMAL",
    "PENALTY_SCALE_FACTOR",
    "SCORE_CONVERSION_FACTOR",
    # similarity
    "distancia_hamming",
    "calcular_distancia_minima_historico",
    "penalizar_por_similaridade",
    "calcular_distribuicao_quadrantes",
    "avaliar_quadrantes_estatistico",
    "calcular_taxa_regressao",
    "QUADRANT_CONCENTRATION_THRESHOLD",
    "QUADRANT_PVALUE_THRESHOLD",
    # advanced
    "matriz_coocorrencia_numeros",
    "get_pares_mais_frequentes",
    "get_pares_que_se_repelem",
    "calcular_matriz_transicao",
    "analisar_transicoes_anomalas",
    "teste_runs_numero",
    "teste_runs_todos_numeros",
    "indice_dispersao",
    # monte_carlo
    "bootstrap_ic_soma",
    "monte_carlo_probabilidade_acerto",
    # gaps
    "analisar_gaps_geometricos",
    "analisar_gaps_todos_numeros",
    # temporal
    "calcular_autocorrelacao_frequencias",
    "detectar_tendencia_frequencia",
    # clustering
    "extrair_features_jogo",
    "clusterizar_jogos_kmeans",
    "clusterizar_jogos_dbscan",
    "encontrar_numero_otimo_clusters",
]
