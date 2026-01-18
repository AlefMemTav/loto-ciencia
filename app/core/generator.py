# app/core/generator.py
import math
import random
import time
import pandas as pd
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


def _calcular_pesos_dinamicos(tabela, estrategia, taxa_regressao=None):
    """
    Calcula os pesos de probabilidade para cada número baseado na estratégia escolhida.
    Retorna uma Series pandas com os pesos indexados pelos números.
    """
    if estrategia == "pura":
        # Peso 1.0 para todos (sem viés)
        return pd.Series(1.0, index=tabela.index)

    # Lógica de Regressão (Define o quanto vamos respeitar o atraso)
    peso_gap = 0.50  # Default (Balanceada sem regressão)

    # 1. Analisa a Regressão (Se houver dados)
    tem_regressao_forte = (
        taxa_regressao
        and taxa_regressao["correlacao"] > 0.3
        and taxa_regressao["p_value"] < 0.05
    )
    tem_regressao_moderada = taxa_regressao and taxa_regressao["correlacao"] > 0.1

    if tem_regressao_forte:
        # Se o atraso importa matematicamente
        if estrategia == "agressiva":
            peso_gap = 0.80
        elif estrategia == "conservadora":
            peso_gap = 0.50
        else:
            peso_gap = 0.65

    elif tem_regressao_moderada:
        if estrategia == "agressiva":
            peso_gap = 0.60
        elif estrategia == "conservadora":
            peso_gap = 0.40
        else:
            peso_gap = 0.50

    else:
        # Sem evidência de que atraso importa (Falácia do Apostador)
        if estrategia == "agressiva":
            peso_gap = 0.30
        elif estrategia == "conservadora":
            peso_gap = 0.70
        else:
            peso_gap = 0.20

    # 2. Aplica a Fórmula: Score = Frequência vs Atraso
    # Normaliza Z-Scores para garantir valores positivos
    z_freq = tabela["Z_Freq"]
    z_gap = tabela["Z_Gap"]

    # Fórmula de Combinação Linear
    pesos_raw = z_freq * (1 - peso_gap) + z_gap * peso_gap

    # Normalização final (Remove negativos e garante mínimo de 0.01)
    pesos = pesos_raw - pesos_raw.min() + 0.01

    return pesos


def _minerar_jogo_core(
    finais_poisson,
    pool_numeros,
    pesos_pool,
    numeros_fixos,
    qtd_a_preencher,
    contexto_validacao,
    estrategia,
    target_score=85,
    max_tentativas=5000,
):
    """
    Motor genérico que minera combinações até achar uma boa.
    Funciona tanto para jogos livres quanto restritos.
    """
    tentativas = 0
    melhor_jogo = None
    melhor_score = -1

    # Extrai contexto para performance
    config = contexto_validacao["config"]

    while tentativas < max_tentativas:
        tentativas += 1

        # Seleção Inteligente do Complemento
        complemento_set = set()

        # Otimização: Random Choices é rápido, mas pode repetir.
        # Loopamos até preencher a quantidade necessária.
        while len(complemento_set) < qtd_a_preencher:
            falta = qtd_a_preencher - len(complemento_set)
            # Pesos devem bater com o pool. Python < 3.9 exige lista, não Series.
            candidatos = random.choices(pool_numeros, weights=pesos_pool, k=falta)
            complemento_set.update(candidatos)

        # Monta candidato
        jogo = sorted(numeros_fixos + list(complemento_set))

        # Valida
        val = validar_jogo(
            jogo,
            config,
            historico_jogos=contexto_validacao["historico"],
            ic_info=contexto_validacao["ic_info"],
            df_historico=contexto_validacao["df"],
            distribuicoes_geometricas=contexto_validacao["geom"],
        )

        # Ajuste de Score por Estratégia
        score_base = val["score"]
        score_geom = val.get("metricas", {}).get("score_geom", 70)

        score_final = score_base
        if estrategia == "pura":
            score_final = score_base + (score_geom - 70) * 0.02
        else:
            score_final = score_base + (score_geom - 70) * 0.12

        # Rastreia o melhor esforço
        if score_final > melhor_score:
            melhor_score = score_final
            melhor_jogo = jogo[:]

        # Early Stop (Sucesso)
        if score_final >= target_score:
            return jogo

    # Fallback: Retorna o melhor que encontrou
    if melhor_jogo:
        return melhor_jogo

    # Último caso: Aleatório puro (só acontece se o pool for minusculo e ruim)
    complemento = random.sample(pool_numeros, qtd_a_preencher)
    return sorted(numeros_fixos + complemento)


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
    df, config: GameConfig, estrategia="balanceada", contexto_precomputado=None
):
    """Gera um jogo do zero (sem restrições). Wrapper para a engine."""
    return gerar_com_restricoes(
        df,
        config,
        finais_poisson=None,
        numeros_fixos=[],
        numeros_evitados=[],
        estrategia=estrategia,
        contexto_precomputado=contexto_precomputado,
    )


def gerar_com_restricoes(
    df,
    config: GameConfig,
    finais_poisson=None,
    numeros_fixos=None,
    numeros_evitados=None,
    estrategia="balanceada",
    contexto_precomputado=None,
):
    """Prepara os dados (pesos, pool) e chama a engine de mineração."""

    # 1. Carrega Contexto (Boilerplate padrão)
    taxa_regressao = None
    if contexto_precomputado:
        tabela = contexto_precomputado["tabela"]
        # Tenta pegar regressão
        taxa_regressao = contexto_precomputado.get("taxa_regressao")
        # Prepara objeto de validação unificado
        ctx_val = {
            "config": config,
            "historico": contexto_precomputado["historico_jogos"],
            "ic_info": contexto_precomputado["ic_info"],
            "df": df,
            "geom": contexto_precomputado["distribuicoes_geometricas"],
        }
    else:
        # Recalcula se não vier pré-computado (Modo Lento)
        tabela = get_tabela_inteligencia(df, config)
        if len(df) >= 150:
            taxa_regressao = calcular_taxa_regressao(df, config, janela=100)

        ctx_val = {
            "config": config,
            "historico": get_historico_jogos(df, config),
            "ic_info": analise_intervalo_confianca(df, config),
            "df": df,
            "geom": calcular_distribuicoes_geometricas(
                df, config.get_geometric_groups(), config
            ),
        }

    if tabela.empty:
        return None

    # 2. Tratamento de Inputs
    numeros_fixos = numeros_fixos or []
    numeros_evitados = numeros_evitados or []

    # 3. Definição do Pool (Universo Disponível)
    pool = [
        n
        for n in range(1, config.n_numbers + 1)
        if n not in numeros_evitados and n not in numeros_fixos
    ]

    qtd_a_preencher = config.bet_size - len(numeros_fixos)

    # Validações Físicas
    if qtd_a_preencher < 0:
        return {"erro": "Muitos números fixos"}
    if len(pool) < qtd_a_preencher:
        return {"erro": "Pool insuficiente"}
    if qtd_a_preencher == 0:
        return sorted(numeros_fixos)  # Jogo já veio pronto

    # 4. Cálculo de Pesos (Inteligência)
    todos_pesos = _calcular_pesos_dinamicos(tabela, estrategia, taxa_regressao)
    pesos_pool = todos_pesos.loc[pool].tolist()  # Filtra pesos só para o pool

    # 5. Chama a Engine
    return _minerar_jogo_core(
        finais_poisson=finais_poisson,
        pool_numeros=pool,
        pesos_pool=pesos_pool,
        numeros_fixos=numeros_fixos,
        qtd_a_preencher=qtd_a_preencher,
        contexto_validacao=ctx_val,
        estrategia=estrategia,
        target_score=85 if estrategia != "pura" else 75,
    )


def gerar_multiplos_jogos(
    df,
    config: GameConfig,
    finais_poisson=None,
    quantidade=10,
    estrategia="balanceada",
    garantir_diversidade=True,
    numeros_fixos=None,
    numeros_evitados=None,
    contexto_precomputado=None,
):
    """Gerador em lote que chama o gerador único."""
    logger.info(f"Minerando lote: {quantidade} jogos de {config.name}")

    jogos_gerados = []
    jogos_set = set()
    tentativas = 0
    max_tentativas = quantidade * 50

    # Configuração de diversidade
    fator_div = 0.85 if config.n_numbers <= 25 else 0.70
    max_comum = max(2, int(config.bet_size * fator_div))

    # Desativa diversidade se o jogo estiver muito "travado" por fixos
    if numeros_fixos and len(numeros_fixos) > (config.bet_size / 2):
        garantir_diversidade = False

    while len(jogos_gerados) < quantidade and tentativas < max_tentativas:
        tentativas += 1

        jogo = gerar_com_restricoes(
            df,
            config,
            finais_poisson,
            numeros_fixos,
            numeros_evitados,
            estrategia,
            contexto_precomputado,
        )

        if not jogo or (isinstance(jogo, dict) and "erro" in jogo):
            continue

        jogo_tuple = tuple(jogo)

        # 1. Duplicata Exata
        if jogo_tuple in jogos_set:
            continue

        # 2. Diversidade (Hamming)
        if garantir_diversidade and jogos_gerados:
            sobrepoe_muito = False
            for ant in jogos_gerados:
                if len(set(jogo).intersection(set(ant))) > max_comum:
                    sobrepoe_muito = True
                    break
            if sobrepoe_muito:
                continue

        jogos_gerados.append(jogo)
        jogos_set.add(jogo_tuple)

    return jogos_gerados


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
