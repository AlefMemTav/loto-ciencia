import random
from itertools import combinations
from app.src.validator import validar_jogo
from app.src.statistics import get_historico_jogos, get_tabela_inteligencia


def gerar_jogo_perfeito(df, finais_poisson):
    """
    Gera um jogo usando Amostragem Ponderada baseada em Z-Score (Frequência + Atraso).
    Substitui a lógica antiga de '3 quentes + 2 frios'.
    """
    # 1. Busca a Tabela de Inteligência (Frequência, Gaps e Pesos)
    # Essa função já está cacheada no statistics.py, então é rápida.
    tabela = get_tabela_inteligencia(df)
    historico = get_historico_jogos(df)

    if tabela.empty:
        # Fallback de segurança se não tiver dados
        return sorted(random.sample(range(1, 61), 6))

    numeros_disponiveis = tabela.index.tolist()  # [1, 2, ..., 60]
    pesos = tabela[
        "Peso_Geracao"
    ].tolist()  # [1.5, 0.8, ..., 2.1] (Score de probabilidade)

    tentativas = 0
    # Aumentamos as tentativas porque agora buscamos a "perfeição estatística"
    while tentativas < 20000:
        tentativas += 1

        # 2. O Pulo do Gato: Sorteio Ponderado (Weighted Sampling)
        # Em vez de random.sample (chance igual), usamos random.choices (chance baseada no peso)
        # Como choices pode repetir números, fazemos um loop até ter 6 únicos.
        pre_jogo = set()

        # Otimização: Tenta pegar 6 de uma vez, se der duplicado, completa.
        candidatos = random.choices(numeros_disponiveis, weights=pesos, k=6)
        pre_jogo.update(candidatos)

        while len(pre_jogo) < 6:
            novo = random.choices(numeros_disponiveis, weights=pesos, k=1)[0]
            pre_jogo.add(novo)

        jogo = sorted(list(pre_jogo))

        # 3. Refinamento de Poisson (Opcional)
        # Se houver dígitos finais atrasados, tenta forçar a troca de um número 'fraco'
        if finais_poisson and random.random() < 0.3:  # 30% de chance de ativar
            final_desejado = random.choice(finais_poisson)
            # Acha números com esse final que NÃO estão no jogo
            candidatos_final = [
                n for n in range(1, 61) if n % 10 == final_desejado and n not in jogo
            ]

            if candidatos_final:
                # Escolhe um candidato baseado no peso dele na tabela também!
                pesos_candidatos = [
                    tabela.loc[c, "Peso_Geracao"] for c in candidatos_final
                ]
                novo_numero = random.choices(
                    candidatos_final, weights=pesos_candidatos, k=1
                )[0]

                # Remove um número aleatório do jogo para dar lugar
                jogo.pop(random.randint(0, 5))
                jogo.append(novo_numero)
                jogo.sort()

        # 4. Validação Rigorosa (Só passa o Créme de la Créme)
        val = validar_jogo(jogo, historico_jogos=historico)

        # Aceitamos Score >= 85 (Excelente).
        # O validador garante Gauss, Quadrantes e Pares.
        if val["score"] >= 85:
            return jogo

    # Fallback se o loop estourar (raro)
    return sorted(random.sample(range(1, 61), 6))


def gerar_fechamento(numeros_base):
    if len(numeros_base) < 6:
        return []
    comb = list(combinations(numeros_base, 6))
    return [sorted(list(c)) for c in comb]
