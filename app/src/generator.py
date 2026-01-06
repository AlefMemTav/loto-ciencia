import random
import time
import numpy as np
from math import comb
from itertools import combinations
from app.src.validator import validar_jogo
from app.src.games import GameConfig
from app.src.logger import logger
from app.src.statistics import (
    analise_intervalo_confianca,
    get_historico_jogos,
    get_tabela_inteligencia,
)


def gerar_jogo_perfeito(
    df, config: GameConfig, finais_poisson=None, estrategia="balanceada"
):
    """
    Gerador genérico para qualquer jogo (Mega-Sena, Quina, Lotofácil).

    Args:
        df: DataFrame com histórico
        config: GameConfig do jogo (MEGASENA, QUINA, LOTOFACIL)
        finais_poisson: Lista de dígitos finais atrasados (não usado)
        estrategia: 'balanceada', 'conservadora', 'agressiva', 'pura'

    Returns:
        Lista com k números ordenados (6 para Mega, 5 para Quina, 15 para Lotofácil)
    """

    start_time = time.time()

    # 1. Busca dados
    tabela = get_tabela_inteligencia(df, config)
    historico = get_historico_jogos(df, config)
    ic_info = analise_intervalo_confianca(df, config)

    if tabela.empty:
        logger.warning(f"Tentativa de gerar jogo para {config.name} com tabela vazia.")
        return sorted(random.sample(range(1, config.n_numbers + 1), config.k))

    numeros_disponiveis = tabela.index.tolist()  # [1, 2, ..., N]

    # 2. Seleciona pesos
    if estrategia == "conservadora":
        pesos_raw = tabela["Z_Freq"] * 0.70 + tabela["Z_Gap"] * 0.30
    elif estrategia == "agressiva":
        pesos_raw = tabela["Z_Freq"] * 0.20 + tabela["Z_Gap"] * 0.80
    elif estrategia == "pura":
        pesos_raw = [1.0] * config.n_numbers
    else:
        pesos_raw = tabela["Peso_Geracao"]

    if estrategia != "pura":
        pesos = pesos_raw - pesos_raw.min() + 0.01
        pesos = pesos.tolist()
    else:
        pesos = pesos_raw

    # 3. Loop de geração
    tentativas = 0
    melhor_jogo = None
    melhor_score = -1

    while tentativas < 10000:
        tentativas += 1

        pre_jogo = set()
        candidatos = random.choices(numeros_disponiveis, weights=pesos, k=config.k)
        pre_jogo.update(candidatos)

        while len(pre_jogo) < config.k:
            novo = random.choices(numeros_disponiveis, weights=pesos, k=1)[0]
            pre_jogo.add(novo)

        jogo = sorted(list(pre_jogo))

        # 4. Validação
        val = validar_jogo(
            jogo,
            config,
            historico_jogos=historico,
            ic_info=ic_info,
            df_historico=df,
        )

        score_base = val["score"]
        score_geom = val.get("metricas", {}).get("score_geom", None)

        score_final = score_base
        if score_geom is not None:
            if estrategia == "pura":
                score_final = score_base + (score_geom - 70) * 0.02
            else:
                score_final = score_base + (score_geom - 70) * 0.12

        if score_final > melhor_score:
            melhor_score = score_final
            melhor_jogo = jogo.copy()

        # Early stopping inteligente
        if val["score"] >= config.target_score_excellent and (
            score_geom is None or score_geom >= config.min_geom_score
        ):
            # Log de sucesso (Performance)
            duration = time.time() - start_time
            logger.info(
                f"[{config.name}] Jogo encontrado em {tentativas} tentativas ({duration:.3f}s). Score: {val['score']}"
            )
            return jogo

        # Fallback adaptativo
        if tentativas == 5000 and melhor_score >= config.target_score_accept:
            logger.info(
                f"[{config.name}] Fallback acionado em 5000 tentativas. Melhor Score: {melhor_score}"
            )
            return melhor_jogo
    logger.warning(
        f"[{config.name}] Limite de 10k tentativas atingido. Retornando melhor esforço (Score {melhor_score})."
    )
    return (
        melhor_jogo
        if melhor_jogo
        else sorted(random.sample(range(1, config.n_numbers + 1), config.k))
    )


def gerar_multiplos_jogos(
    df,
    config: GameConfig,
    quantidade=10,
    estrategia="balanceada",
    garantir_diversidade=True,
    finais_poisson=None,
):
    """
    Gerador de múltiplos jogos genéricos com controle de diversidade.

    Args:
        df: DataFrame histórico
        config: GameConfig do jogo (MEGASENA, QUINA, LOTOFACIL)
        quantidade: Número de jogos a gerar
        estrategia: Modo de geração (ver gerar_jogo_perfeito)
        garantir_diversidade: Se True, evita jogos com mais de 4 números em comum
        finais_poisson: (Não usado mais, mantido para compatibilidade)

    Returns:
        Lista de jogos
    """
    logger.info(
        f"Iniciando geração em lote: {quantidade} jogos de {config.name} ({estrategia})"
    )
    jogos_gerados = []
    jogos_set = set()

    tentativas = 0
    max_tentativas = quantidade * 100

    # Define limiar de sobreposição baseado no tamanho do jogo
    # Mega (6): max 4 em comum | Quina (5): max 3 | Lotofácil (15): max 10
    max_comum = max(2, int(config.k * 0.7))

    while len(jogos_gerados) < quantidade and tentativas < max_tentativas:
        tentativas += 1

        jogo = gerar_jogo_perfeito(df, config, estrategia=estrategia)
        jogo_tuple = tuple(jogo)

        # Verifica duplicata
        if jogo_tuple in jogos_set:
            continue

        # Verifica diversidade
        if garantir_diversidade and jogos_gerados:
            sobrepoe_muito = False
            for jogo_anterior in jogos_gerados:
                comum = len(set(jogo).intersection(set(jogo_anterior)))
                if comum > max_comum:
                    sobrepoe_muito = True
                    break

            if sobrepoe_muito:
                continue

        jogos_gerados.append(jogo)
        jogos_set.add(jogo_tuple)
    logger.info(f"Lote finalizado. {len(jogos_gerados)} jogos gerados.")
    return jogos_gerados


def gerar_com_restricoes(
    df,
    config: GameConfig,
    numeros_fixos=None,
    numeros_evitados=None,
    estrategia="balanceada",
):
    """
    Gerador genérico com restrições personalizadas.

    Args:
        df: DataFrame histórico
        config: GameConfig do jogo (MEGASENA, QUINA, LOTOFACIL)
        numeros_fixos: Lista de números que DEVEM estar no jogo
        numeros_evitados: Lista de números que NÃO podem estar no jogo
        estrategia: Modo de geração

    Returns:
        Lista com 6 números ou dict com erro
    """
    tabela = get_tabela_inteligencia(df, config)
    historico = get_historico_jogos(df, config)
    ic_info = analise_intervalo_confianca(df, config)

    if tabela.empty:
        return None

    # Validações
    numeros_fixos = numeros_fixos or []
    numeros_evitados = numeros_evitados or []

    if len(numeros_fixos) > config.k:
        return {"erro": f"Não pode ter mais de {config.k} números fixos"}

    if set(numeros_fixos).intersection(set(numeros_evitados)):
        return {"erro": "Números fixos e evitados não podem se sobrepor"}

    # Pool disponível
    pool = [
        n
        for n in range(1, config.n_numbers + 1)
        if n not in numeros_evitados and n not in numeros_fixos
    ]

    if len(pool) + len(numeros_fixos) < config.k:
        return {"erro": "Pool insuficiente para gerar jogo"}

    # Pesos do pool
    pesos_pool = tabela.loc[pool, "Peso_Geracao"].tolist()

    # Gera complemento
    tentativas = 0
    while tentativas < 5000:
        tentativas += 1

        qtd_necessaria = config.k - len(numeros_fixos)
        complemento = []

        while len(complemento) < qtd_necessaria:
            novo = random.choices(pool, weights=pesos_pool, k=1)[0]
            if novo not in complemento:
                complemento.append(novo)

        jogo = sorted(numeros_fixos + complemento)

        val = validar_jogo(
            jogo,
            config,
            historico_jogos=historico,
            ic_info=ic_info,
            df_historico=df,
        )

        if val["score"] >= 75:
            return jogo

    # Fallback
    complemento = random.sample(pool, config.k - len(numeros_fixos))
    return sorted(numeros_fixos + complemento)


def gerar_fechamento(numeros_base, config: GameConfig, max_combinacoes=1000):
    """
    Limita fechamentos genéricos grandes para evitar explosão combinatória.

    Args:
        numeros_base: Lista de números base
        config: GameConfig do jogo (MEGASENA, QUINA, LOTOFACIL)
        max_combinacoes: Limite máximo de jogos

    Returns:
        Lista de jogos ou dict com erro
    """
    if len(numeros_base) < config.k:
        return []

    n = len(numeros_base)

    # Calcula número de combinações
    try:
        total_comb = np.math.factorial(n) // (
            np.math.factorial(config.k) * np.math.factorial(n - config.k)
        )
    except:
        total_comb = comb(n, config.k)

    if total_comb > max_combinacoes:
        return {
            "erro": f"Fechamento de {n} números gera {total_comb:,} jogos. "
            f"Limite: {max_combinacoes:,}. Reduza a quantidade de números."
        }
    logger.info(
        f"Gerando fechamento para {config.name}: {n} números base -> {total_comb} jogos."
    )
    comb_iter = combinations(numeros_base, config.k)
    return [sorted(list(c)) for c in comb_iter]


def analise_estatistica_jogo(jogo, df, config: GameConfig):
    """
    Análise completa genérica de um jogo específico.
    Args:
        jogo: Lista de números do jogo
        df: DataFrame histórico
        config: GameConfig do jogo (MEGASENA, QUINA, LOTOFACIL)
    Returns:
        Dict com análise estatística
    """
    tabela = get_tabela_inteligencia(df, config)

    if tabela.empty:
        return None

    # Métricas individuais dos números
    stats_nums = tabela.loc[jogo]

    # Análise agregada
    analise = {
        "frequencia_media": round(stats_nums["Frequencia"].mean(), 2),
        "atraso_medio": round(stats_nums["Atraso"].mean(), 2),
        "z_freq_medio": round(stats_nums["Z_Freq"].mean(), 3),
        "z_gap_medio": round(stats_nums["Z_Gap"].mean(), 3),
        "peso_medio": round(stats_nums["Peso_Geracao"].mean(), 3),
        "percentil_freq_medio": round(stats_nums["Percentil_Freq"].mean() * 100, 1),
        "percentil_gap_medio": round(stats_nums["Percentil_Gap"].mean() * 100, 1),
    }

    # Interpretações
    if analise["z_freq_medio"] > 0.5:
        analise["perfil"] = "🔥 Números Quentes"
    elif analise["z_freq_medio"] < -0.5:
        analise["perfil"] = "❄️ Números Frios"
    else:
        analise["perfil"] = "⚖️ Balanceado"

    if analise["z_gap_medio"] > 0.5:
        analise["status_atraso"] = "🕐 Muito Atrasados (Regressão)"
    elif analise["z_gap_medio"] < -0.5:
        analise["status_atraso"] = "🆕 Recentemente Sorteados"
    else:
        analise["status_atraso"] = "⏱️ Atraso Normal"

    return analise
