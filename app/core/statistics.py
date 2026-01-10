# app/core/statistics.py
import pandas as pd
import numpy as np
from scipy.stats import poisson, chisquare, kstest
from app.core.lottery import GameConfig


# ============================================
# CONSTANTES DE CONFIGURAÇÃO ESTATÍSTICA
# ============================================

# Pesos para cálculo do score composto
WEIGHT_FREQUENCY: float = 0.40
WEIGHT_GAP: float = 0.60

# Limiares de confiança para teste Chi²
CHI2_HIGH_CONFIDENCE: float = 0.05
CHI2_MEDIUM_CONFIDENCE: float = 0.01

# Limiares de coeficiente de variação
CV_EXCELLENT: float = 10.0
CV_GOOD: float = 20.0
CV_ACCEPTABLE: float = 30.0

# Epsilon para evitar divisão por zero
EPSILON: float = 1e-9


def compute_zscore(value: float, mean: float, std: float) -> float:
    """
    Calcula o Z-score (desvio padrão normalizado) de um valor.
    
    O Z-score indica quantos desvios-padrão um valor está da média.
    Usa EPSILON para evitar divisão por zero.
    
    Parameters
    ----------
    value : float
        Valor observado.
    mean : float
        Média da distribuição.
    std : float
        Desvio padrão da distribuição.
    
    Returns
    -------
    float
        Z-score calculado.
    
    Examples
    --------
    >>> compute_zscore(15, 10, 2)
    2.5
    >>> compute_zscore(10, 10, 0)  # std=0, usa EPSILON
    0.0
    """
    return (value - mean) / (std + EPSILON)


def _flatten_draws(df: pd.DataFrame, config: GameConfig) -> np.ndarray:
    return df[config.draw_cols].values.flatten()


def get_numeros_quentes_frios(df: pd.DataFrame, config: GameConfig) -> pd.Series:
    """
    Retorna contagem de frequência de todos os números.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    pd.Series
        Série com frequência de cada número, ordenada decrescentemente.
    """
    if df.empty:
        return pd.Series()
    todos = _flatten_draws(df, config)
    return pd.Series(todos).value_counts().sort_values(ascending=False)


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


def get_historico_jogos(df: pd.DataFrame, config: GameConfig) -> set[tuple]:
    """
    SET de jogos já sorteados para lookup O(1).
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    set[tuple]
        Conjunto de tuplas ordenadas representando cada jogo sorteado.
    """
    if df.empty:
        return set()
    jogos = df[config.draw_cols].values
    return set(tuple(sorted(jogo)) for jogo in jogos)


def verificar_historico(numeros: list[int], df: pd.DataFrame, config: GameConfig, alvos: list[int] | None = None) -> dict[int, list[str]]:
    """
    Verifica quantos acertos o jogo teria com sorteios históricos.
    
    Parameters
    ----------
    numeros : list[int]
        Lista de números do jogo a verificar.
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    alvos : list[int] | None, optional
        Lista de quantidades de acertos a verificar. 
        Se None, usa [k, k-1, k-2] onde k é o tamanho do sorteio.
    
    Returns
    -------
    dict[int, list[str]]
        Dicionário mapeando quantidade de acertos para lista de concursos.
    """
    meus = set(numeros)
    if alvos is None:
        alvos = [config.k, config.k - 1, config.k - 2]

    res = {a: [] for a in alvos}
    for idx, row in df.iterrows():
        sorteio = set(row[config.draw_cols].values)
        acertos = len(meus.intersection(sorteio))
        if acertos in res:
            res[acertos].append(f"Conc. {idx}")
    return res


def get_reis_da_sequencia(df: pd.DataFrame, config: GameConfig) -> list[int]:
    """
    Identifica números que mais formam pares consecutivos.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    list[int]
        Lista de números que mais aparecem em sequências consecutivas.
    """
    if df.empty:
        return []

    todos_pares = []
    for _, row in df.iterrows():
        sorteio = sorted(row[config.draw_cols].values)
        for i in range(len(sorteio) - 1):
            if sorteio[i + 1] == sorteio[i] + 1:
                todos_pares.append((sorteio[i], sorteio[i + 1]))

    if not todos_pares:
        return []

    freq_pares = pd.Series(todos_pares).value_counts().head(15)
    numeros = set()
    for par in freq_pares.index:
        numeros.add(par[0])
        numeros.add(par[1])

    return sorted(list(numeros))


def calcular_atrasos(df: pd.DataFrame, config: GameConfig) -> pd.Series:
    """
    Adiciona normalização por tamanho da base.
    Gap relativo = Gap absoluto / Total de jogos.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    pd.Series
        Série com atraso de cada número desde o último sorteio,
        ordenada decrescentemente.
    """
    if df.empty:
        return pd.Series()

    ultimo_concurso = df.index.max()
    total_concursos = len(df)

    stacked = df[config.draw_cols].stack().reset_index()
    stacked.columns = ["Concurso", "Col", "Numero"]
    ultima_aparicao = stacked.groupby("Numero")["Concurso"].max()

    atrasos = {}
    for n in range(1, config.n_numbers + 1):
        if n in ultima_aparicao:
            gap_absoluto = ultimo_concurso - ultima_aparicao[n]
            atrasos[n] = gap_absoluto
        else:
            atrasos[n] = ultimo_concurso

    return pd.Series(atrasos).sort_values(ascending=False)


def get_tabela_inteligencia(df: pd.DataFrame, config: GameConfig) -> pd.DataFrame:
    """
    Calcula tabela de inteligência com frequências, atrasos e pesos.
    
    Calcula Z-scores para frequência e atraso, peso composto normalizado
    e percentis para análise estatística dos números.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    
    Returns
    -------
    pd.DataFrame
        DataFrame com colunas:
        - Frequencia: contagem de aparições
        - Atraso: sorteios desde última aparição
        - Z_Freq: Z-score da frequência
        - Z_Gap: Z-score do atraso
        - Peso_Composto: score combinado
        - Peso_Geracao: peso normalizado para geração
        - Percentil_Freq: percentil da frequência
        - Percentil_Gap: percentil do atraso
    """
    if df.empty:
        return pd.DataFrame()

    freq = get_numeros_quentes_frios(df, config).sort_index()
    atrasos = calcular_atrasos(df, config).sort_index()

    df_stats = pd.DataFrame(index=range(1, config.n_numbers + 1))
    df_stats["Frequencia"] = freq
    df_stats["Atraso"] = atrasos
    df_stats = df_stats.fillna(0)

    # 1. Z-Scores
    mu_freq = df_stats["Frequencia"].mean()
    sigma_freq = df_stats["Frequencia"].std()
    df_stats["Z_Freq"] = compute_zscore(df_stats["Frequencia"], mu_freq, sigma_freq)

    mu_gap = df_stats["Atraso"].mean()
    sigma_gap = df_stats["Atraso"].std()
    df_stats["Z_Gap"] = compute_zscore(df_stats["Atraso"], mu_gap, sigma_gap)

    # 2. Peso Composto
    df_stats["Peso_Composto"] = df_stats["Z_Freq"] * WEIGHT_FREQUENCY + df_stats["Z_Gap"] * WEIGHT_GAP

    # 3. Normalização
    peso_min = df_stats["Peso_Composto"].min()
    peso_max = df_stats["Peso_Composto"].max()
    df_stats["Peso_Geracao"] = (
        (df_stats["Peso_Composto"] - peso_min) / (peso_max - peso_min + EPSILON)
    ) + 0.01

    # 4. Métricas adicionais
    df_stats["Percentil_Freq"] = df_stats["Frequencia"].rank(pct=True)
    df_stats["Percentil_Gap"] = df_stats["Atraso"].rank(pct=True)

    return df_stats


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
