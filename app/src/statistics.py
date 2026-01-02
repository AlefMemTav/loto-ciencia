import pandas as pd
import streamlit as st
from scipy.stats import poisson


@st.cache_data
def get_numeros_quentes_frios(df):
    if df.empty:
        return pd.Series()
    todos = df.values.flatten()
    return pd.Series(todos).value_counts().sort_values(ascending=False)


@st.cache_data
def analise_poisson(df, alpha=0.05):
    """
    Analisa se a contagem de dígitos finais está estatisticamente abaixo
    do esperado segundo um processo de Poisson.

    Retorna apenas desvios estatisticamente relevantes.
    """
    if df.empty:
        return []

    # Flatten dos números
    numeros = df[["D1", "D2", "D3", "D4", "D5", "D6"]].values.flatten()
    finais = pd.Series([n % 10 for n in numeros])

    total = len(finais)
    lambda_esperado = total * 0.10  # taxa Poisson esperada por dígito

    resultado = []

    for digito in range(10):
        observado = (finais == digito).sum()

        # Probabilidade de observar <= k eventos dado λ
        p_value = poisson.cdf(observado, lambda_esperado)

        if p_value < alpha:
            resultado.append(
                {
                    "digito": digito,
                    "observado": observado,
                    "esperado": int(lambda_esperado),
                    "p_value": round(p_value, 5),
                    "interpretacao": "Desvio estatisticamente relevante",
                }
            )

    return resultado


def verificar_historico_sena(numeros, df):
    # Transforma os números do usuário em um conjunto (set) para comparação rápida
    meus_nums = set(numeros)
    ja_saiu_sena, ja_saiu_quina, ja_saiu_quadra = [], [], []

    # Itera sobre cada linha do histórico (Concursos reais)
    # iterrows é lento para big data, mas para 2600 linhas é instantâneo
    for index, row in df.iterrows():
        # Pega as bolas do sorteio atual
        sorteio = set(row[["D1", "D2", "D3", "D4", "D5", "D6"]].values)

        # Vê quantos números coincidem (Intersecção)
        acertos = len(meus_nums.intersection(sorteio))

        concurso_info = f"Conc. {row.name if row.name else index} ({row.iloc[1] if len(row) > 1 else 'Data N/A'})"  # Tenta pegar data se existir

        if acertos == 6:
            ja_saiu_sena.append(concurso_info)
        elif acertos == 5:
            ja_saiu_quina.append(concurso_info)
        elif acertos == 4:
            ja_saiu_quadra.append(concurso_info)

    return ja_saiu_sena, ja_saiu_quina, ja_saiu_quadra


@st.cache_data
def get_reis_da_sequencia(df):
    """
    Identifica os números que mais formam pares consecutivos.
    Retorna uma lista plana com os números desses pares.
    """
    if df.empty:
        return []

    todos_pares = []
    for _, row in df.iterrows():
        sorteio = sorted(row[["D1", "D2", "D3", "D4", "D5", "D6"]].values)
        for i in range(len(sorteio) - 1):
            if sorteio[i + 1] == sorteio[i] + 1:
                todos_pares.append((sorteio[i], sorteio[i + 1]))

    if not todos_pares:
        return []

    # Pega os Top 15 pares
    freq_pares = pd.Series(todos_pares).value_counts().head(15)

    # Desempacota para lista de números únicos
    numeros = set()
    for par in freq_pares.index:
        numeros.add(par[0])
        numeros.add(par[1])

    return sorted(list(numeros))
