# app/core/statistics/distributions.py
"""
Análises estatísticas de distribuições para sorteios de loteria.

Este módulo contém funções para testes de aleatoriedade, incluindo
Poisson, Chi-quadrado, Kolmogorov-Smirnov, intervalos de confiança
e coeficiente de variação.
"""

import pandas as pd
import numpy as np
from scipy.stats import poisson, chisquare, kstest
from app.core.lottery import GameConfig
from app.core.statistics.basic import _flatten_draws, get_numeros_quentes_frios


# ============================================
# CONSTANTES DE CONFIGURAÇÃO ESTATÍSTICA
# ============================================

# Limiares de confiança para teste Chi²
CHI2_HIGH_CONFIDENCE: float = 0.05
CHI2_MEDIUM_CONFIDENCE: float = 0.01

# Limiares de coeficiente de variação
CV_EXCELLENT: float = 10.0
CV_GOOD: float = 20.0
CV_ACCEPTABLE: float = 30.0


def analise_poisson(df: pd.DataFrame, config: GameConfig, alpha: float = 0.05) -> list[dict]:
    """
    Analisa dígitos finais usando distribuição de Poisson.
    
    Testa se os dígitos finais dos números sorteados seguem a distribuição
    esperada baseada na distribuição teórica do jogo.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    alpha : float, optional
        Nível de significância para o teste (default: 0.05).
    
    Returns
    -------
    list[dict]
        Lista de dígitos com desvios significativos. Cada dicionário contém:
        - digito: o dígito final (0-9)
        - observado: contagem observada
        - esperado: contagem esperada
        - desvio: diferença (observado - esperado)
        - tipo: "Déficit" ou "Excesso"
        - p_value: valor-p do teste
        - interpretacao: mensagem interpretativa
    """
    if df.empty:
        return []

    numeros = _flatten_draws(df, config)
    finais = pd.Series([n % 10 for n in numeros])
    total_bolas_sorteadas = len(finais)

    resultado = []

    universo = list(range(1, config.n_numbers + 1))
    finais_universo = [n % 10 for n in universo]
    contagem_teorica = pd.Series(finais_universo).value_counts().sort_index()

    for digito in range(10):
        prob_teorica = contagem_teorica.get(digito, 0) / config.n_numbers
        lambda_esperado = total_bolas_sorteadas * prob_teorica
        observado = (finais == digito).sum()

        if lambda_esperado == 0:
            continue

        p_inferior = poisson.cdf(observado, lambda_esperado)
        p_superior = 1 - poisson.cdf(observado - 1, lambda_esperado)
        p_value = min(p_inferior, p_superior) * 2

        if p_value < alpha:
            tipo = "Déficit" if observado < lambda_esperado else "Excesso"
            resultado.append(
                {
                    "digito": digito,
                    "observado": observado,
                    "esperado": round(lambda_esperado, 2),
                    "desvio": observado - lambda_esperado,
                    "tipo": tipo,
                    "p_value": round(p_value, 5),
                    "interpretacao": f"Desvio ({tipo}) - Esperado: {prob_teorica:.1%}",
                }
            )

    return resultado


def calcular_chi_quadrado(df: pd.DataFrame, config: GameConfig) -> dict | None:
    """
    Testa aleatoriedade dos sorteios usando Chi-quadrado e Kolmogorov-Smirnov.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    dict | None
        Dicionário com resultados dos testes:
        - chi2_stat: estatística Chi-quadrado
        - p_chi: p-value do teste Chi-quadrado
        - ks_stat: estatística Kolmogorov-Smirnov
        - p_ks: p-value do teste KS
        - status: interpretação qualitativa
        - confianca: nível de confiança (Alta/Média/Baixa)
        - n_amostras: tamanho da amostra
        Retorna None se df vazio.
    """
    if df.empty:
        return None

    todos_numeros = _flatten_draws(df, config)
    contagem = pd.Series(todos_numeros).value_counts().sort_index()
    contagem = contagem.reindex(range(1, config.n_numbers + 1), fill_value=0)

    f_obs = contagem.values
    total_bolas = len(todos_numeros)
    f_esp = [total_bolas / config.n_numbers] * config.n_numbers

    chi2_stat, p_chi = chisquare(f_obs, f_exp=f_esp)

    ks_stat, p_ks = kstest(sorted(todos_numeros), lambda x: x / config.n_numbers)

    if p_chi > CHI2_HIGH_CONFIDENCE and p_ks > CHI2_HIGH_CONFIDENCE:
        status = "✅ Honesto (Aleatório)"
        confianca = "Alta"
    elif p_chi > CHI2_MEDIUM_CONFIDENCE or p_ks > CHI2_MEDIUM_CONFIDENCE:
        status = "⚠️ Possivelmente Honesto"
        confianca = "Média"
    else:
        status = "🚨 Suspeito (Viciado)"
        confianca = "Baixa"

    return {
        "chi2_stat": round(chi2_stat, 2),
        "p_chi": round(p_chi, 4),
        "ks_stat": round(ks_stat, 4),
        "p_ks": round(p_ks, 4),
        "status": status,
        "confianca": confianca,
        "n_amostras": len(todos_numeros),
    }


def analise_intervalo_confianca(df: pd.DataFrame, config: GameConfig) -> dict | None:
    """
    Calcula intervalos de confiança para a soma dos números sorteados.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    dict | None
        Dicionário com estatísticas da soma:
        - media: média das somas
        - mediana: mediana das somas
        - desvio: desvio padrão
        - ic_50: intervalo de confiança 50% (Q1, Q3)
        - ic_80: intervalo de confiança 80% (P10, P90)
        - ic_95: intervalo de confiança 95% (P2.5, P97.5)
        - min_historico: menor soma observada
        - max_historico: maior soma observada
        Retorna None se df vazio.
    """
    if df.empty:
        return None

    somas = df[config.draw_cols].sum(axis=1)

    media = somas.mean()
    mediana = somas.median()
    desvio = somas.std()

    ic_50 = (somas.quantile(0.25), somas.quantile(0.75))
    ic_80 = (somas.quantile(0.10), somas.quantile(0.90))
    ic_95 = (somas.quantile(0.025), somas.quantile(0.975))

    return {
        "media": round(media, 1),
        "mediana": round(mediana, 1),
        "desvio": round(desvio, 1),
        "ic_50": (round(ic_50[0], 0), round(ic_50[1], 0)),
        "ic_80": (round(ic_80[0], 0), round(ic_80[1], 0)),
        "ic_95": (round(ic_95[0], 0), round(ic_95[1], 0)),
        "min_historico": int(somas.min()),
        "max_historico": int(somas.max()),
    }


def calcular_coeficiente_variacao(df: pd.DataFrame, config: GameConfig) -> dict | None:
    """
    Calcula coeficiente de variação das frequências dos números.
    
    O coeficiente de variação (CV) mede a uniformidade da distribuição
    de frequências. Valores baixos indicam distribuição mais uniforme.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    dict | None
        Dicionário com:
        - coeficiente_variacao: CV em percentual
        - interpretacao: classificação da uniformidade
        - freq_max: maior frequência observada
        - freq_min: menor frequência observada
        - amplitude: diferença entre máxima e mínima
        Retorna None se df vazio.
    """
    if df.empty:
        return None

    freq = get_numeros_quentes_frios(df, config)
    cv = (freq.std() / freq.mean()) * 100

    if cv < CV_EXCELLENT:
        interpretacao = "Excelente uniformidade"
    elif cv < CV_GOOD:
        interpretacao = "Boa uniformidade"
    elif cv < CV_ACCEPTABLE:
        interpretacao = "Uniformidade aceitável"
    else:
        interpretacao = "Possível viés detectado"

    return {
        "coeficiente_variacao": round(cv, 2),
        "interpretacao": interpretacao,
        "freq_max": int(freq.max()),
        "freq_min": int(freq.min()),
        "amplitude": int(freq.max() - freq.min()),
    }
