import math
import numpy as np
from app.ui.game_constants import get_constants_for_game
from collections import Counter
from app.src.games import GameConfig

from app.src.advanced_statistics import (
    calcular_distribuicoes_geometricas,
    avaliar_jogo_geometria_estatistica,
    penalizar_por_similaridade,
    calcular_distribuicao_quadrantes,
    avaliar_quadrantes_estatistico,
    calcular_taxa_regressao,
)


# ===== FUNÇÕES DE ANÁLISE ESPACIAL (GENÉRICAS) =====


def _verificar_linhas(numeros, config: GameConfig):
    """Análise de linhas genérica baseada no layout."""
    layout = config.layout
    contagem = [0] * layout.rows

    for num in numeros:
        linha_idx = (num - 1) // layout.cols
        if 0 <= linha_idx < layout.rows:
            contagem[linha_idx] += 1

    return contagem


def _verificar_quadrantes(numeros, config: GameConfig):
    """Quadrantes geométricos derivados do layout."""
    layout = config.layout
    quads = [0, 0, 0, 0]

    for num in numeros:
        for i in range(1, 5):
            if num in layout.quadrant_numbers(i):
                quads[i - 1] += 1
                break

    return quads


def _verificar_metades(numeros, config: GameConfig):
    """Metades baseadas no n_numbers."""
    meio = config.n_numbers // 2
    superior = len([n for n in numeros if n <= meio])
    inferior = len([n for n in numeros if n > meio])

    return {"superior": superior, "inferior": inferior}


# ===== FUNÇÕES DE CÁLCULO =====


def _calcular_entropia_shannon(numeros):
    """
    Entropia de Shannon (gaps entre números).
    Detecta padrões visuais repetitivos.
    """
    if len(numeros) < 2:
        return 0.0

    gaps = [numeros[i + 1] - numeros[i] for i in range(len(numeros) - 1)]
    counts = Counter(gaps)
    total = len(gaps)

    entropia = 0
    for count in counts.values():
        p = count / total
        if p > 0:
            entropia -= p * math.log2(p)

    return entropia


def _calcular_coeficiente_gini(numeros, config: GameConfig):
    """
    Coeficiente de Gini normalizado pelo n_numbers.
    Gini = 0 → Perfeitamente distribuído
    Gini → 1 → Muito concentrado
    """
    norm = [(n - 1) / (config.n_numbers - 1) for n in numeros]
    norm_sorted = sorted(norm)

    n = len(norm_sorted)
    if sum(norm_sorted) == 0:
        return 0

    gini = (2 * sum((i + 1) * y for i, y in enumerate(norm_sorted))) / (
        n * sum(norm_sorted)
    ) - (n + 1) / n

    return gini


# ===== MÓDULOS DE ANÁLISE =====


def _analise_tecnica(report, numeros, config: GameConfig, ic_info=None):
    """Validação técnica genérica baseada em intervalos de confiança reais."""
    # Regra 1: Soma com IC
    soma = sum(numeros)

    # Só usa histórico se o tamanho do jogo for igual ao do sorteio
    usar_historico = ic_info and (len(numeros) == config.k)

    if usar_historico:
        ic_80 = ic_info["ic_80"]
        ic_95 = ic_info["ic_95"]

        if ic_80[0] <= soma <= ic_80[1]:
            report["msgs"].append(f"✅ Soma ({soma}) no IC80% [{ic_80[0]}, {ic_80[1]}]")
        elif ic_95[0] <= soma <= ic_95[1]:
            report["score"] -= 10
            report["msgs"].append(f"⚠️ Soma ({soma}) fora do IC80%, mas no IC95%")
        else:
            report["score"] -= 25
            report["msgs"].append(
                f"❌ Soma ({soma}) fora do IC95% [{ic_95[0]}, {ic_95[1]}]"
            )
    else:
        qtd_numeros = len(numeros)
        media_teorica = qtd_numeros * (config.n_numbers + 1) / 2
        desvio_teorico = media_teorica * 0.20

        if abs(soma - media_teorica) <= desvio_teorico:
            report["msgs"].append(
                f"✅ Soma ({soma}) equilibrada (Teórica: ~{media_teorica:.0f})."
            )
        else:
            report["score"] -= 15
            report["msgs"].append(
                f"⚠️ Soma ({soma}) desviada da média teórica ({media_teorica:.0f})."
            )

    # Regra 2: Pares e Ímpares
    qtd_numeros = len(numeros)
    pares = sum(1 for n in numeros if n % 2 == 0)

    ideal_min = int(qtd_numeros * 0.35)
    ideal_max = int(qtd_numeros * 0.65)

    if pares in [0, qtd_numeros]:
        report["score"] -= 25
        report["msgs"].append(
            f"❌ Desequilíbrio extremo Par/Ímpar ({pares}/{qtd_numeros-pares})."
        )
    elif pares < ideal_min or pares > ideal_max:
        report["score"] -= 10
        report["msgs"].append(f"⚠️ Distribuição Par/Ímpar subótima ({pares} pares).")
    else:
        report["msgs"].append(f"✅ Distribuição Par/Ímpar equilibrada ({pares} pares).")

    # Regra 3: Linhas
    if config.layout.rows > 0:
        linhas = _verificar_linhas(numeros, config)
        linhas_vazias = linhas.count(0)

        limit_vazias = max(1, config.layout.rows - int(qtd_numeros / 2))

        if linhas_vazias > limit_vazias:
            report["msgs"].append(
                f"⚠️ {linhas_vazias} linhas vazias (Concentração Vertical)."
            )
            report["score"] -= 5

    # Regra 4: Metades (Superior/Inferior)
    metades = _verificar_metades(numeros, config)
    sup = metades["superior"]
    inf = metades["inferior"]

    if sup == 0 or inf == 0:
        report["score"] -= 20
        report["msgs"].append(
            f"❌ Desequilíbrio total ({sup} superior, {inf} inferior)."
        )
    elif abs(sup - inf) >= qtd_numeros * 0.6:
        report["score"] -= 10
        report["msgs"].append(
            f"⚠️ Desequilíbrio vertical ({sup} superior, {inf} inferior)."
        )

    # Regra 5: Finais
    finais = [n % 10 for n in numeros]
    contagem = Counter(finais)
    max_repeticao = max(contagem.values()) if contagem else 0

    if max_repeticao >= config.final_digit_error:
        report["score"] -= 15
        report["msgs"].append(
            f"❌ Vício de Final: {max_repeticao} números terminam igual."
        )
    elif max_repeticao >= config.final_digit_alert:
        report["score"] -= 5
        report["msgs"].append(
            f"⚠️ Concentração: {max_repeticao} números com final igual."
        )
    else:
        if max_repeticao < config.final_digit_alert:
            report["msgs"].append("✅ Finais bem distribuídos.")


def _analise_entropia(report, numeros, config: GameConfig):
    """Detecta padrões visuais repetitivos."""
    if len(numeros) < 3:
        return

    entropia = _calcular_entropia_shannon(numeros)

    k = len(numeros)
    limiar_baixo = 0.5 if k <= 6 else 1.0
    limiar_alto = 2.0 if k <= 6 else 3.5

    if entropia < limiar_baixo:
        report["score"] -= 25
        report["msgs"].append(
            f"❌ Entropia Baixa ({entropia:.2f}): Padrão visual detectado."
        )
        report["risco_divisao"] = "ALTO"
    elif entropia > limiar_alto:
        report["score"] += 5
        report["msgs"].append(
            f"✅ Entropia Alta ({entropia:.2f}): Excelente aleatoriedade."
        )
    else:
        report["msgs"].append(f"✅ Entropia Normal ({entropia:.2f}).")


def _analise_popularidade(report, numeros, config: GameConfig):
    """Detecta padrões populares que aumentam risco de divisão."""
    seqs = sum(1 for i in range(len(numeros) - 1) if numeros[i + 1] == numeros[i] + 1)
    datas = len([n for n in numeros if n <= 31])
    lost_nums = {4, 8, 15, 16, 23, 42}
    qtd_lost = len(set(numeros).intersection(lost_nums))

    pontos_risco = 0
    qtd = len(numeros)

    # Sequências
    limite_seq = max(1, int(qtd * 0.6))
    if seqs > limite_seq:
        pontos_risco += 2
        report["msgs"].append(f"⚠️ Muitas sequências ({seqs}).")

    # Datas (1-31)
    limite_datas = int(qtd * 0.70)
    if qtd <= 6:
        limite_datas = max(limite_datas, 4)

    if config.n_numbers >= 50 and datas >= limite_datas:
        pontos_risco += 2
        report["msgs"].append(f"⚠️ Foco excessivo em datas ({datas} números <= 31).")

    # Lost numbers
    if qtd_lost >= 4:
        pontos_risco += 3
        report["msgs"].append("⚠️ Padrão 'Lost' detectado.")

    current_risk = report.get("risco_divisao", "Baixo")

    if pontos_risco >= 3 or current_risk == "ALTO":
        report["risco_divisao"] = "ALTO"
        if pontos_risco >= 3:
            report["msgs"].append(
                "💸 Jogo popular (padrões comuns). Risco alto de divisão."
            )
            report["score"] -= 20
    elif pontos_risco >= 1:
        report["risco_divisao"] = "Médio"
        report["score"] -= 10
    else:
        if current_risk != "ALTO":
            report["risco_divisao"] = "Baixo"
            report["msgs"].append("💎 Aposta Blindada: Padrão único.")


def _analise_distribuicao_espacial(report, numeros, config: GameConfig):
    """Análise de distribuição espacial."""
    gini = _calcular_coeficiente_gini(numeros, config)

    if gini < 0.15:
        report["score"] += 5
        report["msgs"].append(f"✅ Distribuição espacial ótima (Gini: {gini:.3f}).")
    elif gini > 0.50:
        report["score"] -= 10
        report["msgs"].append(f"⚠️ Concentração espacial alta (Gini: {gini:.3f}).")
    else:
        report["msgs"].append(f"✅ Distribuição espacial aceitável (Gini: {gini:.3f}).")


def _analise_geometrica(report, numeros, config: GameConfig, df_historico=None):
    """
    Análise geométrica baseada em estatística, não heurística.
    """
    if df_historico is None or df_historico.empty:
        report["msgs"].append("ℹ️ Análise geométrica indisponível (sem histórico)")
        return

    constants = get_constants_for_game(config)
    grupos = {
        "moldura": constants["moldura"],
        "miolo": constants["miolo"],
        "cruz": constants["cruz"],
        "xis": constants["xis"],
        "cantos": constants["cantos"],
    }

    # 1. Calcula distribuições empíricas
    distribuicoes = calcular_distribuicoes_geometricas(df_historico, grupos, config)

    # 2. Avalia o jogo usando estatística
    resultado = avaliar_jogo_geometria_estatistica(
        numeros, grupos, distribuicoes, config
    )

    score_geom = resultado["score_geom"]
    report["metricas"]["score_geom"] = score_geom
    report["metricas"]["geom_detalhes"] = resultado["detalhes"]

    # 3. Penalidades baseadas em significância estatística
    detalhes = resultado["detalhes"]

    extremos = sum(1 for d in detalhes.values() if d["categoria"] == "Extremo")
    muito_raros = sum(1 for d in detalhes.values() if d["categoria"] == "Muito Raro")
    raros = sum(1 for d in detalhes.values() if d["categoria"] == "Raro")

    if extremos >= 2:
        report["score"] -= 15
        report["msgs"].append("⚠️ Múltiplos padrões geométricos extremos (p < 0.001)")
        report["risco_divisao"] = "ALTO"
    elif extremos >= 1:
        report["score"] -= 10
        report["msgs"].append("⚠️ Padrão geométrico extremo detectado")
    elif muito_raros >= 2:
        report["score"] -= 8
        report["msgs"].append("⚠️ Geometria incomum (múltiplos padrões raros)")
    elif raros >= 3:
        report["score"] -= 5
        report["msgs"].append("ℹ️ Alguns padrões geométricos atípicos")
    else:
        report["msgs"].append("✅ Geometria dentro do esperado historicamente")

    # Detalha os padrões mais problemáticos (apenas extremos/muito raros)
    for nome, det in detalhes.items():
        if det["categoria"] in ["Extremo", "Muito Raro"]:
            report["msgs"].append(
                f"  • {nome.title()}: {det['presentes']} números "
                f"(μ={det['media_historica']}, z={det['z_score']})"
            )


def _analise_primos(report, numeros, config: GameConfig):
    """Análise de números primos (só relevante para jogos até 60)."""
    if config.n_numbers > 60:
        return

    primos = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59}
    qtd_primos = len([n for n in numeros if n in primos])

    qtd = len(numeros)
    esperado = int(qtd * 0.3)

    if abs(qtd_primos - esperado) <= 2:
        report["msgs"].append(f"✅ {qtd_primos} números primos (distribuição natural).")
    else:
        report["score"] -= 5
        report["msgs"].append(f"⚠️ {qtd_primos} números primos (atípico).")


def _analises_avancadas(report, numeros, config: GameConfig, df_historico):
    """
    Módulo completo de análises avançadas baseadas em dados.
    - Distância de Hamming
    - Quadrantes estatísticos
    - Regressão à média (informativo)
    """
    if df_historico is None or df_historico.empty:
        return

    # 1. Distância de Hamming
    penalizar_por_similaridade(report, numeros, df_historico, config)

    # 2. Quadrantes estatísticos
    stats_quad = calcular_distribuicao_quadrantes(df_historico, config)
    resultado_quad = avaliar_quadrantes_estatistico(numeros, config, stats_quad)
    report["metricas"]["quadrantes"] = resultado_quad

    if resultado_quad["score_quadrantes"] < 60:
        report["score"] -= 5
        report["msgs"].append("⚠️ Distribuição de quadrantes atípica")

    # 3. Validação de Regressão (informativo apenas)
    regressao = calcular_taxa_regressao(df_historico, config)
    if regressao:
        report["metricas"]["regressao"] = regressao

        if regressao["correlacao"] > 0.2:
            report["msgs"].append(
                f"ℹ️ Evidência de regressão à média (ρ={regressao['correlacao']})"
            )


# ===== FUNÇÃO PRINCIPAL =====


def validar_jogo(
    numeros, config: GameConfig, historico_jogos=None, ic_info=None, df_historico=None
):
    """
    Validador genérico para qualquer jogo.
    Usa análises estatísticas avançadas.
    """
    report = {
        "score": 100,
        "msgs": [],
        "status": "Excelente",
        "risco_divisao": "Baixo",
        "ja_saiu": False,
        "score_original": 0,
        "metricas": {},
    }

    # 1. Verificação de histórico
    if historico_jogos:
        if len(numeros) == config.k:
            jogo_tuple = tuple(sorted(numeros))
            if jogo_tuple in historico_jogos:
                report["ja_saiu"] = True

    # 2. Análises técnicas
    _analise_tecnica(report, numeros, config, ic_info)
    _analise_entropia(report, numeros, config)
    _analise_popularidade(report, numeros, config)
    _analise_distribuicao_espacial(report, numeros, config)
    _analise_geometrica(report, numeros, config, df_historico=df_historico)

    _analise_primos(report, numeros, config)

    # Análises avançadas (Hamming, Quadrantes, Regressão)
    _analises_avancadas(report, numeros, config, df_historico)

    # 3. Calcula score técnico
    score_tecnico = max(0, min(100, report["score"]))
    report["score_original"] = score_tecnico

    # 4. Métricas adicionais
    report["metricas"].update(
        {
            "soma": sum(numeros),
            "entropia": round(_calcular_entropia_shannon(numeros), 3),
            "gini": round(_calcular_coeficiente_gini(numeros, config), 3),
            "pares": sum(1 for n in numeros if n % 2 == 0),
            "sequencias": sum(
                1 for i in range(len(numeros) - 1) if numeros[i + 1] == numeros[i] + 1
            ),
        }
    )

    # 5. Penalidade final
    if report["ja_saiu"]:
        report["score"] = 0
        report["status"] = "⛔ Já Saiu"
        report["msgs"].insert(0, "⛔ Este jogo JÁ FOI SORTEADO! Score zerado.")
    else:
        report["score"] = score_tecnico

        if score_tecnico >= 85:
            report["status"] = "💎 Excelente"
        elif score_tecnico >= 70:
            report["status"] = "✅ Muito Bom"
        elif score_tecnico >= 55:
            report["status"] = "👍 Bom"
        elif score_tecnico >= 40:
            report["status"] = "⚠️ Razoável"
        else:
            report["status"] = "🗑️ Fraco"

    return report
