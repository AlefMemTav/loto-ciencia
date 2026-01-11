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


def analise_poisson(
    df: pd.DataFrame, config: GameConfig, alpha: float = 0.05
) -> list[dict]:
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


def testar_distribuicao_gaps_bilhete(numeros: list[int], config: GameConfig) -> dict:
    """
    Testa se os gaps entre números do bilhete seguem distribuição esperada.

    Para um bilhete aleatório, os gaps devem seguir aproximadamente uma
    distribuição exponencial (ou uniforme, dependendo da interpretação).

    Parameters
    ----------
    numeros : list[int]
        Lista de números do jogo (ordenados).
    config : GameConfig
        Configuração do jogo.

    Returns
    -------
    dict
        Resultado do teste:
        - 'gaps': lista de gaps entre números consecutivos
        - 'gap_medio': média dos gaps
        - 'gap_std': desvio padrão dos gaps
        - 'gap_esperado': gap médio esperado para distribuição uniforme
        - 'cv_gaps': coeficiente de variação dos gaps
        - 'ks_statistic': estatística do teste KS
        - 'ks_pvalue': p-value do teste
        - 'conclusao': interpretação do resultado
        - 'penalidade': penalidade sugerida (0-15)

    Examples
    --------
    >>> resultado = testar_distribuicao_gaps_bilhete([1, 2, 3, 4, 5, 6], config)
    >>> resultado['conclusao']
    '❌ Gaps muito regulares (padrão aritmético)'
    """
    numeros_sorted = sorted(numeros)
    k = len(numeros_sorted)

    if k < 3:
        return {"erro": "Jogo muito pequeno para análise de gaps"}

    # Calcula gaps entre números consecutivos
    gaps = [numeros_sorted[i + 1] - numeros_sorted[i] for i in range(k - 1)]

    gap_medio = np.mean(gaps)
    gap_std = np.std(gaps)

    # Gap esperado para distribuição uniforme: (N - 1) / (k - 1)
    # onde N = n_numbers e k = quantidade de números no jogo
    gap_esperado = (config.n_numbers - 1) / (k - 1)

    # Normaliza gaps para teste KS (escala 0-1)
    gaps_norm = np.array(gaps) / config.n_numbers

    # Teste KS contra distribuição exponencial
    # (gaps aleatórios tendem a seguir exponencial)
    if gap_std > 0:
        scale = gap_medio / config.n_numbers
        ks_stat, ks_pvalue = kstest(gaps_norm, "expon", args=(0, scale))
    else:
        # Todos os gaps iguais (padrão aritmético)
        ks_stat, ks_pvalue = 1.0, 0.0

    # Análise adicional: coeficiente de variação dos gaps
    cv_gaps = (gap_std / gap_medio) if gap_medio > 0 else 0

    # Interpretação e penalidade
    # IMPORTANTE: Ajustar limiares baseado na densidade do jogo
    # Densidade = k / N (proporção do volante que é sorteada)
    densidade = k / config.n_numbers

    penalidade = 0

    # Para jogos densos (Lotofácil: 15/25 = 60%), gaps pequenos e regulares são ESPERADOS
    # Para jogos esparsos (Mega: 6/60 = 10%), gaps regulares indicam padrão humano

    if densidade >= 0.5:
        # Jogo denso (Lotofácil, Lotomania): limiares mais tolerantes
        if ks_pvalue < 0.001 and cv_gaps < 0.1:
            conclusao = "⚠️ Gaps extremamente regulares"
            penalidade = 8
        elif cv_gaps < 0.15:
            conclusao = "ℹ️ Gaps regulares (comum em jogos densos)"
            penalidade = 0
        else:
            conclusao = "✅ Distribuição de gaps natural"
            penalidade = 0
    elif densidade >= 0.2:
        # Jogo intermediário (Quina: 5/80 = 6%)
        if ks_pvalue < 0.01 or cv_gaps < 0.15:
            conclusao = "⚠️ Gaps muito regulares"
            penalidade = 10
        elif cv_gaps < 0.3:
            conclusao = "ℹ️ Gaps com baixa variabilidade"
            penalidade = 3
        else:
            conclusao = "✅ Distribuição de gaps natural"
            penalidade = 0
    else:
        # Jogo esparso (Mega-Sena: 6/60 = 10%)
        if ks_pvalue < 0.01 or cv_gaps < 0.2:
            conclusao = "❌ Gaps muito regulares (padrão aritmético detectado)"
            penalidade = 15
        elif ks_pvalue < 0.05 or cv_gaps < 0.4:
            conclusao = "⚠️ Gaps com baixa variabilidade"
            penalidade = 8
        elif cv_gaps > 1.5:
            conclusao = "⚠️ Gaps muito irregulares (possível concentração)"
            penalidade = 5
        else:
            conclusao = "✅ Distribuição de gaps natural"
            penalidade = 0

    return {
        "gaps": gaps,
        "gap_medio": round(gap_medio, 2),
        "gap_std": round(gap_std, 2),
        "gap_esperado": round(gap_esperado, 2),
        "cv_gaps": round(cv_gaps, 3),
        "ks_statistic": round(ks_stat, 4),
        "ks_pvalue": round(ks_pvalue, 4),
        "conclusao": conclusao,
        "penalidade": penalidade,
    }


def calcular_order_statistics(numeros: list[int], config: GameConfig) -> dict:
    """
    Verifica se as posições dos números estão dentro do esperado.

    Para k números sorteados de N, a posição esperada do i-ésimo
    menor número (order statistic) é: E[X(i)] = i * (N+1) / (k+1)

    Parameters
    ----------
    numeros : list[int]
        Lista de números do jogo.
    config : GameConfig
        Configuração do jogo.

    Returns
    -------
    dict
        Resultado da análise das posições, com as seguintes chaves:

        - 'detalhes' (list[dict]): lista com a análise de cada posição,
          contendo as chaves 'posicao', 'numero', 'esperado',
          'desvio' e 'desvio_relativo'.
        - 'desvio_medio' (float): desvio médio relativo entre as posições
          observadas e as esperadas.
        - 'conclusao' (str): texto resumindo se as posições estão dentro
          ou fora do esperado.
        - 'penalidade' (int): penalidade numérica associada ao desvio
          médio observado.
    """
    numeros_sorted = sorted(numeros)
    k = len(numeros_sorted)
    N = config.n_numbers

    desvios = []
    detalhes = []

    for i, num in enumerate(numeros_sorted, start=1):
        # Valor esperado do i-ésimo order statistic
        esperado = i * (N + 1) / (k + 1)
        desvio = num - esperado
        desvio_rel = desvio / (N / k)  # Normalizado

        desvios.append(abs(desvio_rel))
        detalhes.append(
            {
                "posicao": i,
                "numero": num,
                "esperado": round(esperado, 1),
                "desvio": round(desvio, 1),
                "desvio_relativo": round(desvio_rel, 2),
            }
        )

    # Score baseado no desvio médio
    desvio_medio = np.mean(desvios)

    # Ajusta thresholds baseado na densidade do jogo
    # Jogos densos (ex: Lotofácil 15/25) naturalmente têm posições mais variáveis
    density = k / N
    if density > 0.5:
        # Alta densidade: thresholds mais relaxados
        threshold_alto = 2.5
        threshold_medio = 1.8
    elif density > 0.3:
        # Média densidade
        threshold_alto = 2.0
        threshold_medio = 1.3
    else:
        # Baixa densidade (Mega-Sena etc): thresholds originais
        threshold_alto = 1.5
        threshold_medio = 1.0

    if desvio_medio > threshold_alto:
        conclusao = "⚠️ Posições muito atípicas"
        penalidade = 8
    elif desvio_medio > threshold_medio:
        conclusao = "ℹ️ Algumas posições atípicas"
        penalidade = 3
    else:
        conclusao = "✅ Posições dentro do esperado"
        penalidade = 0

    return {
        "detalhes": detalhes,
        "desvio_medio": round(desvio_medio, 3),
        "conclusao": conclusao,
        "penalidade": penalidade,
    }


def detectar_motifs_gaps(numeros: list[int], config: GameConfig = None) -> dict:
    """
    Detecta padrões periódicos (motifs) nos gaps entre números.

    Identifica se há repetições como [a, b, a, b] ou [a, a, a].
    Esses padrões indicam escolha humana sistemática.

    IMPORTANTE: Para jogos densos (Lotofácil), gaps pequenos repetidos
    são ESPERADOS e não devem ser penalizados severamente.

    Parameters
    ----------
    numeros : list[int]
        Lista de números do jogo (será ordenada internamente).
    config : GameConfig, optional
        Configuração do jogo (para ajustar limiares por densidade).

    Returns
    -------
    dict
        - 'motif_detectado': bool
        - 'tipo_motif': descrição do padrão encontrado
        - 'gaps': lista de gaps
        - 'penalidade': penalidade sugerida
    """
    numeros_sorted = sorted(numeros)
    k = len(numeros_sorted)

    if k < 4:
        return {"motif_detectado": False, "penalidade": 0, "gaps": []}

    gaps = [numeros_sorted[i + 1] - numeros_sorted[i] for i in range(k - 1)]

    # Calcula densidade do jogo (se config disponível)
    if config:
        densidade = k / config.n_numbers
    else:
        densidade = 0.1  # Assume jogo esparso se não tiver config

    # Para jogos densos (Lotofácil), reduzir penalidades significativamente
    fator_densidade = 1.0 if densidade < 0.3 else (0.3 if densidade >= 0.5 else 0.5)

    # Padrão 1: Todos os gaps iguais (progressão aritmética)
    if len(set(gaps)) == 1:
        # Para Lotofácil com gaps de 1 ou 2, isso pode ser natural
        if densidade >= 0.5 and gaps[0] <= 2:
            return {
                "motif_detectado": False,
                "tipo_motif": None,
                "gaps": gaps,
                "penalidade": 0,
            }
        return {
            "motif_detectado": True,
            "tipo_motif": "Progressão aritmética (todos gaps iguais)",
            "gaps": gaps,
            "penalidade": int(20 * fator_densidade),
        }

    # Padrão 2: Alternância [a, b, a, b, ...]
    if k >= 5:
        alternante = True
        for i in range(len(gaps) - 2):
            if gaps[i] != gaps[i + 2]:
                alternante = False
                break

        if alternante and gaps[0] != gaps[1]:
            # Para Lotofácil, alternância de gaps pequenos é esperada
            if densidade >= 0.5 and max(gaps[0], gaps[1]) <= 3:
                return {
                    "motif_detectado": False,
                    "tipo_motif": None,
                    "gaps": gaps,
                    "penalidade": 0,
                }
            return {
                "motif_detectado": True,
                "tipo_motif": f"Alternância detectada [{gaps[0]}, {gaps[1]}, ...]",
                "gaps": gaps,
                "penalidade": int(15 * fator_densidade),
            }

    # Padrão 3: Repetição de subsequência
    for periodo in range(2, len(gaps) // 2 + 1):
        padrao = gaps[:periodo]
        repeticoes = 0
        for i in range(0, len(gaps) - periodo + 1, periodo):
            if gaps[i : i + periodo] == padrao:
                repeticoes += 1

        if repeticoes >= 2 and repeticoes * periodo >= len(gaps) * 0.7:
            # Para jogos densos, padrões de gaps pequenos são naturais
            if densidade >= 0.5 and max(padrao) <= 3:
                return {
                    "motif_detectado": False,
                    "tipo_motif": None,
                    "gaps": gaps,
                    "penalidade": 0,
                }
            return {
                "motif_detectado": True,
                "tipo_motif": f"Padrão repetitivo: {padrao}",
                "gaps": gaps,
                "penalidade": int(12 * fator_densidade),
            }

    return {
        "motif_detectado": False,
        "tipo_motif": None,
        "gaps": gaps,
        "penalidade": 0,
    }
