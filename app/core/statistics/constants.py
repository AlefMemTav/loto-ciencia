# app/core/statistics/constants.py
"""
Constantes estatísticas compartilhadas entre módulos.

Este arquivo é a ÚNICA fonte de verdade para constantes usadas
em análises de geometria, similaridade e validação.
"""

# ============================================
# MÚLTIPLOS TESTES - CORREÇÃO DE BONFERRONI
# ============================================

# Número de testes estatísticos independentes realizados
N_TESTS_GEOMETRIC = 5  # moldura, miolo, cruz, xis, cantos
N_TESTS_QUADRANTS = 4  # Q1, Q2, Q3, Q4
N_TESTS_BASIC = 6  # soma, par/ímpar, linhas, metades, finais, primos
N_TESTS_TOTAL = N_TESTS_GEOMETRIC + N_TESTS_QUADRANTS + N_TESTS_BASIC  # 15 testes

# Nível de significância desejado (família de testes)
ALPHA_FAMILY = 0.05

# Correção de Bonferroni: α_individual = α_family / n_tests
ALPHA_BONFERRONI = ALPHA_FAMILY / N_TESTS_TOTAL  # 0.0033

# ============================================
# CONSTANTES DE Z-SCORE (COM BONFERRONI)
# ============================================

# Thresholds SEM correção (uso limitado, apenas para referência)
ZSCORE_EXTREME_NAIVE = 3.0  # 0.3% de chance (3-sigma)
ZSCORE_VERY_RARE_NAIVE = 2.0  # 5% de chance (2-sigma)
ZSCORE_RARE_NAIVE = 1.0  # 32% de chance (1-sigma)

# Thresholds COM correção de Bonferroni (usar estes!)
# Para α = 0.0033 bilateral: z = 2.97 (crítico)
# Para α = 0.0033 unilateral: z = 2.73
ZSCORE_EXTREME = 2.97  # Evento de ~0.3% após correção
ZSCORE_VERY_RARE = 2.39  # Evento de ~1.7% após correção
ZSCORE_RARE = 1.64  # Evento de ~10% após correção


# ============================================
# PENALIDADES PARA SCORING
# ============================================

# Pesos de penalidade por categoria de Z-score
PENALTY_EXTREME: float = 3.0  # Penalidade máxima
PENALTY_VERY_RARE: float = 2.0  # Penalidade alta
PENALTY_RARE: float = 1.0  # Penalidade moderada
PENALTY_NORMAL: float = 0.0  # Sem penalidade

# Fator de escala para penalidade (ajusta impacto no score)
PENALTY_SCALE_FACTOR: float = 0.5

# Fator de conversão penalidade -> score (0-100)
SCORE_CONVERSION_FACTOR: float = 8.0


# ============================================
# LIMIARES DE QUADRANTES
# ============================================

# Limiar de concentração em quadrantes (70% em um único quadrante)
QUADRANT_CONCENTRATION_THRESHOLD: float = 0.7

# Limiar de p-value para quadrantes (usando Bonferroni)
QUADRANT_PVALUE_THRESHOLD: float = ZSCORE_VERY_RARE  # 2.39


# ============================================
# AJUSTES POR DENSIDADE DO JOGO
# ============================================


def ajustar_threshold_por_densidade(valor_base: float, densidade: float) -> float:
    """
    Ajusta thresholds estatísticos baseado na densidade do jogo.

    Densidade = k / N (proporção do volante que é sorteada)

    Jogos densos (LotofÃ¡cil: 15/25 = 60%) têm padrões mais "óbvios"
    naturalmente, então precisam de thresholds mais relaxados.

    Parameters
    ----------
    valor_base : float
        Threshold original (para jogos esparsos).
    densidade : float
        Densidade do jogo (k/N).

    Returns
    -------
    float
        Threshold ajustado.

    Examples
    --------
    >>> ajustar_threshold_por_densidade(0.3, 0.6)  # LotofÃ¡cil
    0.45  # 50% mais tolerante

    >>> ajustar_threshold_por_densidade(0.3, 0.1)  # Mega-Sena
    0.3   # Sem ajuste
    """
    if densidade >= 0.5:
        # Jogos muito densos (LotofÃ¡cil, Lotomania): +50% tolerância
        return valor_base * 1.5
    elif densidade >= 0.3:
        # Jogos intermediários: +20% tolerância
        return valor_base * 1.2
    else:
        # Jogos esparsos (Mega-Sena, Quina): sem ajuste
        return valor_base


# ============================================
# LOGGING E MONITORAMENTO
# ============================================

# Métricas de performance para monitoramento
PERFORMANCE_METRICS = {
    "generator_attempts_histogram": [100, 500, 1000, 5000, 10000],
    "score_buckets": [0, 40, 60, 80, 100],
    "tiempo_medio_geracao_ms": [],
    "cache_hit_rate": 0.0,
}
