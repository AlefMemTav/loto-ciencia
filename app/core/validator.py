# app/core/validator.py
import math
import numpy as np
from app.core.logger import logger
from collections import Counter
from app.core.lottery import GameConfig

from app.core.statistics import (
    avaliar_jogo_geometria_estatistica,
    penalizar_por_similaridade,
    calcular_distribuicao_quadrantes,
    avaliar_quadrantes_estatistico,
    calcular_taxa_regressao,
    calcular_atrasos,
    get_pares_que_se_repelem,
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


def _analise_geometrica(report, numeros, config, distribuicoes_geometricas):
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

    # Penalidades baseadas em significância estatística
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


def _analises_avancadas(
    report, numeros, config: GameConfig, df_historico, stats_quadrantes=None
):
    """
    Módulo completo de análises avançadas baseadas em dados.

    - Distância de Hamming
    - Quadrantes estatísticos
    - Regressão à média
    """
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
        # fallback (recalcula se necessário)
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
            # Adiciona métricas ao report
            report["metricas"]["regressao_media"] = {
                "correlacao": taxa_regressao["correlacao"],
                "p_value": taxa_regressao["p_value"],
                "taxa_retorno": taxa_regressao["taxa_retorno"],
                "interpretacao": taxa_regressao["interpretacao"],
            }

            # ANÁLISE 1: Regressão estatisticamente significativa
            if taxa_regressao["correlacao"] > 0.3 and taxa_regressao["p_value"] < 0.05:
                # Regressão validada! Números atrasados importam
                atrasos = calcular_atrasos(df_historico, config)
                mediana_atrasos = atrasos.median()

                # Conta quantos números do jogo estão atrasados
                atrasados_no_jogo = [
                    n for n in numeros if atrasos.get(n, 0) > mediana_atrasos
                ]

                proporcao_atrasados = len(atrasados_no_jogo) / len(numeros)

                # BONIFICAÇÃO: Se 40%+ do jogo são números atrasados
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

                # NEUTRO: Entre 20% e 40%
                elif proporcao_atrasados >= 0.2:
                    report["msgs"].append(
                        f"ℹ️ Regressão detectada: {len(atrasados_no_jogo)} números atrasados "
                        f"(ρ={taxa_regressao['correlacao']:.2f})"
                    )

                # ALERTA: Menos de 20% de atrasados
                else:
                    report["msgs"].append(
                        f"⚠️ Poucos números atrasados ({len(atrasados_no_jogo)}), "
                        f"mas regressão histórica é forte (ρ={taxa_regressao['correlacao']:.2f})"
                    )

            # ANÁLISE 2: Regressão moderada (0.1 < ρ < 0.3)
            elif 0.1 < taxa_regressao["correlacao"] <= 0.3:
                report["msgs"].append(
                    f"ℹ️ Regressão moderada detectada (ρ={taxa_regressao['correlacao']:.2f}): "
                    "atrasos têm algum poder preditivo"
                )

            # ANÁLISE 3: Regressão fraca ou inexistente
            else:
                report["msgs"].append(
                    f"ℹ️ Regressão fraca (ρ={taxa_regressao['correlacao']:.2f}): "
                    "atrasos não são bons preditores neste jogo"
                )

                # INSIGHT ADICIONAL: Se o jogo tem muitos atrasados mas regressão é fraca
                if len(df_historico) > 0:
                    atrasos = calcular_atrasos(df_historico, config)
                    mediana_atrasos = atrasos.median()
                    atrasados_no_jogo = [
                        n for n in numeros if atrasos.get(n, 0) > mediana_atrasos
                    ]

                    if len(atrasados_no_jogo) >= len(numeros) * 0.5:
                        report["msgs"].append(
                            "   ⚠️ Cuidado: jogo tem muitos atrasados, mas histórico "
                            "não valida essa estratégia"
                        )

        else:
            # Erro no cálculo ou dados insuficientes
            report["metricas"]["regressao_media"] = "Dados insuficientes"

    else:
        # Menos de 100 sorteios no histórico
        report["metricas"]["regressao_media"] = {
            "status": "Histórico insuficiente",
            "minimo_necessario": 100,
            "disponivel": len(df_historico),
        }


def _analise_coocorrencia_rara(report, numeros, config: GameConfig, df_historico):
    """
    Detecta se o jogo contém múltiplos pares que NUNCA ou RARAMENTE saíram juntos.
    
    Filosofia: Não tentamos prever o futuro, mas evitamos combinações
    estatisticamente raras (pares que historicamente quase nunca co-ocorrem).
    
    Se um jogo tem muitos pares "repelentes", é estatisticamente improvável,
    mesmo que cada número individualmente seja comum.
    """
    if df_historico is None or df_historico.empty or len(df_historico) < 50:
        # Dados insuficientes para análise confiável
        return
    
    # Pega os 100 pares que mais se repelem (menor co-ocorrência)
    pares_repelentes = get_pares_que_se_repelem(df_historico, config, top_n=100)
    
    if not pares_repelentes:
        return
    
    # Cria set dos pares repelentes para lookup rápido
    # Considera apenas pares que apareceram ZERO vezes ou muito poucas (razão < 0.3)
    pares_muito_raros = set()
    for item in pares_repelentes:
        if item['ocorrencias'] == 0 or item['razao'] < 0.3:
            pares_muito_raros.add(item['par'])
    
    if not pares_muito_raros:
        return
    
    # Verifica quantos pares do jogo atual estão na lista de repelentes
    pares_do_jogo = []
    for i in range(len(numeros)):
        for j in range(i + 1, len(numeros)):
            par = (numeros[i], numeros[j])
            if par in pares_muito_raros:
                pares_do_jogo.append(par)
    
    # Penalização baseada na quantidade de pares raros
    n_pares_raros = len(pares_do_jogo)
    total_pares = len(numeros) * (len(numeros) - 1) // 2
    proporcao = n_pares_raros / total_pares if total_pares > 0 else 0
    
    # Se mais de 20% dos pares são historicamente raros, penalizar
    if proporcao >= 0.3:
        # Muitos pares raros - combinação muito improvável
        penalidade = 15
        report["score"] -= penalidade
        report["msgs"].append(
            f"⚠️ Combinação rara: {n_pares_raros} pares nunca/raramente co-ocorreram "
            f"({proporcao*100:.0f}% dos pares)"
        )
        report["metricas"]["pares_raros"] = {
            "count": n_pares_raros,
            "proporcao": round(proporcao, 3),
            "exemplos": pares_do_jogo[:3]  # Mostra até 3 exemplos
        }
    elif proporcao >= 0.2:
        # Alguns pares raros - alerta moderado
        penalidade = 8
        report["score"] -= penalidade
        report["msgs"].append(
            f"ℹ️ Alguns pares raros: {n_pares_raros} pares com baixa co-ocorrência histórica"
        )
        report["metricas"]["pares_raros"] = {
            "count": n_pares_raros,
            "proporcao": round(proporcao, 3)
        }
    elif proporcao >= 0.1:
        # Poucos pares raros - apenas informativo
        report["msgs"].append(
            f"ℹ️ Contém {n_pares_raros} pares com baixa co-ocorrência histórica"
        )


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
    Usa análises estatísticas avançadas.
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

    if report["ja_saiu"]:
        logger.warning(f"⚠️ [VALIDATOR] Jogo JÁ SAIU: {numeros}")

    if report["score"] < 50:
        logger.info(f"⚠️ [VALIDATOR] Score baixo ({report['score']}): {numeros}")

    logger.debug(
        f"✅ [VALIDATOR] Resultado: score={report['score']}, "
        f"geom={report['metricas'].get('score_geom', 'N/A')}, "
        f"risco={report['risco_divisao']}"
    )

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
    _analise_geometrica(report, numeros, config, distribuicoes_geometricas)

    _analise_primos(report, numeros, config)

    # Análises avançadas (Hamming, Quadrantes, Regressão)
    _analises_avancadas(report, numeros, config, df_historico, stats_quadrantes)
    
    # Análise de co-ocorrência rara (evita pares que historicamente não saem juntos)
    _analise_coocorrencia_rara(report, numeros, config, df_historico)

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
