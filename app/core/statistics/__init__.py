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
    detectar_multiplos_de_d,
    calcular_indice_compressibilidade,
    WEIGHT_FREQUENCY,
    WEIGHT_GAP,
    EPSILON,
    PRIMES_ANALYSIS_MAX_N,
    PENALTY_MULTIPLOS_10_ALL,
    PENALTY_MULTIPLOS_3_5_ALL,
    PENALTY_MULTIPLOS_2_ALL,
    PENALTY_MULTIPLOS_HIGH,
    PENALTY_MULTIPLOS_MEDIUM,
    FRACTION_ALL,
    FRACTION_HIGH,
    FRACTION_MEDIUM,
    FRACTION_EXPECTED_MAX,
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
    calibrar_pesos_dinamicos,
)

from app.core.statistics.monte_carlo import (
    bootstrap_ic_soma,
    monte_carlo_probabilidade_acerto,
)

from app.core.statistics.null_model import (
    NullModel,
    get_null_model,
    build_null_model,
    NULL_MODEL_VERSION,
)

from app.core.statistics.feature_percentiles import (
    batch_feature_percentiles,
    summarize_feature_percentiles,
)
from app.core.statistics.score_calibration import (
    get_score_calibration_model,
    score_calibration_diagnostics,
    score_structural_batch,
    summarize_score_calibration,
)
from app.core.statistics.prize_model import (
    diagnostics_to_dict,
    financial_diagnostics,
    parse_prize_table,
    resolve_prize_table,
)

from app.core.statistics.temporal import (
    calcular_ciclo_atual,
    analise_temporal_somas,
    analise_temporal_repetidos,
    calcular_autocorrelacao_frequencias,
    detectar_tendencia_frequencia,
)

from app.core.statistics.clustering import (
    extrair_features_jogo,
    clusterizar_jogos_kmeans,
    clusterizar_jogos_dbscan,
    encontrar_numero_otimo_clusters,
)

# Bootstrap IC
from app.core.statistics.bootstrap_integration import (
    avaliar_soma_com_bootstrap,
    calcular_bootstrap_ic_com_cache,
)

# Cluster Profile
from app.core.statistics.cluster_profile import (
    interpretar_cluster_por_centroide,
    analisar_perfil_cluster,
)


# Backtest
from app.core.statistics.backtest import executar_backtest_temporal

# Padrões avançados
from app.core.statistics.patterns import (
    detectar_progressao_aritmetica_geral,
    detectar_sequencias_longas,
    detectar_diagonal_volante,
    detectar_bordas_extremas,
    analise_completa_padroes,
)

# Auditoria de independência entre sorteios
from app.core.statistics.auditoria_independencia import (
    AuditoriaIndependencia,
    ResultadoTeste,
    auditar_independencia,
)
from app.core.statistics.multiple_testing import (
    benjamini_hochberg,
    holm_bonferroni,
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
    "detectar_multiplos_de_d",
    "calcular_indice_compressibilidade",
    "WEIGHT_FREQUENCY",
    "WEIGHT_GAP",
    "EPSILON",
    "PRIMES_ANALYSIS_MAX_N",
    "PENALTY_MULTIPLOS_10_ALL",
    "PENALTY_MULTIPLOS_3_5_ALL",
    "PENALTY_MULTIPLOS_2_ALL",
    "PENALTY_MULTIPLOS_HIGH",
    "PENALTY_MULTIPLOS_MEDIUM",
    "FRACTION_ALL",
    "FRACTION_HIGH",
    "FRACTION_MEDIUM",
    "FRACTION_EXPECTED_MAX",
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
    "calibrar_pesos_dinamicos",
    # monte_carlo
    "bootstrap_ic_soma",
    "monte_carlo_probabilidade_acerto",
    # null model / percentiles
    "NullModel",
    "get_null_model",
    "build_null_model",
    "NULL_MODEL_VERSION",
    "batch_feature_percentiles",
    "summarize_feature_percentiles",
    "get_score_calibration_model",
    "score_calibration_diagnostics",
    "score_structural_batch",
    "summarize_score_calibration",
    "diagnostics_to_dict",
    "financial_diagnostics",
    "parse_prize_table",
    "resolve_prize_table",
    # bootstrap iC
    "avaliar_soma_com_bootstrap",
    "calcular_bootstrap_ic_com_cache",
    # gaps
    "analisar_gaps_geometricos",
    "analisar_gaps_todos_numeros",
    # temporal
    "calcular_autocorrelacao_frequencias",
    "detectar_tendencia_frequencia",
    "calcular_ciclo_atual",
    "analise_temporal_somas",
    "analise_temporal_repetidos",
    # clustering
    "extrair_features_jogo",
    "clusterizar_jogos_kmeans",
    "clusterizar_jogos_dbscan",
    "encontrar_numero_otimo_clusters",
    # cluster profile
    "interpretar_cluster_por_centroide",
    "analisar_perfil_cluster",
    # Backtest
    "executar_backtest_temporal",
    # Patterns
    "detectar_progressao_aritmetica_geral",
    "detectar_sequencias_longas",
    "detectar_diagonal_volante",
    "detectar_bordas_extremas",
    "analise_completa_padroes",
    # Auditoria de independência
    "AuditoriaIndependencia",
    "ResultadoTeste",
    "auditar_independencia",
    "benjamini_hochberg",
    "holm_bonferroni",
]
