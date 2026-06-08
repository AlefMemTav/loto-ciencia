from types import SimpleNamespace

import numpy as np
import pandas as pd

from app.core.generator_objective import score_plausibility_batch
from app.core.lottery.catalog import MEGASENA
from app.services.lottery_service import LotteryService


def _ctx(config=MEGASENA):
    tabela = pd.DataFrame(
        {
            "Z_Freq": np.zeros(config.n_numbers),
            "Z_Gap": np.zeros(config.n_numbers),
        }
    )
    return SimpleNamespace(
        config=config,
        tabela=tabela,
        ic_info={"ic_95": [120, 255], "ic_80": [140, 235]},
        historico_set=set(),
        matriz_coocorrencia=np.ones((config.n_numbers, config.n_numbers)),
        matriz_transicao=None,
        ciclo_atual={},
        df=pd.DataFrame(),
        pesos_dinamicos={"w_freq": 0.5, "w_gap": 0.5},
    )


def test_generator_objective_penalizes_obvious_sequence():
    ctx = _ctx()
    candidates = np.array(
        [
            [1, 2, 3, 4, 5, 6],
            [7, 18, 29, 36, 44, 58],
        ],
        dtype=int,
    )

    scores = score_plausibility_batch(candidates, ctx, null_model_samples=1000)

    assert scores[1] > scores[0]


def test_service_generate_does_not_call_validator(monkeypatch):
    ctx = _ctx()
    service = LotteryService()

    def fail_if_called(*args, **kwargs):
        raise AssertionError("validator must not select generated games")

    monkeypatch.setattr("app.services.lottery_service.validar_jogo", fail_if_called)

    games = service.generate(
        MEGASENA.slug,
        {
            "quantidade": 4,
            "estrategia": "balanceada",
            "seed": 123,
            "null_model_samples": 1000,
        },
        ctx=ctx,
    )

    assert len(games) == 4
    assert all(len(game) == MEGASENA.bet_size for game in games)


def test_generated_portfolio_has_overlap_diversity():
    ctx = _ctx()
    service = LotteryService()

    games = service.generate(
        MEGASENA.slug,
        {
            "quantidade": 5,
            "estrategia": "balanceada",
            "seed": 42,
            "null_model_samples": 1000,
        },
        ctx=ctx,
    )

    overlap_limit = MEGASENA.get_overlap_limit()
    for i, game in enumerate(games):
        for other in games[i + 1 :]:
            assert len(set(game) & set(other)) <= overlap_limit


def test_sparse_portfolio_caps_number_exposure():
    ctx = _ctx()
    service = LotteryService()

    games = service.generate(
        MEGASENA.slug,
        {
            "quantidade": 5,
            "estrategia": "pura",
            "seed": 7,
            "null_model_samples": 1000,
        },
        ctx=ctx,
    )

    exposure = {}
    for game in games:
        for number in game:
            exposure[number] = exposure.get(number, 0) + 1

    assert max(exposure.values()) <= 2
