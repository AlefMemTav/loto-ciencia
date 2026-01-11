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

        # Ajuste por densidade
        densidade = k / config.n_numbers

        # Para jogos densos, gaps pequenos (1-2) são naturais
        if densidade >= 0.5 and razao <= 2:
            return {
                "pa_detectada": False,
                "tipo": None,
                "razao": razao,
                "penalidade": 0,
                "conclusao": "✅ Gaps consecutivos naturais para jogo denso",
            }

        # PA óbvia
        penalidade = 25 if densidade < 0.3 else 15

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

        # Proporção esperada
        prop_esperada = multiplos_disponiveis / config.n_numbers

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

        # Ajuste para jogos densos
        if densidade >= 0.5 and gap_mais_comum <= 2:
            return {"pa_detectada": False, "penalidade": 0}

        penalidade = 12 if densidade < 0.3 else 6

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

    Parameters
    ----------
    numeros : List[int]
        Lista de números do jogo.
    config : GameConfig
        Configuração do jogo.
    min_len : int, default=4
        Tamanho mínimo de sequência para alertar.

    Returns
    -------
    Dict
        Informação sobre a maior sequência detectada.
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

    # Última sequência
    if len(seq_atual) >= min_len:
        sequencias.append(seq_atual[:])

    if not sequencias:
        return {"sequencia_longa": False, "penalidade": 0}

    maior_seq = max(sequencias, key=len)
    tamanho = len(maior_seq)

    # Ajuste por densidade
    densidade = len(numeros) / config.n_numbers

    # Para LotofÃ¡cil (densidade 60%), sequências de 4-5 são comuns
    if densidade >= 0.5:
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


def detectar_diagonal_volante(numeros: List[int], config: GameConfig) -> Dict:
    """
    Detecta se os números formam uma diagonal no volante.

    Exemplo: Em Mega-Sena (6x10), [1, 12, 23, 34, 45, 56] forma diagonal.

    Parameters
    ----------
    numeros : List[int]
        Lista de números.
    config : GameConfig
        Configuração do jogo.

    Returns
    -------
    Dict
        Informação sobre diagonalidade.
    """
    layout = config.layout

    # Pega coordenadas
    coords = [layout.pos(n) for n in numeros]

    # Testa diagonal principal (r == c)
    diag_principal = sum(1 for r, c in coords if r == c)

    # Testa diagonal secundária (r + c == cols - 1)
    diag_secundaria = sum(1 for r, c in coords if r + c == layout.cols - 1)

    # Ajuste por densidade
    k = len(numeros)
    densidade = k / config.n_numbers

    # Threshold ajustado
    if densidade >= 0.5:
        threshold = int(k * 0.6)
    else:
        threshold = int(k * 0.5)

    if diag_principal >= threshold:
        return {
            "diagonal": True,
            "tipo": "principal",
            "count": diag_principal,
            "penalidade": 15,
            "conclusao": f"❌ {diag_principal} números na diagonal principal",
        }

    if diag_secundaria >= threshold:
        return {
            "diagonal": True,
            "tipo": "secundaria",
            "count": diag_secundaria,
            "penalidade": 15,
            "conclusao": f"❌ {diag_secundaria} números na diagonal secundária",
        }

    return {"diagonal": False, "penalidade": 0}


def detectar_bordas_extremas(numeros: List[int], config: GameConfig) -> Dict:
    """
    Detecta concentração nas bordas extremas (primeiros/últimos N números).

    Ex: [1, 2, 3, 4, 5, 6] ou [55, 56, 57, 58, 59, 60]

    Parameters
    ----------
    numeros : List[int]
        Lista de números.
    config : GameConfig
        Configuração do jogo.

    Returns
    -------
    Dict
        Informação sobre concentração em bordas.
    """
    k = len(numeros)
    N = config.n_numbers

    # Define "borda" como primeiros/últimos 20%
    borda_size = max(5, int(N * 0.2))

    borda_inferior = set(range(1, borda_size + 1))
    borda_superior = set(range(N - borda_size + 1, N + 1))

    nums_set = set(numeros)

    na_inferior = len(nums_set & borda_inferior)
    na_superior = len(nums_set & borda_superior)

    # Threshold: >= 70% em uma borda
    densidade = k / N

    if densidade >= 0.5:
        threshold = int(k * 0.8)
    else:
        threshold = int(k * 0.7)

    if na_inferior >= threshold:
        return {
            "borda_extrema": True,
            "tipo": "inferior",
            "count": na_inferior,
            "penalidade": 15,
            "conclusao": f"❌ {na_inferior} números nos primeiros {borda_size}",
        }

    if na_superior >= threshold:
        return {
            "borda_extrema": True,
            "tipo": "superior",
            "count": na_superior,
            "penalidade": 15,
            "conclusao": f"❌ {na_superior} números nos últimos {borda_size}",
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
