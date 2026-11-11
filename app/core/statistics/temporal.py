# app/core/statistics/temporal.py
"""
Análises temporais de frequências e tendências.

Este módulo contém funções para análise de autocorrelação temporal,
detecção de ciclos e análise de tendências nas frequências de números
ao longo do tempo.
"""
import math
import numpy as np
import pandas as pd
from typing import Optional, List
from scipy import stats
from app.core.lottery import GameConfig


def calcular_ciclo_atual(df: pd.DataFrame, config: GameConfig) -> dict:
    """
    Calcula o status do Ciclo das Dezenas.

    Um ciclo se fecha quando todos os números do universo (ex: 1 a 25)
    foram sorteados pelo menos uma vez desde o início do ciclo.

    Parameters
    ----------
    df : pd.DataFrame
        Histórico completo.
    config : GameConfig
        Configuração do jogo.

    Returns
    -------
    dict
        - 'ciclo_numero': número do ciclo atual
        - 'aberto_ha': quantos concursos o ciclo atual já dura
        - 'faltam_sair': lista de números que faltam para fechar
        - 'progresso': percentual de conclusão (0-100)
    """
    if df.empty:
        return {
            "ciclo_numero": 0,
            "aberto_ha": 0,
            "faltam_sair": list(range(1, config.n_numbers + 1)),
            "progresso": 0.0,
        }

    todos_numeros = set(range(1, config.n_numbers + 1))

    ciclo_atual = 1
    numeros_no_ciclo = set()
    inicio_ciclo_idx = 0

    # Percorre o histórico cronologicamente
    for i in range(len(df)):
        sorteio = set(df.iloc[i][config.draw_cols].values)
        numeros_no_ciclo.update(sorteio)

        # Se completou o ciclo (todos os números saíram)
        if len(numeros_no_ciclo) == config.n_numbers:
            # Só reseta se NÃO for o último sorteio (se fechou no último, inicia novo agora)
            if i < len(df) - 1:
                ciclo_atual += 1
                numeros_no_ciclo = set()
                inicio_ciclo_idx = i + 1
            else:
                # Fechou EXATAMENTE no último sorteio.
                # O status atual é: Ciclo Fechado -> Novo ciclo começa vazio no próximo.
                return {
                    "ciclo_numero": ciclo_atual + 1,
                    "aberto_ha": 0,
                    "faltam_sair": sorted(list(todos_numeros)),
                    "progresso": 0.0,
                    "status": "Ciclo acabou de fechar!",
                }

    # Calcula o status do ciclo aberto
    faltam = todos_numeros - numeros_no_ciclo
    qtd_sorteados = len(numeros_no_ciclo)
    progresso = (qtd_sorteados / config.n_numbers) * 100

    # Quantos jogos já rolaram neste ciclo?
    aberto_ha = len(df) - inicio_ciclo_idx

    return {
        "ciclo_numero": ciclo_atual,
        "aberto_ha": aberto_ha,
        "faltam_sair": sorted(list(faltam)),
        "progresso": round(progresso, 1),
        "status": "Em andamento",
    }


def analise_temporal_somas(
    df: pd.DataFrame, config: GameConfig, janela: int = 20, janela_media: int = 5
) -> dict:
    """
    Prepara dados para o gráfico de 'Eletrocardiograma' (Somas).

    Parameters
    ----------
    df : pd.DataFrame
        Histórico.
    janela : int
        Quantos últimos concursos analisar.
    janela_media : int
        Tamanho (em concursos) da média móvel de `Media_Movel`. Os concursos
        anteriores à janela são usados para que o primeiro ponto já tenha a
        média completa.

    Returns
    -------
    dict
        Dados prontos para plotagem (lista de dicts) e faixas ideais.
    """
    if df.empty:
        return {"dados": [], "min_ideal": 0, "max_ideal": 0}

    janela_media = max(1, int(janela_media))
    df_tail = df.tail(janela + janela_media - 1).copy()
    somas_todas = df_tail[config.draw_cols].sum(axis=1)
    medias = somas_todas.rolling(janela_media, min_periods=1).mean().tail(janela)
    somas = somas_todas.tail(janela)

    N = config.n_numbers
    k = config.k

    media_teorica = k * (N + 1) / 2

    var_universo = (N**2 - 1) / 12
    fator_correcao = (N - k) / (N - 1)
    sigma = math.sqrt(k * var_universo * fator_correcao)

    min_ideal = int(media_teorica - (2.0 * sigma))
    max_ideal = int(media_teorica + (2.0 * sigma))

    dados_grafico = []
    for idx, soma in somas.items():
        dados_grafico.append(
            {
                "Concurso": idx,
                "Soma": int(soma),
                "Media_Movel": round(float(medias.loc[idx]), 1),
                "Status": ("Normal" if min_ideal <= soma <= max_ideal else "Atípico"),
            }
        )

    return {"dados": dados_grafico, "min_ideal": min_ideal, "max_ideal": max_ideal}


def analise_temporal_repetidos(
    df: pd.DataFrame, config: GameConfig, janela: int = 20
) -> dict:
    """
    Calcula quantos números se repetiram do concurso anterior (R5, R9, etc).
    """
    if df.empty or len(df) < 2:
        return {"dados": [], "media_repetidos": 0}

    # Pega um pouco mais que a janela para calcular o primeiro diff
    df_tail = df.tail(janela + 1).copy()

    dados_grafico = []
    repetidos_lista = []

    indices = df_tail.index.tolist()

    for i in range(1, len(indices)):
        atual_idx = indices[i]
        ant_idx = indices[i - 1]

        nums_atual = set(df_tail.loc[atual_idx, config.draw_cols].values)
        nums_ant = set(df_tail.loc[ant_idx, config.draw_cols].values)

        qtd_repetidos = len(nums_atual.intersection(nums_ant))
        repetidos_lista.append(qtd_repetidos)

        dados_grafico.append({"Concurso": atual_idx, "Repetidos": qtd_repetidos})

    media = sum(repetidos_lista) / len(repetidos_lista) if repetidos_lista else 0

    return {
        "dados": dados_grafico,
        "media_repetidos": round(media, 1),
        "moda": (
            max(set(repetidos_lista), key=repetidos_lista.count)
            if repetidos_lista
            else 0
        ),
    }


def calcular_autocorrelacao_frequencias(
    df: pd.DataFrame, config: GameConfig, max_lag: int = 50, janela: int = 10
) -> dict:
    """
    Calcula autocorrelação das frequências de números ao longo do tempo.

    Divide o histórico em janelas de `janela` sorteios, conta quantas vezes
    cada número saiu em cada janela e mede, para cada número, a autocorrelação
    dessa série de contagens. O resultado por lag é a média da autocorrelação
    entre todos os números do universo.

    Sob independência entre sorteios, a autocorrelação de cada número tem
    desvio ≈ 1/√W (W = número de janelas), então a média sobre N números tem
    desvio ≈ 1/√(W·N). Como são testados `max_lag` lags de uma vez, o limite
    de significância usa correção de Bonferroni: sem ela, com 50 lags a chance
    de algum lag passar do limite por acaso é de cerca de 92%.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico de sorteios.
    config : GameConfig
        Configuração do jogo.
    max_lag : int, default=50
        Número máximo de lags para calcular autocorrelação.
    janela : int, default=10
        Tamanho da janela (em sorteios) para agregação.

    Returns
    -------
    dict
        Autocorrelações e análise de ciclos:
        - 'autocorrelacoes': autocorrelação média por lag, já corrigida do
          viés do estimador (o valor esperado sem dependência é zero)
        - 'limite_significancia': limite bilateral já corrigido por lags
        - 'lags_significativos': lags com autocorrelação significativa
        - 'ciclo_detectado': se foi detectado padrão cíclico
        - 'periodo_ciclo': período estimado do ciclo (se houver)
    """
    if df.empty or len(df) < janela * 3:
        return None

    n_universo = config.n_numbers
    n_janelas = len(df) // janela

    # Contagem de cada número em cada janela: matriz (janelas x números)
    valores = df[config.draw_cols].to_numpy(dtype=int)[: n_janelas * janela]
    por_sorteio = valores.shape[1]
    indice_janela = np.repeat(np.arange(n_janelas), janela * por_sorteio)
    indice_numero = valores.ravel() - 1
    validos = (indice_numero >= 0) & (indice_numero < n_universo)
    contagens = np.zeros((n_janelas, n_universo))
    np.add.at(contagens, (indice_janela[validos], indice_numero[validos]), 1)

    # Números sem variação (nunca saíram, ou sempre iguais) não têm autocorrelação
    centrada = contagens - contagens.mean(axis=0)
    soma_quadrados = (centrada**2).sum(axis=0)
    com_variacao = soma_quadrados > 0
    if not com_variacao.any():
        return None
    centrada = centrada[:, com_variacao]
    soma_quadrados = soma_quadrados[com_variacao]
    n_series = int(com_variacao.sum())

    # Autocorrelação de cada número em cada lag, e média entre os números
    max_lag = min(max_lag, n_janelas // 2)
    lags = np.arange(1, max_lag + 1)
    autocorrs = np.array(
        [
            ((centrada[:-lag] * centrada[lag:]).sum(axis=0) / soma_quadrados).mean()
            for lag in lags
        ]
    )

    # O estimador com média amostral removida tem viés negativo sob ruído branco,
    # E[r_k] ≈ -(W - k) / (W (W - 1)); subtrai para que o zero seja o valor nulo.
    autocorrs = autocorrs + (n_janelas - lags) / (n_janelas * (n_janelas - 1))

    # Limite de significância bilateral (5%) com Bonferroni sobre os lags
    z_crit = stats.norm.isf(0.05 / (2 * max(1, max_lag)))
    limite_sig = float(z_crit / np.sqrt(n_janelas * n_series))

    # Encontra lags significativos
    lags_significativos = [
        i + 1 for i, ac in enumerate(autocorrs) if abs(ac) > limite_sig
    ]

    # Detecta ciclo (pico positivo na autocorrelação)
    if len(autocorrs) > 0:
        pico_idx = int(np.argmax(autocorrs))
        ciclo_detectado = bool(autocorrs[pico_idx] > limite_sig)
        periodo_ciclo = pico_idx + 1 if ciclo_detectado else None
    else:
        ciclo_detectado = False
        periodo_ciclo = None

    return {
        "autocorrelacoes": autocorrs.tolist(),
        "lags": list(range(1, len(autocorrs) + 1)),
        "limite_significancia": round(limite_sig, 4),
        "lags_significativos": lags_significativos,
        "ciclo_detectado": ciclo_detectado,
        "periodo_ciclo": periodo_ciclo,
        "n_janelas": n_janelas,
        "tamanho_janela": janela,
    }


def detectar_tendencia_frequencia(
    df: pd.DataFrame, config: GameConfig, numero: int, janela: int = 50
) -> dict:
    """
    Detecta tendência na frequência de um número específico.

    Usa regressão linear para identificar se a frequência está
    aumentando, diminuindo ou estável ao longo do tempo.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com histórico.
    config : GameConfig
        Configuração do jogo.
    numero : int
        Número a analisar.
    janela : int, default=50
        Tamanho da janela móvel.

    Returns
    -------
    dict
        Análise de tendência com coeficiente angular e p-value.
    """
    if df.empty or len(df) < janela * 2:
        return None

    # Calcula frequência móvel
    n_janelas = len(df) // janela
    frequencias = []

    for i in range(n_janelas):
        inicio = i * janela
        fim = inicio + janela
        df_janela = df.iloc[inicio:fim]

        count = sum(
            1
            for _, row in df_janela.iterrows()
            if numero in row[config.draw_cols].values
        )
        frequencias.append(count / janela)

    if len(frequencias) < 3:
        return None

    # Regressão linear
    x = np.arange(len(frequencias))
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, frequencias)

    # Interpretação
    if p_value < 0.05:
        if slope > 0:
            tendencia = "📈 Frequência aumentando"
        else:
            tendencia = "📉 Frequência diminuindo"
    else:
        tendencia = "➡️ Frequência estável"

    return {
        "numero": numero,
        "slope": round(slope, 6),
        "r_squared": round(r_value**2, 4),
        "p_value": round(p_value, 4),
        "tendencia": tendencia,
        "frequencias_janela": frequencias,
    }
