# app/core/generator.py
import math
import random
import time
from math import comb
from itertools import combinations
from app.core.statistics import (
    calcular_distribuicoes_geometricas,
    calcular_taxa_regressao,
)
from app.core.validator import validar_jogo
from app.core.lottery import GameConfig
from app.core.logger import logger
from app.core.statistics import (
    analise_intervalo_confianca,
    get_historico_jogos,
    get_tabela_inteligencia,
)


# ============================================
# MÉTRICAS DE PERFORMANCE
# ============================================
_performance_stats = {
    "total_geracoes": 0,
    "tentativas_acumuladas": 0,
    "early_stop_count": 0,
    "fallback_count": 0,
    "tempo_total_ms": 0,
}


def _registrar_performance(tentativas: int, tempo_ms: float, early_stop: bool):
    """Registra métricas de performance do gerador."""
    global _performance_stats
    _performance_stats["total_geracoes"] += 1
    _performance_stats["tentativas_acumuladas"] += tentativas
    _performance_stats["tempo_total_ms"] += tempo_ms
    if early_stop:
        _performance_stats["early_stop_count"] += 1
    else:
        _performance_stats["fallback_count"] += 1


def get_performance_stats() -> dict:
    """Retorna estatísticas de performance acumuladas."""
    if _performance_stats["total_geracoes"] == 0:
        return {"erro": "Nenhuma geração registrada"}

    return {
        "total_geracoes": _performance_stats["total_geracoes"],
        "tentativas_media": _performance_stats["tentativas_acumuladas"]
        / _performance_stats["total_geracoes"],
        "tempo_medio_ms": _performance_stats["tempo_total_ms"]
        / _performance_stats["total_geracoes"],
        "taxa_early_stop": _performance_stats["early_stop_count"]
        / _performance_stats["total_geracoes"],
        "taxa_fallback": _performance_stats["fallback_count"]
        / _performance_stats["total_geracoes"],
    }


def gerar_jogo_perfeito(
    df,
    config: GameConfig,
    finais_poisson=None,
    estrategia="balanceada",
    contexto_precomputado=None,
):
    """
    Gerador genérico para qualquer jogo (MEGASENA, QUINA, LOTOFACIL, LOTOMANIA).

    Args:
        df: DataFrame com histórico
        config: GameConfig do jogo (MEGASENA, QUINA, LOTOFACIL, LOTOMANIA)
        finais_poisson: Lista de dígitos finais atrasados (não usado)
        estrategia: 'balanceada', 'conservadora', 'agressiva', 'pura'

    Returns:
        Lista com k números ordenados (6 para MEGASENA, 5 para QUINA, 15 para LOTOFACIL, 50 para LOTOMANIA)
    """

    start_time = time.time()
    if contexto_precomputado:
        logger.debug(f"✅ [GENERATOR] Usando contexto pré-computado para {config.name}")
        tabela = contexto_precomputado["tabela"]
        historico_jogos = contexto_precomputado["historico_jogos"]
        ic_info = contexto_precomputado["ic_info"]
        distribuicoes_geometricas = contexto_precomputado["distribuicoes_geometricas"]
        taxa_regressao = contexto_precomputado.get("taxa_regressao")
    else:
        logger.warning(f"⚠️ [GENERATOR] Contexto não fornecido, recalculando (LENTO)")
        tabela = get_tabela_inteligencia(df, config)
        historico_jogos = get_historico_jogos(df, config)
        ic_info = analise_intervalo_confianca(df, config)

        constants = config.as_constants_dict()
        grupos_geometricos = config.get_geometric_groups()
        distribuicoes_geometricas = calcular_distribuicoes_geometricas(
            df, grupos_geometricos, config
        )

        # Calcula regressão se houver dados suficientes
        taxa_regressao = None
        if len(df) >= 150:
            taxa_regressao = calcular_taxa_regressao(df, config, janela=100)

    tamanho_aposta = config.bet_size

    if tabela.empty:
        logger.warning(f"Tentativa de gerar jogo para {config.name} com tabela vazia.")
        return sorted(random.sample(range(1, config.n_numbers + 1), tamanho_aposta))

    numeros_disponiveis = tabela.index.tolist()  # [1, 2, ..., N]

    # ============================================
    # Ajuste dinâmico de pesos baseado em regressão
    # ============================================
    if estrategia == "pura":
        # Estratégia pura: sem viés
        pesos_raw = [1.0] * config.n_numbers
        peso_gap_usado = 0.0
    else:
        # Determina peso de gaps baseado em evidência empírica
        if (
            taxa_regressao
            and taxa_regressao["correlacao"] > 0.3
            and taxa_regressao["p_value"] < 0.05
        ):
            # Regressão FORTE validada: atrasos importam
            logger.debug(
                f"✅ Regressão validada (ρ={taxa_regressao['correlacao']:.2f})"
            )

            if estrategia == "agressiva":
                peso_gap = 0.80
            elif estrategia == "conservadora":
                peso_gap = 0.50
            else:  # balanceada
                peso_gap = 0.65

        elif taxa_regressao and taxa_regressao["correlacao"] > 0.1:
            # Regressão MODERADA: reduz peso de gaps
            logger.debug(f"⚠️ Regressão moderada (ρ={taxa_regressao['correlacao']:.2f})")

            if estrategia == "agressiva":
                peso_gap = 0.60
            elif estrategia == "conservadora":
                peso_gap = 0.40
            else:  # balanceada
                peso_gap = 0.50

        else:
            # SEM evidência de regressão: ignora atrasos (anti-falácia do apostador)
            logger.debug(f"❌ Sem evidência de regressão, ignorando atrasos")

            if estrategia == "agressiva":
                peso_gap = 0.30  # Reduzido drasticamente
            elif estrategia == "conservadora":
                peso_gap = 0.70  # Inverte: prioriza frequência
            else:  # balanceada
                peso_gap = 0.20  # Quase ignora gaps

        peso_gap_usado = peso_gap
        pesos_raw = tabela["Z_Freq"] * (1 - peso_gap) + tabela["Z_Gap"] * peso_gap
        pesos = pesos_raw - pesos_raw.min() + 0.01
        pesos = pesos.tolist()

    # ============================================
    # Loop de geração
    # ============================================
    tentativas = 0
    melhor_jogo = None
    melhor_score = -1

    while tentativas < 10000:
        tentativas += 1

        pre_jogo = set()
        candidatos = random.choices(
            numeros_disponiveis, weights=pesos, k=tamanho_aposta
        )
        pre_jogo.update(candidatos)

        while len(pre_jogo) < tamanho_aposta:
            novo = random.choices(numeros_disponiveis, weights=pesos, k=1)[0]
            pre_jogo.add(novo)

        jogo = sorted(list(pre_jogo))

        # Validação
        val = validar_jogo(
            jogo,
            config,
            historico_jogos=historico_jogos,
            ic_info=ic_info,
            df_historico=df,
            distribuicoes_geometricas=distribuicoes_geometricas,
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

        # Early stopping com limites dinâmicos
        score_geom_minimo = 50

        if val["score"] >= config.target_score_excellent and (
            score_geom is None or score_geom >= score_geom_minimo
        ):
            duration = (time.time() - start_time) * 1000
            _registrar_performance(tentativas, duration, early_stop=True)

            logger.info(
                f"[{config.name}] Jogo encontrado em {tentativas} tentativas ({duration:.1f}ms). "
                f"Score: {val['score']}, Geom: {score_geom}, Peso Gap: {peso_gap_usado:.2f}"
            )
            return jogo

        # Fallback adaptativo
        if tentativas == 5000 and melhor_score >= config.target_score_accept:
            duration = (time.time() - start_time) * 1000
            _registrar_performance(tentativas, duration, early_stop=False)

            logger.info(
                f"[{config.name}] Fallback acionado em 5000 tentativas. Melhor Score: {melhor_score:.1f}"
            )
            return melhor_jogo

    duration = (time.time() - start_time) * 1000
    _registrar_performance(tentativas, duration, early_stop=False)

    logger.warning(
        f"[{config.name}] Limite de 10k tentativas atingido. Retornando melhor esforço (Score {melhor_score})."
    )

    return (
        melhor_jogo
        if melhor_jogo
        else sorted(random.sample(range(1, config.n_numbers + 1), tamanho_aposta))
    )


def gerar_multiplos_jogos(
    df,
    config: GameConfig,
    quantidade=10,
    estrategia="balanceada",
    garantir_diversidade=True,
    finais_poisson=None,
    contexto_precomputado=None,
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

    # Se o universo for pequeno (LOTOFACIL) ou o jogo muito denso, aumentamos a tolerância
    if config.n_numbers <= 25:  # LOTOFACIL
        fator_diversidade = 0.85  # Permite até 12 números iguais (15 * 0.85 = 12.7)
    else:
        fator_diversidade = 0.70  # Padrão para Mega/Quina

    max_comum = max(2, int(config.bet_size * fator_diversidade))

    while len(jogos_gerados) < quantidade and tentativas < max_tentativas:
        tentativas += 1

        jogo = gerar_jogo_perfeito(
            df,
            config,
            estrategia=estrategia,
            contexto_precomputado=contexto_precomputado,
        )
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
    contexto_precomputado=None,
):
    """
    Gerador genérico com restrições personalizadas.

    Args:
        df: DataFrame histórico
        config: GameConfig do jogo (MEGASENA, QUINA, LOTOFACIL)
        numeros_fixos: Lista de números que DEVEM estar no jogo
        numeros_evitados: Lista de números que NÃO podem estar no jogo
        estrategia: Modo de geração
        contexto_precomputado: dict com estatísticas pré-computadas (otimização)

    Returns:
        Lista com números ou dict com erro
    """
    if contexto_precomputado:
        tabela = contexto_precomputado["tabela"]
        historico = contexto_precomputado["historico_jogos"]
        ic_info = contexto_precomputado["ic_info"]
        distribuicoes_geometricas = contexto_precomputado["distribuicoes_geometricas"]
    else:
        tabela = get_tabela_inteligencia(df, config)
        historico = get_historico_jogos(df, config)
        ic_info = analise_intervalo_confianca(df, config)

        constants = config.as_constants_dict()
        grupos_geometricos = {
            "Moldura (Borda)": constants["moldura"],
            "Miolo (Centro)": constants["miolo"],
            "Cruz": constants["cruz"],
            "Xis (Diagonais)": constants["xis"],
            "Cantos": constants["cantos"],
        }
        distribuicoes_geometricas = calcular_distribuicoes_geometricas(
            df, grupos_geometricos, config
        )

    if tabela.empty:
        return None

    # Validações
    numeros_fixos = numeros_fixos or []
    numeros_evitados = numeros_evitados or []

    tamanho_aposta = config.bet_size

    if len(numeros_fixos) > tamanho_aposta:
        return {"erro": f"Não pode ter mais de {tamanho_aposta} números fixos"}

    if set(numeros_fixos).intersection(set(numeros_evitados)):
        return {"erro": "Números fixos e evitados não podem se sobrepor"}

    # Pool disponível
    pool = [
        n
        for n in range(1, config.n_numbers + 1)
        if n not in numeros_evitados and n not in numeros_fixos
    ]

    if len(pool) + len(numeros_fixos) < tamanho_aposta:
        return {"erro": "Pool insuficiente para gerar jogo"}

    # Pesos do pool
    pesos_pool = tabela.loc[pool, "Peso_Geracao"].tolist()

    # Gera complemento
    tentativas = 0
    while tentativas < 5000:
        tentativas += 1

        qtd_necessaria = tamanho_aposta - len(numeros_fixos)
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
            distribuicoes_geometricas=distribuicoes_geometricas,
        )

        if val["score"] >= 75:
            return jogo

    # Fallback
    complemento = random.sample(pool, tamanho_aposta - len(numeros_fixos))
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
    tamanho_jogo = config.bet_size

    if len(numeros_base) < tamanho_jogo:
        return []

    n = len(numeros_base)

    # Calcula número de combinações
    try:
        total_comb = math.factorial(n) // (
            (math.factorial(tamanho_jogo) * math.factorial(n - tamanho_jogo))
        )
    except:
        total_comb = comb(n, tamanho_jogo)

    if total_comb > max_combinacoes:
        return {
            "erro": f"Fechamento de {n} números gera {total_comb:,} jogos. "
            f"Limite: {max_combinacoes:,}. Reduza a quantidade de números."
        }

    logger.info(
        f"Gerando fechamento para {config.name}: {n} números base -> {total_comb} jogos."
    )
    comb_iter = combinations(numeros_base, tamanho_jogo)
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
