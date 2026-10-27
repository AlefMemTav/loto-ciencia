import numpy as np

from app.core.lottery.catalog import LOTOFACIL, MEGASENA
from app.core.statistics.prize_model import (
    diagnostics_to_dict,
    financial_diagnostics,
    parse_prize_table,
    resolve_prize_table,
)


def test_lotofacil_default_prize_table_has_fixed_tiers():
    table = resolve_prize_table(LOTOFACIL)

    assert table[11] == 6.0
    assert table[12] == 12.0
    assert table[13] == 30.0
    assert 14 not in table
    assert 15 not in table


def test_prize_overrides_extend_defaults():
    table = resolve_prize_table(
        LOTOFACIL,
        parse_prize_table(["14=1500", "15=1500000"]),
    )

    assert table[11] == 6.0
    assert table[14] == 1500.0
    assert table[15] == 1500000.0


def test_financial_diagnostics_counts_cost_per_future_draw():
    games = [[1, 2, 3, 4, 5, 6]]
    draws = np.array(
        [
            [1, 2, 3, 4, 10, 11],
            [1, 2, 3, 20, 21, 22],
        ],
        dtype=int,
    )

    result = diagnostics_to_dict(
        financial_diagnostics(
            games,
            draws,
            MEGASENA,
            prize_table={4: 100.0},
        )
    )

    assert result["custo_total"] == MEGASENA.game_price * 2
    assert result["receita_bruta"] == 100.0
    assert result["hits_pagos"] == {"4": 1}
    assert result["fator_retorno"] > 1
