# app/src/advanced_statistics.py
"""
Análises estatísticas avançadas baseadas em dados reais.
Substitui heurísticas por distribuições empíricas.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from app.core.statistics import calcular_atrasos


# ============================================
# DISTRIBUIÇÕES GEOMÉTRICAS
# ============================================


@dataclass
class GeometricDistribution:
    """Distribuição empírica de um padrão geométrico"""

    mean: float
    std: float
    percentiles: Dict[int, float]  # {5: val, 25: val, 50: val, 75: val, 95: val}
    z_scores: np.ndarray


def calcular_distribuicoes_geometricas(
    df, conjuntos: dict, config
) -> Dict[str, GeometricDistribution]:
    """
    Calcula distribuições empíricas REAIS dos padrões geométricos.
    Substitui heurísticas por estatística baseada em dados.

    Returns:
        Dict com distribuições para cada grupo (moldura, miolo, cruz, xis, cantos)
    """
    if df.empty:
        return {}

    historico_sets = [set(row) for row in df[config.draw_cols].values]

    distribuicoes = {}

    for nome, numeros_grupo in conjuntos.items():
        set_grupo = set(numeros_grupo)

        # Conta quantos números de cada grupo apareceram em CADA sorteio
        contagens = np.array([len(sorteio & set_grupo) for sorteio in historico_sets])

        # Estatísticas descritivas
        mean = contagens.mean()
        std = contagens.std()

        # Percentis empíricos
        percentiles = {
            5: np.percentile(contagens, 5),
            25: np.percentile(contagens, 25),
            50: np.percentile(contagens, 50),
            75: np.percentile(contagens, 75),
            95: np.percentile(contagens, 95),
        }

        # Z-scores históricos (para detectar outliers)
        z_scores = (contagens - mean) / (std + 1e-9)

        distribuicoes[nome] = GeometricDistribution(
            mean=mean, std=std, percentiles=percentiles, z_scores=z_scores
        )

    return distribuicoes


def avaliar_jogo_geometria_estatistica(
    numeros: list,
    conjuntos: dict,
    distribuicoes: Dict[str, GeometricDistribution],
    config,
) -> Dict:
    """
    Avalia geometria usando PROBABILIDADE EMPÍRICA ao invés de heurísticas.

    Retorna:
        - z_score: Quão anormal é cada padrão (-2 a +2 é normal)
        - p_value: Probabilidade de ver esse valor ou mais extremo
        - categoria: Normal, Raro, Muito Raro, Extremo
    """
    jogo = set(numeros)
    resultados = {}

    penalidade_total = 0.0

    for nome, numeros_grupo in conjuntos.items():
        if nome not in distribuicoes:
            continue

        dist = distribuicoes[nome]
        presentes = len(jogo & set(numeros_grupo))

        # Ajuste para jogos grandes (Lotomania: aposta 50 vs sorteio 20)
        qtd_jogada = len(numeros)
        if config.k != qtd_jogada and config.k > 0:
            fator_projecao = qtd_jogada / config.k
            mean_ajustada = dist.mean * fator_projecao
            std_ajustada = dist.std * np.sqrt(fator_projecao)
        else:
            mean_ajustada = dist.mean
            std_ajustada = dist.std

        # Z-score: quantos desvios-padrão do normal?
        z_score = (presentes - mean_ajustada) / (std_ajustada + 1e-9)

        # P-value empírico: qual % dos sorteios históricos foram tão extremos?
        mais_extremos = np.sum(np.abs(dist.z_scores) >= abs(z_score))
        p_value = mais_extremos / len(dist.z_scores) if len(dist.z_scores) > 0 else 1.0

        # Categorização baseada em Z-scores
        if abs(z_score) > 3:  # Evento de 3 sigma (0.3% de chance)
            categoria = "Extremo"
            peso = 3.0
        elif abs(z_score) > 2:  # 2 sigma (5% de chance)
            categoria = "Muito Raro"
            peso = 2.0
        elif abs(z_score) > 1:  # 1 sigma (32% de chance)
            categoria = "Raro"
            peso = 1.0
        else:
            categoria = "Normal"
            peso = 0.0

        penalidade_total += peso * abs(z_score) * 0.5  # Fator de escala

        resultados[nome] = {
            "presentes": presentes,
            "media_historica": round(float(mean_ajustada), 2),
            "desvio_historico": round(float(std_ajustada), 2),
            "z_score": round(float(z_score), 3),
            "p_value": round(float(p_value), 4),
            "categoria": categoria,
            "percentil_5": float(dist.percentiles[5]),
            "percentil_95": float(dist.percentiles[95]),
        }

    # Score geométrico baseado em desvios reais
    score_geom = max(0, min(100, int(100 - penalidade_total * 8)))

    return {
        "score_geom": score_geom,
        "detalhes": resultados,
        "penalidade": round(float(penalidade_total), 2),
    }


# ============================================
# DISTÂNCIA DE HAMMING
# ============================================


def distancia_hamming(jogo1: List[int], jogo2: List[int]) -> int:
    """
    Conta quantos números são DIFERENTES entre dois jogos.

    Exemplo:
        jogo1 = [1, 2, 3, 4, 5, 6]
        jogo2 = [1, 2, 3, 7, 8, 9]
        hamming = 3 (números 4,5,6 vs 7,8,9)
    """
    set1 = set(jogo1)
    set2 = set(jogo2)
    return len(set1.symmetric_difference(set2))


def calcular_distancia_minima_historico(
    jogo: List[int], df, config, top_n: int = 100
) -> Tuple[int, float]:
    """
    Calcula a menor distância de Hamming entre o jogo e o histórico.
    Returns:
        (distancia_minima, similaridade_maxima)
    """
    if df.empty or config.bet_size != config.k:
        return (config.bet_size, 0.0)

    df_recente = df.tail(top_n)
    jogo_set = set(jogo)

    distancias = df_recente[config.draw_cols].apply(
        lambda row: len(jogo_set.symmetric_difference(set(row))), axis=1
    )

    min_dist = int(distancias.min())
    max_sim = 1 - (min_dist / config.bet_size)

    return (min_dist, max_sim)


def penalizar_por_similaridade(report, numeros, df, config):
    """
    Adiciona penalidades baseadas em distância de Hamming.
    """
    # Só aplica se o jogo tem mesmo tamanho do sorteio
    if config.bet_size != config.k:
        report["metricas"]["hamming_min"] = "N/A"
        report["metricas"]["similaridade_max"] = "N/A"
        return

    min_dist, max_sim = calcular_distancia_minima_historico(numeros, df, config)

    report["metricas"]["hamming_min"] = min_dist
    report["metricas"]["similaridade_max"] = round(max_sim, 3)

    k = config.bet_size

    if min_dist == 0:
        # Jogo idêntico (já detectado por outro sistema)
        pass
    elif min_dist == 1:
        report["score"] -= 30
        report["msgs"].append(
            "🚨 Quase idêntico a um sorteio anterior (apenas 1 número diferente)"
        )
        report["risco_divisao"] = "ALTO"
    elif min_dist == 2:
        report["score"] -= 20
        report["msgs"].append(
            "⚠️ Muito similar a sorteio anterior (apenas 2 números diferentes)"
        )
        report["risco_divisao"] = "Médio"
    elif min_dist <= k // 3:  # Ex: ≤2 diferentes em jogo de 6
        report["score"] -= 10
        report["msgs"].append(f"⚠️ Similaridade alta com histórico (Hamming={min_dist})")
    elif min_dist >= k // 2:
        report["msgs"].append(f"✅ Jogo suficientemente único (Hamming={min_dist})")


# ============================================
# ANÁLISE DE QUADRANTES
# ============================================


def calcular_distribuicao_quadrantes(df, config) -> dict:
    """
    Calcula distribuição empírica de números por quadrante.
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


def avaliar_quadrantes_estatistico(numeros, config, stats_quadrantes) -> dict:
    """
    Avalia distribuição de quadrantes usando estatística.
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

        # Ajuste para jogos grandes (Lotomania)
        qtd_jogada = len(numeros)
        if config.k != qtd_jogada and config.k > 0:
            fator = qtd_jogada / config.k
            mean_ajustada = stat["mean"] * fator
            std_ajustada = stat["std"] * np.sqrt(fator)
        else:
            mean_ajustada = stat["mean"]
            std_ajustada = stat["std"]

        z = (presentes - mean_ajustada) / (std_ajustada + 1e-9)

        # Evento extremo: fora do intervalo 90%
        if abs(z) > 1.64:  # p < 0.10
            penalidade += abs(z) * 0.5
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
    if max_concentracao >= len(numeros) * 0.7:
        penalidade += 2.0
        resultados["alerta"] = f"⚠️ {max_concentracao} números em 1 quadrante"

    score = max(0, min(100, int(100 - penalidade * 8)))

    return {
        "score_quadrantes": score,
        "detalhes": resultados,
        "penalidade": round(float(penalidade), 2),
    }


# ============================================
# REGRESSÃO À MÉDIA
# ============================================


def calcular_taxa_regressao(df, config, janela: int = 100) -> Optional[dict]:
    """
    Mede se números atrasados realmente tendem a sair.
    Valida se a "regressão à média" funciona nos dados.
    """
    if df.empty or len(df) < janela + 10:
        return None

    # Pega um ponto no passado
    df_analise = df.iloc[:-janela]
    df_futuro = df.iloc[-janela:]

    atrasos_passado = calcular_atrasos(df_analise, config)

    # Top 20% mais atrasados
    top_atrasados = set(atrasos_passado.nlargest(int(config.n_numbers * 0.2)).index)

    # Quantos saíram nos próximos 'janela' sorteios?
    saidas = set()
    for _, row in df_futuro.iterrows():
        saidas.update(row[config.draw_cols].values)

    retornaram = len(top_atrasados & saidas)
    taxa_retorno = retornaram / len(top_atrasados) if top_atrasados else 0

    # Correlação entre atraso e frequência futura
    try:
        from scipy.stats import spearmanr

        freq_futura = []
        for num in range(1, config.n_numbers + 1):
            ocorrencias = sum(
                1
                for _, row in df_futuro.iterrows()
                if num in row[config.draw_cols].values
            )
            freq_futura.append(ocorrencias)

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
    except:
        return None
