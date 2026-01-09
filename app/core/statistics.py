import pandas as pd
import numpy as np
from scipy.stats import poisson, chisquare, kstest
from app.core.games import GameConfig


def _flatten_draws(df, config: GameConfig):
    return df[config.draw_cols].values.flatten()


def get_numeros_quentes_frios(df, config: GameConfig):
    """Retorna contagem de frequência de todos os números."""
    if df.empty:
        return pd.Series()
    todos = _flatten_draws(df, config)
    return pd.Series(todos).value_counts().sort_values(ascending=False)


def analise_poisson(df, config: GameConfig, alpha=0.05):
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


def get_historico_jogos(df, config: GameConfig):
    """SET de jogos já sorteados para lookup O(1)."""
    if df.empty:
        return set()
    jogos = df[config.draw_cols].values
    return set(tuple(sorted(jogo)) for jogo in jogos)


def verificar_historico(numeros, df, config: GameConfig, alvos=None):
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


def get_reis_da_sequencia(df, config: GameConfig):
    """Identifica números que mais formam pares consecutivos."""
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


def calcular_atrasos(df, config: GameConfig):
    """
    Adiciona normalização por tamanho da base.
    Gap relativo = Gap absoluto / Total de jogos.
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


def get_tabela_inteligencia(df, config: GameConfig):
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
    df_stats["Z_Freq"] = (df_stats["Frequencia"] - mu_freq) / (sigma_freq + 1e-9)

    mu_gap = df_stats["Atraso"].mean()
    sigma_gap = df_stats["Atraso"].std()
    df_stats["Z_Gap"] = (df_stats["Atraso"] - mu_gap) / (sigma_gap + 1e-9)

    # 2. Peso Composto
    df_stats["Peso_Composto"] = df_stats["Z_Freq"] * 0.40 + df_stats["Z_Gap"] * 0.60

    # 3. Normalização
    peso_min = df_stats["Peso_Composto"].min()
    peso_max = df_stats["Peso_Composto"].max()
    df_stats["Peso_Geracao"] = (
        (df_stats["Peso_Composto"] - peso_min) / (peso_max - peso_min + 1e-9)
    ) + 0.01

    # 4. Métricas adicionais
    df_stats["Percentil_Freq"] = df_stats["Frequencia"].rank(pct=True)
    df_stats["Percentil_Gap"] = df_stats["Atraso"].rank(pct=True)

    return df_stats


def calcular_chi_quadrado(df, config: GameConfig):
    if df.empty:
        return None

    todos_numeros = _flatten_draws(df, config)
    contagem = pd.Series(todos_numeros).value_counts().sort_index()
    contagem = contagem.reindex(range(1, config.n_numbers + 1), fill_value=0)

    f_obs = contagem.values
    total_bolas = len(todos_numeros)
    f_esp = [total_bolas / config.n_numbers] * config.n_numbers

    chi2_stat, p_chi = chisquare(f_obs, f_exp=f_esp)

    uniform_sample = np.linspace(1, config.n_numbers, len(todos_numeros))
    ks_stat, p_ks = kstest(sorted(todos_numeros), lambda x: x / config.n_numbers)

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


def analise_intervalo_confianca(df, config: GameConfig):
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


def calcular_coeficiente_variacao(df, config: GameConfig):
    if df.empty:
        return None

    freq = get_numeros_quentes_frios(df, config)
    cv = (freq.std() / freq.mean()) * 100

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
