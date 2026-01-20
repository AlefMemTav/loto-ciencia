# app/core/generator_fast.py
"""
Motor de Geração Vetorial de Alta Performance (NumPy).
"""

from logging import config
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
) -> List[List[int]]:

    config = ctx.config
    n_numbers = config.n_numbers
    k = config.bet_size

    # --- DEBUG INPUT ---
    if numeros_fixos:
        logger.warning(f"🔧 [DEBUG] Fixos recebidos no gerador: {numeros_fixos}")
    # -------------------

    # 1. Pesos Dinâmicos
    if hasattr(ctx, "pesos_dinamicos") and ctx.pesos_dinamicos:
        w_freq = ctx.pesos_dinamicos["w_freq"]
        w_gap = ctx.pesos_dinamicos["w_gap"]
    else:
        w_freq = 0.7 if config.is_dense else 0.3
        w_gap = 1.0 - w_freq

    # 2. Prepara Probabilidades com Mapeamento Explícito
    z_freq = np.zeros(n_numbers, dtype=np.float64)
    z_gap = np.zeros(n_numbers, dtype=np.float64)

    df_raw = ctx.tabela.copy()

    if "Numero" in df_raw.columns:
        bolas_indices = df_raw["Numero"].values.astype(int)
    elif "numero" in df_raw.columns:
        bolas_indices = df_raw["numero"].values.astype(int)
    else:
        bolas_indices = df_raw.index.values.astype(int)

    if config.n_numbers >= 100:
        bolas_indices = np.where(bolas_indices == 0, n_numbers, bolas_indices)

    vals_freq = df_raw["Z_Freq"].values
    vals_gap = df_raw["Z_Gap"].values

    mask_safe = (bolas_indices >= 1) & (bolas_indices <= n_numbers)
    dest_indices = bolas_indices[mask_safe] - 1

    z_freq[dest_indices] = vals_freq[mask_safe]
    z_gap[dest_indices] = vals_gap[mask_safe]

    # Cálculo dos Scores
    scores_raw = (z_freq * w_freq) + (z_gap * w_gap)

    if estrategia == "agressiva":
        scores_final = (z_gap * 0.8) + (z_freq * 0.2)
    elif estrategia == "conservadora":
        scores_final = (z_freq * 0.8) + (z_gap * 0.2)
    elif estrategia == "pura":
        scores_final = np.ones(n_numbers)
    else:
        scores_final = scores_raw

    # Normalização
    scores_final = np.nan_to_num(scores_final, nan=0.0)
    scores_final = scores_final - scores_final.min() + 0.05
    probs = scores_final / scores_final.sum()

    # Ajuste de Evitados
    pool = np.arange(1, n_numbers + 1)
    if numeros_evitados:
        mask_evitados = np.isin(pool, numeros_evitados)
        probs[mask_evitados] = 0
        probs /= probs.sum()

    # --- LOG DE DIAGNÓSTICO ---
    try:
        # Pega a bola com MAIOR probabilidade e a com MENOR (que não seja zero)
        idx_max = np.argmax(probs)
        prob_max = probs[idx_max]

        # Bola 1 (Index 0)
        prob_bola_1 = probs[0]

        logger.debug(
            f"📊 [PROBS] Bola {idx_max+1} (Top): {prob_max:.4f} | Bola 1: {prob_bola_1:.4f}"
        )

        if prob_bola_1 > prob_max * 0.9 and idx_max != 0:
            logger.warning(
                "⚠️ [ALERTA] A Bola 1 tem probabilidade tão alta quanto a Top! Possível viés de init."
            )

    except Exception as e:
        logger.error(f"Erro debug logs: {e}")
    # -----------------------------------------------

    n_fixos = len(numeros_fixos) if numeros_fixos else 0
    k_to_gen = k - n_fixos

    if k_to_gen <= 0:
        return [sorted(numeros_fixos)] * quantidade

    jogos_aceitos = []
    attempts = 0
    max_attempts = 30

    while len(jogos_aceitos) < quantidade and attempts < max_attempts:
        attempts += 1

        # A. Gumbel-Max
        u_noise = np.random.rand(buffer_size, n_numbers)
        gumbel_noise = -np.log(-np.log(u_noise + 1e-10))
        weighted_scores = np.log(probs.reshape(1, -1) + 1e-10) + gumbel_noise

        # --- DEBUG GUMBEL ---
        if attempts == 1:
            # Verifica se o Gumbel está respeitando as probs
            mean_score_top = weighted_scores[:, idx_max].mean()
            mean_score_1 = weighted_scores[:, 0].mean()
            logger.debug(
                f"🎲 [GUMBEL] Score Médio Top ({idx_max+1}): {mean_score_top:.2f} | Score Médio Bola 1: {mean_score_1:.2f}"
            )
        # --------------------

        # Seleção Top K
        candidatos_idx = np.argpartition(weighted_scores, -k_to_gen, axis=1)[
            :, -k_to_gen:
        ]
        candidatos = pool[candidatos_idx]

        if n_fixos > 0:
            fixos_arr = np.array(numeros_fixos)
            fixos_grid = np.tile(fixos_arr, (buffer_size, 1))
            candidatos = np.hstack([candidatos, fixos_grid])

        # Ordena cada jogo
        candidatos.sort(axis=1)

        # --- DEBUG CANDIDATOS ---
        if attempts == 1:
            # Amostra o primeiro candidato gerado antes de filtrar
            amostra = candidatos[0]
            logger.debug(f"🧬 [AMOSTRA RAW] Primeiro candidato gerado: {amostra}")
            if config.is_sparse and amostra[0] == 1 and amostra[1] == 2:
                logger.warning(
                    "⚠️ [ALERTA] Início 1, 2 em jogo esparso! Verifique possível viés."
                )
        # ------------------------

        # Filtros
        mask_valid = np.ones(buffer_size, dtype=bool)

        # Filtro Soma
        somas = candidatos.sum(axis=1)
        ic_raw = ctx.ic_info.get("ic_95", [k * n_numbers * 0.15, k * n_numbers * 0.85])

        # Se o tamanho da aposta (ex: 50) for diferente do sorteio (ex: 20),
        # precisamos escalar o intervalo de confiança proporcionalmente.
        if config.bet_size != config.k:
            fator_escala = config.bet_size / config.k
            ic_min = ic_raw[0] * fator_escala
            ic_max = ic_raw[1] * fator_escala
        else:
            ic_min = ic_raw[0]
            ic_max = ic_raw[1]

        # Aplica o filtro com os limites corretos
        mask_valid &= (somas >= ic_min) & (somas <= ic_max)

        validos_batch = candidatos[mask_valid]
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
    if not lista_aceitos:
        return True
    limite_igualdade = config.get_overlap_limit()
    set_jogo = set(jogo)
    for aceito in lista_aceitos:
        comum = len(set_jogo.intersection(set(aceito)))
        if comum > limite_igualdade:
            return False
    return True


# Fim do arquivo app/core/generator_fast.py
