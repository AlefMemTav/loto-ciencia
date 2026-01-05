import math
import numpy as np
from collections import Counter

from app.src.constants import QUAD_GEO_Q1, QUAD_GEO_Q2, QUAD_GEO_Q3, QUAD_GEO_Q4


# ===== FUNÇÕES DE ANÁLISE ESPACIAL ====


def _verificar_linhas(numeros):
    """
    Usa o layout REAL do volante (6 linhas × 10 colunas).
    Retorna [linha1, linha2, linha3, linha4, linha5, linha6].
    """
    contagem = [0] * 6

    for num in numeros:
        if 1 <= num <= 10:
            contagem[0] += 1
        elif 11 <= num <= 20:
            contagem[1] += 1
        elif 21 <= num <= 30:
            contagem[2] += 1
        elif 31 <= num <= 40:
            contagem[3] += 1
        elif 41 <= num <= 50:
            contagem[4] += 1
        elif 51 <= num <= 60:
            contagem[5] += 1

    return contagem


def _verificar_quadrantes(numeros):
    """
    Quadrantes geométricos (layout 6×10 => quadrantes 3×5).
    Q1: superior esquerdo; Q2: superior direito; Q3: inferior esquerdo; Q4: inferior direito.
    """
    s = set(numeros)
    q1 = len(s.intersection(QUAD_GEO_Q1))
    q2 = len(s.intersection(QUAD_GEO_Q2))
    q3 = len(s.intersection(QUAD_GEO_Q3))
    q4 = len(s.intersection(QUAD_GEO_Q4))
    return [q1, q2, q3, q4]


def _verificar_metades(numeros):
    """Divide em Superior (1-30) e Inferior (31-60)."""
    superior = len([n for n in numeros if n <= 30])
    inferior = len([n for n in numeros if n > 30])

    return {"superior": superior, "inferior": inferior}


# ===== FUNÇÕES DE CÁLCULO =====


def _calcular_entropia_shannon(numeros):
    """
    Entropia de Shannon baseada nos intervalos (gaps).
    Detecta padrões visuais repetitivos.
    """
    gaps = [numeros[i + 1] - numeros[i] for i in range(len(numeros) - 1)]
    counts = Counter(gaps)
    total = len(gaps)

    entropia = 0
    for count in counts.values():
        p = count / total
        if p > 0:
            entropia -= p * math.log2(p)

    return entropia


def _calcular_coeficiente_gini(numeros):
    """
    Coeficiente de Gini para medir distribuição.
    Gini = 0 → Perfeitamente distribuído
    Gini → 1 → Muito concentrado
    """
    norm = [(n - 1) / 59 for n in numeros]
    norm_sorted = sorted(norm)

    n = len(norm_sorted)
    gini = (2 * sum((i + 1) * y for i, y in enumerate(norm_sorted))) / (
        n * sum(norm_sorted)
    ) - (n + 1) / n

    return gini


# ===== MÓDULOS DE ANÁLISE =====


def _analise_tecnica(report, numeros, ic_info=None):
    """
    Validação baseada em intervalos de confiança REAIS.
    """
    # Regra 1: Soma com IC baseado em dados históricos
    soma = sum(numeros)

    if ic_info:
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
        # Fallback: usa cálculo teórico
        if 140 <= soma <= 240:
            report["msgs"].append(f"✅ Soma ({soma}) na faixa esperada.")
        else:
            report["score"] -= 20
            report["msgs"].append(f"❌ Soma ({soma}) fora da faixa [140-240].")

    # Regra 2: Pares e Ímpares
    pares = sum(1 for n in numeros if n % 2 == 0)

    if pares in [0, 6]:
        report["score"] -= 25
        report["msgs"].append("❌ Desequilíbrio extremo Par/Ímpar (6/0 ou 0/6).")
    elif pares not in [2, 3, 4]:
        report["score"] -= 10
        report["msgs"].append(f"⚠️ Distribuição Par/Ímpar subótima ({pares} pares).")
    else:
        report["msgs"].append(f"✅ Distribuição Par/Ímpar equilibrada ({pares} pares).")

    # Regra 3: LINHAS
    linhas = _verificar_linhas(numeros)
    linhas_vazias = linhas.count(0)

    if linhas_vazias >= 3:
        report["score"] -= 20
        report["msgs"].append(
            f"❌ {linhas_vazias} linhas vazias (muito concentrado verticalmente)."
        )
    elif linhas_vazias == 2:
        report["score"] -= 10
        report["msgs"].append("⚠️ 2 linhas vazias (concentração moderada).")
    else:
        report["msgs"].append(
            f"✅ Apenas {linhas_vazias} linha(s) vazia(s) (boa distribuição vertical)."
        )

    # Regra 4: Metades (Superior/Inferior)
    metades = _verificar_metades(numeros)
    sup = metades["superior"]
    inf = metades["inferior"]

    if sup in [0, 6] or inf in [0, 6]:
        report["score"] -= 15
        report["msgs"].append(
            f"❌ Desequilíbrio vertical extremo ({sup} superior, {inf} inferior)."
        )
    elif abs(sup - inf) >= 4:
        report["score"] -= 5
        report["msgs"].append(
            f"⚠️ Leve desequilíbrio vertical ({sup} superior, {inf} inferior)."
        )

    # Regra 5: Finais
    finais = [n % 10 for n in numeros]
    contagem = Counter(finais)
    max_repeticao = max(contagem.values())

    if max_repeticao >= 4:
        report["score"] -= 20
        report["msgs"].append(f"❌ {max_repeticao} números com mesmo final.")
    elif max_repeticao == 3:
        report["score"] -= 5
        report["msgs"].append(f"⚠️ 3 números com mesmo final.")
    else:
        report["msgs"].append("✅ Finais bem distribuídos.")


def _analise_entropia(report, numeros):
    """Detecta padrões visuais no volante."""
    entropia = _calcular_entropia_shannon(numeros)

    if entropia < 1.0:
        report["score"] -= 30
        report["msgs"].append(
            f"❌ Entropia Baixa ({entropia:.2f}): Padrão visual detectado."
        )
        report["risco_divisao"] = "ALTO"
    elif entropia > 2.0:
        report["score"] += 5
        report["msgs"].append(
            f"✅ Entropia Alta ({entropia:.2f}): Excelente aleatoriedade."
        )
    else:
        report["msgs"].append(f"✅ Entropia Normal ({entropia:.2f}).")


def _analise_popularidade(report, numeros):
    """Detecta padrões populares que aumentam risco de divisão de prêmio."""
    seqs = sum(1 for i in range(len(numeros) - 1) if numeros[i + 1] == numeros[i] + 1)
    datas = len([n for n in numeros if n <= 31])
    lost_nums = {4, 8, 15, 16, 23, 42}
    qtd_lost = len(set(numeros).intersection(lost_nums))

    pontos_risco = 0

    if seqs > 1:
        pontos_risco += 2
    if datas >= 4:
        pontos_risco += 2
    if qtd_lost >= 4:
        pontos_risco += 3

    current_risk = report.get("risco_divisao", "Baixo")

    if pontos_risco >= 3 or current_risk == "ALTO":
        report["risco_divisao"] = "ALTO"
        if pontos_risco >= 3:
            report["msgs"].append(
                "💸 Jogo popular (múltiplas datas/Lost). Risco alto de divisão."
            )
            report["score"] -= 20
    elif pontos_risco >= 1:
        report["risco_divisao"] = "Médio"
        report["msgs"].append("⚠️ Contém padrões populares (Datas ou Sequências).")
        report["score"] -= 10
    else:
        if current_risk != "ALTO":
            report["risco_divisao"] = "Baixo"
            report["msgs"].append("💎 Aposta Blindada: Padrão único.")


def _analise_distribuicao_espacial(report, numeros):
    """Análise de distribuição espacial avançada."""
    gini = _calcular_coeficiente_gini(numeros)

    if gini < 0.15:
        report["score"] += 5
        report["msgs"].append(f"✅ Distribuição espacial ótima (Gini: {gini:.3f}).")
    elif gini > 0.40:
        report["score"] -= 10
        report["msgs"].append(f"⚠️ Concentração espacial alta (Gini: {gini:.3f}).")
    else:
        report["msgs"].append(f"✅ Distribuição espacial aceitável (Gini: {gini:.3f}).")


def _analise_primos(report, numeros):
    """
    Análise de números primos.
    Histórico da Mega: ~35% dos números sorteados são primos.
    """
    primos = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59}
    qtd_primos = len([n for n in numeros if n in primos])

    # Esperado: 2-3 primos (35% de 6 = 2.1)
    if qtd_primos in [2, 3]:
        report["msgs"].append(f"✅ {qtd_primos} números primos (distribuição natural).")
    elif qtd_primos in [1, 4]:
        report["msgs"].append(f"⚠️ {qtd_primos} números primos (aceitável).")
    else:
        report["score"] -= 5
        report["msgs"].append(f"⚠️ {qtd_primos} números primos (distribuição atípica).")


# ===== FUNÇÃO PRINCIPAL =====


def validar_jogo(numeros, historico_jogos=None, ic_info=None):
    """
    Validador completo com análises avançadas.
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
        jogo_tuple = tuple(sorted(numeros))
        if jogo_tuple in historico_jogos:
            report["ja_saiu"] = True

    # 2. Análises técnicas
    _analise_tecnica(report, numeros, ic_info)
    _analise_entropia(report, numeros)
    _analise_popularidade(report, numeros)
    _analise_distribuicao_espacial(report, numeros)
    _analise_primos(report, numeros)

    # 3. Calcula score técnico
    score_tecnico = max(0, min(100, report["score"]))
    report["score_original"] = score_tecnico

    # 4. Métricas adicionais
    report["metricas"] = {
        "soma": sum(numeros),
        "entropia": round(_calcular_entropia_shannon(numeros), 3),
        "gini": round(_calcular_coeficiente_gini(numeros), 3),
        "pares": sum(1 for n in numeros if n % 2 == 0),
        "sequencias": sum(
            1 for i in range(len(numeros) - 1) if numeros[i + 1] == numeros[i] + 1
        ),
    }

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
