# app/core/validator.py
import math
import numpy as np
from app.core.logger import logger
from collections import Counter
from app.core.lottery import GameConfig
from app.core.ticket_features import extract_ticket_features
from app.core.statistics.feature_percentiles import summarize_feature_percentiles

from app.core.statistics import (
    avaliar_jogo_geometria_estatistica,
    penalizar_por_similaridade,
    calcular_distribuicao_quadrantes,
    avaliar_quadrantes_estatistico,
    calcular_taxa_regressao,
    calcular_atrasos,
    get_pares_que_se_repelem,
    get_pares_mais_frequentes,
    testar_distribuicao_gaps_bilhete,
    calcular_order_statistics,
    calcular_entropia_faixas,
    detectar_motifs_gaps,
    calcular_min_gap_e_span,
    detectar_multiplos_de_d,
    calcular_simetria_reflexao,
    calcular_indice_compressibilidade,
    PRIMES_ANALYSIS_MAX_N,
)

# Importa detector de padrões avançados
try:
    from app.core.statistics.patterns import analise_completa_padroes

    PATTERNS_AVAILABLE = True
except ImportError:
    PATTERNS_AVAILABLE = False
    logger.warning("Módulo de padrões avançados não disponível")

# Importa constantes com Bonferroni
from app.core.statistics.constants import (
    ajustar_threshold_por_densidade,
    ZSCORE_EXTREME,
    ZSCORE_VERY_RARE,
    ZSCORE_RARE,
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

    # Regra 2: Pares e Ímpares (com ajuste por densidade)
    qtd_numeros = len(numeros)
    pares = sum(1 for n in numeros if n % 2 == 0)

    densidade = config.density
    # Ajusta thresholds por densidade
    ideal_min_base = 0.35
    ideal_max_base = 0.65

    ideal_min = int(
        qtd_numeros * ajustar_threshold_por_densidade(ideal_min_base, densidade)
    )
    ideal_max = int(
        qtd_numeros * ajustar_threshold_por_densidade(ideal_max_base, densidade)
    )

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

    # Regra 5: Finais (com ajuste por densidade)
    finais = [n % 10 for n in numeros]
    contagem = Counter(finais)
    max_repeticao = max(contagem.values()) if contagem else 0

    # Ajusta thresholds por densidade
    final_alert_ajustado = ajustar_threshold_por_densidade(
        config.final_digit_alert, densidade
    )
    final_error_ajustado = ajustar_threshold_por_densidade(
        config.final_digit_error, densidade
    )

    if max_repeticao >= final_error_ajustado:
        report["score"] -= 15
        report["msgs"].append(
            f"❌ Vício de Final: {max_repeticao} números terminam igual."
        )
    elif max_repeticao >= final_alert_ajustado:
        report["score"] -= 5
        report["msgs"].append(
            f"⚠️ Concentração: {max_repeticao} números com final igual."
        )
    else:
        if max_repeticao < final_alert_ajustado:
            report["msgs"].append("✅ Finais bem distribuídos.")


def _analise_entropia(report, numeros, config: GameConfig):
    """Detecta padrões visuais repetitivos (com ajuste por densidade)."""
    if len(numeros) < 3:
        return

    entropia = _calcular_entropia_shannon(numeros)

    k = len(numeros)
    densidade = config.density

    # Ajusta limiares por densidade
    limiar_baixo_base = 0.5 if k <= 6 else 1.0
    limiar_alto_base = 2.0 if k <= 6 else 3.5

    limiar_baixo = ajustar_threshold_por_densidade(limiar_baixo_base, densidade)
    limiar_alto = ajustar_threshold_por_densidade(limiar_alto_base, densidade)

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

    # Calcula densidade para ajustar thresholds
    densidade = config.density

    # Sequências - ajusta baseado na densidade
    if densidade > 0.5:
        # Alta densidade: espera-se muitas sequências
        limite_seq = max(3, int(qtd * ajustar_threshold_por_densidade(0.8, densidade)))
    else:
        # Baixa densidade (Mega-Sena etc)
        limite_seq = max(1, int(qtd * ajustar_threshold_por_densidade(0.6, densidade)))

    if seqs > limite_seq:
        pontos_risco += 2
        report["msgs"].append(f"⚠️ Muitas sequências ({seqs}).")

    # Datas (1-31) - ajustado por densidade
    limite_datas = int(qtd * ajustar_threshold_por_densidade(0.70, densidade))
    if qtd <= 6:
        limite_datas = max(limite_datas, 4)

    if config.n_numbers >= 50 and datas >= limite_datas:
        pontos_risco += 2
        report["msgs"].append(f"⚠️ Foco excessivo em datas ({datas} números <= 31).")

    # Lost numbers - ajusta threshold baseado na densidade
    lost_disponivel = len([n for n in lost_nums if n <= config.n_numbers])
    if densidade > 0.5:
        # Alta densidade: só penaliza se tem todos os Lost disponíveis
        if qtd_lost == lost_disponivel and lost_disponivel >= 4:
            pontos_risco += 1
            report["msgs"].append(
                f"ℹ️ Contém todos números Lost ({qtd_lost}/{lost_disponivel})."
            )
    else:
        # Baixa densidade: 4+ já é suspeito
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
            report["msgs"].append("✅ 🛡️ Aposta Blindada: Padrão único.")


def _analise_numeros_sortudos(report, numeros, config: GameConfig):
    """Penaliza excesso de números sortudos culturais."""
    sortudos = {7, 3, 13, 21, 33, 11, 27, 9}
    qtd_sortudos = len(set(numeros) & sortudos)

    densidade = config.density
    threshold = ajustar_threshold_por_densidade(5, densidade)

    if qtd_sortudos >= threshold:
        report["score"] -= 12
        report["msgs"].append(
            f"🍀 EXCESSO de números 'sortudos': {sorted(set(numeros) & sortudos)} ({qtd_sortudos})"
        )
        if report.get("risco_divisao") != "ALTO":
            report["risco_divisao"] = "Médio"

    report["metricas"]["qtd_sortudos"] = qtd_sortudos


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


def _analise_geometrica(report, numeros, config, distribuicoes_geometricas):
    """Análise geométrica com thresholds Bonferroni."""
    if not distribuicoes_geometricas:
        report["msgs"].append("ℹ️ Análise geométrica indisponível (sem histórico)")
        return

    grupos_geometricos = config.get_geometric_groups()

    resultado = avaliar_jogo_geometria_estatistica(
        numeros, grupos_geometricos, distribuicoes_geometricas, config
    )

    score_geom = resultado["score_geom"]
    report["metricas"]["score_geom"] = score_geom
    report["metricas"]["geom_detalhes"] = resultado["detalhes"]

    # Penalidades baseadas em significância estatística (COM BONFERRONI)
    detalhes = resultado["detalhes"]

    extremos = sum(1 for d in detalhes.values() if d["categoria"] == "Extremo")
    muito_raros = sum(1 for d in detalhes.values() if d["categoria"] == "Muito Raro")
    raros = sum(1 for d in detalhes.values() if d["categoria"] == "Raro")

    if extremos >= 2:
        report["score"] -= 15
        report["msgs"].append(
            f"⚠️ Múltiplos padrões geométricos extremos (p < 0.001) (Geom: {score_geom})."
        )
        report["risco_divisao"] = "ALTO"
    elif extremos >= 1:
        report["score"] -= 10
        report["msgs"].append(
            f"⚠️ Padrão geométrico extremo detectado (Geom: {score_geom})."
        )
    elif muito_raros >= 2:
        report["score"] -= 8
        report["msgs"].append(
            f"⚠️ Geometria incomum (múltiplos padrões raros) (Geom: {score_geom})."
        )
    elif raros >= 3:
        report["score"] -= 5
        report["msgs"].append(
            f"ℹ️ Alguns padrões geométricos atípicos (Geom: {score_geom})"
        )
    else:
        report["msgs"].append(
            f"✅ Geometria dentro do esperado historicamente (Geom: {score_geom})"
        )

    # Detalha os padrões mais problemáticos
    for nome, det in detalhes.items():
        if det["categoria"] in ["Extremo", "Muito Raro"]:
            report["msgs"].append(
                f"  • {nome}: {det['presentes']} números "
                f"(μ={det['media_historica']:.1f}, z={det['z_score']:.2f})"
            )


def _analise_primos(report: dict, numeros: list[int], config: "GameConfig") -> None:
    """Análise de números primos com ajuste por densidade."""
    if config.n_numbers > PRIMES_ANALYSIS_MAX_N:
        return

    primos = {
        2,
        3,
        5,
        7,
        11,
        13,
        17,
        19,
        23,
        29,
        31,
        37,
        41,
        43,
        47,
        53,
        59,
        61,
        67,
        71,
        73,
        79,
        83,
        89,
        97,
    }
    primos_validos = {p for p in primos if p <= config.n_numbers}

    qtd_primos = len([n for n in numeros if n in primos_validos])
    k = len(numeros)

    if k == 0:
        report["metricas"]["qtd_primos"] = 0
        report["metricas"]["primos_esperado"] = 0.0
        report["msgs"].append("⚠️ Análise de primos ignorada: lista de números vazia.")
        return

    # Fração esperada com ajuste por densidade
    densidade = config.density
    frac_primos_universo = len(primos_validos) / config.n_numbers
    esperado_base = k * frac_primos_universo
    esperado = ajustar_threshold_por_densidade(esperado_base, densidade)

    report["metricas"]["qtd_primos"] = qtd_primos
    report["metricas"]["primos_esperado"] = round(esperado, 1)

    # CASO EXTREMO: Todos primos
    if qtd_primos == k and k >= 4:
        report["score"] -= 25
        report["msgs"].append(f"❌ TODOS os {k} números são primos (ultra-raro)")
        report["risco_divisao"] = "ALTO"
        return

    # CASO EXTREMO: Quase todos primos (>= 90%)
    if qtd_primos >= k * 0.9 and k >= 5:
        report["score"] -= 18
        report["msgs"].append(
            f"⚠️ {qtd_primos}/{k} números são primos ({qtd_primos/k*100:.0f}%)"
        )
        return

    # CASO EXTREMO: Zero primos (quando esperado >= 1.5)
    if qtd_primos == 0 and esperado >= 1.5:
        report["score"] -= 15
        report["msgs"].append(f"⚠️ Nenhum número primo (esperado ~{esperado:.1f})")
        return

    # Desvio normal (tolerância ajustada por densidade)
    tolerancia = ajustar_threshold_por_densidade(2.0, densidade)

    if abs(qtd_primos - esperado) <= tolerancia:
        report["msgs"].append(f"✅ {qtd_primos} primos (esperado ~{esperado:.1f})")
    else:
        report["score"] -= 5
        report["msgs"].append(
            f"⚠️ {qtd_primos} primos (atípico, esperado ~{esperado:.1f})"
        )


def _analise_multiplos(report: dict, numeros: list[int], config: "GameConfig") -> None:
    """Analisa concentração de múltiplos de divisores comuns."""
    resultado = detectar_multiplos_de_d(numeros, config)

    # Salva métricas
    report["metricas"]["multiplos"] = {
        "divisor_dominante": resultado["divisor_dominante"],
        "fracao_maxima": resultado["fracao_maxima"],
        "fracao_esperada": resultado["fracao_esperada"],
    }

    # Aplica penalidade
    if resultado["penalidade"] > 0:
        report["score"] -= resultado["penalidade"]
        report["msgs"].append(resultado["conclusao"])

        # Se penalidade alta, marca risco de divisão
        if resultado["penalidade"] >= 15:
            report["risco_divisao"] = "ALTO"


def _analise_quase_reta(report: dict, numeros: list[int], config: "GameConfig") -> None:
    """Detecta se 5+ números estão na mesma linha ou coluna do layout."""
    layout = config.layout
    if not layout or layout.rows == 0 or layout.cols == 0:
        return

    k = len(numeros)
    densidade = config.density

    # Define limiar dinâmico baseado no tamanho do jogo E densidade
    if k <= 6:
        limiar_linha = int(ajustar_threshold_por_densidade(5, densidade))
        limiar_coluna = int(ajustar_threshold_por_densidade(4, densidade))
    elif k <= 10:
        limiar_linha = int(ajustar_threshold_por_densidade(6, densidade))
        limiar_coluna = int(ajustar_threshold_por_densidade(5, densidade))
    else:
        limiar_linha = max(6, int(k * ajustar_threshold_por_densidade(0.4, densidade)))
        limiar_coluna = max(
            5, int(k * ajustar_threshold_por_densidade(0.35, densidade))
        )

    # Conta números por linha e coluna
    contagem_linhas = [0] * layout.rows
    contagem_colunas = [0] * layout.cols

    for num in numeros:
        if num < 1 or num > config.n_numbers:
            continue
        try:
            row, col = layout.pos(num)
            if 0 <= row < layout.rows:
                contagem_linhas[row] += 1
            if 0 <= col < layout.cols:
                contagem_colunas[col] += 1
        except (ValueError, IndexError):
            continue

    max_linha = max(contagem_linhas) if contagem_linhas else 0
    max_coluna = max(contagem_colunas) if contagem_colunas else 0

    # Salva métricas
    report["metricas"]["max_numa_linha"] = max_linha
    report["metricas"]["max_numa_coluna"] = max_coluna

    # Verifica concentração em linha
    if max_linha >= limiar_linha:
        penalidade = 15 if max_linha >= k * 0.8 else 10
        report["score"] -= penalidade
        report["msgs"].append(
            f"❌ {max_linha} números na mesma linha (padrão visual óbvio)"
        )
        report["risco_divisao"] = "ALTO"
        return

    # Verifica concentração em coluna
    if max_coluna >= limiar_coluna:
        penalidade = 12 if max_coluna >= k * 0.7 else 8
        report["score"] -= penalidade
        report["msgs"].append(f"⚠️ {max_coluna} números na mesma coluna")


def _aplicar_raridade_conjunta(report: dict, config: "GameConfig") -> None:
    """Aplica penalidade extra quando múltiplos padrões raros co-ocorrem."""
    metricas = report.get("metricas", {})
    alertas_graves = 0
    detalhes = []

    densidade = config.density

    # Checa flags graves (com ajuste por densidade)

    # 1. Simetria forte
    if metricas.get("pares_simetricos", 0) >= ajustar_threshold_por_densidade(
        2, densidade
    ):
        alertas_graves += 1
        detalhes.append("simetria")

    # 2. Gaps muito regulares
    cv_gaps = metricas.get("cv_gaps")
    cv_threshold = ajustar_threshold_por_densidade(0.2, densidade)
    if cv_gaps is not None and cv_gaps < cv_threshold:
        alertas_graves += 1
        detalhes.append("gaps_regulares")

    # 3. Múltiplos concentrados
    multiplos = metricas.get("multiplos", {})
    multiplos_threshold = ajustar_threshold_por_densidade(0.8, densidade)
    if multiplos.get("fracao_maxima", 0) >= multiplos_threshold:
        alertas_graves += 1
        detalhes.append("multiplos")

    # 4. Span muito baixo
    span_threshold = ajustar_threshold_por_densidade(0.4, densidade)
    if metricas.get("span_relativo", 1.0) < span_threshold:
        alertas_graves += 1
        detalhes.append("span_baixo")

    # 5. Concentração em linha/coluna
    linha_threshold = ajustar_threshold_por_densidade(5, densidade)
    if metricas.get("max_numa_linha", 0) >= linha_threshold:
        alertas_graves += 1
        detalhes.append("linha_concentrada")

    # 6. Entropia muito baixa
    entropia_threshold = ajustar_threshold_por_densidade(1.0, densidade)
    if metricas.get("entropia", 2.0) < entropia_threshold:
        alertas_graves += 1
        detalhes.append("baixa_entropia")

    # Aplica penalidade conjunta
    if alertas_graves >= 3:
        penalidade = 15
        report["score"] -= penalidade
        report["msgs"].append(
            f"❌ 🚨 Raridade conjunta extrema: {alertas_graves} padrões estruturais anômalos ({', '.join(detalhes)})"
        )
        report["risco_divisao"] = "ALTO"
    elif alertas_graves >= 2:
        penalidade = 8
        report["score"] -= penalidade
        report["msgs"].append(
            f"⚠️ Raridade conjunta: {alertas_graves} padrões atípicos ({', '.join(detalhes)})"
        )

    # Salva métrica
    report["metricas"]["alertas_estruturais"] = alertas_graves
    report["metricas"]["detalhes_alertas"] = detalhes


def _analises_avancadas(
    report, numeros, config: GameConfig, df_historico, stats_quadrantes=None
):
    """Módulo completo de análises avançadas baseadas em dados."""
    if df_historico is None or df_historico.empty:
        return

    # 1. Distância de Hamming
    penalizar_por_similaridade(report, numeros, df_historico, config)

    # 2. Quadrantes estatísticos
    if stats_quadrantes:
        resultado_quad = avaliar_quadrantes_estatistico(
            numeros, config, stats_quadrantes
        )
    else:
        stats_quad = calcular_distribuicao_quadrantes(df_historico, config)
        resultado_quad = avaliar_quadrantes_estatistico(numeros, config, stats_quad)

    report["metricas"]["quadrantes"] = resultado_quad
    if resultado_quad["score_quadrantes"] < 60:
        report["score"] -= 5
        report["msgs"].append("⚠️ Distribuição de quadrantes atípica")

    # 3. Validação de Regressão (COM AJUSTE DE SCORE)
    if len(df_historico) >= 100:
        taxa_regressao = calcular_taxa_regressao(df_historico, config, janela=100)

        if taxa_regressao:
            report["metricas"]["regressao_media"] = {
                "correlacao": taxa_regressao["correlacao"],
                "p_value": taxa_regressao["p_value"],
                "taxa_retorno": taxa_regressao["taxa_retorno"],
                "interpretacao": taxa_regressao["interpretacao"],
            }

            # Análise baseada em evidência estatística
            if taxa_regressao["correlacao"] > 0.3 and taxa_regressao["p_value"] < 0.05:
                atrasos = calcular_atrasos(df_historico, config)
                mediana_atrasos = atrasos.median()

                atrasados_no_jogo = [
                    n for n in numeros if atrasos.get(n, 0) > mediana_atrasos
                ]

                proporcao_atrasados = len(atrasados_no_jogo) / len(numeros)

                if proporcao_atrasados >= 0.4:
                    bonus = 5
                    report["score"] += bonus
                    report["msgs"].append(
                        f"✅ Regressão validada: {len(atrasados_no_jogo)} números atrasados "
                        f"(ρ={taxa_regressao['correlacao']:.2f}, p={taxa_regressao['p_value']:.4f})"
                    )
                    report["msgs"].append(
                        f"   Histórico confirma: números atrasados tendem a sair (+{bonus} pts)"
                    )
                elif proporcao_atrasados >= 0.2:
                    report["msgs"].append(
                        f"ℹ️ Regressão detectada: {len(atrasados_no_jogo)} números atrasados "
                        f"(ρ={taxa_regressao['correlacao']:.2f})"
                    )
                else:
                    report["msgs"].append(
                        f"⚠️ Poucos números atrasados ({len(atrasados_no_jogo)}), "
                        f"mas regressão histórica é forte (ρ={taxa_regressao['correlacao']:.2f})"
                    )

            elif 0.1 < taxa_regressao["correlacao"] <= 0.3:
                report["msgs"].append(
                    f"ℹ️ Regressão moderada detectada (ρ={taxa_regressao['correlacao']:.2f}): "
                    "atrasos têm algum poder preditivo"
                )
            else:
                report["msgs"].append(
                    f"ℹ️ Regressão fraca (ρ={taxa_regressao['correlacao']:.2f}): "
                    "atrasos não são bons preditores neste jogo"
                )

        else:
            report["metricas"]["regressao_media"] = "Dados insuficientes"
    else:
        report["metricas"]["regressao_media"] = {
            "status": "Histórico insuficiente",
            "minimo_necessario": 100,
            "disponivel": len(df_historico),
        }


def _analise_coocorrencia_rara(report, numeros, config: GameConfig, df_historico):
    """Detecta se o jogo contém múltiplos pares que NUNCA ou RARAMENTE saíram juntos."""
    if df_historico is None or df_historico.empty or len(df_historico) < 50:
        return

    pares_repelentes = get_pares_que_se_repelem(df_historico, config, top_n=100)

    if not pares_repelentes:
        return

    pares_muito_raros = set()
    for item in pares_repelentes:
        if item["ocorrencias"] == 0 or item["razao"] < 0.3:
            pares_muito_raros.add(item["par"])

    if not pares_muito_raros:
        return

    pares_do_jogo = []
    for i in range(len(numeros)):
        for j in range(i + 1, len(numeros)):
            par = (numeros[i], numeros[j])
            if par in pares_muito_raros:
                pares_do_jogo.append(par)

    n_pares_raros = len(pares_do_jogo)
    total_pares = len(numeros) * (len(numeros) - 1) // 2
    proporcao = n_pares_raros / total_pares if total_pares > 0 else 0

    # Ajusta threshold por densidade
    densidade = config.density
    threshold_alto = ajustar_threshold_por_densidade(0.3, densidade)
    threshold_medio = ajustar_threshold_por_densidade(0.2, densidade)
    threshold_baixo = ajustar_threshold_por_densidade(0.1, densidade)

    if proporcao >= threshold_alto:
        penalidade = 15
        report["score"] -= penalidade
        report["msgs"].append(
            f"⚠️ Combinação rara: {n_pares_raros} pares nunca/raramente co-ocorreram "
            f"({proporcao*100:.0f}% dos pares)"
        )
        report["metricas"]["pares_raros"] = {
            "count": n_pares_raros,
            "proporcao": round(proporcao, 3),
            "exemplos": pares_do_jogo[:3],
        }
    elif proporcao >= threshold_medio:
        penalidade = 8
        report["score"] -= penalidade
        report["msgs"].append(
            f"ℹ️ Alguns pares raros: {n_pares_raros} pares com baixa co-ocorrência histórica"
        )
        report["metricas"]["pares_raros"] = {
            "count": n_pares_raros,
            "proporcao": round(proporcao, 3),
        }
    elif proporcao >= threshold_baixo:
        report["msgs"].append(
            f"ℹ️ Contém {n_pares_raros} pares com baixa co-ocorrência histórica"
        )


def _analise_pares_populares(report, numeros, config: GameConfig, df_historico):
    """Detecta se o jogo contém muitos pares POPULARES."""
    if df_historico is None or df_historico.empty or len(df_historico) < 50:
        return

    pares_frequentes = get_pares_mais_frequentes(df_historico, config, top_n=50)

    if not pares_frequentes:
        return

    pares_populares = set()
    for item in pares_frequentes:
        if item["razao"] >= 1.3:
            pares_populares.add(item["par"])

    if not pares_populares:
        return

    pares_do_jogo = []
    for i in range(len(numeros)):
        for j in range(i + 1, len(numeros)):
            par = (numeros[i], numeros[j])
            if par in pares_populares:
                pares_do_jogo.append(par)

    n_pares_populares = len(pares_do_jogo)
    total_pares = len(numeros) * (len(numeros) - 1) // 2
    proporcao = n_pares_populares / total_pares if total_pares > 0 else 0

    # Ajusta threshold por densidade
    densidade = config.density
    threshold_alto = ajustar_threshold_por_densidade(0.3, densidade)
    threshold_medio = ajustar_threshold_por_densidade(0.2, densidade)

    if proporcao >= threshold_alto:
        report["msgs"].append(
            f"💸 Risco de divisão: {n_pares_populares} pares muito populares "
            f"({proporcao*100:.0f}% dos pares)"
        )
        report["metricas"]["pares_populares"] = {
            "count": n_pares_populares,
            "proporcao": round(proporcao, 3),
            "exemplos": pares_do_jogo[:3],
        }
        if report.get("risco_divisao") != "ALTO":
            report["risco_divisao"] = "Médio"
    elif proporcao >= threshold_medio:
        report["msgs"].append(
            f"ℹ️ Alguns pares populares: {n_pares_populares} pares frequentes no histórico"
        )
        report["metricas"]["pares_populares"] = {
            "count": n_pares_populares,
            "proporcao": round(proporcao, 3),
        }


def _analise_estrutural(report: dict, numeros: list[int], config: GameConfig) -> None:
    """Análise estrutural consolidada: span, gaps, motifs, simetria."""
    # 1. Min-gap e Span (calculados juntos para otimização)
    metricas_gaps = calcular_min_gap_e_span(numeros, config)
    if "erro" in metricas_gaps:
        return

    report["metricas"]["min_gap"] = metricas_gaps["min_gap"]
    report["metricas"]["span"] = metricas_gaps["span"]
    report["metricas"]["span_relativo"] = metricas_gaps["span_relativo"]

    # Penalidade por span extremo (ajustado por densidade)
    densidade = config.density
    span_esperado = config.n_numbers * (len(numeros) - 1) / (len(numeros) + 1)

    threshold_baixo = ajustar_threshold_por_densidade(0.4, densidade)
    threshold_medio = ajustar_threshold_por_densidade(0.6, densidade)
    threshold_alto = ajustar_threshold_por_densidade(1.4, densidade)

    if metricas_gaps["span"] < span_esperado * threshold_baixo:
        report["score"] -= 15
        report["msgs"].append(
            f"❌ Span muito baixo ({metricas_gaps['span']}): números muito concentrados"
        )
    elif metricas_gaps["span"] < span_esperado * threshold_medio:
        report["score"] -= 8
        report["msgs"].append(
            f"⚠️ Span baixo ({metricas_gaps['span']}): possível concentração"
        )
    elif metricas_gaps["span"] > span_esperado * threshold_alto:
        report["msgs"].append(
            f"ℹ️ Span alto ({metricas_gaps['span']}): boa cobertura do volante"
        )
    else:
        report["msgs"].append(f"✅ Span adequado ({metricas_gaps['span']})")

    # 2. Teste de distribuição de gaps
    teste_gaps = testar_distribuicao_gaps_bilhete(numeros, config)
    if "erro" not in teste_gaps and teste_gaps.get("penalidade", 0) > 0:
        report["score"] -= teste_gaps["penalidade"]
        report["msgs"].append(teste_gaps["conclusao"])
    report["metricas"]["cv_gaps"] = teste_gaps.get("cv_gaps")

    # 3. Detecção de motifs (padrões repetitivos)
    motifs = detectar_motifs_gaps(numeros, config)
    if motifs["motif_detectado"]:
        report["score"] -= motifs["penalidade"]
        report["msgs"].append(f"🔄 {motifs['tipo_motif']}")
        report["risco_divisao"] = "ALTO"

    # 4. Simetria por reflexão
    simetria = calcular_simetria_reflexao(numeros, config)
    if simetria["penalidade"] > 0:
        report["score"] -= simetria["penalidade"]
        report["msgs"].append(simetria["conclusao"])
    report["metricas"]["pares_simetricos"] = simetria["n_pares"]


def _analise_order_statistics(
    report: dict, numeros: list[int], config: GameConfig
) -> None:
    """Análise de order statistics (posições esperadas)."""
    order_stats = calcular_order_statistics(numeros, config)

    if order_stats["penalidade"] > 0:
        report["score"] -= order_stats["penalidade"]
        report["msgs"].append(order_stats["conclusao"])

    report["metricas"]["desvio_posicional"] = order_stats["desvio_medio"]


def _analise_entropia_faixas(
    report: dict, numeros: list[int], config: GameConfig
) -> None:
    """Análise de entropia por faixas do volante."""
    entropia_faixas = calcular_entropia_faixas(numeros, config)

    if entropia_faixas["penalidade"] > 0:
        report["score"] -= entropia_faixas["penalidade"]
        report["msgs"].append(entropia_faixas["conclusao"])

    report["metricas"]["entropia_faixas"] = entropia_faixas["entropia_normalizada"]
    report["metricas"]["faixas_vazias"] = entropia_faixas["faixas_vazias"]


def _analise_padroes_avancados(
    report: dict, numeros: list[int], config: GameConfig
) -> None:
    """
    Análise completa de padrões avançados.

    Detecta:
    - PA com qualquer razão
    - Sequências longas
    - Diagonais no volante
    - Bordas extremas
    """
    if not PATTERNS_AVAILABLE:
        return

    try:
        resultado = analise_completa_padroes(numeros, config)

        # Aplica penalidade total
        if resultado["penalidade_total"] > 0:
            report["score"] -= resultado["penalidade_total"]

        # Adiciona conclusões
        report["msgs"].extend(resultado["conclusoes"])

        # Salva detalhes
        report["metricas"]["padroes_avancados"] = {
            "padroes_detectados": resultado["padroes_detectados"],
            "penalidade_total": resultado["penalidade_total"],
            "detalhes": resultado["detalhes"],
        }

        # Se detectou múltiplos padrões graves, marca risco alto
        if resultado["padroes_detectados"] >= 2:
            report["risco_divisao"] = "ALTO"

    except Exception as e:
        logger.error(f"Erro na análise de padrões avançados: {e}")


# ===== FUNÇÕES DE SCORE =====


def calcular_score_rapido(
    numeros: list[int],
    config: "GameConfig",
    ic_info: dict = None,
    historico_jogos: set = None,
) -> int:
    """
    Score rápido para filtragem interna dos geradores.
    Versão 2.1: Penalidades calibradas para alinhar com validador completo.

    O validador completo aplica ~20 análises diferentes. Este score rápido
    aplica as 10 mais impactantes com penalidades ajustadas para que o
    score final seja aproximado ao do validador completo.

    Verificações realizadas (em ordem de impacto):
    1. Jogo já sorteado (retorna 0 imediatamente)
    2. Soma dentro do IC95/IC80
    3. Paridade equilibrada
    4. Entropia mínima (detecta PAs e sequências óbvias)
    5. Span mínimo
    6. Finais repetidos (vício de terminal)
    7. Metades (superior/inferior)
    8. Concentração em linhas (layout)
    9. Números sortudos em excesso
    10. Múltiplos dominantes

    Args:
        numeros: Lista de números do jogo (já ordenados)
        config: Configuração do jogo
        ic_info: Informações de intervalo de confiança (opcional)
        historico_jogos: Set de jogos já sorteados como tuplas (opcional)

    Returns:
        Score inteiro de 0 a 100
    """
    # Base score ajustado: validador completo tende a dar scores mais baixos
    # devido às múltiplas análises. Começamos com 85 para compensar.
    score = 85
    k = len(numeros)
    numeros_sorted = sorted(numeros)

    # 1. Já saiu? (eliminação imediata)
    if historico_jogos and tuple(numeros_sorted) in historico_jogos:
        return 0

    # 2. Soma (IC95 e IC80)
    soma = sum(numeros)
    if ic_info:
        ic_95 = ic_info.get("ic_95")
        ic_80 = ic_info.get("ic_80")

        if ic_95 and len(ic_95) == 2:
            # Ajusta IC para o tamanho real da aposta se diferente
            if k != config.k:
                fator = k / config.k
                ic_min_95, ic_max_95 = ic_95[0] * fator, ic_95[1] * fator
                ic_min_80 = ic_80[0] * fator if ic_80 else ic_min_95 * 1.05
                ic_max_80 = ic_80[1] * fator if ic_80 else ic_max_95 * 0.95
            else:
                ic_min_95, ic_max_95 = ic_95[0], ic_95[1]
                ic_min_80 = ic_80[0] if ic_80 else ic_min_95 * 1.05
                ic_max_80 = ic_80[1] if ic_80 else ic_max_95 * 0.95

            if not (ic_min_95 <= soma <= ic_max_95):
                score -= 30  # Fora do IC95 - penalidade severa
            elif not (ic_min_80 <= soma <= ic_max_80):
                score -= 12  # Fora do IC80 mas dentro do IC95

    # 3. Paridade (pares vs ímpares)
    pares = sum(1 for n in numeros if n % 2 == 0)
    if pares in [0, k]:
        # Extremo: todos pares ou todos ímpares - penalidade severa
        score -= 30
    elif pares < k * 0.15 or pares > k * 0.85:
        # Muito desequilibrado (ex: 2/15 ou 13/15 para Lotofácil)
        score -= 12
    elif pares < k * 0.25 or pares > k * 0.75:
        # Desequilibrado
        score -= 8

    # 4. Entropia (detecta sequências e PAs)
    penalidade_entropia = 0
    if k >= 3:
        gaps = [numeros_sorted[i + 1] - numeros_sorted[i] for i in range(k - 1)]
        unique_gaps = len(set(gaps))

        # Todos os gaps iguais = PA perfeita (muito previsível)
        if unique_gaps == 1:
            penalidade_entropia = 30
        # Poucos gaps únicos = padrão repetitivo
        elif unique_gaps <= 2 and k >= 6:
            penalidade_entropia = 15

        # Detecta sequências longas (consecutivos)
        max_seq = 1
        current_seq = 1
        for g in gaps:
            if g == 1:
                current_seq += 1
                max_seq = max(max_seq, current_seq)
            else:
                current_seq = 1

        # Usa a MAIOR penalidade entre entropia e sequência (evita dupla contagem)
        penalidade_seq = 0
        if max_seq >= 5:
            penalidade_seq = 12
        elif max_seq >= 4:
            penalidade_seq = 6

        score -= max(penalidade_entropia, penalidade_seq)

    # 5. Span mínimo
    span = numeros_sorted[-1] - numeros_sorted[0]
    span_minimo = config.n_numbers * 0.35
    if span < span_minimo:
        score -= 20
    elif span < config.n_numbers * 0.45:
        score -= 10

    # 6. Finais repetidos (vício de terminal)
    finais = [n % 10 for n in numeros]
    contagem_finais = Counter(finais)
    max_final = max(contagem_finais.values()) if contagem_finais else 0

    # Penalidade calibrada para o tamanho do jogo
    limite_final_error = max(4, int(k * 0.35))
    limite_final_alert = max(3, int(k * 0.25))

    if max_final >= limite_final_error:
        score -= 18
    elif max_final >= limite_final_alert:
        score -= 8

    # 7. Metades (Superior/Inferior)
    meio = config.n_numbers // 2
    superior = sum(1 for n in numeros if n <= meio)
    inferior = k - superior

    if superior == 0 or inferior == 0:
        score -= 25
    elif abs(superior - inferior) >= k * 0.6:
        score -= 12

    # 8. Concentração em linhas (se layout disponível)
    layout = config.layout
    if layout and layout.rows > 0 and layout.cols > 0:
        contagem_linhas = [0] * layout.rows
        for num in numeros:
            if 1 <= num <= config.n_numbers:
                linha_idx = (num - 1) // layout.cols
                if 0 <= linha_idx < layout.rows:
                    contagem_linhas[linha_idx] += 1

        max_linha = max(contagem_linhas) if contagem_linhas else 0
        limite_linha = max(4, int(k * 0.45))

        if max_linha >= limite_linha:
            score -= 12

    # 9. Números sortudos em excesso (risco de divisão)
    # Nota: Penalidade moderada - o validador completo considera mais fatores
    sortudos = {7, 3, 13, 21, 33, 11, 27, 9}
    qtd_sortudos = len(set(numeros) & sortudos)
    if qtd_sortudos >= 6:
        score -= 10
    elif qtd_sortudos >= 5:
        score -= 5

    # 10. Múltiplos dominantes
    for d in [5, 10, 3]:
        multiplos = sum(1 for n in numeros if n % d == 0)
        fracao = multiplos / k
        if fracao >= 0.7:
            score -= 12
            break
        elif fracao >= 0.55:
            score -= 6
            break

    # Garante que o score fique entre 0 e 100
    return max(0, min(100, score))


# ===== FUNÇÃO PRINCIPAL =====


def validar_jogo(
    numeros,
    config: GameConfig,
    historico_jogos=None,
    ic_info=None,
    df_historico=None,
    distribuicoes_geometricas: dict = None,
    stats_quadrantes=None,
):
    """
    Validador genérico para qualquer jogo.
    Usa análises estatísticas avançadas com correção de Bonferroni.

    - Correção de Bonferroni (α = 0.0033)
    - Ajustes por densidade em todas as análises
    - Detecção de PA genérica (qualquer razão)
    - Padrões avançados (sequências longas, diagonais, bordas)
    - Validação de regressão à média
    """
    logger.debug(f"🔍 [VALIDATOR] Validando jogo {numeros} ({config.name})")

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

    # ============================================
    # 2. ANÁLISES TÉCNICAS BÁSICAS
    # ============================================
    _analise_tecnica(report, numeros, config, ic_info)
    _analise_entropia(report, numeros, config)
    _analise_popularidade(report, numeros, config)
    _analise_numeros_sortudos(report, numeros, config)
    _analise_distribuicao_espacial(report, numeros, config)

    # ============================================
    # 3. ANÁLISE GEOMÉTRICA (COM BONFERRONI)
    # ============================================
    _analise_geometrica(report, numeros, config, distribuicoes_geometricas)

    # ============================================
    # 4. ANÁLISES MATEMÁTICAS
    # ============================================
    _analise_primos(report, numeros, config)
    _analise_multiplos(report, numeros, config)
    _analise_quase_reta(report, numeros, config)

    # ============================================
    # 5. ANÁLISES AVANÇADAS (Hamming, Quadrantes, Regressão)
    # ============================================
    _analises_avancadas(report, numeros, config, df_historico, stats_quadrantes)

    # ============================================
    # 6. ANÁLISE DE CO-OCORRÊNCIA
    # ============================================
    _analise_coocorrencia_rara(report, numeros, config, df_historico)
    _analise_pares_populares(report, numeros, config, df_historico)

    # ============================================
    # 7. ANÁLISES ESTRUTURAIS
    # ============================================
    _analise_estrutural(report, numeros, config)
    _analise_order_statistics(report, numeros, config)
    _analise_entropia_faixas(report, numeros, config)

    # ============================================
    # 8. PADRÕES AVANÇADOS (NOVO)
    # ============================================
    _analise_padroes_avancados(report, numeros, config)

    # ============================================
    # 9. RARIDADE CONJUNTA (Fase 2)
    # ============================================
    _aplicar_raridade_conjunta(report, config)

    # ============================================
    # 10. ÍNDICE DE COMPRESSIBILIDADE (Fase 2)
    # ============================================
    compressibilidade = calcular_indice_compressibilidade(report, config)
    report["metricas"]["compressibilidade"] = compressibilidade

    # ============================================
    # 11. CALCULA SCORE TÉCNICO FINAL
    # ============================================
    score_tecnico = max(0, min(100, report["score"]))
    report["score_original"] = score_tecnico

    # ============================================
    # 12. MÉTRICAS ADICIONAIS
    # ============================================
    features = extract_ticket_features(numeros, config)
    percentil_info = summarize_feature_percentiles(numeros, config)
    report["metricas"].update(
        {
            "soma": features.soma,
            "entropia": round(_calcular_entropia_shannon(numeros), 3),
            "gini": round(_calcular_coeficiente_gini(numeros, config), 3),
            "pares": features.pares,
            "sequencias": features.sequencias,
            "span": features.span,
            "span_relativo": round(features.span_relativo, 3),
            "max_sequencia": features.max_sequencia,
            "max_final_repetido": features.max_final_repetido,
            "compressibilidade_simples": features.compressibilidade_simples,
            **percentil_info,
        }
    )

    # ============================================
    # 13. PENALIDADE FINAL E STATUS
    # ============================================
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

    # Logging final
    if report["ja_saiu"]:
        logger.warning(f"⚠️ [VALIDATOR] Jogo JÁ SAIU: {numeros}")

    if report["score"] < 50:
        logger.info(f"⚠️ [VALIDATOR] Score baixo ({report['score']}): {numeros}")

    logger.debug(
        f"✅ [VALIDATOR] Resultado: score={report['score']}, "
        f"geom={report['metricas'].get('score_geom', 'N/A')}, "
        f"risco={report['risco_divisao']}, "
        f"padrões_avançados={report['metricas'].get('padroes_avancados', {}).get('padroes_detectados', 0)}"
    )

    return report
