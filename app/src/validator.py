import math
from collections import Counter


def _verificar_quadrantes(numeros):

    q1 = len(
        [
            n
            for n in numeros
            if n in [1, 2, 3, 4, 5, 11, 12, 13, 14, 15, 21, 22, 23, 24, 25]
        ]
    )
    q2 = len(
        [
            n
            for n in numeros
            if n in [6, 7, 8, 9, 10, 16, 17, 18, 19, 20, 26, 27, 28, 29, 30]
        ]
    )
    q3 = len(
        [
            n
            for n in numeros
            if n in [31, 32, 33, 34, 35, 41, 42, 43, 44, 45, 51, 52, 53, 54, 55]
        ]
    )
    q4 = len(
        [
            n
            for n in numeros
            if n in [36, 37, 38, 39, 40, 46, 47, 48, 49, 50, 56, 57, 58, 59, 60]
        ]
    )
    return [q1, q2, q3, q4]


def _calcular_entropia_shannon(numeros):
    """
    Calcula a entropia baseada nos INTERVALOS (gaps) entre os números.
    Padrões visuais (retas, colunas) geram gaps repetidos -> Entropia Baixa (0).
    Caos aleatório gera gaps variados -> Entropia Alta (> 1.5).
    """
    # 1. Calcula as diferenças: [10, 20, 30] -> Gaps: [10, 10]
    gaps = [numeros[i + 1] - numeros[i] for i in range(len(numeros) - 1)]

    # 2. Conta a frequência de cada gap
    counts = Counter(gaps)
    total = len(gaps)

    # 3. Fórmula de Shannon: -Sum(p * log2(p))
    entropia = 0
    for count in counts.values():
        p = count / total
        if p > 0:
            entropia -= p * math.log2(p)

    return entropia


# --- MÓDULOS DE ANÁLISE ---


def analise_tecnica(report, numeros):
    # Regra 1: Soma (Gauss)
    soma = sum(numeros)
    if not (140 <= soma <= 240):
        report["score"] -= 20
        report["msgs"].append(
            f"❌ Soma ({soma}) fora da Curva de Gauss (Ideal: 140-240)."
        )
    else:
        report["msgs"].append(f"✅ Soma ({soma}) dentro da Zona de Ouro.")

    # Regra 2: Pares e Ímpares
    pares = len([n for n in numeros if n % 2 == 0])
    if pares in [0, 6]:
        report["score"] -= 25
        report["msgs"].append("❌ Desequilíbrio Total de Par/Ímpar (6/0).")
    elif pares not in [2, 3, 4]:
        report["score"] -= 10
        report["msgs"].append(f"⚠️ Distribuição Par/Ímpar arriscada ({pares} pares).")
    else:
        report["msgs"].append(f"✅ Distribuição Par/Ímpar equilibrada ({pares} pares).")

    # Regra 3: Quadrantes
    quads = _verificar_quadrantes(numeros)
    zeros = quads.count(0)
    if zeros >= 2:
        report["score"] -= 15
        report["msgs"].append("❌ Jogo muito concentrado (2+ quadrantes vazios).")
    else:
        report["msgs"].append("✅ Jogo bem distribuído nos quadrantes.")

    # Regra 4: Finais
    # Pega apenas o último dígito de cada número (Ex: 58 -> 8)
    finais = [n % 10 for n in numeros]

    # Conta a repetição. Ex: {9: 4, 1: 2} (Quatro finais 9, Dois finais 1)
    contagem = Counter(finais).most_common(1)[0]

    qtd_repetida = contagem[1]
    digito = contagem[0]

    # Regra: Se tiver 4 ou mais números com o mesmo final, penaliza.
    if qtd_repetida >= 4:
        report["score"] -= 20
        report["msgs"].append(
            f"❌ Vício de Final: {qtd_repetida} números terminam em {digito}."
        )
    elif qtd_repetida == 3:
        report["msgs"].append(f"⚠️ Alerta: 3 números com final {digito}.")
        report["score"] -= 5


def analise_entropia(report, numeros):
    """
    Detecta se o jogo foi gerado por um humano tentando fazer 'desenhos' no volante.
    Ex: 1, 11, 21, 31, 41, 51 (Coluna) -> Entropia 0.0
    """
    entropia = _calcular_entropia_shannon(numeros)

    # Calibração para Mega-Sena (5 intervalos):
    # Max Entropia (todos gaps diferentes): ~2.32
    # Min Entropia (todos gaps iguais): 0.00

    if entropia < 1.0:
        report["score"] -= 30  # Penalidade severa para padrões óbvios
        report["msgs"].append(
            f"❌ Entropia Baixa ({entropia:.2f}): Padrão visual/sequencial detectado."
        )
        report["risco_divisao"] = "ALTO"  # Padrões visuais são muito jogados
    elif entropia > 2.0:
        report["score"] += 5  # Bônus por caos saudável
        report["msgs"].append(
            f"✅ Entropia Alta ({entropia:.2f}): Caos estatístico excelente."
        )
    else:
        report["msgs"].append(f"✅ Entropia Normal ({entropia:.2f}).")


def analise_popularidade(report, numeros):
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

    # Se já foi marcado como ALTO pela entropia, mantém
    current_risk = report.get("risco_divisao", "Baixo")

    if pontos_risco >= 3 or current_risk == "ALTO":
        report["risco_divisao"] = "ALTO"
        if pontos_risco >= 3:
            report["msgs"].append(
                "💸 Jogo popular (Datas/Lost). Risco de prêmio baixo."
            )
            report["score"] -= 20
    elif pontos_risco >= 1:
        report["risco_divisao"] = "Médio"
        report["msgs"].append("⚠️ Contém padrões populares (Datas ou Sequências).")
        report["score"] -= 10
    else:
        # Só marca como Blindado se não tiver sido marcado como Alto antes
        if current_risk != "ALTO":
            report["risco_divisao"] = "Baixo"
            report["msgs"].append("💎 Aposta Blindada: Difícil de ser copiada.")


# --- FUNÇÃO PRINCIPAL ---


def validar_jogo(numeros, historico_jogos=None):
    report = {
        "score": 100,
        "msgs": [],
        "status": "Excelente",
        "risco_divisao": "Baixo",
        "ja_saiu": False,  # Novo campo de controle
        "score_original": 0,  # Novo campo para mostrar o "Score Teórico"
    }

    # 1. Verificação de Histórico (Sem retornar imediatamente)
    if historico_jogos:
        jogo_tuple = tuple(sorted(numeros))
        if jogo_tuple in historico_jogos:
            report["ja_saiu"] = True

    analise_tecnica(report, numeros)
    analise_entropia(report, numeros)
    analise_popularidade(report, numeros)

    # 3. Calcula o Score Técnico Real (0 a 100)
    score_tecnico = max(0, min(100, report["score"]))
    report["score_original"] = score_tecnico  # Guarda a nota que "seria"

    # 4. Aplica a Penalidade Final de Histórico
    if report["ja_saiu"]:
        report["score"] = 0  # Zera para o sistema não recomendar
        report["status"] = "⛔ Já Saiu"
        # Adiciona o aviso no topo da lista de mensagens
        report["msgs"].insert(
            0,
            "⛔ Este jogo JÁ FOI SORTEADO! Score zerado por segurança.",
        )
    else:
        # Se não saiu, o score oficial é o técnico
        report["score"] = score_tecnico

        # Define Status Final Normal
        if score_tecnico >= 80:
            report["status"] = "💎 Excelente"
        elif score_tecnico >= 60:
            report["status"] = "✅ Bom"
        elif score_tecnico >= 40:
            report["status"] = "⚠️ Razoável"
        else:
            report["status"] = "🗑️ Fraco"

    return report
