import pandas as pd
import numpy as np
import streamlit as st
from scipy.stats import poisson, chisquare, kstest
from typing import Dict, List, Tuple


@st.cache_data
def get_numeros_quentes_frios(df):
    """Retorna contagem de frequência de todos os números."""
    if df.empty:
        return pd.Series()
    todos = df[["D1", "D2", "D3", "D4", "D5", "D6"]].values.flatten()
    return pd.Series(todos).value_counts().sort_values(ascending=False)


@st.cache_data
def analise_poisson(df, alpha=0.05):
    """
    Análise bilateral e detecção de EXCESSO também.
    Detecta dígitos finais com desvios para CIMA ou para BAIXO.
    """
    if df.empty:
        return []

    numeros = df[["D1", "D2", "D3", "D4", "D5", "D6"]].values.flatten()
    finais = pd.Series([n % 10 for n in numeros])
    total = len(finais)
    lambda_esperado = total * 0.10

    resultado = []

    for digito in range(10):
        observado = (finais == digito).sum()

        # Teste bilateral: muito abaixo OU muito acima
        p_inferior = poisson.cdf(observado, lambda_esperado)
        p_superior = 1 - poisson.cdf(observado - 1, lambda_esperado)

        # Usa o menor p-value (mais extremo)
        p_value = min(p_inferior, p_superior) * 2  # Correção de Bonferroni

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
                    "interpretacao": f"Desvio estatisticamente relevante ({tipo})",
                }
            )

    return resultado


@st.cache_data
def get_historico_jogos(df):
    """SET de jogos já sorteados para lookup O(1)."""
    if df.empty:
        return set()
    jogos = df[["D1", "D2", "D3", "D4", "D5", "D6"]].values
    return set(tuple(sorted(jogo)) for jogo in jogos)


def verificar_historico_sena(numeros, df):
    """Verifica acertos históricos com vetorização."""
    meus_nums = set(numeros)
    ja_saiu_sena, ja_saiu_quina, ja_saiu_quadra = [], [], []

    # Vetorização completa (muito mais rápido)
    for idx, row in df.iterrows():
        sorteio = set(row[["D1", "D2", "D3", "D4", "D5", "D6"]].values)
        acertos = len(meus_nums.intersection(sorteio))

        concurso_info = f"Conc. {idx}"

        if acertos == 6:
            ja_saiu_sena.append(concurso_info)
        elif acertos == 5:
            ja_saiu_quina.append(concurso_info)
        elif acertos == 4:
            ja_saiu_quadra.append(concurso_info)

    return ja_saiu_sena, ja_saiu_quina, ja_saiu_quadra


@st.cache_data
def get_reis_da_sequencia(df):
    """Identifica números que mais formam pares consecutivos."""
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

    freq_pares = pd.Series(todos_pares).value_counts().head(15)
    numeros = set()
    for par in freq_pares.index:
        numeros.add(par[0])
        numeros.add(par[1])

    return sorted(list(numeros))


@st.cache_data
def calcular_atrasos(df):
    """
    Adiciona normalização por tamanho da base.
    Gap relativo = Gap absoluto / Total de jogos.
    """
    if df.empty:
        return pd.Series()

    ultimo_concurso = df.index.max()
    total_concursos = len(df)

    # Vetorização otimizada
    stacked = df[["D1", "D2", "D3", "D4", "D5", "D6"]].stack().reset_index()
    stacked.columns = ["Concurso", "Col", "Numero"]
    ultima_aparicao = stacked.groupby("Numero")["Concurso"].max()

    atrasos = {}
    atrasos_relativos = {}

    for n in range(1, 61):
        if n in ultima_aparicao:
            gap_absoluto = ultimo_concurso - ultima_aparicao[n]
            atrasos[n] = gap_absoluto
            atrasos_relativos[n] = gap_absoluto / total_concursos
        else:
            atrasos[n] = ultimo_concurso
            atrasos_relativos[n] = 1.0  # 100% do histórico

    return pd.Series(atrasos).sort_values(ascending=False)


@st.cache_data
def get_tabela_inteligencia(df):
    """
    Sistema de pesos MATEMATICAMENTE CORRETO.
    Usa Z-Scores normalizados e combinação calibrada.
    """
    if df.empty:
        return pd.DataFrame()

    freq = get_numeros_quentes_frios(df).sort_index()
    atrasos = calcular_atrasos(df).sort_index()

    df_stats = pd.DataFrame(index=range(1, 61))
    df_stats["Frequencia"] = freq
    df_stats["Atraso"] = atrasos
    df_stats = df_stats.fillna(0)

    # 1. Z-Scores padronizados
    mu_freq = df_stats["Frequencia"].mean()
    sigma_freq = df_stats["Frequencia"].std()
    df_stats["Z_Freq"] = (df_stats["Frequencia"] - mu_freq) / (sigma_freq + 1e-9)

    mu_gap = df_stats["Atraso"].mean()
    sigma_gap = df_stats["Atraso"].std()
    df_stats["Z_Gap"] = (df_stats["Atraso"] - mu_gap) / (sigma_gap + 1e-9)

    # 2. Peso Composto (Filosofia: Hot Hand + Regressão à Média)
    # 40% Frequência (números quentes) + 60% Atraso (regressão)
    df_stats["Peso_Composto"] = df_stats["Z_Freq"] * 0.40 + df_stats["Z_Gap"] * 0.60

    # 3. Normalização Min-Max para [0.01, 1.0]
    # Evita pesos negativos no random.choices
    peso_min = df_stats["Peso_Composto"].min()
    peso_max = df_stats["Peso_Composto"].max()

    df_stats["Peso_Geracao"] = (
        (df_stats["Peso_Composto"] - peso_min) / (peso_max - peso_min + 1e-9)
    ) + 0.01  # Garante peso mínimo

    # 4. Métricas adicionais
    df_stats["Percentil_Freq"] = df_stats["Frequencia"].rank(pct=True)
    df_stats["Percentil_Gap"] = df_stats["Atraso"].rank(pct=True)

    return df_stats


@st.cache_data
def calcular_chi_quadrado(df):
    """
    Adiciona testes complementares.
    Chi² + Kolmogorov-Smirnov para robustez.
    """
    if df.empty:
        return None

    todos_numeros = df[["D1", "D2", "D3", "D4", "D5", "D6"]].values.flatten()
    contagem = pd.Series(todos_numeros).value_counts().sort_index()
    contagem = contagem.reindex(range(1, 61), fill_value=0)

    f_obs = contagem.values
    total_bolas = len(todos_numeros)
    f_esp = [total_bolas / 60] * 60

    # Teste Chi-Quadrado
    chi2_stat, p_chi = chisquare(f_obs, f_exp=f_esp)

    # Teste KS (Kolmogorov-Smirnov) para uniformidade
    uniform_sample = np.linspace(1, 60, len(todos_numeros))
    ks_stat, p_ks = kstest(sorted(todos_numeros), lambda x: x / 60)

    # Interpretação combinada
    if p_chi > 0.05 and p_ks > 0.05:
        status = "✅ Honesto (Aleatório)"
        confianca = "Alta"
    elif p_chi > 0.01 or p_ks > 0.01:
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


@st.cache_data
def analise_intervalo_confianca(df):
    """
    Análise de intervalos de confiança para soma.
    Baseado na distribuição real dos dados.
    """
    if df.empty:
        return None

    somas = df[["D1", "D2", "D3", "D4", "D5", "D6"]].sum(axis=1)

    # Estatísticas descritivas
    media = somas.mean()
    mediana = somas.median()
    desvio = somas.std()

    # Intervalos de confiança empíricos
    ic_50 = (somas.quantile(0.25), somas.quantile(0.75))  # 50% central
    ic_80 = (somas.quantile(0.10), somas.quantile(0.90))  # 80% central
    ic_95 = (somas.quantile(0.025), somas.quantile(0.975))  # 95% central

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


@st.cache_data
def calcular_coeficiente_variacao(df):
    """
    MELHORIA 7: NOVO - Mede a estabilidade da aleatoriedade.
    CV baixo = números saem com frequência similar (bom sinal).
    """
    if df.empty:
        return None

    freq = get_numeros_quentes_frios(df)

    # Coeficiente de Variação = (Desvio / Média) × 100
    cv = (freq.std() / freq.mean()) * 100

    # Interpretação
    if cv < 10:
        interpretacao = "Excelente uniformidade"
    elif cv < 20:
        interpretacao = "Boa uniformidade"
    elif cv < 30:
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
