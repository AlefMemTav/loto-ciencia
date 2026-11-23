"""Garantias reais dos fechamentos (Covering Designs) verificadas por força bruta.

Para cada modalidade e base de `v` dezenas, verifica exaustivamente todos os C(v, m)
cenários possíveis para garantir 100% de cobertura matemática.
"""

from itertools import combinations

import numpy as np
import pytest

from app.core.lottery.catalog import LOTOFACIL, LOTOMANIA, MEGASENA, QUINA
from app.core.matrices import (
    MatrixCatalog,
    _gerar_fechamento_dinamico,
    gerar_fechamento,
    gerar_fechamento_detalhado,
    get_matriz_fechamento,
    sugerir_base_antipopular,
    verificar_garantia_fechamento,
)

SLUG_LF = "loto_facil_sorteio"


def _piso(n: int) -> int:
    jogos = [set(linha) for linha in MatrixCatalog.get_template(n, SLUG_LF)]
    return min(
        max(len(set(sorteio) & jogo) for jogo in jogos)
        for sorteio in combinations(range(n), 15)
    )


@pytest.mark.parametrize("n,qtd_jogos", [(16, 1), (17, 8), (18, 24)])
def test_lotofacil_matriz_garante_14_pontos(n, qtd_jogos):
    template = MatrixCatalog.get_template(n, SLUG_LF)
    assert len(template) == qtd_jogos
    assert _piso(n) >= 14


@pytest.mark.parametrize("n", [16, 17, 18, 19])
def test_lotofacil_matriz_sem_jogos_duplicados_e_com_15_dezenas(n):
    template = MatrixCatalog.get_template(n, SLUG_LF)
    assert template is not None
    assert all(len(linha) == 15 for linha in template)
    assert all(len(set(linha)) == 15 for linha in template)
    assert all(0 <= x < n for linha in template for x in linha)
    assert len({frozenset(linha) for linha in template}) == len(template)


def test_lotofacil_19_e_20_garantem_13_se_15_com_economia_real():
    for v in (19, 20):
        base = list(range(1, v + 1))
        res = gerar_fechamento_detalhado(base, LOTOFACIL)
        assert res["garantia_verificada"] is True
        assert res["garantia_t"] == 13 and res["condicao_m"] == 15
        assert len(res["jogos"]) < 60
        ver = verificar_garantia_fechamento(res["jogos"], base, 13, 15)
        assert ver["verificado"] is True
        assert ver["piso_acertos"] >= 13


@pytest.mark.parametrize(
    "v,t,m,max_jogos",
    [
        (10, 5, 6, 20),  # Mega Quina se 6 (vs 210 completo)
        (10, 4, 4, 28),  # Mega Covering Design C(10, 6, 4) (vs 210)
        (12, 4, 6, 10),  # Mega Quadra se 6 (vs 924)
        (15, 4, 6, 30),  # Mega Quadra se 6 (vs 5005)
    ],
)
def test_megasena_covering_designs_verificados_100pct(v, t, m, max_jogos):
    base = list(range(1, v + 1))
    res = gerar_fechamento_detalhado(base, MEGASENA, garantia_t=t, condicao_m=m)
    jogos = res["jogos"]
    assert res["garantia_verificada"] is True
    assert 1 <= len(jogos) <= max_jogos
    assert all(len(j) == 6 and len(set(j)) == 6 for j in jogos)
    ver = verificar_garantia_fechamento(jogos, base, t, m)
    assert ver["verificado"] is True
    assert ver["piso_acertos"] >= t


@pytest.mark.parametrize(
    "v,t,m,max_jogos",
    [
        (10, 4, 5, 22),  # Quina Quadra se 5 (vs 252)
        (10, 3, 3, 22),  # Quina Covering Design C(10, 5, 3) (vs 252)
        (15, 3, 5, 22),  # Quina Terno se 5 (vs 3003)
    ],
)
def test_quina_covering_designs_verificados_100pct(v, t, m, max_jogos):
    base = list(range(1, v + 1))
    res = gerar_fechamento_detalhado(base, QUINA, garantia_t=t, condicao_m=m)
    jogos = res["jogos"]
    assert res["garantia_verificada"] is True
    assert 1 <= len(jogos) <= max_jogos
    assert all(len(j) == 5 and len(set(j)) == 5 for j in jogos)
    ver = verificar_garantia_fechamento(jogos, base, t, m)
    assert ver["verificado"] is True
    assert ver["piso_acertos"] >= t


def test_deduplicacao_base_e_limite_dinamico_acima_de_100():
    # Base com duplicatas não pode gerar bilhetes com dezenas repetidas
    base_dup = [1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
    jogos = get_matriz_fechamento(base_dup, LOTOFACIL)
    assert all(len(j) == 15 and len(set(j)) == 15 for j in jogos)

    # _gerar_fechamento_dinamico deve respeitar limite >= 100 (sem truncar silenciosamente em 50)
    jogos_120 = _gerar_fechamento_dinamico(list(range(1, 61)), 50, limite=120)
    assert len(jogos_120) == 120
    assert len({tuple(j) for j in jogos_120}) == 120


def test_gerar_fechamento_unificado_e_base_antipopular():
    jogos_quina = gerar_fechamento(list(range(1, 11)), QUINA)
    assert isinstance(jogos_quina, list)
    assert len(jogos_quina) <= 22  # usa Covering Design, não 252 completo

    # Base antipopular deve preferir dezenas com menores pesos de popularidade
    class _ModeloFake:
        pesos = np.arange(60, dtype=float)  # 1..10 têm os menores pesos
        pair_matrix = None

    sug = sugerir_base_antipopular(MEGASENA, 10, modelo_popularidade=_ModeloFake())
    assert sug == list(range(1, 11))

    # Lotomania parse de 00 -> 100
    from app.ui.views.closures import _parse_base_numbers

    parsed = _parse_base_numbers("00 01 02 99", LOTOMANIA.slug)
    assert parsed == [1, 2, 99, 100]
