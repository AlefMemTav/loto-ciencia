# app/core/generator_fast.py
"""
Motor de Geração Vetorial de Alta Performance (NumPy).
Versão 2.1: CORREÇÕES CRÍTICAS APLICADAS
- Normalização Softmax (elimina viés negativo)
"""

import numpy as np
from typing import List
from app.core.logger import logger


def gerar_jogos_vetorizado(
    ctx,
    quantidade: int = 10,
    estrategia: str = "balanceada",
    numeros_fixos: List[int] = None,
    numeros_evitados: List[int] = None,
    buffer_size: int = 50000,
    seed: int = None,
) -> List[List[int]]:

    # Reprodutibilidade: define seed se fornecido
    if seed is not None:
        import random

        np.random.seed(seed)
        random.seed(seed)
    config = ctx.config
    n_numbers = config.n_numbers
    k = config.bet_size

    # --- 1. CONFIGURAÇÃO DE PESOS ---
    # Tenta usar pesos calibrados dinamicamente (autópsia dos vencedores)
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

    df_raw = ctx.tabela.copy()

    # Padronizado: cada coluna já representa a bola 1, 2, ..., N
    bolas_indices = np.arange(1, n_numbers + 1)

    if n_numbers >= 100:
        bolas_indices = np.where(bolas_indices == 0, n_numbers, bolas_indices)

    vals_freq = df_raw["Z_Freq"].values
    vals_gap = df_raw["Z_Gap"].values

    mask_safe = (bolas_indices >= 1) & (bolas_indices <= n_numbers)
    dest_indices = bolas_indices[mask_safe] - 1

    z_freq[dest_indices] = vals_freq[mask_safe]
    z_gap[dest_indices] = vals_gap[mask_safe]

    # Aplica estratégia
    if estrategia == "agressiva":
        scores_final = (z_gap * 0.7) + (z_freq * 0.3)
    elif estrategia == "conservadora":
        scores_final = (z_freq * 0.7) + (z_gap * 0.3)
    elif estrategia == "pura":
        scores_final = np.ones(n_numbers)
    else:  # Balanceada
        scores_final = (z_freq * w_freq) + (z_gap * w_gap)

    # ============================================================
    # INJEÇÃO DE INTELIGÊNCIA TEMPORAL (MARKOV + CICLO)
    # ============================================================

    # 1. Bônus Markov (O Efeito Dominó)
    # Aumenta score dos números que o Markov diz que virão após o último sorteio
    if hasattr(ctx, "matriz_transicao") and ctx.matriz_transicao is not None:
        last_draw = ctx.df.iloc[-1][config.draw_cols].values
        z_markov = np.zeros(n_numbers)
        # Soma a probabilidade de transição de cada número do último sorteio
        for num_ant in last_draw:
            if 1 <= num_ant <= n_numbers:
                z_markov += ctx.matriz_transicao[num_ant - 1]

        # Normaliza e adiciona peso (0.3 é um peso seguro)
        if z_markov.max() > 0:
            z_markov /= z_markov.max()
            scores_final += z_markov * 0.3

    # 2. Bônus de Ciclo (A Gravidade)
    # Empurra números que faltam para fechar o ciclo
    if hasattr(ctx, "ciclo_atual") and ctx.ciclo_atual:
        faltam = ctx.ciclo_atual.get("faltam_sair", [])
        if faltam:
            # Jogos densos (Lotofácil) respeitam muito o ciclo -> Bônus alto
            # Jogos esparsos (Mega) respeitam pouco -> Bônus baixo
            peso_ciclo = 2.0 if config.is_dense else 0.5
            indices_faltam = np.array(faltam) - 1
            # Filtra índices válidos para evitar crash
            indices_validos = indices_faltam[
                (indices_faltam >= 0) & (indices_faltam < n_numbers)
            ]
            scores_final[indices_validos] += peso_ciclo

    scores_final = np.nan_to_num(scores_final, nan=-10.0)  # NaN vira muito negativo

    # Softmax robusto (evita overflow numérico)
    scores_exp = np.exp(scores_final - scores_final.max())  # Shift para estabilidade
    probs = scores_exp / scores_exp.sum()

    # Filtro de Evitados
    pool = np.arange(1, n_numbers + 1)
    if numeros_evitados:
        mask_evitados = np.isin(pool, numeros_evitados)
        probs[mask_evitados] = 0
        if probs.sum() > 0:
            probs /= probs.sum()

    # --- 3. GERAÇÃO MASSIVA (GUMBEL-MAX) ---
    n_fixos = len(numeros_fixos) if numeros_fixos else 0
    k_to_gen = k - n_fixos

    if k_to_gen <= 0:
        return [sorted(numeros_fixos)] * quantidade

    jogos_aceitos = []
    attempts = 0
    max_attempts = 20

    # Matriz de Co-ocorrência para informação
    matriz_cooc = getattr(ctx, "matriz_coocorrencia", None)

    while len(jogos_aceitos) < quantidade and attempts < max_attempts:
        attempts += 1

        # Gera ruído Gumbel
        u_noise = np.random.rand(buffer_size, n_numbers)
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
            fixos_grid = np.tile(fixos_arr, (buffer_size, 1))
            candidatos = np.hstack([candidatos, fixos_grid])

        candidatos.sort(axis=1)

        # --- 4. FILTRAGEM VETORIAL RÁPIDA ---
        mask_valid = np.ones(buffer_size, dtype=bool)

        # Filtro A: Soma (IC95)
        somas = candidatos.sum(axis=1)
        # Ajusta IC para o tamanho real da aposta
        ic_raw = ctx.ic_info.get("ic_95", [k * n_numbers * 0.15, k * n_numbers * 0.85])
        if config.bet_size != config.k:
            fator = config.bet_size / config.k
            ic_min, ic_max = ic_raw[0] * fator, ic_raw[1] * fator
        else:
            ic_min, ic_max = ic_raw[0], ic_raw[1]

        mask_valid &= (somas >= ic_min) & (somas <= ic_max)

        # ══════════════════════════════════════════════════════════════════════
        # Co-ocorrência como Reranking (Classificação)
        # ══════════════════════════════════════════════════════════════════════

        validos_batch = candidatos[mask_valid]

        # Se temos a matriz de inteligência, usamos para ORDENAR os jogos (melhores primeiro)
        # Em vez de filtrar/deletar, nós apenas priorizamos.
        if matriz_cooc is not None and len(validos_batch) > 0:
            # Performance: Limitamos o reranking se o batch for gigante para não travar
            limit_rerank = 5000
            if len(validos_batch) > limit_rerank:
                # Se tivermos muitos jogos, pegamos uma amostra aleatória primeiro para ser rápido
                indices_random = np.random.choice(
                    len(validos_batch), limit_rerank, replace=False
                )
                validos_batch = validos_batch[indices_random]

            # Ajusta para índice 0-based para consultar a matriz
            idx_0based = validos_batch - 1
            struct_scores = []

            # Loop rápido (numPy puro seria complexo para extração 3D irregular)
            for jogo in idx_0based:
                # Soma a força de conexão entre os pares do jogo
                sub = matriz_cooc[np.ix_(jogo, jogo)]
                # Pega triângulo superior (soma das conexões únicas)
                score = np.sum(np.triu(sub, 1))
                struct_scores.append(score)

            # RERANKING: Ordena do maior score para o menor
            struct_scores = np.array(struct_scores)
            # argsort dá os índices do menor pro maior, então invertemos [::-1]
            ordem_inteligente = np.argsort(struct_scores)[::-1]

            # Aplica a nova ordem ao batch
            validos_batch = validos_batch[ordem_inteligente]

        # --- 5. SELEÇÃO FINAL E HAMMING ---
        validos_batch = candidatos[mask_valid]

        # Remove duplicatas dentro do batch
        validos_batch = np.unique(validos_batch, axis=0)
        np.random.shuffle(validos_batch)

        for row in validos_batch:
            lista = row.tolist()
            if _passa_hamming(lista, jogos_aceitos, config):
                jogos_aceitos.append(lista)
                if len(jogos_aceitos) >= quantidade:
                    break

    return jogos_aceitos


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
