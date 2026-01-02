import random
from itertools import combinations

from app.src.validator import validar_jogo


def gerar_jogo_perfeito(freq_series, finais_poisson):
    # Separa os conjuntos
    top_quentes = freq_series.head(15).index.tolist()
    top_frios = freq_series.tail(15).index.tolist()
    # Neutros são os que não estão nem no top nem no bottom
    neutros = [n for n in range(1, 61) if n not in top_quentes and n not in top_frios]

    tentativas = 0
    while tentativas < 5000:
        tentativas += 1

        # Estratégia Híbrida: 3 Quentes + 2 Frios + 1 Neutro (ou variação)
        # Adiciona viés de Poisson (se houver finais atrasados, tenta incluir)

        try:
            jogo = []
            jogo += random.sample(top_quentes, 3)
            jogo += random.sample(top_frios, 2)
            jogo += random.sample(neutros, 1)

            # Força Poisson (opcional): Substitui o último por um número com final atrasado se necessário
            if finais_poisson and random.random() < 0.5:
                final_desejado = random.choice(finais_poisson)
                candidatos_final = [
                    n
                    for n in range(1, 61)
                    if n % 10 == final_desejado and n not in jogo
                ]
                if candidatos_final:
                    jogo.pop()
                    jogo.append(random.choice(candidatos_final))

            jogo = sorted(jogo)

            # Passa no Validador Rigoroso
            val = validar_jogo(jogo)
            if val["score"] >= 90:  # Só aceita jogos Nota A
                return jogo
        except ValueError:
            continue  # Caso falte números nas listas (edge case)

    return sorted(random.sample(range(1, 61), 6))  # Fallback se falhar


def gerar_fechamento(numeros_base):
    # Gera todas as combinações de 6 números baseadas na entrada
    # Ex: Se entrar 7 números, gera 7 jogos. Se entrar 8, gera 28 jogos.
    if len(numeros_base) < 6:
        return []
    comb = list(combinations(numeros_base, 6))
    return [sorted(list(c)) for c in comb]
