import pandas as pd
import streamlit as st
from scipy.stats import poisson, chisquare


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


@st.cache_data
def get_historico_jogos(df):
    """
    Retorna um SET contendo todos os jogos que já saíram (como tuplas ordenadas).
    Uso: O(1) Lookup - Extremamente rápido para validação.
    """
    if df.empty:
        return set()

    # Extrai as 6 colunas de dezenas
    jogos = df[["D1", "D2", "D3", "D4", "D5", "D6"]].values

    # Converte cada linha em uma tupla ordenada e adiciona ao set
    historico = set(tuple(sorted(jogo)) for jogo in jogos)

    return historico


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


@st.cache_data
def calcular_atrasos(df):
    """
    Calcula há quantos jogos cada número (1-60) não sai.
    Retorna uma Series onde o índice é o número e o valor é o Gap atual.
    """
    if df.empty:
        return pd.Series()

    ultimo_concurso = df.index.max()
    atrasos = {}

    # Estratégia Vetorizada para Performance:
    # 1. Empilha todos os dados (melt) para ter colunas [Concurso, Numero]
    # 2. Agrupa por Numero e pega o MAX Concurso (última vez que saiu)

    # Vamos assumir que o índice do DF é o número do concurso.
    # Se não for, precisaria de df.reset_index() antes.

    # Cria uma tabela longa: Index (Conc) | Valor (Bola)
    stacked = df[["D1", "D2", "D3", "D4", "D5", "D6"]].stack().reset_index()
    stacked.columns = ["Concurso", "Col", "Numero"]

    # Pega o maior concurso para cada número
    ultima_aparicao = stacked.groupby("Numero")["Concurso"].max()

    # Calcula o Gap
    for n in range(1, 61):
        if n in ultima_aparicao:
            atrasos[n] = ultimo_concurso - ultima_aparicao[n]
        else:
            atrasos[n] = ultimo_concurso  # Nunca saiu (ou base pequena)

    return pd.Series(atrasos).sort_values(ascending=False)


@st.cache_data
def get_tabela_inteligencia(df):
    """
    Gera a 'Tabela Mestra' com Z-Scores para o Algoritmo de Geração.
    Combina Frequência + Atraso + Métricas Estatísticas.
    """
    if df.empty:
        return pd.DataFrame()

    # 1. Dados Brutos
    freq = get_numeros_quentes_frios(df).sort_index()
    atrasos = calcular_atrasos(df).sort_index()

    # Garante que temos todos os números de 1 a 60
    # (freq pode não ter todos se a amostra for pequena)
    df_stats = pd.DataFrame(index=range(1, 61))
    df_stats["Frequencia"] = freq
    df_stats["Atraso"] = atrasos
    df_stats = df_stats.fillna(0)  # Preenche quem nunca saiu com 0

    # 2. Cálculo do Z-Score (Padronização) [Cite: Syllabus - Elo Perdido]
    # Z = (Valor - Média) / Desvio Padrão

    # Z-Score da Frequência (Positivo = Muito Quente, Negativo = Muito Frio)
    mu_freq = df_stats["Frequencia"].mean()
    sigma_freq = df_stats["Frequencia"].std()
    df_stats["Z_Freq"] = (df_stats["Frequencia"] - mu_freq) / (sigma_freq + 1e-9)

    # Z-Score do Atraso (Positivo = Muito Atrasado/Crítico)
    mu_gap = df_stats["Atraso"].mean()
    sigma_gap = df_stats["Atraso"].std()
    df_stats["Z_Gap"] = (df_stats["Atraso"] - mu_gap) / (sigma_gap + 1e-9)

    # 3. Peso Final (Score de Probabilidade para o Gerador)
    # Aqui aplicamos a lógica: Queremos números Quentes (Z_Freq > 0)
    # MAS também queremos números Atrasados (Regressão à Média)
    # Peso = (Z_Freq * 0.6) + (Z_Gap * 0.4) -> Exemplo de calibração

    # Normaliza para 0-1 para usar como probabilidades no random.choices
    # (Adicionamos um bias para nenhum número ter chance zero)
    df_stats["Peso_Geracao"] = df_stats["Frequencia"] + (df_stats["Atraso"] * 2)

    # Se quiser ser purista do Z-Score, usaria a normalização dele,
    # mas para MVP, somar freq + 2xGap funciona bem para dar chance aos atrasados.

    return df_stats


@st.cache_data
def calcular_chi_quadrado(df):
    """
    Realiza o teste Chi-Quadrado para verificar se a distribuição
    dos números é uniforme (honesta) ou viciada.
    """
    if df.empty:
        return None

    # Conta frequência real de cada número (1-60)
    todos_numeros = df.values.flatten()
    contagem = pd.Series(todos_numeros).value_counts().sort_index()

    # Garante que todos os números 1-60 tenham valor (mesmo que 0)
    contagem = contagem.reindex(range(1, 61), fill_value=0)

    f_obs = contagem.values

    # Frequência esperada (Total de bolas sorteadas / 60)
    total_bolas = len(todos_numeros)
    f_esp = [total_bolas / 60] * 60

    # Teste
    chi2_stat, p_value = chisquare(f_obs, f_exp=f_esp)

    return {
        "chi2": chi2_stat,
        "p_value": p_value,
        "status": "Honesto (Aleatório)" if p_value > 0.05 else "Suspeito (Viciado)",
    }
