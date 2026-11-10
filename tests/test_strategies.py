import pytest

from app.core.lottery.catalog import LOTOFACIL, MEGASENA
from app.core.strategies import (
    APELIDOS,
    ESTRATEGIAS,
    estrategia_padrao,
    normalizar_estrategia,
)


def test_estrategias_canonicas():
    assert set(ESTRATEGIAS) == {"balanceada", "cauda_controlada", "pura"}


@pytest.mark.parametrize(
    "antigo,novo",
    [
        ("agressiva", "balanceada"),
        ("conservadora", "balanceada"),
        ("cauda_agressiva", "cauda_controlada"),
        ("cauda_convexa", "cauda_controlada"),
    ],
)
def test_apelidos_resolvem_para_canonica(antigo, novo):
    assert APELIDOS[antigo] == novo
    assert normalizar_estrategia(antigo) == novo
    assert normalizar_estrategia(antigo.upper()) == novo


def test_padrao_e_balanceada_quando_vazio():
    assert normalizar_estrategia(None) == "balanceada"


def test_estrategia_invalida_levanta_erro():
    with pytest.raises(ValueError):
        normalizar_estrategia("adivinhadora")


def test_padrao_por_densidade():
    assert estrategia_padrao(MEGASENA) == "cauda_controlada"
    assert estrategia_padrao(LOTOFACIL) == "balanceada"
