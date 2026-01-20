# app/core/matrices.py
from itertools import combinations
from app.core.lottery import GameConfig
from math import comb
import math
from app.core.logger import logger


class MatrixCatalog:
    """
    Catálogo de Matrizes de Fechamento.
    Agora suporta Lotofácil (Matrizes Específicas) e Fallback Genérico.
    """

    @staticmethod
    def get_template(qtd_dezenas: int, slug: str) -> list[list[int]]:
        """
        Retorna a matriz de índices se existir para aquele jogo específico.
        """

        # === MATRIZES EXCLUSIVAS LOTOFÁCIL ===
        if slug == "loto_facil_sorteio":
            if qtd_dezenas == 16:
                return [
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15],
                ]
            elif qtd_dezenas == 17:
                return [
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15, 16],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 13, 14, 15, 16, 9, 10],
                    [0, 1, 2, 3, 4, 5, 6, 11, 12, 13, 14, 15, 16, 7, 8],
                    [0, 1, 2, 3, 9, 10, 11, 12, 13, 14, 15, 16, 4, 5, 6],
                    [0, 1, 2, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 3, 4],
                    [0, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
                    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
                ]
            elif qtd_dezenas == 18:
                # Matriz 18-15-14-15 (Garantia de 14)
                return [
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15, 16],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 17],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 14, 15, 16, 17],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 13, 14, 15, 16],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 13, 15, 16, 17],
                    [0, 1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14, 16, 17],
                    [0, 1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 14, 15, 16, 17],
                    [0, 1, 2, 3, 4, 7, 8, 9, 10, 11, 12, 13, 15, 16, 17],
                    [0, 1, 2, 3, 4, 7, 8, 9, 10, 13, 14, 15, 16, 17, 12],
                    [0, 1, 2, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17],
                    [0, 1, 2, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17],
                    [0, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17],
                    [0, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17],
                    [1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 15, 16, 17, 8],
                    [1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 14, 15, 16, 17, 7],
                    [1, 2, 3, 4, 5, 7, 8, 11, 12, 13, 14, 15, 16, 17, 6],
                    [1, 2, 3, 4, 6, 7, 8, 9, 10, 12, 13, 14, 15, 17, 16],
                    [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17],
                    [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 15, 16, 17, 9, 10, 11],
                    [0, 1, 2, 3, 4, 5, 6, 12, 13, 14, 9, 10, 11, 7, 8],
                    [0, 1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
                    [0, 2, 3, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
                ]

        # Para Mega-Sena, Quina, etc, não temos matrizes hardcoded neste MVP
        # (Retorna None para usar o gerador combinatório genérico)
        return None


def get_matriz_fechamento(
    numeros_base: list[int], config: GameConfig
) -> list[list[int]]:
    """
    Função principal UNIVERSAL.
    Adapta-se automaticamente ao tamanho do jogo (k) configurado.
    """
    n = len(numeros_base)
    k_jogo = config.k

    # Tenta pegar matriz otimizada (apenas Lotofácil tem por enquanto)
    template = MatrixCatalog.get_template(n, config.slug)

    if template:
        jogos_reais = []
        for linha_indices in template:
            try:
                # Mapeia índice para número real
                jogo = [numeros_base[i] for i in linha_indices]
                jogos_reais.append(sorted(jogo))
            except IndexError:
                continue
        return jogos_reais

    # --- FALLBACK UNIVERSAL (Mega-Sena, Quina, etc) ---
    # Se não tem matriz, usa combinação matemática

    # Segurança: Mega-Sena com muitos números explode a memória
    # Ex: 15 dezenas na Mega = 5005 jogos. É aceitável.
    # Ex: 20 dezenas na Mega = 38760 jogos. Limite de segurança.
    limite_seguranca = 5000

    return _gerar_fechamento_dinamico(numeros_base, k_jogo, limite_seguranca)


def _gerar_fechamento_dinamico(
    numeros: list[int], k: int, limite: int
) -> list[list[int]]:
    """
    Gera fechamento combinatório genérico respeitando o K do jogo.
    """
    # Se o número de combinações for seguro, gera todas
    from math import comb

    total_combs = comb(len(numeros), k)

    if total_combs <= limite:
        return [list(c) for c in combinations(numeros, k)]

    # Se for muito grande, gera uma redução inteligente (Janela Deslizante Circular)
    # Isso garante cobertura espalhada sem explodir a memória
    jogos = []
    n = len(numeros)
    n_jogos_alvo = (
        limite if limite < 100 else 50
    )  # Gera 50 jogos otimizados se for gigante

    for i in range(n_jogos_alvo):
        # Cria jogos "deslizando" sobre a lista circularmente
        # Isso mantém vizinhos juntos e varre toda a lista
        shift = (i * k // 2) % n
        jogo = []
        for j in range(k):
            idx = (shift + j) % n
            jogo.append(numeros[idx])

        # Garante que não tenha duplicados e ordena
        jogo = sorted(list(set(jogo)))

        # Se por acaso o jogo ficou menor que k (raro, mas possível em inputs pequenos), completa
        if len(jogo) < k:
            faltam = k - len(jogo)
            # Pega os primeiros que não estão no jogo
            extras = [x for x in numeros if x not in jogo][:faltam]
            jogo.extend(extras)
            jogo.sort()

        if len(jogo) == k and jogo not in jogos:
            jogos.append(jogo)

    return jogos


def gerar_fechamento(numeros_base, config: GameConfig, max_combinacoes=1000):
    """
    Limita fechamentos genéricos grandes para evitar explosão combinatória.

    Args:
        numeros_base: Lista de números base
        config: GameConfig do jogo (MEGASENA, QUINA, LOTOFACIL)
        max_combinacoes: Limite máximo de jogos

    Returns:
        Lista de jogos ou dict com erro
    """
    tamanho_jogo = config.bet_size

    if len(numeros_base) < tamanho_jogo:
        return []

    n = len(numeros_base)

    # Calcula número de combinações
    try:
        total_comb = math.factorial(n) // (
            (math.factorial(tamanho_jogo) * math.factorial(n - tamanho_jogo))
        )
    except:
        total_comb = comb(n, tamanho_jogo)

    if total_comb > max_combinacoes:
        return {
            "erro": f"Fechamento de {n} números gera {total_comb:,} jogos. "
            f"Limite: {max_combinacoes:,}. Reduza a quantidade de números."
        }

    logger.info(
        f"Gerando fechamento para {config.name}: {n} números base -> {total_comb} jogos."
    )
    comb_iter = combinations(numeros_base, tamanho_jogo)
    return [sorted(list(c)) for c in comb_iter]
