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
                # 8 jogos. Verificado por força bruta: se os 15 sorteados estão
                # entre as 17 dezenas, o piso é 14 acertos (ver tests/test_matrices_fechamento.py).
                return [
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15, 16],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 13, 14, 15, 16],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 13, 14, 15, 16],
                    [0, 1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14, 15, 16],
                    [0, 1, 2, 3, 4, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
                    [0, 1, 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
                    [0, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
                ]
            elif qtd_dezenas == 18:
                # 24 jogos distintos. Verificado por força bruta: se os 15 sorteados estão
                # entre as 18 dezenas, o piso é 14 acertos (ver tests/test_matrices_fechamento.py).
                return [
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 15, 16, 17],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 14, 15, 16, 17],
                    [0, 1, 2, 3, 4, 5, 9, 10, 11, 12, 13, 14, 15, 16, 17],
                    [0, 1, 2, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
                    [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 15, 16],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 17],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 13, 14, 16, 17],
                    [0, 1, 3, 4, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17],
                    [0, 2, 3, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
                    [1, 2, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 17],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 13, 14, 15, 17],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 16, 17],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 13, 14, 15, 16],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 15, 17],
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 14, 15, 16],
                    [0, 1, 3, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
                    [0, 1, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
                    [0, 2, 3, 4, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
                    [0, 2, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17],
                    [1, 2, 3, 4, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
                    [1, 2, 3, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17],
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
    k_jogo = config.bet_size

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
    import numpy as np

    nums = sorted({int(x) for x in numeros})
    n = len(nums)
    if n < k or k <= 0:
        return []

    total_combs = comb(n, k)

    if total_combs <= limite:
        return [list(c) for c in combinations(nums, k)]

    # Acima do limite combinatório: construção gulosa determinística maximizando
    # pares inéditos entre as dezenas-base e equilibrando a exposição individual.
    n_jogos_alvo = min(total_combs, limite if limite < 100 else 50)
    seed_val = (sum((i + 1) * x for i, x in enumerate(nums)) + k * 997) % (2**32)
    rng = np.random.default_rng(seed_val)
    nums_arr = np.asarray(nums, dtype=int)

    pair_covered = np.zeros((n, n), dtype=np.int32)
    exposure = np.zeros(n, dtype=np.int32)
    jogos: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    pool_size = min(200, max(40, total_combs))

    for step in range(n_jogos_alvo):
        inv_exp = 1.0 / (1.0 + exposure.astype(float))
        priorities = rng.random((pool_size, n)) * inv_exp[None, :]
        cand_indices = np.argpartition(priorities, -k, axis=1)[:, -k:]
        cand_indices.sort(axis=1)

        # Inclui um candidato determinístico puramente pelas menores exposições
        least_used = np.argsort(exposure, kind="stable")[:k]
        least_used.sort()
        cand_indices[0] = least_used

        best_idx = None
        best_tuple = None
        best_key = None

        for row in cand_indices:
            tup = tuple(int(nums_arr[idx]) for idx in row)
            if tup in seen:
                continue
            sub = pair_covered[row[:, None], row[None, :]]
            # Subtrai diagonal (sempre 0) para contar pares inéditos ordenados / 2
            new_pairs = int((sub == 0).sum()) - k
            reuse_sum = int(sub.sum())
            exp_sum = int(exposure[row].sum())
            key = (new_pairs, -reuse_sum, -exp_sum)
            if best_key is None or key > best_key:
                best_key = key
                best_idx = row
                best_tuple = tup

        if best_idx is None:
            # Fallback determinístico caso todas as amostras colidam
            for _ in range(128):
                row = np.sort(rng.choice(n, size=k, replace=False))
                tup = tuple(int(nums_arr[idx]) for idx in row)
                if tup not in seen:
                    best_idx = row
                    best_tuple = tup
                    break
            if best_idx is None:
                break

        seen.add(best_tuple)
        jogos.append(list(best_tuple))
        exposure[best_idx] += 1
        pair_covered[best_idx[:, None], best_idx[None, :]] += 1
        np.fill_diagonal(pair_covered, 0)

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
