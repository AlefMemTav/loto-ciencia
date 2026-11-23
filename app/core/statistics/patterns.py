# app/core/statistics/patterns.py
"""
Detecção avançada de padrões em jogos de loteria.

Este módulo detecta progressões aritméticas gerais, padrões geométricos
e outras regularidades que não são cobertas pelos detectores básicos.
"""

import math
from functools import reduce
from typing import List, Dict, Set
from app.core.lottery import GameConfig


def detectar_progressao_aritmetica_geral(
    numeros: List[int], config: GameConfig
) -> Dict:
    """
    Detecta progressão aritmética com QUALQUER razão (não apenas 2, 3, 5, 10).

    Cobre casos como:
    - [7, 14, 21, 28, 35, 42] (razão 7)
    - [11, 22, 33, 44, 55] (razão 11)
    - [6, 12, 18, 24, 30] (razão 6)

    Parameters
    ----------
    numeros : List[int]
        Lista de números do jogo.
    config : GameConfig
        Configuração do jogo.

    Returns
    -------
    Dict
        - 'pa_detectada': bool
        - 'tipo': 'completa', 'multiplos', 'parcial', ou None
        - 'razao': razão da PA (se detectada)
        - 'penalidade': penalidade sugerida
        - 'conclusao': interpretação
    """
    if len(numeros) < 3:
        return {"pa_detectada": False, "penalidade": 0}

    nums_sorted = sorted(numeros)
    k = len(nums_sorted)

    # ============================================
    # Tipo 1: PA COMPLETA (todos gaps iguais)
    # ============================================
    gaps = [nums_sorted[i + 1] - nums_sorted[i] for i in range(k - 1)]

    if len(set(gaps)) == 1:
        razao = gaps[0]
        densidade = k / config.n_numbers

        # Uma PA completa (ex.: [1..6], [1..15], [1..50] ou todos os ímpares [1,3,...,99])
        # tem probabilidade combinatória ínfima em qualquer modalidade e altíssimo risco de rateio.
        penalidade = 25 if densidade < 0.3 else 20

        return {
            "pa_detectada": True,
            "tipo": "completa",
            "razao": razao,
            "penalidade": penalidade,
            "conclusao": f"❌ Progressão aritmética completa (razão {razao})",
        }

    # ============================================
    # Tipo 2: MÚLTIPLOS de uma base (GCD alto)
    # ============================================
    mdc = reduce(math.gcd, numeros)

    if mdc > 1:
        # Todos são múltiplos de mdc

        # Já coberto por detectar_multiplos_de_d se mdc ∈ {2,3,5,10}
        if mdc in {2, 3, 5, 10}:
            return {"pa_detectada": False, "penalidade": 0}

        # detecta múltiplos de bases altas (7, 11, 13, etc)
        densidade = k / config.n_numbers

        # Quantos múltiplos de mdc existem no universo?
        multiplos_disponiveis = config.n_numbers // mdc

        # Se escolheu TODOS múltiplos disponíveis
        if k == multiplos_disponiveis:
            penalidade = 25 if densidade < 0.3 else 15
            return {
                "pa_detectada": True,
                "tipo": "multiplos_completos",
                "razao": mdc,
                "penalidade": penalidade,
                "conclusao": f"❌ Todos os {k} múltiplos de {mdc} disponíveis",
            }

        # Se escolheu > 70% dos múltiplos disponíveis
        if k / multiplos_disponiveis > 0.7:
            penalidade = 15 if densidade < 0.3 else 8
            return {
                "pa_detectada": True,
                "tipo": "multiplos_alta_concentracao",
                "razao": mdc,
                "penalidade": penalidade,
                "conclusao": f"⚠️ {k}/{multiplos_disponiveis} múltiplos de {mdc}",
            }

    # ============================================
    # Tipo 3: PA PARCIAL (maioria dos gaps iguais)
    # ============================================
    from collections import Counter

    gap_counts = Counter(gaps)
    gap_mais_comum, freq_gap = gap_counts.most_common(1)[0]

    # Se >= 70% dos gaps são iguais
    if freq_gap / len(gaps) >= 0.7:
        densidade = k / config.n_numbers

        # Ajuste para jogos densos: gaps 1-2 são comuns em subconjuntos parciais,
        # só alerta se >= 85% dos gaps forem idênticos
        if densidade >= 0.5 and gap_mais_comum <= 2:
            if freq_gap / len(gaps) < 0.85:
                return {"pa_detectada": False, "penalidade": 0}

        penalidade = 12 if densidade < 0.3 else 8

        return {
            "pa_detectada": True,
            "tipo": "parcial",
            "razao": gap_mais_comum,
            "penalidade": penalidade,
            "conclusao": f"⚠️ PA parcial: {freq_gap}/{len(gaps)} gaps = {gap_mais_comum}",
        }

    return {"pa_detectada": False, "penalidade": 0}


def detectar_sequencias_longas(
    numeros: List[int], config: GameConfig, min_len: int = 4
) -> Dict:
    """
    Detecta sequências consecutivas longas (ex: 10, 11, 12, 13, 14).

    Diferente de contar "quantas sequências", detecta se há UMA sequência
    muito longa, o que é estatisticamente raro.
    """
    nums_sorted = sorted(numeros)

    sequencias = []
    seq_atual = [nums_sorted[0]]

    for i in range(1, len(nums_sorted)):
        if nums_sorted[i] == nums_sorted[i - 1] + 1:
            seq_atual.append(nums_sorted[i])
        else:
            if len(seq_atual) >= min_len:
                sequencias.append(seq_atual[:])
            seq_atual = [nums_sorted[i]]

    if len(seq_atual) >= min_len:
        sequencias.append(seq_atual[:])

    if not sequencias:
        return {"sequencia_longa": False, "penalidade": 0}

    maior_seq = max(sequencias, key=len)
    tamanho = len(maior_seq)

    densidade = len(numeros) / config.n_numbers

    if densidade >= 0.5:
        if len(numeros) >= 30:
            threshold_medio = 8
            threshold_alto = 10
        else:
            threshold_alto = 7
            threshold_medio = 6
    else:
        threshold_alto = 5
        threshold_medio = 4

    if tamanho >= threshold_alto:
        penalidade = 20 if densidade < 0.3 else 10
        conclusao = f"❌ Sequência longa detectada: {maior_seq}"
    elif tamanho >= threshold_medio:
        penalidade = 10 if densidade < 0.3 else 5
        conclusao = f"⚠️ Sequência: {maior_seq}"
    else:
        penalidade = 0
        conclusao = "✅ Sequências dentro do normal"

    return {
        "sequencia_longa": tamanho >= threshold_medio,
        "maior_sequencia": maior_seq,
        "tamanho": tamanho,
        "penalidade": penalidade,
        "conclusao": conclusao,
    }


def _hypergeom_tail_p(x: int, n_total: int, k_group: int, k_bet: int) -> float:
    """Probabilidade hipergeométrica exata P(X >= x) para X ~ Hypergeom(n_total, k_group, k_bet)."""
    if x <= 0:
        return 1.0
    if x > min(k_group, k_bet) or k_group <= 0 or k_bet <= 0:
        return 0.0
    from scipy.stats import hypergeom

    return float(hypergeom.sf(x - 1, n_total, k_group, k_bet))


def detectar_diagonal_volante(numeros: List[int], config: GameConfig) -> Dict:
    """
    Detecta concentração estatisticamente rara nas diagonais do volante usando
    calibragem hipergeométrica exata (elimina falsos positivos na Quina e código morto
    em Lotofácil/Lotomania).
    """
    layout = config.layout
    if not layout or layout.rows == 0 or layout.cols == 0:
        return {"diagonal": False, "penalidade": 0}

    coords = [layout.pos(n) for n in numeros]
    k = len(numeros)
    n_tot = int(config.n_numbers)

    diag_p_cells = sum(
        1 for n in range(1, n_tot + 1) if layout.pos(n)[0] == layout.pos(n)[1]
    )
    diag_s_cells = sum(
        1
        for n in range(1, n_tot + 1)
        if layout.pos(n)[0] + layout.pos(n)[1] == layout.cols - 1
    )

    diag_principal = sum(1 for r, c in coords if r == c)
    diag_secundaria = sum(1 for r, c in coords if r + c == layout.cols - 1)

    p_prin = _hypergeom_tail_p(diag_principal, n_tot, diag_p_cells, k)
    p_sec = _hypergeom_tail_p(diag_secundaria, n_tot, diag_s_cells, k)

    # Limiar de cauda exato (p < 0,015 por diagonal) + mínimo físico de 3 bolas
    if diag_principal >= 3 and p_prin < 0.015:
        return {
            "diagonal": True,
            "tipo": "principal",
            "count": diag_principal,
            "p_valor": round(p_prin, 5),
            "penalidade": 15,
            "conclusao": f"❌ {diag_principal}/{diag_p_cells} números na diagonal principal",
        }

    if diag_secundaria >= 3 and p_sec < 0.015:
        return {
            "diagonal": True,
            "tipo": "secundaria",
            "count": diag_secundaria,
            "p_valor": round(p_sec, 5),
            "penalidade": 15,
            "conclusao": f"❌ {diag_secundaria}/{diag_s_cells} números na diagonal secundária",
        }

    # Para volantes quadrados densos (ex.: Lotofácil 5x5), detecta o X completo (ambas diagonais)
    xis_cells = {
        n
        for n in range(1, n_tot + 1)
        if layout.pos(n)[0] == layout.pos(n)[1]
        or layout.pos(n)[0] + layout.pos(n)[1] == layout.cols - 1
    }
    no_xis = len(set(numeros) & xis_cells)
    p_xis = _hypergeom_tail_p(no_xis, n_tot, len(xis_cells), k)
    if no_xis >= len(xis_cells) and p_xis < 0.01:
        return {
            "diagonal": True,
            "tipo": "xis",
            "count": no_xis,
            "p_valor": round(p_xis, 5),
            "penalidade": 12,
            "conclusao": f"❌ Todos os {no_xis} números do X (ambas diagonais) marcados",
        }

    return {"diagonal": False, "penalidade": 0}


def detectar_bordas_extremas(numeros: List[int], config: GameConfig) -> Dict:
    """
    Detecta concentração estatisticamente rara nos primeiros/últimos 20% do volante
    usando p-valor hipergeométrico exato (p < 0,015), calibrado automaticamente
    para todas as modalidades (Mega, Quina, Lotofácil e Lotomania).
    """
    k = len(numeros)
    n_tot = int(config.n_numbers)

    borda_size = max(5, int(n_tot * 0.2))
    borda_inferior = set(range(1, borda_size + 1))
    borda_superior = set(range(n_tot - borda_size + 1, n_tot + 1))

    nums_set = set(numeros)
    na_inferior = len(nums_set & borda_inferior)
    na_superior = len(nums_set & borda_superior)

    p_inf = _hypergeom_tail_p(na_inferior, n_tot, borda_size, k)
    p_sup = _hypergeom_tail_p(na_superior, n_tot, borda_size, k)

    if na_inferior >= 4 and p_inf < 0.015:
        return {
            "borda_extrema": True,
            "tipo": "inferior",
            "count": na_inferior,
            "p_valor": round(p_inf, 5),
            "penalidade": 15,
            "conclusao": f"❌ {na_inferior}/{borda_size} números nos primeiros {borda_size}",
        }

    if na_superior >= 4 and p_sup < 0.015:
        return {
            "borda_extrema": True,
            "tipo": "superior",
            "count": na_superior,
            "p_valor": round(p_sup, 5),
            "penalidade": 15,
            "conclusao": f"❌ {na_superior}/{borda_size} números nos últimos {borda_size}",
        }

    return {"borda_extrema": False, "penalidade": 0}


def analise_completa_padroes(numeros: List[int], config: GameConfig) -> Dict:
    """
    Análise agregada de todos os padrões avançados.

    Retorna relatório consolidado com todas as detecções.
    """
    resultado = {
        "pa_geral": detectar_progressao_aritmetica_geral(numeros, config),
        "sequencias_longas": detectar_sequencias_longas(numeros, config),
        "diagonal": detectar_diagonal_volante(numeros, config),
        "bordas": detectar_bordas_extremas(numeros, config),
    }

    # Penalidade total
    penalidade_total = sum(r.get("penalidade", 0) for r in resultado.values())

    # Conclusões
    conclusoes = [
        r["conclusao"]
        for r in resultado.values()
        if r.get("conclusao") and r.get("penalidade", 0) > 0
    ]

    return {
        "detalhes": resultado,
        "penalidade_total": penalidade_total,
        "conclusoes": conclusoes,
        "padroes_detectados": len(conclusoes),
    }
