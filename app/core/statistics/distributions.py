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

# Cache determinístico do modelo nulo discreto para CV de gaps por (N, k)
_GAPS_CV_NULL_CACHE: dict[tuple[int, int], np.ndarray] = {}


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

    n_sorteios = len(df)
    n_univ = int(config.n_numbers)
    k_draw = int(config.k)
    candidatos_digitos = []

    for digito in range(10):
        n_d = int(contagem_teorica.get(digito, 0))
        if n_d <= 0:
            continue
        prob_teorica = n_d / float(n_univ)
        esperado = total_bolas_sorteadas * prob_teorica
        observado = int((finais == digito).sum())

        # Variância exata sob T sorteios independentes hipergeométricos (k sem reposição em N):
        # Var(X_t) = k * (n_d/N) * (1 - n_d/N) * (N - k) / (N - 1)
        var_por_sorteio = (
            k_draw
            * prob_teorica
            * (1.0 - prob_teorica)
            * max(0, n_univ - k_draw)
            / float(max(1, n_univ - 1))
        )
        std_total = float(np.sqrt(max(1e-9, n_sorteios * var_por_sorteio)))
        z_val = (observado - esperado) / std_total
        from scipy.stats import norm as _norm

        p_raw = float(2.0 * _norm.sf(abs(z_val)))
        candidatos_digitos.append(
            (digito, observado, esperado, prob_teorica, p_raw)
        )

    # Correção Holm-Bonferroni para os múltiplos testes simultâneos nos 10 dígitos finais
    m_testes = len(candidatos_digitos)
    ordenados = sorted(candidatos_digitos, key=lambda item: item[4])
    p_holm_map: dict[int, float] = {}
    max_adj = 0.0
    for rank, (digito, _, _, _, p_raw) in enumerate(ordenados):
        adj = min(1.0, p_raw * (m_testes - rank))
        max_adj = max(max_adj, adj)
        p_holm_map[digito] = max_adj

    for digito, observado, esperado, prob_teorica, p_raw in candidatos_digitos:
        p_adj = p_holm_map[digito]
        if p_adj < alpha:
            tipo = "Déficit" if observado < esperado else "Excesso"
            resultado.append(
                {
                    "digito": digito,
                    "observado": observado,
                    "esperado": round(esperado, 2),
                    "desvio": round(observado - esperado, 2),
                    "tipo": tipo,
                    "p_value": round(p_adj, 5),
                    "p_value_bruto": round(p_raw, 5),
                    "interpretacao": f"Desvio ({tipo}, Holm-corrigido) - Esperado: {prob_teorica:.1%}",
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
    if total_bolas == 0:
        return None

    n_num = config.n_numbers
    f_esp = np.full(n_num, total_bolas / n_num, dtype=float)

    chi2_raw, p_chi_raw = chisquare(f_obs, f_exp=f_esp)
    if 0 < config.k < n_num and n_num > 1:
        from scipy.stats import chi2 as chi2_dist

        fator_hiper = (n_num - 1) / (n_num - config.k)
        chi2_stat = float(chi2_raw * fator_hiper)
        p_chi = float(chi2_dist.sf(chi2_stat, df=n_num - 1))
        fator_var_ks = (n_num - config.k) / (n_num - 1)
    else:
        chi2_stat = float(chi2_raw)
        p_chi = float(p_chi_raw)
        fator_var_ks = 1.0

    # KS discreto para distribuição uniforme em {1..n_numbers} sem reposição
    cdf_obs = np.cumsum(f_obs) / total_bolas
    cdf_esp = np.arange(1, n_num + 1, dtype=float) / n_num
    ks_stat = float(np.max(np.abs(cdf_obs - cdf_esp)))

    if n_num > 1 and fator_var_ks > 0:
        rng = np.random.default_rng(42)
        n_sim = 2000
        sim_counts = rng.multinomial(total_bolas, np.full(n_num, 1.0 / n_num), size=n_sim)
        sim_cdf = np.cumsum(sim_counts, axis=1) / total_bolas
        ks_null = np.max(np.abs(sim_cdf - cdf_esp), axis=1) * np.sqrt(fator_var_ks)
        p_ks = float((np.sum(ks_null >= ks_stat) + 1) / (n_sim + 1))
    else:
        p_ks = 1.0

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

    # Distribuição nula discreta (cached por (N, k)) para calibrar `cv_gaps` e distância empírica
    # sem depender de p-valor KS contínuo inválido (Lilliefors) sobre 4-5 inteiros discretos.
    gap_medio = float(np.mean(gaps))
    gap_std = float(np.std(gaps))
    gap_esperado = (config.n_numbers - 1) / (k - 1)
    cv_gaps = (gap_std / gap_medio) if gap_medio > 0 else 0.0

    # Estatística empírica de afastamento frente aos quantis discretos esperados (geométrica discreta)
    p_geom = min(0.99, max(1e-4, k / float(config.n_numbers)))
    gaps_sorted = np.sort(np.asarray(gaps, dtype=float))
    cdf_teorica = 1.0 - (1.0 - p_geom) ** gaps_sorted
    ecdf_hi = np.arange(1, len(gaps_sorted) + 1) / float(len(gaps_sorted))
    ecdf_lo = np.arange(0, len(gaps_sorted)) / float(len(gaps_sorted))
    ks_stat = (
        1.0
        if gap_std == 0
        else float(
            max(
                np.max(np.abs(ecdf_hi - cdf_teorica)),
                np.max(np.abs(cdf_teorica - ecdf_lo)),
            )
        )
    )

    # Calibração discreta via modelo nulo exato para (N, k) (cached em memória)
    cache_key = (int(config.n_numbers), int(k))
    null_cvs = _GAPS_CV_NULL_CACHE.get(cache_key)
    if null_cvs is None:
        rng_null = np.random.default_rng(9100 + config.n_numbers * 37 + k)
        n_sim = 1500
        pool = np.arange(1, config.n_numbers + 1)
        keys = rng_null.random((n_sim, config.n_numbers))
        amostras = np.sort(pool[np.argpartition(keys, k - 1, axis=1)[:, :k]], axis=1)
        d_sim = np.diff(amostras, axis=1).astype(float)
        m_sim = d_sim.mean(axis=1)
        s_sim = d_sim.std(axis=1)
        null_cvs = np.sort(np.divide(s_sim, m_sim, out=np.zeros_like(s_sim), where=m_sim > 0))
        _GAPS_CV_NULL_CACHE[cache_key] = null_cvs

    # p-valor bilateral discreto (baseado na cauda de regularidade / irregularidade no nulo exato)
    if gap_std == 0:
        ks_pvalue = 0.0
    else:
        p_low = float((np.searchsorted(null_cvs, cv_gaps, side="right") + 1) / (len(null_cvs) + 1))
        p_high = float((len(null_cvs) - np.searchsorted(null_cvs, cv_gaps, side="left") + 1) / (len(null_cvs) + 1))
        ks_pvalue = float(min(1.0, 2.0 * min(p_low, p_high)))

    densidade = k / config.n_numbers
    penalidade = 0

    if densidade >= 0.5:
        # Jogo denso (Lotofácil: 15/25 = 60%, Lotomania: 50/100 = 50%)
        if gap_std == 0 or (ks_pvalue < 0.005 and cv_gaps < 0.15):
            conclusao = "⚠️ Gaps extremamente regulares"
            penalidade = 8
        elif cv_gaps < 0.2:
            conclusao = "ℹ️ Gaps regulares (comum em jogos densos)"
            penalidade = 0
        else:
            conclusao = "✅ Distribuição de gaps natural"
            penalidade = 0
    elif densidade >= 0.2:
        # Jogos de densidade intermediária (20%–50%)
        if gap_std == 0 or cv_gaps < 0.15 or ks_pvalue < 0.01:
            conclusao = "⚠️ Gaps muito regulares"
            penalidade = 10
        elif cv_gaps < 0.3:
            conclusao = "ℹ️ Gaps com baixa variabilidade"
            penalidade = 3
        else:
            conclusao = "✅ Distribuição de gaps natural"
            penalidade = 0
    else:
        # Jogos esparsos (Mega-Sena: 6/60 = 10%, Quina: 5/80 = 6,25%)
        if gap_std == 0 or cv_gaps < 0.2:
            conclusao = "❌ Gaps muito regulares (padrão aritmético detectado)"
            penalidade = 15
        elif cv_gaps < 0.35 or ks_pvalue < 0.02:
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
