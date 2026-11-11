# app/core/statistics/multiple_testing.py
"""Correção para múltiplos testes."""

from __future__ import annotations

import numpy as np


def holm_bonferroni(p: np.ndarray) -> np.ndarray:
    """
    P-valores ajustados de Holm-Bonferroni (controle da taxa de erro familiar).

    Vale sob qualquer estrutura de dependência entre os testes, ao contrário do
    Benjamini-Hochberg, que supõe independência ou dependência positiva.
    """
    p = np.asarray(p, dtype=float)
    m = len(p)
    if m == 0:
        return p.copy()
    ordem = np.argsort(p)
    ajustado = np.empty(m)
    ajustado[ordem] = np.minimum(
        np.maximum.accumulate((m - np.arange(m)) * p[ordem]), 1.0
    )
    return ajustado


def benjamini_hochberg(p: np.ndarray) -> np.ndarray:
    """P-valores ajustados (FDR) de Benjamini-Hochberg."""
    p = np.asarray(p, dtype=float)
    m = len(p)
    if m == 0:
        return p.copy()
    ordem = np.argsort(p)
    ajustado = np.empty(m)
    ajustado[ordem] = np.minimum.accumulate(
        (p[ordem] * m / (np.arange(m) + 1))[::-1]
    )[::-1]
    return np.clip(ajustado, 0.0, 1.0)
