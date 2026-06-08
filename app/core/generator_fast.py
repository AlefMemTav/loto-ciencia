# app/core/generator_fast.py
"""
Motor de Geração Vetorial de Alta Performance (NumPy).
Versão 2.2: OTIMIZAÇÕES DE PERFORMANCE
- Normalização Softmax (elimina viés negativo)
- Co-ocorrência vetorizada (elimina loop Python)
"""

import numpy as np
from typing import List
from app.core.logger import logger
from app.core.generator_objective import (
    score_plausibility_batch,
    select_diverse_portfolio,
)


def _calcular_scores_coocorrencia_batch(
    jogos_idx: np.ndarray, matriz_cooc: np.ndarray
) -> np.ndarray:
    """
    Calcula scores de co-ocorrência para um batch de jogos usando NumPy puro.

    Esta função substitui o loop Python O(n * k²) por operações vetorizadas,
    resultando em ganho de performance de 5-10x.

    Args:
        jogos_idx: Array (n_jogos, k) com índices 0-based dos números
        matriz_cooc: Matriz de co-ocorrência (n_numbers, n_numbers)

    Returns:
        Array (n_jogos,) com scores de co-ocorrência
    """
    n_jogos, k = jogos_idx.shape

    # Cria índices para triângulo superior (i < j)
    # Isso representa todos os pares únicos dentro de cada jogo
    i_idx, j_idx = np.triu_indices(k, k=1)

    # Para cada jogo, pega os números nas posições i e j
    # nums_i[jogo, par] = número na posição i do par
    nums_i = jogos_idx[:, i_idx]  # (n_jogos, n_pares)
    nums_j = jogos_idx[:, j_idx]  # (n_jogos, n_pares)

    # Consulta a matriz de co-ocorrência de forma vetorizada
    # matriz_cooc[nums_i, nums_j] retorna (n_jogos, n_pares)
    scores = matriz_cooc[nums_i, nums_j].sum(axis=1)

    return scores


def gerar_jogos_vetorizado(
    ctx,
    quantidade: int = 10,
    estrategia: str = "balanceada",
    numeros_fixos: List[int] = None,
    numeros_evitados: List[int] = None,
    buffer_size: int = 50000,
    seed: int = None,
    temperatura: float = None,
    usar_quentes: bool = True,
    usar_atrasados: bool = True,
    usar_markov: bool = True,
    usar_ciclo: bool = True,
    usar_coocorrencia: bool = True,
    historical_signal_strength: float = 1.0,
    percentil_min: float = 5.0,
    percentil_max: float = 95.0,
    null_model_samples: int = None,
) -> List[List[int]]:

    rng = np.random.default_rng(seed)
    config = ctx.config
    n_numbers = config.n_numbers
    k = config.bet_size
    numeros_fixos = sorted(set(numeros_fixos or []))
    numeros_evitados = sorted(set(numeros_evitados or []))

    # --- 1. CONFIGURAÇÃO DE PESOS ---
    if hasattr(ctx, "pesos_dinamicos") and ctx.pesos_dinamicos:
        w_freq = ctx.pesos_dinamicos.get("w_freq", 0.5)
        w_gap = ctx.pesos_dinamicos.get("w_gap", 0.5)
    else:
        # Fallback inteligente baseado na densidade
        w_freq = 0.7 if config.is_dense else 0.4
        w_gap = 1.0 - w_freq

    # --- 2. PREPARAÇÃO DOS SCORES LINEARES ---
    # Mapeia Z-Scores para um array alinhado (1..N)
    z_freq = np.zeros(n_numbers, dtype=np.float64)
    z_gap = np.zeros(n_numbers, dtype=np.float64)

    df_raw = ctx.tabela.copy() if getattr(ctx, "tabela", None) is not None else None

    # Padronizado: cada coluna já representa a bola 1, 2, ..., N
    bolas_indices = np.arange(1, n_numbers + 1)

    if n_numbers >= 100:
        bolas_indices = np.where(bolas_indices == 0, n_numbers, bolas_indices)

    if df_raw is not None and not getattr(df_raw, "empty", True):
        vals_freq = df_raw["Z_Freq"].values
        vals_gap = df_raw["Z_Gap"].values

        mask_safe = (bolas_indices >= 1) & (bolas_indices <= n_numbers)
        dest_indices = bolas_indices[mask_safe] - 1

        z_freq[dest_indices] = vals_freq[mask_safe]
        z_gap[dest_indices] = vals_gap[mask_safe]

    # Aplica estratégia
    if estrategia == "agressiva":
        scores_final = (z_gap * 0.55 * usar_atrasados) + (
            z_freq * 0.45 * usar_quentes
        )
    elif estrategia == "conservadora":
        scores_final = (z_freq * 0.65 * usar_quentes) + (
            z_gap * 0.35 * usar_atrasados
        )
    elif estrategia == "pura":
        scores_final = np.ones(n_numbers)
    else:  # Balanceada
        scores_final = (z_freq * w_freq * usar_quentes) + (
            z_gap * w_gap * usar_atrasados
        )

    if estrategia != "pura":
        scores_final *= float(np.clip(historical_signal_strength, 0.0, 2.0))

    # ============================================================
    # INJEÇÃO DE INTELIGÊNCIA TEMPORAL (MARKOV + CICLO)
    # ============================================================

    # 1. Bônus Markov (O Efeito Dominó)
    # Aumenta score dos números que o Markov diz que virão após o último sorteio
    if (
        estrategia != "pura"
        and usar_markov
        and hasattr(ctx, "matriz_transicao")
        and ctx.matriz_transicao is not None
    ):
        last_draw = ctx.df.iloc[-1][config.draw_cols].values
        z_markov = np.zeros(n_numbers)
        # Soma a probabilidade de transição de cada número do último sorteio
        for num_ant in last_draw:
            if 1 <= num_ant <= n_numbers:
                z_markov += ctx.matriz_transicao[num_ant - 1]

        # Normaliza e adiciona peso (0.3 é um peso seguro)
        if z_markov.max() > 0:
            z_markov /= z_markov.max()
            scores_final += z_markov * 0.15

    # 2. Bônus de Ciclo (A Gravidade)
    # Empurra números que faltam para fechar o ciclo
    if (
        estrategia != "pura"
        and usar_ciclo
        and hasattr(ctx, "ciclo_atual")
        and ctx.ciclo_atual
    ):
        faltam = ctx.ciclo_atual.get("faltam_sair", [])
        if faltam:
            # Jogos densos (Lotofácil) respeitam muito o ciclo -> Bônus alto
            # Jogos esparsos (Mega) respeitam pouco -> Bônus baixo
            peso_ciclo = 0.8 if config.is_dense else 0.25
            indices_faltam = np.array(faltam) - 1
            # Filtra índices válidos para evitar crash
            indices_validos = indices_faltam[
                (indices_faltam >= 0) & (indices_faltam < n_numbers)
            ]
            scores_final[indices_validos] += peso_ciclo

    scores_final = np.nan_to_num(scores_final, nan=0.0)
    if estrategia != "pura":
        scores_final = np.clip(scores_final, -2.5, 2.5)

    if temperatura is None:
        temperatura = {
            "conservadora": 1.15,
            "balanceada": 1.35,
            "agressiva": 1.45,
            "pura": 2.0,
        }.get(estrategia, 1.35)
    temperatura = max(float(temperatura), 0.2)

    # Softmax com temperatura: mantém intenção estatística sem colapsar em poucos números.
    logits = scores_final / temperatura
    scores_exp = np.exp(logits - logits.max())
    probs = scores_exp / scores_exp.sum()

    pool = np.arange(1, n_numbers + 1)
    bloqueados = set(numeros_evitados) | set(numeros_fixos)
    if bloqueados:
        mask_bloqueados = np.isin(pool, list(bloqueados))
        probs[mask_bloqueados] = 0
    if probs.sum() <= 0:
        probs = np.ones(n_numbers, dtype=float)
        if bloqueados:
            probs[np.isin(pool, list(bloqueados))] = 0
    if probs.sum() <= 0:
        return []
    probs /= probs.sum()

    # --- 3. GERAÇÃO MASSIVA (GUMBEL-MAX) ---
    n_fixos = len(numeros_fixos)
    k_to_gen = k - n_fixos

    if k_to_gen <= 0:
        jogo = sorted(numeros_fixos)
        return [jogo] if len(jogo) == k else []

    candidatos_acumulados = []
    attempts = 0
    max_attempts = 8
    batch = max(buffer_size, quantidade * 4000)

    while attempts < max_attempts:
        attempts += 1

        # Gera ruído Gumbel
        u_noise = rng.random((batch, n_numbers))
        gumbel_noise = -np.log(-np.log(u_noise + 1e-10))
        weighted_scores = np.log(probs.reshape(1, -1) + 1e-10) + gumbel_noise

        # Seleciona os Top K índices
        candidatos_idx = np.argpartition(weighted_scores, -k_to_gen, axis=1)[
            :, -k_to_gen:
        ]
        candidatos = pool[candidatos_idx]

        # Adiciona fixos se houver
        if n_fixos > 0:
            fixos_arr = np.array(numeros_fixos)
            fixos_grid = np.tile(fixos_arr, (batch, 1))
            candidatos = np.hstack([candidatos, fixos_grid])

        candidatos.sort(axis=1)
        candidatos_acumulados.append(candidatos)

        total = sum(len(c) for c in candidatos_acumulados)
        if total >= max(quantidade * 1500, quantidade):
            break

    if not candidatos_acumulados:
        return []

    candidatos = np.vstack(candidatos_acumulados)
    _, unique_indices = np.unique(candidatos, axis=0, return_index=True)
    candidatos = candidatos[np.sort(unique_indices)]
    scores = score_plausibility_batch(
        candidatos,
        ctx,
        estrategia=estrategia,
        percentil_min=percentil_min,
        percentil_max=percentil_max,
        null_model_samples=null_model_samples,
        usar_quentes=usar_quentes,
        usar_atrasados=usar_atrasados,
        usar_coocorrencia=usar_coocorrencia,
        historical_signal_strength=historical_signal_strength,
    )
    return select_diverse_portfolio(
        candidatos,
        scores,
        config,
        quantidade,
        rng,
        estrategia=estrategia,
    )


def _passa_hamming(jogo, lista_aceitos, config):
    """Garante diversidade entre os jogos gerados."""
    if not lista_aceitos:
        return True
    limite_igualdade = config.get_overlap_limit()
    set_jogo = set(jogo)

    # Checagem rápida contra o último gerado
    if len(lista_aceitos) > 0:
        if len(set_jogo.intersection(set(lista_aceitos[-1]))) > limite_igualdade:
            return False

    # Checagem completa
    for aceito in lista_aceitos[:-1]:
        comum = len(set_jogo.intersection(set(aceito)))
        if comum > limite_igualdade:
            return False
    return True
