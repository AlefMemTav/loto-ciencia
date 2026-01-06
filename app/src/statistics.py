import pandas as pd
import numpy as np
import streamlit as st
from scipy.stats import poisson, chisquare, kstest
from app.src.games import GameConfig


def _flatten_draws(df, config: GameConfig):
    return df[config.draw_cols].values.flatten()


@st.cache_data
def get_numeros_quentes_frios(df, config: GameConfig):
    """Retorna contagem de frequência de todos os números."""
    if df.empty:
        return pd.Series()
    todos = _flatten_draws(df, config)
    return pd.Series(todos).value_counts().sort_values(ascending=False)


@st.cache_data
def analise_poisson(df, config: GameConfig, alpha=0.05):
    if df.empty:
        return []

    numeros = _flatten_draws(df, config)
    finais = pd.Series([n % 10 for n in numeros])
    total_bolas_sorteadas = len(finais)

    resultado = []

    # Conta quantos números no universo (1..N) terminam com cada dígito
    # Ex Mega (60): final 1 aparece 6x (1,11,21,31,41,51) -> Prob 6/60 = 10%
    # Ex Loto (25): final 1 aparece 3x (1,11,21) -> Prob 3/25 = 12%
    # Ex Loto (25): final 6 aparece 2x (6,16) -> Prob 2/25 = 8%

    universo = list(range(1, config.n_numbers + 1))
    finais_universo = [n % 10 for n in universo]
    contagem_teorica = pd.Series(finais_universo).value_counts().sort_index()

    for digito in range(10):
        # Probabilidade teórica exata para este jogo
        prob_teorica = contagem_teorica.get(digito, 0) / config.n_numbers

        # Lambda ajustado
        lambda_esperado = total_bolas_sorteadas * prob_teorica

        observado = (finais == digito).sum()

        # Evita erro se lambda for 0 (jogo muito pequeno, improvável mas seguro)
        if lambda_esperado == 0:
            continue

        # Teste bilateral (Poisson)
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


@st.cache_data
def get_historico_jogos(df, config: GameConfig):
    """SET de jogos já sorteados para lookup O(1)."""
    if df.empty:
        return set()
    jogos = df[config.draw_cols].values
    return set(tuple(sorted(jogo)) for jogo in jogos)


@st.cache_data
def calcular_guia_equilibrio(df, conjuntos: dict, config: GameConfig) -> dict:
    """
    Calcula, para cada grupo (ex. moldura/miolo/cruz/xis/cantos),
    a presença média por sorteio e o risco de "jogo cheio"
    (todos os k números dentro do grupo).
    Retorna dict: {nome_grupo: {"media_ideal": float, "risco_cheio": float}}
    """
    if df.empty:
        return {}

    historico_sets = [set(row) for row in df[config.draw_cols].values]
    total_concursos = len(historico_sets)

    out = {}
    for nome, numeros_grupo in conjuntos.items():
        set_grupo = set(numeros_grupo)

        # média de interseção (quantos números do grupo aparecem por sorteio)
        soma_acertos = sum(len(sorteio & set_grupo) for sorteio in historico_sets)
        media_ideal = soma_acertos / total_concursos

        # risco do evento extremo: sorteio inteiro dentro do grupo
        ocorrencias_full = sum(
            1 for sorteio in historico_sets if sorteio.issubset(set_grupo)
        )
        risco_cheio = (ocorrencias_full / total_concursos) * 100

        out[nome] = {"media_ideal": media_ideal, "risco_cheio": risco_cheio}

    return out


def avaliar_jogo_por_grupos(
    numeros: list, guia: dict, conjuntos: dict, config: GameConfig
) -> dict:
    """
    Avalia um jogo contra o guia (média ideal).
    Pesos adaptativos baseados no jogo (Mega/Quina/Lotofácil).
    """
    jogo = set(numeros)
    k = config.k

    detalhes = {}
    penalidade = 0.0

    # Pesos adaptativos
    pesos = config.geo_weights

    for nome, numeros_grupo in conjuntos.items():
        if nome not in guia:
            continue

        presentes = len(jogo & set(numeros_grupo))
        ideal = guia[nome]["media_ideal"]
        risco_cheio = guia[nome]["risco_cheio"]

        detalhes[nome] = {
            "presentes": presentes,
            "ideal": round(float(ideal), 2),
            "risco_cheio": round(float(risco_cheio), 4),
        }

        # penaliza desvio do ideal
        w = pesos.get(nome, 0.5)
        penalidade += w * abs(presentes - ideal)

        # penaliza extremos: muito concentrado em um grupo
        if k > 0 and presentes >= int(k * 0.8):
            penalidade += 2.0 * w

    # Score geométrico
    score_geom = max(0, min(100, int(100 - penalidade * 12)))

    return {"score_geom": score_geom, "detalhes": detalhes}


def verificar_historico(numeros, df, config: GameConfig, alvos=None):
    meus = set(numeros)
    if alvos is None:
        # default: top 3 faixas abaixo do cheio
        alvos = [config.k, config.k - 1, config.k - 2]

    res = {a: [] for a in alvos}
    for idx, row in df.iterrows():
        sorteio = set(row[config.draw_cols].values)
        acertos = len(meus.intersection(sorteio))
        if acertos in res:
            res[acertos].append(f"Conc. {idx}")
    return res


@st.cache_data
def get_reis_da_sequencia(df, config: GameConfig):
    """
    Identifica números que mais formam pares consecutivos (genérico por jogo).
        Args:
           df (pd.DataFrame): DataFrame com os resultados dos sorteios.
           config (GameConfig): Configuração do jogo.
        Returns:
           List[int]: Lista dos números que mais frequentemente aparecem em pares consecutivos.
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


@st.cache_data
def calcular_atrasos(df, config: GameConfig):
    """
    Adiciona normalização por tamanho da base.
    Gap relativo = Gap absoluto / Total de jogos.
    """
    if df.empty:
        return pd.Series()

    ultimo_concurso = df.index.max()
    total_concursos = len(df)

    # Vetorização otimizada
    stacked = df[config.draw_cols].stack().reset_index()
    stacked.columns = ["Concurso", "Col", "Numero"]
    ultima_aparicao = stacked.groupby("Numero")["Concurso"].max()

    atrasos = {}
    atrasos_relativos = {}

    for n in range(1, config.n_numbers + 1):
        if n in ultima_aparicao:
            gap_absoluto = ultimo_concurso - ultima_aparicao[n]
            atrasos[n] = gap_absoluto
            atrasos_relativos[n] = gap_absoluto / total_concursos
        else:
            atrasos[n] = ultimo_concurso
            atrasos_relativos[n] = 1.0  # 100% do histórico

    return pd.Series(atrasos).sort_values(ascending=False)


@st.cache_data
def get_tabela_inteligencia(df, config: GameConfig):
    """
    Sistema de pesos MATEMATICAMENTE CORRETO.
    Usa Z-Scores normalizados e combinação calibrada.
    """
    if df.empty:
        return pd.DataFrame()

    freq = get_numeros_quentes_frios(df, config).sort_index()
    atrasos = calcular_atrasos(df, config).sort_index()

    df_stats = pd.DataFrame(index=range(1, config.n_numbers + 1))
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
def calcular_chi_quadrado(df, config: GameConfig):
    """
    Chi² + Kolmogorov-Smirnov para robustez.
    """
    if df.empty:
        return None

    todos_numeros = _flatten_draws(df, config)
    contagem = pd.Series(todos_numeros).value_counts().sort_index()
    contagem = contagem.reindex(range(1, config.n_numbers + 1), fill_value=0)

    f_obs = contagem.values
    total_bolas = len(todos_numeros)
    f_esp = [total_bolas / config.n_numbers] * config.n_numbers

    # Teste Chi-Quadrado
    chi2_stat, p_chi = chisquare(f_obs, f_exp=f_esp)

    # Teste KS (Kolmogorov-Smirnov) para uniformidade
    uniform_sample = np.linspace(1, config.n_numbers, len(todos_numeros))
    ks_stat, p_ks = kstest(sorted(todos_numeros), lambda x: x / config.n_numbers)

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
def analise_intervalo_confianca(df, config: GameConfig):
    """
    Análise de intervalos de confiança para soma.
    Baseado na distribuição real dos dados.
    """
    if df.empty:
        return None

    somas = df[config.draw_cols].sum(axis=1)

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
def calcular_coeficiente_variacao(df, config: GameConfig):
    """
    Mede a estabilidade da aleatoriedade.
    CV baixo = números saem com frequência similar (bom sinal).
    """
    if df.empty:
        return None

    freq = get_numeros_quentes_frios(df, config)

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
