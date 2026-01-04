import random
import numpy as np
from itertools import combinations
from app.src.validator import validar_jogo
from app.src.statistics import (
    analise_intervalo_confianca,
    get_historico_jogos,
    get_tabela_inteligencia,
)


def gerar_jogo_perfeito(df, finais_poisson=None, estrategia="balanceada"):
    """
    Gera um jogo usando Amostragem Ponderada baseada em Z-Score.

    Args:
        df: DataFrame com histórico da Mega-Sena
        finais_poisson: Lista de dígitos finais atrasados
        estrategia: Modo de geração
            - 'balanceada': 40% freq + 60% atraso (padrão)
            - 'conservadora': 70% freq + 30% atraso (números quentes)
            - 'agressiva': 20% freq + 80% atraso (regressão à média)
            - 'pura': 100% aleatório (controle)

    Returns:
        Lista com 6 números ordenados
    """
    # 1. Busca dados
    tabela = get_tabela_inteligencia(df)
    historico = get_historico_jogos(df)
    ic_info = analise_intervalo_confianca(df)

    if tabela.empty:
        return sorted(random.sample(range(1, 61), 6))

    numeros_disponiveis = tabela.index.tolist()

    # 2. Seleciona pesos conforme estratégia
    if estrategia == "conservadora":
        pesos_raw = tabela["Z_Freq"] * 0.70 + tabela["Z_Gap"] * 0.30
    elif estrategia == "agressiva":
        pesos_raw = tabela["Z_Freq"] * 0.20 + tabela["Z_Gap"] * 0.80
    elif estrategia == "pura":
        pesos_raw = [1.0] * 60
    else:  # balanceada (padrão)
        pesos_raw = tabela["Peso_Geracao"]

    # Normaliza para positivo
    if estrategia != "pura":
        pesos = pesos_raw - pesos_raw.min() + 0.01
        pesos = pesos.tolist()
    else:
        pesos = pesos_raw

    # 3. Loop de geração com early stopping inteligente
    tentativas = 0
    melhor_jogo = None
    melhor_score = -1

    while tentativas < 10000:  # Reduzido de 20000
        tentativas += 1

        # Gera candidato com amostragem ponderada
        pre_jogo = set()
        candidatos = random.choices(numeros_disponiveis, weights=pesos, k=6)
        pre_jogo.update(candidatos)

        while len(pre_jogo) < 6:
            novo = random.choices(numeros_disponiveis, weights=pesos, k=1)[0]
            pre_jogo.add(novo)

        jogo = sorted(list(pre_jogo))

        # 4. Validação
        val = validar_jogo(jogo, historico_jogos=historico, ic_info=ic_info)

        # Guarda o melhor
        if val["score"] > melhor_score:
            melhor_score = val["score"]
            melhor_jogo = jogo.copy()

        # Early stopping: aceita score >= 85 (excelente)
        if val["score"] >= 85:
            return jogo

        # Fallback adaptativo: se já tentou 5000x, aceita >= 70
        if tentativas == 5000 and melhor_score >= 70:
            return melhor_jogo

    # Retorna o melhor encontrado
    return melhor_jogo if melhor_jogo else sorted(random.sample(range(1, 61), 6))


def gerar_multiplos_jogos(
    df,
    quantidade=10,
    estrategia="balanceada",
    garantir_diversidade=True,
    finais_poisson=None,
):
    """
    Gerador de múltiplos jogos com controle de diversidade.

    Args:
        df: DataFrame histórico
        quantidade: Número de jogos a gerar
        estrategia: Modo de geração (ver gerar_jogo_perfeito)
        garantir_diversidade: Se True, evita jogos com mais de 4 números em comum
        finais_poisson: (Não usado mais, mantido para compatibilidade)

    Returns:
        Lista de jogos
    """
    jogos_gerados = []
    jogos_set = set()

    tentativas = 0
    max_tentativas = quantidade * 100

    while len(jogos_gerados) < quantidade and tentativas < max_tentativas:
        tentativas += 1

        jogo = gerar_jogo_perfeito(df, estrategia=estrategia)
        jogo_tuple = tuple(jogo)

        # Verifica duplicata
        if jogo_tuple in jogos_set:
            continue

        # Verifica diversidade
        if garantir_diversidade and jogos_gerados:
            sobrepoe_muito = False
            for jogo_anterior in jogos_gerados:
                comum = len(set(jogo).intersection(set(jogo_anterior)))
                if comum > 4:
                    sobrepoe_muito = True
                    break

            if sobrepoe_muito:
                continue

        jogos_gerados.append(jogo)
        jogos_set.add(jogo_tuple)

    return jogos_gerados


def gerar_com_restricoes(
    df, numeros_fixos=None, numeros_evitados=None, estrategia="balanceada"
):
    """
    Gerador com restrições personalizadas.

    Args:
        numeros_fixos: Lista de números que DEVEM estar no jogo
        numeros_evitados: Lista de números que NÃO podem estar no jogo
        estrategia: Modo de geração

    Returns:
        Lista com 6 números ou dict com erro
    """
    tabela = get_tabela_inteligencia(df)
    historico = get_historico_jogos(df)
    ic_info = analise_intervalo_confianca(df)

    if tabela.empty:
        return None

    # Validações
    numeros_fixos = numeros_fixos or []
    numeros_evitados = numeros_evitados or []

    if len(numeros_fixos) > 6:
        return {"erro": "Não pode ter mais de 6 números fixos"}

    if set(numeros_fixos).intersection(set(numeros_evitados)):
        return {"erro": "Números fixos e evitados não podem se sobrepor"}

    # Pool disponível
    pool = [
        n for n in range(1, 61) if n not in numeros_evitados and n not in numeros_fixos
    ]

    if len(pool) + len(numeros_fixos) < 6:
        return {"erro": "Pool insuficiente para gerar jogo"}

    # Pesos do pool
    pesos_pool = tabela.loc[pool, "Peso_Geracao"].tolist()

    # Gera complemento
    tentativas = 0
    while tentativas < 5000:
        tentativas += 1

        qtd_necessaria = 6 - len(numeros_fixos)
        complemento = []

        while len(complemento) < qtd_necessaria:
            novo = random.choices(pool, weights=pesos_pool, k=1)[0]
            if novo not in complemento:
                complemento.append(novo)

        jogo = sorted(numeros_fixos + complemento)

        val = validar_jogo(jogo, historico_jogos=historico, ic_info=ic_info)

        if val["score"] >= 75:
            return jogo

    # Fallback
    complemento = random.sample(pool, 6 - len(numeros_fixos))
    return sorted(numeros_fixos + complemento)


def gerar_fechamento(numeros_base, max_combinacoes=1000):
    """
    Limita fechamentos grandes para evitar explosão combinatória.

    Args:
        numeros_base: Lista de números base (7-12 recomendado)
        max_combinacoes: Limite máximo de jogos

    Returns:
        Lista de jogos ou dict com erro
    """
    if len(numeros_base) < 6:
        return []

    # Calcula número de combinações
    n = len(numeros_base)

    # Usa math.comb do Python 3.8+
    try:
        total_comb = np.math.factorial(n) // (
            np.math.factorial(6) * np.math.factorial(n - 6)
        )
    except:
        # Fallback para versões antigas
        from math import comb

        total_comb = comb(n, 6)

    if total_comb > max_combinacoes:
        return {
            "erro": f"Fechamento de {n} números gera {total_comb:,} jogos. "
            f"Limite: {max_combinacoes:,}. Reduza a quantidade de números."
        }

    comb_iter = combinations(numeros_base, 6)
    return [sorted(list(c)) for c in comb_iter]


def analise_estatistica_jogo(jogo, df):
    """
    Análise completa de um jogo específico.

     Args:
         jogo: Lista com 6 números
         df: DataFrame histórico

     Returns:
         Dict com métricas estatísticas
    """
    tabela = get_tabela_inteligencia(df)

    if tabela.empty:
        return None

    # Métricas individuais dos números
    stats_nums = tabela.loc[jogo]

    # Análise agregada
    analise = {
        "frequencia_media": round(stats_nums["Frequencia"].mean(), 2),
        "atraso_medio": round(stats_nums["Atraso"].mean(), 2),
        "z_freq_medio": round(stats_nums["Z_Freq"].mean(), 3),
        "z_gap_medio": round(stats_nums["Z_Gap"].mean(), 3),
        "peso_medio": round(stats_nums["Peso_Geracao"].mean(), 3),
        "percentil_freq_medio": round(stats_nums["Percentil_Freq"].mean() * 100, 1),
        "percentil_gap_medio": round(stats_nums["Percentil_Gap"].mean() * 100, 1),
    }

    # Interpretações
    if analise["z_freq_medio"] > 0.5:
        analise["perfil"] = "🔥 Números Quentes"
    elif analise["z_freq_medio"] < -0.5:
        analise["perfil"] = "❄️ Números Frios"
    else:
        analise["perfil"] = "⚖️ Balanceado"

    if analise["z_gap_medio"] > 0.5:
        analise["status_atraso"] = "🕐 Muito Atrasados (Regressão)"
    elif analise["z_gap_medio"] < -0.5:
        analise["status_atraso"] = "🆕 Recentemente Sorteados"
    else:
        analise["status_atraso"] = "⏱️ Atraso Normal"

    return analise
