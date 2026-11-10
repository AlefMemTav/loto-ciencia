from types import SimpleNamespace

import numpy as np
import pandas as pd

from app.core.generator_objective import (
    portfolio_diagnostics,
    score_plausibility_batch,
)
from app.core.lottery.catalog import MEGASENA, LOTOFACIL
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
    monkeypatch.setattr("app.core.validator.calcular_score_rapido", fail_if_called)

    games = service.generate(
        MEGASENA.slug,
        {
            "quantidade": 4,
            "estrategia": "balanceada",
            "seed": 123,
            "null_model_samples": 1000,
            "usar_calibracao_score": True,
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


def test_tail_controlled_strategy_caps_exposure_and_pairs():
    ctx = _ctx()
    service = LotteryService()

    games = service.generate(
        MEGASENA.slug,
        {
            "quantidade": 20,
            "estrategia": "cauda_controlada",
            "seed": 99,
            "null_model_samples": 1000,
        },
        ctx=ctx,
    )

    diag = portfolio_diagnostics(games, MEGASENA, ctx.matriz_coocorrencia)

    assert len(games) == 20
    assert diag["max_exposicao"] <= 5
    assert diag["max_repeticao_par"] <= 3
    assert diag["overlap_max"] <= MEGASENA.get_overlap_limit()


def test_old_tail_names_are_aliases_of_tail_controlled():
    """cauda_agressiva e cauda_convexa foram fundidas em cauda_controlada."""
    ctx = _ctx()
    service = LotteryService()

    def gerar(nome):
        return service.generate(
            MEGASENA.slug,
            {
                "quantidade": 10,
                "estrategia": nome,
                "seed": 202,
                "null_model_samples": 1000,
            },
            ctx=ctx,
        )

    base = gerar("cauda_controlada")
    assert gerar("cauda_convexa") == base
    assert gerar("cauda_agressiva") == base


def test_tail_controlled_dense_game_uses_density_aware_caps():
    ctx = _ctx(LOTOFACIL)
    service = LotteryService()

    games = service.generate(
        LOTOFACIL.slug,
        {
            "quantidade": 5,
            "estrategia": "cauda_controlada",
            "seed": 303,
            "null_model_samples": 1000,
        },
        ctx=ctx,
    )

    diag = portfolio_diagnostics(games, LOTOFACIL, ctx.matriz_coocorrencia)

    assert len(games) == 5
    assert all(len(game) == LOTOFACIL.bet_size for game in games)
    assert diag["overlap_max"] <= LOTOFACIL.get_overlap_limit()


def test_real_game_mode_returns_auditable_package_without_validator(monkeypatch):
    ctx = _ctx()
    service = LotteryService()

    def fail_if_called(*args, **kwargs):
        raise AssertionError("validator must not select real-game packages")

    monkeypatch.setattr("app.services.lottery_service.validar_jogo", fail_if_called)

    result = service.generate_real_game(
        MEGASENA.slug,
        {
            "quantidade": 2,
            "perfil_esforco": "rapido",
            "estrategia_base": "balanceada",
            "seed": 123,
            "candidate_pool_size": 16,
            "tournament_packages": 10,
            "monte_carlo_packages": 20,
            "null_model_samples": 1000,
        },
        ctx=ctx,
    )

    assert len(result["jogos"]) == 2
    assert all(len(game) == MEGASENA.bet_size for game in result["jogos"])
    assert result["relatorio"]["modo"] == "jogo_real"
    assert result["relatorio"]["seed"] == 123
    assert 0 <= result["relatorio"]["percentil_vs_monte_carlo"] <= 100
    assert 0 <= result["relatorio"]["p_empirico_mc_supera_ou_iguala"] <= 1
    assert result["relatorio"]["diagnostico_calibracao_score"]["js_vs_alvo"] >= 0
