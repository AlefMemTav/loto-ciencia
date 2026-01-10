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
    WEIGHT_FREQUENCY,
    WEIGHT_GAP,
    EPSILON,
)

from app.core.statistics.distributions import (
    analise_poisson,
    calcular_chi_quadrado,
    analise_intervalo_confianca,
    calcular_coeficiente_variacao,
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
)

from app.core.statistics.similarity import (
    distancia_hamming,
    calcular_distancia_minima_historico,
    penalizar_por_similaridade,
    calcular_distribuicao_quadrantes,
    avaliar_quadrantes_estatistico,
    calcular_taxa_regressao,
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
    "WEIGHT_FREQUENCY",
    "WEIGHT_GAP",
    "EPSILON",
    # distributions
    "analise_poisson",
    "calcular_chi_quadrado",
    "analise_intervalo_confianca",
    "calcular_coeficiente_variacao",
    "CHI2_HIGH_CONFIDENCE",
    "CHI2_MEDIUM_CONFIDENCE",
    "CV_EXCELLENT",
    "CV_GOOD",
    "CV_ACCEPTABLE",
    # geometry
    "GeometricDistribution",
    "calcular_distribuicoes_geometricas",
    "avaliar_jogo_geometria_estatistica",
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
]
