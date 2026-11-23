# app/core/matrices.py
"""
Matrizes de fechamento (Covering Designs / Lottery Wheels) com garantias verificáveis.

Suporta:
- Garantias exatas L(v, k, t, m): se `m` dezenas sorteadas estiverem dentro das `v` dezenas
  da base, ao menos um bilhete de tamanho `k` acerta `>= t` dezenas.
- Covering designs C(v, k, t) = L(v, k, t, t): garante `>= t` acertos bastando acertar `t`
  dezenas dentro da base.
- Verificação exaustiva por bitmask de 100% dos C(v, m) cenários.
- Cobertura parcial balanceada (maximização gulosa de pares inéditos + equilíbrio de exposição)
  para universos grandes (ex.: Lotomania 51..70 dezenas).
- Sugestão de base menos popular (anti-rateio) usando `modelo_popularidade`.
"""

from __future__ import annotations

from functools import lru_cache
from itertools import combinations
from math import comb
from typing import Any

import numpy as np

from app.core.logger import logger
from app.core.lottery import GameConfig


class MatrixCatalog:
    """
    Catálogo de matrizes de fechamento ótimas/verificadas (índices 0..v-1).
    """

    @staticmethod
    def get_template(
        qtd_dezenas: int,
        slug: str,
        garantia_t: int | None = None,
        condicao_m: int | None = None,
    ) -> list[list[int]] | None:
        """
        Retorna matriz de índices pré-verificada (ou gerada por covering design em cache)
        para `(slug, qtd_dezenas, garantia_t, condicao_m)`.
        """
        # === LOTOFÁCIL (k=15): matrizes de Turán exatas para 14-se-15 ===
        if slug == "loto_facil_sorteio":
            if (garantia_t is None or garantia_t == 14) and (
                condicao_m is None or condicao_m == 15
            ):
                if qtd_dezenas == 16:
                    # Pelo princípio da casa dos pombos (15 + 15 - 16 = 14),
                    # 1 único bilhete de 15 entre 16 já garante >= 14 acertos se os 15 estiverem na base.
                    return [list(range(15))]
                if qtd_dezenas == 17:
                    # 8 jogos (ótimo de Turán): garante >= 14 se 15 estiverem nas 17.
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
                if qtd_dezenas == 18:
                    # 24 jogos distintos (ótimo de Turán): garante >= 14 se 15 estiverem nas 18.
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
            if (garantia_t == 13 or (garantia_t is None and 19 <= qtd_dezenas <= 20)) and (
                condicao_m is None or condicao_m == 15
            ):
                if 17 <= qtd_dezenas <= 20:
                    return [list(r) for r in construir_covering_design(qtd_dezenas, 15, 13, 15)]

        # === MEGA-SENA (k=6): Covering Designs reais (Quadra se 6, Quina se 6, Quadra se 4) ===
        if slug == "mega_sena_sorteio":
            if garantia_t is not None and condicao_m is not None:
                if 7 <= qtd_dezenas <= 15 and 3 <= garantia_t <= 6 and garantia_t <= condicao_m <= 6:
                    if comb(qtd_dezenas, condicao_m) <= 6000:
                        return [
                            list(r)
                            for r in construir_covering_design(
                                qtd_dezenas, 6, garantia_t, condicao_m
                            )
                        ]
            elif 8 <= qtd_dezenas <= 12:
                # Padrão equilibrado: garante Quina se os 6 sorteados estiverem na base (4..46 jogos)
                return [list(r) for r in construir_covering_design(qtd_dezenas, 6, 5, 6)]
            elif 13 <= qtd_dezenas <= 15:
                # Base grande: garante Quadra se os 6 sorteados estiverem na base (12..25 jogos)
                return [list(r) for r in construir_covering_design(qtd_dezenas, 6, 4, 6)]

        # === QUINA (k=5): Covering Designs reais (Terno se 5, Quadra se 5, Terno se 3) ===
        if slug == "quina_sorteio":
            if garantia_t is not None and condicao_m is not None:
                if 6 <= qtd_dezenas <= 15 and 2 <= garantia_t <= 5 and garantia_t <= condicao_m <= 5:
                    if comb(qtd_dezenas, condicao_m) <= 6000:
                        return [
                            list(r)
                            for r in construir_covering_design(
                                qtd_dezenas, 5, garantia_t, condicao_m
                            )
                        ]
            elif 7 <= qtd_dezenas <= 12:
                # Padrão equilibrado: garante Quadra se os 5 sorteados estiverem na base (3..41 jogos)
                return [list(r) for r in construir_covering_design(qtd_dezenas, 5, 4, 5)]
            elif 13 <= qtd_dezenas <= 15:
                # Base grande: garante Terno se os 5 sorteados estiverem na base (9..17 jogos)
                return [list(r) for r in construir_covering_design(qtd_dezenas, 5, 3, 5)]

        return None


@lru_cache(maxsize=128)
def construir_covering_design(
    v: int,
    k: int,
    t: int,
    m: int,
    seed: int = 42,
) -> tuple[tuple[int, ...], ...]:
    """
    Constrói uma matriz de cobertura determinística e verificada L(v, k, t, m)
    sobre os índices `{0, ..., v - 1}` via algoritmo guloso com bitmasks + poda de redundâncias.

    Garante matematicamente que todo subconjunto de tamanho `m` de `{0, ..., v - 1}`
    tem interseção >= `t` com pelo menos um bilhete de tamanho `k` da matriz retornada.
    """
    if v < k or k <= 0 or t <= 0 or m <= 0 or t > min(k, m):
        return ()

    # Atalho exato do princípio da casa dos pombos: 1 único bilhete já garante >= t
    if k + m - v >= t:
        return (tuple(range(k)),)

    # Caso degenerado: exigir k acertos se k sorteados = desdobramento completo
    if t == k and m == k:
        return tuple(combinations(range(v), k))

    m_subs = [sum(1 << x for x in c) for c in combinations(range(v), m)]
    total_k = comb(v, k)
    rng = np.random.default_rng(seed + v * 1009 + k * 97 + t * 13 + m * 7)

    cands_all = (
        [sum(1 << x for x in c) for c in combinations(range(v), k)]
        if total_k <= 3200
        else None
    )

    uncovered = list(m_subs)
    chosen: list[int] = []
    max_cand_sample = 500

    while uncovered:
        if cands_all is not None:
            pool = cands_all
        else:
            pool_set: set[int] = set()
            for u in uncovered[: min(35, len(uncovered))]:
                u_bits = [b for b in range(v) if (u >> b) & 1]
                other = [b for b in range(v) if not ((u >> b) & 1)]
                for _ in range(8):
                    if k == m:
                        keep = int(rng.integers(t, min(k, len(u_bits)) + 1))
                        c = list(rng.choice(u_bits, keep, replace=False))
                        if k - keep > 0:
                            c.extend(rng.choice(other, k - keep, replace=False).tolist())
                    elif k > m:
                        c = u_bits + rng.choice(other, k - m, replace=False).tolist()
                    else:
                        c = rng.choice(u_bits, k, replace=False).tolist()
                    pool_set.add(sum(1 << int(x) for x in c))
            while len(pool_set) < max_cand_sample:
                c = rng.choice(v, k, replace=False)
                pool_set.add(sum(1 << int(x) for x in c))
            pool = list(pool_set)

        if len(uncovered) <= 3500:
            u_eval = uncovered
        else:
            idx_sample = rng.choice(len(uncovered), size=2000, replace=False)
            u_eval = [uncovered[int(i)] for i in idx_sample]

        best_c = pool[0]
        best_cov = -1
        for c in pool:
            cov = sum(1 for u in u_eval if (c & u).bit_count() >= t)
            if cov > best_cov:
                best_cov = cov
                best_c = c
        chosen.append(best_c)
        uncovered = [u for u in uncovered if (best_c & u).bit_count() < t]

    # Poda exata de bilhetes redundantes preservando 100% da cobertura em todos os C(v, m) cenários
    pruned = list(chosen)
    idx_p = 0
    while idx_p < len(pruned):
        trial = pruned[:idx_p] + pruned[idx_p + 1 :]
        if trial and all(any((c & u).bit_count() >= t for c in trial) for u in m_subs):
            pruned = trial
        else:
            idx_p += 1

    tickets = tuple(
        sorted(tuple(b for b in range(v) if (c >> b) & 1) for c in pruned)
    )
    return tickets


def verificar_garantia_fechamento(
    jogos: list[list[int]],
    numeros_base: list[int],
    t_garantia: int,
    m_condicao: int,
) -> dict[str, Any]:
    """
    Verifica exaustivamente por bitmask se o fechamento atinge a garantia `t_garantia`
    para 100% dos `C(v, m_condicao)` cenários possíveis dentro de `numeros_base`.
    """
    base = sorted({int(x) for x in numeros_base})
    v = len(base)
    if not jogos or v < m_condicao or m_condicao <= 0 or t_garantia <= 0:
        return {"verificado": False, "cobertura_pct": 0.0, "piso_acertos": 0, "cenarios": 0}

    total_cenarios = comb(v, m_condicao)
    pos_map = {num: idx for idx, num in enumerate(base)}
    ticket_masks = []
    for jogo in jogos:
        mask = 0
        for num in jogo:
            idx = pos_map.get(int(num))
            if idx is not None:
                mask |= 1 << idx
        ticket_masks.append(mask)

    piso = m_condicao
    cobertos = 0
    for c in combinations(range(v), m_condicao):
        u = sum(1 << x for x in c)
        melhor = max((tm & u).bit_count() for tm in ticket_masks)
        if melhor < piso:
            piso = melhor
        if melhor >= t_garantia:
            cobertos += 1

    return {
        "verificado": bool(cobertos == total_cenarios),
        "cobertura_pct": round(100.0 * cobertos / max(1, total_cenarios), 4),
        "piso_acertos": int(piso),
        "cenarios": int(total_cenarios),
    }


def opcoes_fechamento_para_jogo(config: GameConfig, n_base: int) -> list[dict[str, Any]]:
    """Lista os modos de fechamento disponíveis para `(config, n_base)`."""
    slug = config.slug
    opcoes: list[dict[str, Any]] = []
    if slug == "mega_sena_sorteio":
        if 8 <= n_base <= 12:
            opcoes.append(
                {"id": "quina_se_6", "label": "Garantir Quina (se acertar 6 na base)", "t": 5, "m": 6}
            )
        if 7 <= n_base <= 12:
            opcoes.append(
                {"id": "quadra_se_4", "label": "Covering Design: Garantir Quadra (se acertar 4 na base)", "t": 4, "m": 4}
            )
        if 9 <= n_base <= 15:
            opcoes.append(
                {"id": "quadra_se_6", "label": "Econômico: Garantir Quadra (se acertar 6 na base)", "t": 4, "m": 6}
            )
        if comb(n_base, 6) <= 1000:
            opcoes.append(
                {"id": "completo", "label": f"Desdobramento Completo ({comb(n_base, 6)} jogos, garante Sena)", "t": 6, "m": 6}
            )
    elif slug == "quina_sorteio":
        if 7 <= n_base <= 12:
            opcoes.append(
                {"id": "quadra_se_5", "label": "Garantir Quadra (se acertar 5 na base)", "t": 4, "m": 5}
            )
        if 6 <= n_base <= 12:
            opcoes.append(
                {"id": "terno_se_3", "label": "Covering Design: Garantir Terno (se acertar 3 na base)", "t": 3, "m": 3}
            )
        if 8 <= n_base <= 15:
            opcoes.append(
                {"id": "terno_se_5", "label": "Econômico: Garantir Terno (se acertar 5 na base)", "t": 3, "m": 5}
            )
        if comb(n_base, 5) <= 1000:
            opcoes.append(
                {"id": "completo", "label": f"Desdobramento Completo ({comb(n_base, 5)} jogos, garante Quina)", "t": 5, "m": 5}
            )
    elif slug == "loto_facil_sorteio":
        if 16 <= n_base <= 18:
            opcoes.append(
                {"id": "14_se_15", "label": "Garantir 14 pontos (se acertar 15 na base)", "t": 14, "m": 15}
            )
        if 17 <= n_base <= 20:
            opcoes.append(
                {"id": "13_se_15", "label": "Econômico: Garantir 13 pontos (se acertar 15 na base)", "t": 13, "m": 15}
            )
        if comb(n_base, 15) <= 1000:
            opcoes.append(
                {"id": "completo", "label": f"Desdobramento Completo ({comb(n_base, 15)} jogos, garante 15)", "t": 15, "m": 15}
            )
        if not opcoes:
            opcoes.append(
                {"id": "parcial", "label": "Cobertura Parcial Balanceada (sem garantia exata)", "t": None, "m": None}
            )
    else:
        opcoes.append(
            {"id": "parcial", "label": "Cobertura Balanceada de Pares e Exposição", "t": None, "m": None}
        )
    return opcoes


def gerar_fechamento_detalhado(
    numeros_base: list[int],
    config: GameConfig,
    garantia_t: int | None = None,
    condicao_m: int | None = None,
    completo: bool = False,
    max_jogos: int | None = None,
) -> dict[str, Any]:
    """
    Gera o fechamento com deduplicação/ordenação segura da base e retorna metadados
    honestos sobre a garantia real verificada da matriz gerada.
    """
    base = sorted({int(x) for x in numeros_base})
    n = len(base)
    k_jogo = config.bet_size

    if n < k_jogo or k_jogo <= 0:
        return {
            "jogos": [],
            "base": base,
            "garantia_t": None,
            "condicao_m": None,
            "garantia_verificada": False,
            "descricao_garantia": "base insuficiente para o tamanho da aposta",
        }

    total_combs = comb(n, k_jogo)

    if completo or (garantia_t == k_jogo and condicao_m == k_jogo):
        limite_full = max_jogos if max_jogos is not None else 5000
        if total_combs <= limite_full:
            jogos_full = [list(c) for c in combinations(base, k_jogo)]
            return {
                "jogos": jogos_full,
                "base": base,
                "garantia_t": k_jogo,
                "condicao_m": config.k,
                "garantia_verificada": True,
                "descricao_garantia": (
                    f"total ({len(jogos_full)} jogos): todas as combinações da base. "
                    f"Se os {config.k} números sorteados estiverem na base, o prêmio máximo está garantido"
                ),
            }

    # Determina garantia efetiva padrão quando o chamador não especifica
    eff_t = garantia_t
    eff_m = condicao_m
    if eff_t is None and eff_m is None:
        if config.slug == "loto_facil_sorteio":
            if 16 <= n <= 18:
                eff_t, eff_m = 14, 15
            elif 19 <= n <= 20:
                eff_t, eff_m = 13, 15
        elif config.slug == "mega_sena_sorteio":
            if 8 <= n <= 12:
                eff_t, eff_m = 5, 6
            elif 13 <= n <= 15:
                eff_t, eff_m = 4, 6
        elif config.slug == "quina_sorteio":
            if 7 <= n <= 12:
                eff_t, eff_m = 4, 5
            elif 13 <= n <= 15:
                eff_t, eff_m = 3, 5

    template = MatrixCatalog.get_template(
        n, config.slug, garantia_t=eff_t, condicao_m=eff_m
    )

    if template:
        jogos_reais = [sorted([base[i] for i in linha]) for linha in template]
        desc = (
            f"pelo menos {eff_t} acertos se {eff_m} número(s) sorteado(s) estiverem "
            f"entre as {n} dezenas da base (verificada em 100% dos {comb(n, eff_m):,} cenários)"
            if eff_t is not None and eff_m is not None
            else "matriz otimizada aplicada"
        )
        return {
            "jogos": jogos_reais,
            "base": base,
            "garantia_t": eff_t,
            "condicao_m": eff_m,
            "garantia_verificada": bool(eff_t is not None and eff_m is not None),
            "descricao_garantia": desc,
        }

    # Fallback: desdobramento completo apenas se pequeno (<= 200 ou <= max_jogos explícito)
    limite_completo = 200 if max_jogos is None else min(max_jogos, 5000)
    if total_combs <= limite_completo:
        jogos_full = [list(c) for c in combinations(base, k_jogo)]
        return {
            "jogos": jogos_full,
            "base": base,
            "garantia_t": k_jogo,
            "condicao_m": config.k,
            "garantia_verificada": True,
            "descricao_garantia": (
                f"total ({len(jogos_full)} jogos): todas as combinações da base. "
                f"Se todos os números sorteados estiverem na base, o prêmio máximo está garantido"
            ),
        }

    qtd_alvo = max_jogos if (max_jogos is not None and max_jogos > 0) else 25
    jogos_dyn = _gerar_fechamento_dinamico(base, k_jogo, limite=qtd_alvo, n_alvo=qtd_alvo)
    return {
        "jogos": jogos_dyn,
        "base": base,
        "garantia_t": None,
        "condicao_m": None,
        "garantia_verificada": False,
        "descricao_garantia": (
            f"cobertura parcial balanceada ({len(jogos_dyn)} jogos, sem garantia matemática exata)"
        ),
    }


def get_matriz_fechamento(
    numeros_base: list[int],
    config: GameConfig,
    garantia_t: int | None = None,
    condicao_m: int | None = None,
    completo: bool = False,
    max_jogos: int | None = None,
) -> list[list[int]]:
    """
    Função principal UNIVERSAL de fechamento.
    Deduplica e ordena `numeros_base`, aplica Covering Designs verificados para
    Mega-Sena, Quina e Lotofácil, e usa cobertura balanceada para bases grandes/Lotomania.
    """
    return gerar_fechamento_detalhado(
        numeros_base,
        config,
        garantia_t=garantia_t,
        condicao_m=condicao_m,
        completo=completo,
        max_jogos=max_jogos,
    )["jogos"]


def _gerar_fechamento_dinamico(
    numeros: list[int], k: int, limite: int, n_alvo: int | None = None
) -> list[list[int]]:
    """
    Gera cobertura parcial balanceada (maximização gulosa determinística de pares inéditos
    + equilíbrio de exposição).

    - Se `n_alvo` for informado, gera exatamente `min(C(n, k), n_alvo)` jogos.
    - Caso contrário, trata `limite` como teto combinatório de segurança: devolve todas as
      combinações se `C(n, k) <= limite`, ou amostra `limite` (se `<= 200`) / `50` (se `limite > 200`).
    """
    nums = sorted({int(x) for x in numeros})
    n = len(nums)
    if n < k or k <= 0 or limite <= 0:
        return []

    total_combs = comb(n, k)
    if n_alvo is not None:
        if n_alvo <= 0:
            return []
        n_jogos_alvo = min(total_combs, int(n_alvo))
        if total_combs <= n_jogos_alvo:
            return [list(c) for c in combinations(nums, k)]
    else:
        if total_combs <= limite:
            return [list(c) for c in combinations(nums, k)]
        n_jogos_alvo = min(total_combs, limite if limite <= 200 else 50)

    seed_val = (sum((i + 1) * x for i, x in enumerate(nums)) + k * 997) % (2**32)
    rng = np.random.default_rng(seed_val)
    nums_arr = np.asarray(nums, dtype=int)

    pair_covered = np.zeros((n, n), dtype=np.int32)
    exposure = np.zeros(n, dtype=np.int32)
    jogos: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    pool_size = min(200, max(40, total_combs))

    for _ in range(n_jogos_alvo):
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
            new_pairs = int((sub == 0).sum()) - k
            reuse_sum = int(sub.sum())
            exp_sum = int(exposure[row].sum())
            key = (new_pairs, -reuse_sum, -exp_sum)
            if best_key is None or key > best_key:
                best_key = key
                best_idx = row
                best_tuple = tup

        if best_idx is None:
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


def sugerir_base_antipopular(
    config: GameConfig,
    qtd_dezenas: int,
    modelo_popularidade: Any = None,
) -> list[int]:
    """
    Seleciona `qtd_dezenas` com menor risco medido de divisão de prêmio
    usando os pesos individuais e a matriz de pares (se disponível) de `modelo_popularidade`.
    """
    n_tot = int(config.n_numbers)
    qtd = max(config.bet_size, min(int(qtd_dezenas), n_tot))
    if modelo_popularidade is None or getattr(modelo_popularidade, "pesos", None) is None:
        # Fallback neutro: evita concentração exclusiva em 1..31 quando universo > 31
        if n_tot > 31:
            pool_alto = list(range(32, n_tot + 1))
            pool_baixo = list(range(1, 32))
            rng = np.random.default_rng(n_tot * 31 + qtd)
            n_altos = min(len(pool_alto), max(1, int(round(qtd * 0.65))))
            n_baixos = qtd - n_altos
            esc = (
                rng.choice(pool_alto, n_altos, replace=False).tolist()
                + rng.choice(pool_baixo, n_baixos, replace=False).tolist()
            )
            return sorted(int(x) for x in esc)
        rng = np.random.default_rng(n_tot * 31 + qtd)
        return sorted(int(x) for x in rng.choice(np.arange(1, n_tot + 1), qtd, replace=False))

    pesos = np.asarray(modelo_popularidade.pesos, dtype=float)
    pair_mat = getattr(modelo_popularidade, "pair_matrix", None)
    if pair_mat is None:
        idx = np.argsort(pesos, kind="stable")[:qtd]
        return sorted(int(i + 1) for i in idx)

    # Seleção gulosa minimizando soma de pesos individuais + interações de pares
    chosen: list[int] = [int(np.argmin(pesos))]
    chosen_set = set(chosen)
    while len(chosen) < qtd:
        best_i = None
        best_delta = float("inf")
        for i in range(n_tot):
            if i in chosen_set:
                continue
            delta = float(pesos[i]) + 2.0 * float(pair_mat[i, chosen].sum())
            if delta < best_delta:
                best_delta = delta
                best_i = i
        if best_i is None:
            break
        chosen.append(best_i)
        chosen_set.add(best_i)
    return sorted(int(i + 1) for i in chosen)


def gerar_fechamento(
    numeros_base: list[int],
    config: GameConfig,
    max_combinacoes: int = 1000,
    completo: bool = False,
):
    """
    Wrapper compatível usado por `LotteryService.closures()`.
    Usa `get_matriz_fechamento` (Covering Designs reais) por padrão e valida o limite de jogos.
    """
    base = sorted({int(x) for x in numeros_base})
    tamanho_jogo = config.bet_size
    if len(base) < tamanho_jogo:
        return []

    if completo:
        total_comb = comb(len(base), tamanho_jogo)
        if total_comb > max_combinacoes:
            return {
                "erro": f"Fechamento completo de {len(base)} números gera {total_comb:,} jogos. "
                f"Limite: {max_combinacoes:,}. Reduza a quantidade de números ou use Covering Design."
            }
        logger.info(
            f"Gerando fechamento completo para {config.name}: {len(base)} números -> {total_comb} jogos."
        )
        return [list(c) for c in combinations(base, tamanho_jogo)]

    jogos = get_matriz_fechamento(base, config, max_jogos=max_combinacoes)
    if len(jogos) > max_combinacoes:
        return {
            "erro": f"Fechamento de {len(base)} números gera {len(jogos):,} jogos. "
            f"Limite: {max_combinacoes:,}. Reduza a quantidade de números."
        }
    logger.info(
        f"Gerando fechamento otimizado para {config.name}: {len(base)} números base -> {len(jogos)} jogos."
    )
    return jogos
