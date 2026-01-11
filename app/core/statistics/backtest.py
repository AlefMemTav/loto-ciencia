# app/core/statistics/backtest.py
"""
Módulo de backtest para validação científica do sistema de scoring.

Este módulo valida se scores altos realmente correlacionam com
"jogos melhores" segundo métricas objetivas.
"""

import numpy as np
import pandas as pd
import random
from typing import Dict, List, Tuple
from collections import defaultdict
from scipy.stats import spearmanr, pearsonr

from app.core.lottery import GameConfig
from app.core.validator import validar_jogo
from app.core.statistics import (
    get_historico_jogos,
    get_tabela_inteligencia,
    analise_intervalo_confianca,
    calcular_distribuicoes_geometricas,
    calcular_distancia_minima_historico,
)
from app.core.logger import logger


def backtest_validator(
    df: pd.DataFrame, config: GameConfig, n_amostras: int = 1000, random_state: int = 42
) -> dict:
    """
    Valida se scores altos correlacionam com jogos de maior qualidade.

    Metodologia:
    1. Gera N jogos aleatórios
    2. Valida cada um (score 0-100)
    3. Separa em buckets de score
    4. Calcula métricas objetivas por bucket
    5. Testa correlação entre score e métricas

    Hipótese: Scores altos devem ter:
    - Maior distância de Hamming (mais únicos)
    - Somas dentro do IC histórico
    - Menos padrões óbvios detectados

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    n_amostras : int, default=1000
        Número de jogos aleatórios a gerar.
    random_state : int, default=42
        Seed para reprodutibilidade.

    Returns
    -------
    dict
        Resultado completo do backtest com correlações e análise por bucket.
    """
    logger.info(f"🧪 Iniciando backtest com {n_amostras} amostras para {config.name}")

    random.seed(random_state)
    np.random.seed(random_state)

    # Prepara contexto
    historico = get_historico_jogos(df, config)
    ic_info = analise_intervalo_confianca(df, config)
    tabela = get_tabela_inteligencia(df, config)

    grupos_geom = config.get_geometric_groups()
    distribuicoes_geom = calcular_distribuicoes_geometricas(df, grupos_geom, config)

    # Coleta resultados
    resultados = []

    for i in range(n_amostras):
        # Gera jogo aleatório
        jogo = sorted(random.sample(range(1, config.n_numbers + 1), config.bet_size))

        # Valida
        validacao = validar_jogo(
            jogo,
            config,
            historico_jogos=historico,
            ic_info=ic_info,
            df_historico=df,
            distribuicoes_geometricas=distribuicoes_geom,
        )

        # Métricas objetivas
        score = validacao["score"]
        soma = sum(jogo)
        ja_saiu = validacao["ja_saiu"]

        # Distância de Hamming mínima
        if config.bet_size == config.k:
            min_hamming, max_sim = calcular_distancia_minima_historico(jogo, df, config)
        else:
            min_hamming, max_sim = config.bet_size, 0.0

        # Dentro do IC?
        if ic_info:
            ic_80 = ic_info["ic_80"]
            dentro_ic80 = ic_80[0] <= soma <= ic_80[1]
            distancia_ic_centro = abs(soma - ic_info["media"]) / ic_info["desvio"]
        else:
            dentro_ic80 = True
            distancia_ic_centro = 0.0

        # Contagem de alertas
        n_alertas = sum(1 for msg in validacao["msgs"] if "⚠️" in msg or "❌" in msg)

        resultados.append(
            {
                "jogo": jogo,
                "score": score,
                "soma": soma,
                "hamming": min_hamming,
                "ja_saiu": ja_saiu,
                "dentro_ic80": dentro_ic80,
                "distancia_ic_centro": distancia_ic_centro,
                "n_alertas": n_alertas,
                "risco_divisao": validacao["risco_divisao"],
            }
        )

        if (i + 1) % 200 == 0:
            logger.info(f"  Progresso: {i+1}/{n_amostras}")

    df_resultados = pd.DataFrame(resultados)

    # Análise por bucket
    buckets = [(0, 40), (40, 60), (60, 80), (80, 100)]
    analise_buckets = {}

    for min_score, max_score in buckets:
        bucket_name = f"{min_score}-{max_score}"
        mask = (df_resultados["score"] >= min_score) & (
            df_resultados["score"] < max_score
        )
        df_bucket = df_resultados[mask]

        if len(df_bucket) == 0:
            continue

        analise_buckets[bucket_name] = {
            "n_jogos": len(df_bucket),
            "score_medio": df_bucket["score"].mean(),
            "hamming_medio": df_bucket["hamming"].mean(),
            "hamming_std": df_bucket["hamming"].std(),
            "dentro_ic80_pct": df_bucket["dentro_ic80"].mean() * 100,
            "distancia_ic_media": df_bucket["distancia_ic_centro"].mean(),
            "n_alertas_medio": df_bucket["n_alertas"].mean(),
            "risco_alto_pct": (df_bucket["risco_divisao"] == "ALTO").mean() * 100,
            "ja_saiu_pct": df_bucket["ja_saiu"].mean() * 100,
        }

    # Correlações
    scores = df_resultados["score"].values

    corr_hamming, p_hamming = spearmanr(scores, df_resultados["hamming"])
    corr_alertas, p_alertas = spearmanr(scores, df_resultados["n_alertas"])
    corr_ic_dist, p_ic_dist = spearmanr(scores, df_resultados["distancia_ic_centro"])

    # Interpretação
    interpretacao = []

    if corr_hamming > 0.3 and p_hamming < 0.05:
        interpretacao.append(
            "✅ Scores altos correlacionam com maior unicidade (Hamming)"
        )
    elif corr_hamming < -0.1:
        interpretacao.append("⚠️ PROBLEMA: Scores altos associados a jogos MENOS únicos")

    if corr_alertas < -0.3 and p_alertas < 0.05:
        interpretacao.append("✅ Scores altos têm menos alertas detectados")
    elif corr_alertas > 0.1:
        interpretacao.append("⚠️ PROBLEMA: Scores altos associados a MAIS alertas")

    if abs(corr_ic_dist) < 0.2:
        interpretacao.append("✅ Scores capturam mais que apenas proximidade à média")

    # Validade geral
    validacao_passou = (
        corr_hamming > 0.2
        and corr_alertas < -0.2
        and p_hamming < 0.05
        and p_alertas < 0.05
    )

    resultado_final = {
        "validacao_passou": validacao_passou,
        "n_amostras": n_amostras,
        "correlacoes": {
            "hamming": {"rho": round(corr_hamming, 3), "p_value": round(p_hamming, 4)},
            "n_alertas": {
                "rho": round(corr_alertas, 3),
                "p_value": round(p_alertas, 4),
            },
            "distancia_ic": {
                "rho": round(corr_ic_dist, 3),
                "p_value": round(p_ic_dist, 4),
            },
        },
        "buckets": analise_buckets,
        "interpretacao": interpretacao,
        "config": {
            "jogo": config.name,
            "n_numbers": config.n_numbers,
            "k": config.k,
            "densidade": config.density,
        },
    }

    if validacao_passou:
        logger.info(
            f"✅ Backtest PASSOU: Sistema de scoring validado para {config.name}"
        )
    else:
        logger.warning(
            f"⚠️ Backtest FALHOU: Revisar critérios de scoring para {config.name}"
        )

    return resultado_final


def comparar_estrategias_gerador(
    df: pd.DataFrame, config: GameConfig, n_jogos_por_estrategia: int = 100
) -> dict:
    """
    Compara qualidade dos jogos gerados por diferentes estratégias.

    Testa: "conservadora", "balanceada", "agressiva", "pura"

    Parameters
    ----------
    df : pd.DataFrame
        Histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    n_jogos_por_estrategia : int, default=100
        Quantos jogos gerar por estratégia.

    Returns
    -------
    dict
        Comparação de scores médios e distribuições por estratégia.
    """
    from app.core.generator import gerar_multiplos_jogos

    estrategias = ["conservadora", "balanceada", "agressiva", "pura"]

    logger.info(f"🔬 Comparando estratégias de geração para {config.name}")

    # Pré-calcula contexto para evitar recalcular a cada geração
    contexto_precomputado = {
        "tabela": get_tabela_inteligencia(df, config),
        "historico_jogos": get_historico_jogos(df, config),
        "ic_info": analise_intervalo_confianca(df, config),
        "distribuicoes_geometricas": calcular_distribuicoes_geometricas(
            df, config.get_geometric_groups(), config
        ),
        "taxa_regressao": None,  # Pode ser calculado se necessário
    }

    resultados = {}

    for estrategia in estrategias:
        logger.info(f"  Testando estratégia: {estrategia}")

        jogos = gerar_multiplos_jogos(
            df,
            config,
            quantidade=n_jogos_por_estrategia,
            estrategia=estrategia,
            garantir_diversidade=True,
            contexto_precomputado=contexto_precomputado,
        )

        scores = []
        for jogo in jogos:
            val = validar_jogo(jogo, config, df_historico=df)
            scores.append(val["score"])

        resultados[estrategia] = {
            "score_medio": np.mean(scores),
            "score_mediana": np.median(scores),
            "score_std": np.std(scores),
            "score_min": np.min(scores),
            "score_max": np.max(scores),
            "pct_excelente": (np.array(scores) >= 85).mean() * 100,
            "pct_bom": (np.array(scores) >= 70).mean() * 100,
        }

    # Melhor estratégia
    melhor = max(resultados.items(), key=lambda x: x[1]["score_medio"])

    logger.info(
        f"📊 Melhor estratégia: {melhor[0]} (score médio: {melhor[1]['score_medio']:.1f})"
    )

    return {
        "resultados": resultados,
        "melhor_estrategia": melhor[0],
        "config": config.name,
    }


def validar_regressao_media(
    df: pd.DataFrame, config: GameConfig, janelas: List[int] = [50, 100, 200]
) -> dict:
    """
    Valida se a regressão à média é real para diferentes janelas temporais.

    Testa a hipótese: "Números atrasados tendem a sair nos próximos N sorteios"

    Parameters
    ----------
    df : pd.DataFrame
        Histórico completo.
    config : GameConfig
        Configuração do jogo.
    janelas : List[int]
        Tamanhos de janela futura a testar.

    Returns
    -------
    dict
        Correlações e taxas de retorno para cada janela.
    """
    from app.core.statistics import calcular_taxa_regressao

    logger.info(f"📈 Validando regressão à média para {config.name}")

    if len(df) < max(janelas) + 50:
        return {"erro": "Histórico insuficiente"}

    resultados = {}

    for janela in janelas:
        taxa = calcular_taxa_regressao(df, config, janela=janela)

        if taxa:
            resultados[f"janela_{janela}"] = taxa

            significativo = taxa["p_value"] < 0.05
            forca = taxa["correlacao"]

            logger.info(
                f"  Janela {janela}: ρ={forca:.3f}, "
                f"p={taxa['p_value']:.4f}, "
                f"{'✅ SIGNIFICATIVO' if significativo else '❌ não significativo'}"
            )

    # Conclusão geral
    correlacoes = [r["correlacao"] for r in resultados.values()]
    p_values = [r["p_value"] for r in resultados.values()]

    media_corr = np.mean(correlacoes)
    min_p = min(p_values)

    conclusao = (
        "✅ Regressão à média validada"
        if media_corr > 0.2 and min_p < 0.05
        else "⚠️ Regressão fraca ou inexistente"
    )

    return {
        "resultados": resultados,
        "media_correlacao": round(media_corr, 3),
        "min_p_value": round(min_p, 4),
        "conclusao": conclusao,
        "recomendacao": (
            "Estratégias 'agressivas' são justificadas"
            if media_corr > 0.2
            else "Preferir estratégias 'balanceadas' ou 'conservadoras'"
        ),
    }
