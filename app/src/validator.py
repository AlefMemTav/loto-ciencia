# def _verificar_quadrantes(numeros):
#    # Inicializa contadores para Q1, Q2, Q3, Q4
#    q_counts = [0, 0, 0, 0]
#
#    for n in numeros:
#        if n == 0: continue # Segurança
#
#        # Ajusta para índice 0-59 para facilitar a matemática
#        idx = n - 1
#
#        # Calcula linha (0-5) e coluna (0-9)
#        linha = idx // 10
#        coluna = idx % 10
#
#        # Lógica Geométrica:
#        # Linhas 0, 1, 2 são Superior. Linhas 3, 4, 5 são Inferior.
#        # Colunas 0, 1, 2, 3, 4 são Esquerda. Colunas 5, 6, 7, 8, 9 são Direita.
#
#        if linha < 3: # Parte Superior
#            if coluna < 5:
#                q_counts[0] += 1 # Q1 (Superior Esquerdo)
#            else:
#                q_counts[1] += 1 # Q2 (Superior Direito)
#        else: # Parte Inferior
#            if coluna < 5:
#                q_counts[2] += 1 # Q3 (Inferior Esquerdo)
#            else:
#                q_counts[3] += 1 # Q4 (Inferior Direito)
#
#    return q_counts
#


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


def analise_tecnica(report, numeros):

    # Regra 1: Soma (Gauss)
    soma = sum(numeros)
    if not (140 <= soma <= 240):
        report["score"] -= 25
        report["msgs"].append(
            f"❌ Soma ({soma}) fora da Curva de Gauss (Ideal: 140-240)."
        )
    else:
        report["msgs"].append(f"✅ Soma ({soma}) dentro da Zona de Ouro.")

    # Regra 2: Pares e Ímpares
    pares = len([n for n in numeros if n % 2 == 0])
    if pares == 6 or pares == 0:
        report["score"] -= 30
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
        report["score"] -= 20
        report["msgs"].append("❌ Jogo concentrado. Dois ou mais quadrantes vazios.")
    else:
        report["msgs"].append("✅ Jogo bem distribuído no volante.")


def analise_popularidade(report, numeros):

    seqs = sum(1 for i in range(len(numeros) - 1) if numeros[i + 1] == numeros[i] + 1)
    datas = len([n for n in numeros if n <= 31])

    # Check de "Lost" (Números muito famosos: 4, 8, 15, 16, 23, 42)
    lost_nums = {4, 8, 15, 16, 23, 42}
    qtd_lost = len(set(numeros).intersection(lost_nums))

    pontos_risco = 0
    if seqs > 1:
        pontos_risco += 2
    if datas >= 4:
        pontos_risco += 2
    if qtd_lost >= 4:
        pontos_risco += 3  # Penalidade alta para fãs de Lost

    # Define o Rótulo de Risco
    if pontos_risco >= 3:
        report["risco_divisao"] = "ALTO"
        report["msgs"].append(
            "💸 Jogo muito popular (Datas/Sequências). Se ganhar, o prêmio será minúsculo."
        )
        report["score"] -= 20
    elif pontos_risco >= 1:
        report["risco_divisao"] = "Médio"
        report["msgs"].append("⚠️ Cuidado: Contém padrões comuns (Datas ou Sequências).")
        report["score"] -= 10
    else:
        report["risco_divisao"] = "Baixo"
        report["msgs"].append(
            "💎 Aposta Blindada: Combinação difícil de ser copiada por amadores."
        )


def validar_jogo(numeros):
    report = {"score": 100, "msgs": [], "status": "Excelente"}

    # Análise Técnica
    analise_tecnica(report, numeros)

    # Análise de Popularidade
    analise_popularidade(report, numeros)

    # Define Status Final
    if report["score"] >= 80:
        report["status"] = "💎 Excelente"
    elif report["score"] >= 50:
        report["status"] = "⚠️ Razoável"
    else:
        report["status"] = "🗑️ Fraco"

    return report
