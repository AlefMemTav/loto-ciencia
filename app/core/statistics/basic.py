# app/core/statistics/basic.py
"""
Funções básicas de estatística para análise de sorteios de loteria.

Este módulo contém funções para cálculo de frequências, atrasos,
tabela de inteligência e outras análises básicas.
"""

import pandas as pd
import numpy as np
import math
from collections import Counter
from app.core.lottery import GameConfig


# ============================================
# CONSTANTES DE CONFIGURAÇÃO ESTATÍSTICA
# ============================================

# Pesos para cálculo do score composto
WEIGHT_FREQUENCY: float = 0.40
WEIGHT_GAP: float = 0.60

# Epsilon para evitar divisão por zero
EPSILON: float = 1e-9

# Penalidades para detecção de múltiplos
PENALTY_MULTIPLOS_10_ALL: int = 25  # Todos múltiplos de 10
PENALTY_MULTIPLOS_3_5_ALL: int = 20  # Todos múltiplos de 3 ou 5
PENALTY_MULTIPLOS_2_ALL: int = 20  # Todos pares
PENALTY_MULTIPLOS_HIGH: int = 12  # >= 80% múltiplos quando esperado <= 50%
PENALTY_MULTIPLOS_MEDIUM: int = 8  # >= 70% múltiplos de 5 ou 10

# Limiares para análise de múltiplos
FRACTION_ALL: float = 1.0  # 100% dos números
FRACTION_HIGH: float = 0.8  # 80% dos números
FRACTION_MEDIUM: float = 0.7  # 70% dos números
FRACTION_EXPECTED_MAX: float = 0.5  # 50% esperado

# Limite para análise de primos
PRIMES_ANALYSIS_MAX_N: int = 100  # Máximo N para análise de primos


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
    """
    Flatten all draw columns into a 1D array.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with lottery draws.
    config : GameConfig
        Game configuration.

    Returns
    -------
    np.ndarray
        Flattened array of all drawn numbers.
    """
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


def verificar_historico(
    numeros: list[int],
    df: pd.DataFrame,
    config: GameConfig,
    alvos: list[int] | None = None,
) -> dict[int, list[str]]:
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
    df_stats["Peso_Composto"] = (
        df_stats["Z_Freq"] * WEIGHT_FREQUENCY + df_stats["Z_Gap"] * WEIGHT_GAP
    )

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


def calcular_min_gap_e_span(numeros: list[int], config: GameConfig) -> dict:
    """
    Calcula o menor gap entre números consecutivos e o span total.

    Otimizado para calcular ambas as métricas em um único passo.

    Parameters
    ----------
    numeros : list[int]
        Lista de números do jogo.
    config : GameConfig
        Configuração do jogo.

    Returns
    -------
    dict
        - 'min_gap': menor distância entre números consecutivos
        - 'max_gap': maior distância entre números consecutivos
        - 'span': amplitude total (max - min)
        - 'span_relativo': span / (n_numbers - 1)
        - 'gaps': lista de gaps entre números consecutivos
        - 'sequencias': quantidade de gaps iguais a 1 (números em sequência)
        - 'taxa_sequencias': proporção de gaps iguais a 1 em relação ao total de gaps
        - 'compactacao': se o jogo está muito compacto

    Examples
    --------
    >>> calcular_min_gap_e_span([1, 2, 3, 10, 20, 30], config)
    {'min_gap': 1, 'max_gap': 10, 'span': 29, ...}
    """
    if len(numeros) < 2:
        return {"erro": "Jogo precisa de pelo menos 2 números"}

    numeros_sorted = sorted(numeros)

    # Calcula gaps em um único passo
    gaps = [
        numeros_sorted[i + 1] - numeros_sorted[i]
        for i in range(len(numeros_sorted) - 1)
    ]

    min_gap = min(gaps)
    max_gap = max(gaps)
    span = numeros_sorted[-1] - numeros_sorted[0]
    span_relativo = span / (config.n_numbers - 1)

    # Análise de compactação
    # Se min_gap = 1 para muitos pares, jogo está compacto
    sequencias = sum(1 for g in gaps if g == 1)
    taxa_sequencias = sequencias / len(gaps)

    compactacao = (
        "extrema"
        if taxa_sequencias > 0.6
        else "alta" if taxa_sequencias > 0.4 else "normal"
    )

    return {
        "min_gap": min_gap,
        "max_gap": max_gap,
        "span": span,
        "span_relativo": round(span_relativo, 3),
        "gaps": gaps,
        "sequencias": sequencias,
        "taxa_sequencias": round(taxa_sequencias, 3),
        "compactacao": compactacao,
    }


def calcular_entropia_faixas(
    numeros: list[int], config: GameConfig, n_faixas: int = 10
) -> dict:
    """
    Calcula entropia da distribuição de números por faixas do volante.

    Divide o volante em n_faixas e mede a uniformidade da distribuição
    dos números escolhidos entre essas faixas.

    Parameters
    ----------
    numeros : list[int]
        Lista de números do jogo.
    config : GameConfig
        Configuração do jogo.
    n_faixas : int, default=10
        Número de faixas para dividir o volante.

    Returns
    -------
    dict
        - 'entropia': entropia calculada
        - 'entropia_maxima': entropia máxima possível
        - 'entropia_normalizada': entropia / entropia_maxima
        - 'distribuicao': contagem por faixa
        - 'faixas_vazias': número de faixas sem números
        - 'n_faixas': número total de faixas consideradas
        - 'conclusao': interpretação qualitativa da distribuição
        - 'penalidade': valor numérico de penalidade associado à distribuição
    """
    # Tamanho de cada faixa
    tamanho_faixa = config.n_numbers / n_faixas

    # Conta números por faixa
    contagem = Counter()
    for num in numeros:
        faixa = min(int((num - 1) / tamanho_faixa), n_faixas - 1)
        contagem[faixa] += 1

    # Calcula entropia
    total = len(numeros)
    entropia = 0.0

    for faixa in range(n_faixas):
        count = contagem.get(faixa, 0)
        if count > 0:
            p = count / total
            entropia -= p * math.log2(p)

    # Entropia máxima (distribuição uniforme)
    # Depende de quantas faixas podem ser ocupadas dado k números
    faixas_ocupaveis = min(n_faixas, len(numeros))
    entropia_maxima = math.log2(faixas_ocupaveis) if faixas_ocupaveis > 0 else 0

    entropia_norm = entropia / entropia_maxima if entropia_maxima > 0 else 0

    faixas_vazias = n_faixas - len(contagem)

    # Interpretação
    if entropia_norm < 0.5:
        conclusao = "⚠️ Alta concentração em poucas faixas"
        penalidade = 10
    elif entropia_norm < 0.7:
        conclusao = "ℹ️ Concentração moderada"
        penalidade = 5
    else:
        conclusao = "✅ Boa distribuição entre faixas"
        penalidade = 0

    return {
        "entropia": round(entropia, 3),
        "entropia_maxima": round(entropia_maxima, 3),
        "entropia_normalizada": round(entropia_norm, 3),
        "distribuicao": dict(contagem),
        "faixas_vazias": faixas_vazias,
        "n_faixas": n_faixas,
        "conclusao": conclusao,
        "penalidade": penalidade,
    }


def detectar_multiplos_de_d(
    numeros: list[int], config: "GameConfig", divisores: list[int] | None = None
) -> dict:
    """
    Detecta se muitos números são múltiplos de um mesmo divisor.

    "Todos múltiplos de 5" ou "todos pares" são padrões ultra-compressíveis
    e combinatoriamente raros no espaço C(N,k).

    Parameters
    ----------
    numeros : list[int]
        Lista de números do jogo.
    config : GameConfig
        Configuração do jogo.
    divisores : list[int], optional
        Lista de divisores a verificar. Default: [2, 3, 5, 10]

    Returns
    -------
    dict
        - 'analise_por_divisor': dict com análise para cada d
        - 'divisor_dominante': divisor com maior fração observada
        - 'fracao_maxima': fração de números múltiplos do divisor dominante
        - 'fracao_esperada': fração esperada sob aleatoriedade
        - 'excesso': quanto acima do esperado está
        - 'penalidade': penalidade sugerida (0-25)
        - 'conclusao': interpretação do resultado

    Examples
    --------
    >>> detectar_multiplos_de_d([5, 10, 15, 20, 25, 30], config)
    {'divisor_dominante': 5, 'fracao_maxima': 1.0, 'penalidade': 20, ...}

    >>> detectar_multiplos_de_d([2, 4, 6, 8, 10, 12], config)
    {'divisor_dominante': 2, 'fracao_maxima': 1.0, 'penalidade': 20, ...}
    """
    if divisores is None:
        divisores = [2, 3, 5, 10]

    k = len(numeros)
    N = config.n_numbers

    analise = {}

    for d in divisores:
        # Conta múltiplos no jogo
        multiplos_no_jogo = sum(1 for n in numeros if n % d == 0)
        fracao_observada = multiplos_no_jogo / k

        # Fração esperada: quantos múltiplos de d existem em 1..N
        multiplos_em_N = N // d
        fracao_esperada = multiplos_em_N / N

        # Excesso relativo
        if fracao_esperada > 0:
            excesso = (fracao_observada - fracao_esperada) / fracao_esperada
        else:
            excesso = 0

        analise[d] = {
            "multiplos": multiplos_no_jogo,
            "fracao_observada": round(fracao_observada, 3),
            "fracao_esperada": round(fracao_esperada, 3),
            "excesso": round(excesso, 3),
        }

    # Encontra divisor dominante (maior fração observada, preferindo d maiores em empate)
    # Quando todos têm fração 1.0, prefere 10 > 5 > 3 > 2
    divisor_dominante = max(
        analise.keys(), key=lambda d: (analise[d]["fracao_observada"], d)
    )

    fracao_max = analise[divisor_dominante]["fracao_observada"]
    fracao_esp = analise[divisor_dominante]["fracao_esperada"]

    # Calcula penalidade
    penalidade = 0
    conclusao = "✅ Distribuição de múltiplos normal"

    # 100% múltiplos de d (exceto d=2 que é "todos pares")
    if fracao_max == FRACTION_ALL:
        if divisor_dominante == 10:
            penalidade = PENALTY_MULTIPLOS_10_ALL
            conclusao = f"❌ TODOS múltiplos de 10 (ultra-compressível)"
        elif divisor_dominante in [3, 5]:
            penalidade = PENALTY_MULTIPLOS_3_5_ALL
            conclusao = f"❌ TODOS múltiplos de {divisor_dominante} (padrão raro)"
        elif divisor_dominante == 2:
            penalidade = PENALTY_MULTIPLOS_2_ALL
            conclusao = "❌ TODOS os números são pares (ultra-raro)"
    # >= 80% múltiplos quando esperado <= 50%
    elif fracao_max >= FRACTION_HIGH and fracao_esp <= FRACTION_EXPECTED_MAX:
        penalidade = PENALTY_MULTIPLOS_HIGH
        conclusao = f"⚠️ {fracao_max*100:.0f}% múltiplos de {divisor_dominante} (acima do esperado)"
    # >= 70% múltiplos de 5 ou 10 (mais raro)
    elif fracao_max >= FRACTION_MEDIUM and divisor_dominante in [5, 10]:
        penalidade = PENALTY_MULTIPLOS_MEDIUM
        conclusao = f"⚠️ Alta concentração de múltiplos de {divisor_dominante}"

    return {
        "analise_por_divisor": analise,
        "divisor_dominante": divisor_dominante,
        "fracao_maxima": fracao_max,
        "fracao_esperada": fracao_esp,
        "penalidade": penalidade,
        "conclusao": conclusao,
    }


def calcular_indice_compressibilidade(report: dict, config: "GameConfig") -> dict:
    """
    Calcula índice agregado de compressibilidade do jogo.

    Combina todas as métricas estruturais em um único índice (0-100):
    - 100 = alta complexidade/aleatoriedade (bom)
    - 0 = muito compressível/regular (ruim)

    Parameters
    ----------
    report : dict
        Report do validador com métricas já calculadas.
    config : GameConfig
        Configuração do jogo.

    Returns
    -------
    dict
        - 'indice': valor 0-100
        - 'categoria': "Excelente", "Bom", "Regular", "Compressível", "Ultra-compressível"
        - 'flags_ativas': lista de regularidades detectadas
        - 'penalidade_total': soma das penalidades estruturais
    """
    metricas = report.get("metricas", {})
    flags = []
    penalidade_estrutural = 0

    # Flag 1: Baixa entropia de gaps
    entropia = metricas.get("entropia", 2.0)
    if entropia < 1.0:
        flags.append("baixa_entropia")
        penalidade_estrutural += 15
    elif entropia < 1.5:
        flags.append("entropia_moderada")
        penalidade_estrutural += 5

    # Flag 2: Gaps muito regulares (CV baixo)
    cv_gaps = metricas.get("cv_gaps", 0.5)
    if cv_gaps is not None and cv_gaps < 0.2:
        flags.append("gaps_regulares")
        penalidade_estrutural += 15
    elif cv_gaps is not None and cv_gaps < 0.3:
        flags.append("gaps_pouco_variados")
        penalidade_estrutural += 8

    # Flag 3: Simetria por reflexão
    pares_simetricos = metricas.get("pares_simetricos", 0)
    if pares_simetricos >= 2:
        flags.append("simetria_forte")
        penalidade_estrutural += 12
    elif pares_simetricos == 1:
        flags.append("simetria_leve")
        penalidade_estrutural += 5

    # Flag 4: Múltiplos concentrados
    multiplos = metricas.get("multiplos", {})
    if multiplos.get("fracao_maxima", 0) >= 0.8:
        flags.append("multiplos_concentrados")
        penalidade_estrutural += 15

    # Flag 5: Primos extremos
    qtd_primos = metricas.get("qtd_primos", 0)
    primos_esperado = metricas.get("primos_esperado", 2)
    if qtd_primos == 0 and primos_esperado >= 1.5:
        flags.append("zero_primos")
        penalidade_estrutural += 10

    # Flag 6: Span muito baixo
    span_rel = metricas.get("span_relativo", 0.8)
    if span_rel < 0.4:
        flags.append("span_muito_baixo")
        penalidade_estrutural += 12
    elif span_rel < 0.5:
        flags.append("span_baixo")
        penalidade_estrutural += 6

    # Flag 7: Concentração em linha/coluna
    max_linha = metricas.get("max_numa_linha", 0)
    max_coluna = metricas.get("max_numa_coluna", 0)
    if max_linha >= 5 or max_coluna >= 4:
        flags.append("concentracao_grid")
        penalidade_estrutural += 10

    # Flag 8: Order statistics atípico
    desvio_pos = metricas.get("desvio_posicional", 0.5)
    if desvio_pos > 1.5:
        flags.append("posicoes_atipicas")
        penalidade_estrutural += 8

    # Calcula índice (100 - penalidades, mínimo 0)
    indice = max(0, min(100, 100 - penalidade_estrutural))

    # Categoriza
    if indice >= 85:
        categoria = "Excelente"
    elif indice >= 70:
        categoria = "Bom"
    elif indice >= 50:
        categoria = "Regular"
    elif indice >= 30:
        categoria = "Compressível"
    else:
        categoria = "Ultra-compressível"

    return {
        "indice": indice,
        "categoria": categoria,
        "flags_ativas": flags,
        "total_flags": len(flags),
        "penalidade_estrutural": penalidade_estrutural,
    }


def calcular_probabilidade_vitoria(
    config: GameConfig, qtd_apostas: int = 1
) -> tuple[int, float]:
    """
    Calcula a probabilidade real de acerto do prêmio máximo.
    Retorna: (total_combinacoes, chance_1_em_x)
    """
    # Combinação Simples: C(n, k)
    # Ex: Lotofácil 25 números, escolhe 15.
    total_combinacoes = math.comb(config.n_numbers, config.bet_size)

    # Se o jogo permitir apostas múltiplas (ex: jogar 16 números), a lógica muda,
    # mas assumindo jogos simples aqui:
    chance = total_combinacoes / max(1, qtd_apostas)

    return total_combinacoes, chance
