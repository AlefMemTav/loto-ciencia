# app/core/statistics/constants.py
"""
Constantes estatísticas compartilhadas entre módulos.

Este arquivo é a ÚNICA fonte de verdade para constantes usadas
em análises de geometria, similaridade e validação.
"""

# ============================================
# CONSTANTES DE Z-SCORE (REGRA EMPÍRICA)
# ============================================

# Limiares baseados na distribuição normal
ZSCORE_EXTREME: float = 3.0  # 0.3% de chance (3-sigma)
ZSCORE_VERY_RARE: float = 2.0  # 5% de chance (2-sigma)
ZSCORE_RARE: float = 1.0  # 32% de chance (1-sigma)


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

# Limiar de p-value para quadrantes (90% IC, equivale a z=1.64)
QUADRANT_PVALUE_THRESHOLD: float = 1.64
