"""Garantias reais dos fechamentos da Lotofácil, verificadas por força bruta.

Para n dezenas na base, considera todos os C(n, 15) casos em que os 15 números
sorteados estão dentro da base e confere o pior caso de acertos entre os jogos
da matriz.
"""

from itertools import combinations

import pytest

from app.core.matrices import MatrixCatalog

SLUG = "loto_facil_sorteio"


def _piso(n: int) -> int:
    jogos = [set(linha) for linha in MatrixCatalog.get_template(n, SLUG)]
    return min(
        max(len(set(sorteio) & jogo) for jogo in jogos)
        for sorteio in combinations(range(n), 15)
    )


@pytest.mark.parametrize("n,qtd_jogos", [(16, 3), (17, 8), (18, 24)])
def test_matriz_garante_14_pontos(n, qtd_jogos):
    template = MatrixCatalog.get_template(n, SLUG)
    assert len(template) == qtd_jogos
    assert _piso(n) >= 14


@pytest.mark.parametrize("n", [16, 17, 18])
def test_matriz_sem_jogos_duplicados_e_com_15_dezenas(n):
    template = MatrixCatalog.get_template(n, SLUG)
    assert all(len(linha) == 15 for linha in template)
    assert all(len(set(linha)) == 15 for linha in template)
    assert all(0 <= x < n for linha in template for x in linha)
    assert len({frozenset(linha) for linha in template}) == len(template)
