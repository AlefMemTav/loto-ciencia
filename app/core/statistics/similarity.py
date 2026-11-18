# app/core/statistics/similarity.py
"""
Análises de similaridade e regressão à média para sorteios de loteria.

Este módulo contém funções para análise de distância de Hamming,
distribuição de quadrantes e regressão à média.
"""

import numpy as np
import pandas as pd
from app.core.lottery import GameConfig
from app.core.statistics.basic import (
    build_draws_binary_matrix,
    calcular_atrasos,
    compute_zscore,
    EPSILON,
)
from app.core.statistics.constants import (
    ZSCORE_VERY_RARE,
    PENALTY_SCALE_FACTOR,
    SCORE_CONVERSION_FACTOR,
    QUADRANT_CONCENTRATION_THRESHOLD,
    QUADRANT_PVALUE_THRESHOLD,
)


# ============================================
# DISTÂNCIA DE HAMMING
# ============================================


def distancia_hamming(jogo1: list[int], jogo2: list[int]) -> int:
    """
    Conta quantos números são DIFERENTES entre dois jogos.

    Mede ``max(len(set1), len(set2)) - len(set1 & set2)`` (= ``k - |A ∩ B|``
    quando ambos têm tamanho ``k``), alinhado à definição de número de trocas
    necessárias e à similaridade ``1 - dist / k``.

    Parameters
    ----------
    jogo1 : list[int]
        Primeiro jogo.
    jogo2 : list[int]
        Segundo jogo.

    Returns
    -------
    int
        Número de elementos diferentes entre os dois jogos.

    Examples
    --------
    >>> distancia_hamming([1, 2, 3, 4, 5, 6], [1, 2, 3, 7, 8, 9])
    3
    """
    set1 = set(jogo1)
    set2 = set(jogo2)
    return max(len(set1), len(set2)) - len(set1 & set2)


def calcular_distancia_minima_historico(
    jogo: list[int],
    df: pd.DataFrame,
    config: GameConfig,
    top_n: int | None = None,
    draws_bin: np.ndarray | None = None,
) -> tuple[int, float]:
    """
    Calcula a menor distância de Hamming (em dezenas distintas) contra o histórico.

    Parameters
    ----------
    jogo : list[int]
        Lista de números do jogo a verificar.
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    top_n : int | None, optional
        Quantidade de sorteios mais recentes a verificar (default: ``None`` = todo o histórico).
    draws_bin : np.ndarray | None, optional
        Matriz binária pré-computada ``(T, N)`` via ``build_draws_binary_matrix``.

    Returns
    -------
    tuple[int, float]
        Tupla ``(distancia_minima, similaridade_maxima)`` onde:
        - ``distancia_minima``: ``k - max_acertos``
        - ``similaridade_maxima``: ``max(0.0, 1 - (distancia_minima / tamanho_jogo))``
    """
    if config.bet_size != config.k:
        return (config.bet_size, 0.0)

    if draws_bin is None:
        if df is None or df.empty:
            return (config.bet_size, 0.0)
        draws_bin, _ = build_draws_binary_matrix(df, config)

    if len(draws_bin) == 0:
        return (config.bet_size, 0.0)

    if top_n is not None:
        if top_n <= 0:
            return (config.bet_size, 0.0)
        matrix = draws_bin[-int(top_n) :]
    else:
        matrix = draws_bin

    n_num = int(config.n_numbers)
    valid_cols = np.array(
        sorted({int(x) - 1 for x in jogo if 1 <= int(x) <= n_num}),
        dtype=np.int64,
    )
    if len(valid_cols) == 0 or len(matrix) == 0:
        return (config.bet_size, 0.0)

    acertos = matrix[:, valid_cols].sum(axis=1, dtype=np.int16)
    max_acertos = int(acertos.max())
    min_dist = max(0, int(max(len(valid_cols), config.k) - max_acertos))
    max_sim = max(0.0, 1.0 - (min_dist / config.bet_size))

    return (min_dist, max_sim)


def penalizar_por_similaridade(
    report: dict,
    numeros: list[int],
    df: pd.DataFrame,
    config: GameConfig,
    draws_bin: np.ndarray | None = None,
) -> None:
    """
    Adiciona métricas e penalidades calibradas baseadas em distância de Hamming.

    Varre todo o histórico (``hamming_historico_min``) e a janela recente dos últimos
    100 sorteios (``hamming_recente_100``), aplicando penalidades calibradas pela
    raridade hipergeométrica (densidade e tamanho de sorteio ``k``).
    """
    # Só aplica se o jogo tem mesmo tamanho do sorteio
    if config.bet_size != config.k:
        report["metricas"]["hamming_min"] = "N/A"
        report["metricas"]["hamming_historico_min"] = "N/A"
        report["metricas"]["hamming_recente_100"] = "N/A"
        report["metricas"]["similaridade_max"] = "N/A"
        return

    if draws_bin is None and df is not None and not df.empty:
        draws_bin, _ = build_draws_binary_matrix(df, config)

    if draws_bin is None or len(draws_bin) == 0:
        report["metricas"]["hamming_min"] = config.bet_size
        report["metricas"]["hamming_historico_min"] = config.bet_size
        report["metricas"]["hamming_recente_100"] = config.bet_size
        report["metricas"]["acertos_max_historico"] = 0
        report["metricas"]["acertos_max_recente_100"] = 0
        report["metricas"]["similaridade_max"] = 0.0
        report["metricas"]["similaridade_recente_100"] = 0.0
        return

    min_dist_full, max_sim_full = calcular_distancia_minima_historico(
        numeros, df, config, top_n=None, draws_bin=draws_bin
    )
    min_dist_100, max_sim_100 = calcular_distancia_minima_historico(
        numeros, df, config, top_n=100, draws_bin=draws_bin
    )

    k = config.bet_size
    max_hits_full = max(0, k - min_dist_full)
    max_hits_100 = max(0, k - min_dist_100)

    report["metricas"]["hamming_min"] = min_dist_full
    report["metricas"]["hamming_historico_min"] = min_dist_full
    report["metricas"]["hamming_recente_100"] = min_dist_100
    report["metricas"]["acertos_max_historico"] = max_hits_full
    report["metricas"]["acertos_max_recente_100"] = max_hits_100
    report["metricas"]["similaridade_max"] = round(max_sim_full, 3)
    report["metricas"]["similaridade_recente_100"] = round(max_sim_100, 3)

    if min_dist_full == 0:
        if len(numeros) == config.k:
            report["ja_saiu"] = True
        return

    if min_dist_100 == 1:
        if config.is_dense:
            report["score"] -= 12
            report["msgs"].append(
                f"⚠️ Quase idêntico a um dos últimos 100 sorteios ({max_hits_100}/{k} acertos, Hamming={min_dist_100})"
            )
            if report.get("risco_divisao") == "Baixo":
                report["risco_divisao"] = "Médio"
        else:
            report["score"] -= 25
            report["msgs"].append(
                f"🚨 Quase idêntico a sorteio recente nos últimos 100 concursos ({max_hits_100}/{k} acertos; 1 número diferente)"
            )
            report["risco_divisao"] = "ALTO"
    elif min_dist_full == 1:
        if config.is_dense:
            report["msgs"].append(
                f"ℹ️ Já atingiu {max_hits_full}/{k} em concurso antigo (Hamming histórico={min_dist_full}, últimos 100={min_dist_100})"
            )
        elif k <= 5:
            report["score"] -= 5
            report["msgs"].append(
                f"ℹ️ Quase idêntico ({max_hits_full}/{k}) a concurso antigo fora dos últimos 100 (Hamming histórico={min_dist_full}, recente={min_dist_100})"
            )
        else:
            report["score"] -= 8
            report["msgs"].append(
                f"⚠️ Quase idêntico ({max_hits_full}/{k}) a concurso antigo no histórico (Hamming histórico={min_dist_full}, últimos 100={min_dist_100})"
            )
    elif min_dist_100 == 2:
        if config.is_dense:
            report["msgs"].append(
                f"ℹ️ Similaridade natural nos últimos 100 concursos ({max_hits_100}/{k} acertos, Hamming={min_dist_100})"
            )
        elif k <= 5:
            report["score"] -= 3
            report["msgs"].append(
                f"ℹ️ Similar a sorteio recente ({max_hits_100}/{k} nos últimos 100; Hamming={min_dist_100})"
            )
        else:
            report["score"] -= 8
            report["msgs"].append(
                f"⚠️ Similar a sorteio recente nos últimos 100 concursos ({max_hits_100}/{k}; Hamming={min_dist_100})"
            )
            if report.get("risco_divisao") == "Baixo":
                report["risco_divisao"] = "Médio"
    elif (not config.is_dense and min_dist_full >= 3) or min_dist_100 >= 4:
        report["msgs"].append(
            f"✅ Boa unicidade frente ao histórico (Hamming histórico={min_dist_full}, últimos 100={min_dist_100})"
        )
    else:
        report["msgs"].append(
            f"ℹ️ Similaridade dentro do esperado (Hamming histórico={min_dist_full}, últimos 100={min_dist_100})"
        )



# ============================================
# ANÁLISE DE QUADRANTES
# ============================================


def calcular_distribuicao_quadrantes(
    df: pd.DataFrame, config: GameConfig
) -> dict[int, dict[str, float]]:
    """
    Calcula distribuição empírica de números por quadrante.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.

    Returns
    -------
    dict[int, dict[str, float]]
        Dicionário mapeando quadrante (1-4) para estatísticas:
        - mean: média de números por quadrante
        - std: desvio padrão
        - p5: percentil 5%
        - p95: percentil 95%
    """
    if df.empty:
        return {}

    historico_sets = [set(row) for row in df[config.draw_cols].values]

    contagens_por_quad = {1: [], 2: [], 3: [], 4: []}

    for sorteio in historico_sets:
        for q in range(1, 5):
            nums_quadrante = set(config.layout.quadrant_numbers(q))
            qtd = len(sorteio & nums_quadrante)
            contagens_por_quad[q].append(qtd)

    # Estatísticas por quadrante
    stats = {}
    for q, contagens in contagens_por_quad.items():
        arr = np.array(contagens)
        stats[q] = {
            "mean": arr.mean(),
            "std": arr.std(),
            "p5": np.percentile(arr, 5),
            "p95": np.percentile(arr, 95),
        }

    return stats


def avaliar_quadrantes_estatistico(
    numeros: list[int], config: GameConfig, stats_quadrantes: dict
) -> dict:
    """
    Avalia distribuição de quadrantes usando estatística.

    Parameters
    ----------
    numeros : list[int]
        Lista de números do jogo a avaliar.
    config : GameConfig
        Configuração do jogo.
    stats_quadrantes : dict
        Estatísticas dos quadrantes do histórico.

    Returns
    -------
    dict
        Dicionário com:
        - score_quadrantes: score (0-100)
        - detalhes: análise por quadrante (Q1-Q4) com presentes, esperado, z_score e categoria
        - penalidade: penalidade total
        - alerta: mensagem se houver concentração extrema (opcional)
    """
    if not stats_quadrantes:
        return {"score_quadrantes": 100, "detalhes": {}, "penalidade": 0.0}

    jogo = set(numeros)
    resultados = {}
    penalidade = 0.0

    for q in range(1, 5):
        nums_q = set(config.layout.quadrant_numbers(q))
        presentes = len(jogo & nums_q)

        stat = stats_quadrantes[q]

        # Ajuste para jogos grandes (Lotomania): variância hipergeométrica exata
        # Var(m) / Var(k) = (m / k) * (N - m) / (N - k)
        qtd_jogada = len(numeros)
        if config.k != qtd_jogada and config.k > 0:
            fator = qtd_jogada / config.k
            mean_ajustada = stat["mean"] * fator
            denom = max(1, config.n_numbers - config.k)
            fator_var = fator * max(0.0, (config.n_numbers - qtd_jogada) / denom)
            std_ajustada = stat["std"] * np.sqrt(fator_var)
        else:
            mean_ajustada = stat["mean"]
            std_ajustada = stat["std"]

        z = compute_zscore(presentes, mean_ajustada, std_ajustada)

        # Evento extremo: fora do intervalo 90%
        if abs(z) > QUADRANT_PVALUE_THRESHOLD:  # p < 0.10
            penalidade += abs(z) * PENALTY_SCALE_FACTOR
            categoria = "Atípico"
        else:
            categoria = "Normal"

        resultados[f"Q{q}"] = {
            "presentes": presentes,
            "esperado": round(float(mean_ajustada), 2),
            "z_score": round(float(z), 2),
            "categoria": categoria,
        }

    # Detecta concentração extrema
    max_concentracao = max(r["presentes"] for r in resultados.values())
    if max_concentracao >= len(numeros) * QUADRANT_CONCENTRATION_THRESHOLD:
        penalidade += ZSCORE_VERY_RARE
        resultados["alerta"] = f"⚠️ {max_concentracao} números em 1 quadrante"

    score = max(0, min(100, int(100 - penalidade * SCORE_CONVERSION_FACTOR)))

    return {
        "score_quadrantes": score,
        "detalhes": resultados,
        "penalidade": round(float(penalidade), 2),
    }


# ============================================
# REGRESSÃO À MÉDIA
# ============================================


def calcular_taxa_regressao(
    df: pd.DataFrame, config: GameConfig, janela: int = 100
) -> dict | None:
    """
    Mede se números atrasados realmente tendem a sair.

    Valida se a "regressão à média" funciona nos dados, calculando
    correlação entre atrasos passados e frequência futura.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    janela : int, optional
        Número de sorteios futuros a analisar (default: 100).

    Returns
    -------
    dict | None
        Dicionário com:
        - correlacao: correlação de Spearman entre atraso e frequência futura
        - p_value: significância da correlação
        - taxa_retorno: proporção de números atrasados que retornaram
        - interpretacao: classificação da força da regressão
        Retorna None se não houver dados suficientes ou erro na importação.
    """
    if df.empty or len(df) < janela + 10:
        return None

    # Pega um ponto no passado
    df_analise = df.iloc[:-janela]
    df_futuro = df.iloc[-janela:]

    atrasos_passado = calcular_atrasos(df_analise, config)

    # Top 20% mais atrasados
    top_atrasados = set(atrasos_passado.nlargest(int(config.n_numbers * 0.2)).index)

    # Quantos saíram nos próximos 'janela' sorteios? (vetorizado)
    draws_futuro = df_futuro[config.draw_cols].to_numpy(dtype=int)
    n_num = int(config.n_numbers)
    B_fut = np.zeros((draws_futuro.shape[0], n_num), dtype=np.int64)
    valid = (draws_futuro >= 1) & (draws_futuro <= n_num)
    if np.all(valid):
        B_fut[np.arange(draws_futuro.shape[0])[:, None], draws_futuro - 1] = 1
    else:
        for r_i, row in enumerate(draws_futuro):
            vals = row[(row >= 1) & (row <= n_num)]
            B_fut[r_i, vals - 1] = 1

    counts_fut = B_fut.sum(axis=0)
    saidas = {int(i) + 1 for i in np.flatnonzero(counts_fut > 0)}

    retornaram = len(top_atrasados & saidas)
    taxa_retorno = retornaram / len(top_atrasados) if top_atrasados else 0

    # Correlação entre atraso e frequência futura
    try:
        from scipy.stats import spearmanr

        freq_futura = counts_fut.tolist()

        atrasos_array = [
            atrasos_passado.get(i, 0) for i in range(1, config.n_numbers + 1)
        ]
        corr, p_value = spearmanr(atrasos_array, freq_futura)

        return {
            "correlacao": round(corr, 3),
            "p_value": round(p_value, 4),
            "taxa_retorno": round(taxa_retorno, 3),
            "interpretacao": (
                "Regressão forte"
                if corr > 0.3
                else "Regressão fraca" if corr > 0.1 else "Sem evidência clara"
            ),
        }
    except ImportError:
        return None
    except (ValueError, RuntimeError) as e:
        # Catch specific statistical computation errors
        return None


# ============================================
# ANÁLISE DE GAPS GEOMÉTRICOS
# ============================================


def _chi2_geometric_gof(
    gaps_array: np.ndarray,
    p_teorico: float,
    min_expected: float = 5.0,
) -> tuple[float, float]:
    """Teste Qui-Quadrado agrupado de aderência à distribuição Geométrica(p)."""
    from scipy.stats import chi2, geom

    n_gaps = len(gaps_array)
    if n_gaps < int(min_expected * 2):
        return 0.0, 1.0

    max_gap = int(np.max(gaps_array))
    obs_counts = np.bincount(gaps_array, minlength=max_gap + 2)[1:]

    grouped_obs: list[float] = []
    grouped_exp: list[float] = []
    acc_obs = 0.0
    acc_prob = 0.0
    covered_prob = 0.0

    for g in range(1, max_gap + 1):
        prob_g = float(geom.pmf(g, p_teorico))
        acc_obs += float(obs_counts[g - 1])
        acc_prob += prob_g
        covered_prob += prob_g
        if acc_prob * n_gaps >= min_expected:
            grouped_obs.append(acc_obs)
            grouped_exp.append(acc_prob * n_gaps)
            acc_obs = 0.0
            acc_prob = 0.0

    tail_prob = max(0.0, 1.0 - covered_prob) + acc_prob
    tail_exp = tail_prob * n_gaps
    if grouped_exp and tail_exp < min_expected:
        grouped_obs[-1] += acc_obs
        grouped_exp[-1] += tail_exp
    elif tail_exp > 0:
        grouped_obs.append(acc_obs)
        grouped_exp.append(tail_exp)

    if len(grouped_exp) < 2:
        return 0.0, 1.0

    obs_arr = np.asarray(grouped_obs, dtype=float)
    exp_arr = np.asarray(grouped_exp, dtype=float)
    exp_arr = exp_arr * (obs_arr.sum() / max(1e-12, exp_arr.sum()))
    chi2_stat = float(np.sum(((obs_arr - exp_arr) ** 2) / np.maximum(exp_arr, 1e-12)))
    dof = max(1, len(exp_arr) - 1)
    chi2_pvalue = float(np.clip(chi2.sf(chi2_stat, dof), 0.0, 1.0))
    return chi2_stat, chi2_pvalue


def analisar_gaps_geometricos(
    df: pd.DataFrame,
    config: GameConfig,
    numero: int
) -> dict:
    """
    Analisa se os gaps de um número seguem distribuição geométrica.
    
    Para um sorteio aleatório, a probabilidade de um número específico
    aparecer é p = k/n. Os gaps entre aparições devem seguir Geom(p).
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    numero : int
        Número a ser analisado (1 a n_numbers).
    
    Returns
    -------
    dict
        Estatísticas do teste de aderência à distribuição geométrica:
        - 'gaps': lista de gaps observados
        - 'media_gap': média dos gaps
        - 'media_teorica': média teórica (1/p)
        - 'ks_statistic': estatística supremum discreta |F_n(g) - F_Geom(g)|
        - 'ks_pvalue': p-value de aderência discreta
        - 'chi2_statistic': estatística Qui-Quadrado agrupada
        - 'chi2_pvalue': p-value Qui-Quadrado agrupado
        - 'conclusao': interpretação do resultado
    """
    if df.empty or numero < 1 or numero > config.n_numbers:
        return None

    draw_vals = df[config.draw_cols].to_numpy()
    aparicoes = np.flatnonzero((draw_vals == numero).any(axis=1))

    if len(aparicoes) < 2:
        return {
            'erro': f'Número {numero} apareceu menos de 2 vezes',
            'aparicoes': int(len(aparicoes))
        }

    # Calcula gaps entre aparições consecutivas
    gaps_array = np.diff(aparicoes).astype(int)
    gaps = gaps_array.tolist()
    n_gaps = len(gaps_array)

    # Probabilidade teórica de aparecer em um sorteio
    p_teorico = config.k / config.n_numbers

    # Média teórica do gap (distribuição geométrica)
    media_teorica = 1 / p_teorico

    try:
        from scipy.stats import geom, kstwo

        max_gap = int(np.max(gaps_array))
        support = np.arange(1, max_gap + 1, dtype=int)
        counts = np.bincount(gaps_array, minlength=max_gap + 1)[1:]
        emp_cdf = np.cumsum(counts) / float(n_gaps)
        theo_cdf = geom.cdf(support, p_teorico)

        # Estatística KS discreta: sup_{g >= 1} |F_n(g) - F_Geom(g)|
        # (evita o falso positivo de scipy.stats.kstest em saltos discretos F_n(g^-))
        ks_stat = float(np.max(np.abs(emp_cdf - theo_cdf)))
        ks_pvalue = float(np.clip(kstwo.sf(ks_stat, n_gaps), 0.0, 1.0))
        chi2_stat, chi2_pvalue = _chi2_geometric_gof(gaps_array, p_teorico)

        # Interpretação
        if ks_pvalue > 0.05:
            conclusao = "✅ Gaps seguem distribuição geométrica (aleatório)"
        elif ks_pvalue > 0.01:
            conclusao = "⚠️ Possível desvio da aleatoriedade"
        else:
            conclusao = "🚨 Gaps não seguem distribuição geométrica"

        return {
            'numero': numero,
            'gaps': gaps,
            'n_gaps': n_gaps,
            'media_gap': float(np.mean(gaps_array)),
            'std_gap': float(np.std(gaps_array)),
            'media_teorica': round(media_teorica, 2),
            'p_teorico': round(p_teorico, 4),
            'ks_statistic': round(ks_stat, 4),
            'ks_pvalue': round(ks_pvalue, 4),
            'chi2_statistic': round(chi2_stat, 4),
            'chi2_pvalue': round(chi2_pvalue, 4),
            'conclusao': conclusao,
        }
    except ImportError:
        return None


def analisar_gaps_todos_numeros(
    df: pd.DataFrame,
    config: GameConfig
) -> dict:
    """
    Analisa gaps geométricos para todos os números do jogo.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico.
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    dict
        Resumo com análise de todos os números e estatísticas agregadas.
    """
    resultados = {}
    numeros_anomalos = []
    
    for num in range(1, config.n_numbers + 1):
        resultado = analisar_gaps_geometricos(df, config, num)
        if resultado and 'erro' not in resultado:
            resultados[num] = resultado
            if resultado['ks_pvalue'] < 0.05:
                numeros_anomalos.append(num)
    
    return {
        'resultados_por_numero': resultados,
        'numeros_anomalos': numeros_anomalos,
        'total_anomalos': len(numeros_anomalos),
        'percentual_anomalos': round(len(numeros_anomalos) / config.n_numbers * 100, 2),
    }
