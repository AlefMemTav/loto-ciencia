import numpy as np
import pandas as pd
import pytest

from app.core.lottery.catalog import LOTOFACIL, LOTOMANIA, MEGASENA
from app.core.statistics.prize_model import (
    diagnostics_to_dict,
    estimar_ev_concurso_ex_ante,
    filtrar_detalhes_causais,
    financial_diagnostics,
    hypergeometric_hit_probability,
    parse_prize_table,
    poisson_ev_elasticity,
    poisson_retention_factor,
    resolve_prize_table,
)


def test_lotofacil_default_prize_table_has_fixed_tiers():
    table = resolve_prize_table(LOTOFACIL)

    assert table[11] == 7.0
    assert table[12] == 14.0
    assert table[13] == 35.0
    assert 14 not in table
    assert 15 not in table


def test_prize_overrides_extend_defaults():
    table = resolve_prize_table(
        LOTOFACIL,
        parse_prize_table(["14=1500", "15=1500000"]),
    )

    assert table[11] == 7.0
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


def test_poisson_retention_and_elasticity_limits():
    assert poisson_retention_factor(0.0, 1.0) == pytest.approx(1.0)
    assert poisson_retention_factor(1.0, 1.0) == pytest.approx(1.0 - np.exp(-1.0))
    assert poisson_retention_factor(2.0, 0.5) > poisson_retention_factor(2.0, 1.0)
    assert poisson_ev_elasticity(0.0, 1.0) == pytest.approx(0.0)
    assert poisson_ev_elasticity(5.0, 1.0) > poisson_ev_elasticity(0.5, 1.0)
    assert hypergeometric_hit_probability(100, 20, 50, 0) == pytest.approx(
        hypergeometric_hit_probability(100, 20, 50, 20)
    )


def test_estimar_ev_concurso_ex_ante_detecta_acumulado_e_antipopularidade():
    rng = np.random.default_rng(42)
    n = 60
    arr = rng.uniform(4e7, 7e7, size=n)
    est = arr * 0.45
    est[-1] = 2.8e8  # Mega acumulado no ultimo concurso conhecido (t-1)
    df_det = pd.DataFrame(
        {
            "Concurso": np.arange(1, n + 1),
            "valorArrecadado": arr,
            "valorEstimadoProximoConcurso": est,
            "valorAcumuladoProximoConcurso": est * 0.85,
            "valorAcumuladoConcursoEspecial": np.zeros(n),
            "acumulado": [i % 2 == 0 for i in range(n - 1)] + [True],
            "faixa1_ganhadores": [1 if i % 2 == 1 else 0 for i in range(n)],
            "faixa1_premio": est,
            "faixa2_ganhadores": np.full(n, 80),
            "faixa2_premio": arr * 0.06 / 80.0,
            "faixa3_ganhadores": np.full(n, 5000),
            "faixa3_premio": arr * 0.08 / 5000.0,
        }
    )
    ev_base = estimar_ev_concurso_ex_ante(MEGASENA, df_det, razao_popularidade=1.0)
    ev_anti = estimar_ev_concurso_ex_ante(MEGASENA, df_det, razao_popularidade=0.55)
    ev_bolao = estimar_ev_concurso_ex_ante(
        MEGASENA, df_det, razao_popularidade=0.55, agio_bolao=0.35
    )

    assert ev_base["disponivel"] is True
    assert ev_anti["ev_por_real_ajustado"] > ev_base["ev_por_real_aleatorio"]
    assert ev_anti["ganho_relativo_antipopular"] > 0.15
    assert ev_anti["recomendacao_aposta"] in {
        "APOSTAR_EV_POSITIVO",
        "APOSTAR_ACUMULADO_TOP10",
    }
    assert ev_bolao["ev_por_real_ajustado"] == pytest.approx(
        ev_anti["ev_por_real_ajustado"] / 1.35, rel=1e-3
    )


def test_prize_model_usa_coluna_acumulou_guarda_est_zero_e_fresh_f1():
    """Regressão: schema real da Caixa ('acumulou' bool/str, est_prox==0 histórico, fresh_f1 Lotofácil)."""
    rng = np.random.default_rng(123)
    n = 80
    arr = rng.uniform(2.5e7, 3.5e7, size=n)
    est = np.where(np.arange(n) < 25, 0.0, arr * 0.078)
    # Metade dos concursos têm ganhadores na faixa 1; quando acumula em t-1,
    # o pagamento total em t inclui o carryover acumulado + 0,078 da arrecadação nova.
    acum_col = ["False" if i % 2 == 0 else "True" for i in range(n - 1)] + ["False"]
    acum_prox = np.where(np.array(acum_col) == "True", arr * 0.078, 0.0)
    acum_prev = np.concatenate([[0.0], acum_prox[:-1]])
    f1_w = np.array([2 if a == "False" else 0 for a in acum_col])
    f1_p = np.where(f1_w > 0, (acum_prev + arr * 0.078) / np.maximum(f1_w, 1), 0.0)
    df_det = pd.DataFrame(
        {
            "Concurso": np.arange(1, n + 1),
            "valorArrecadado": arr,
            "valorEstimadoProximoConcurso": est,
            "valorAcumuladoProximoConcurso": acum_prox,
            "valorAcumuladoConcursoEspecial": np.zeros(n),
            "acumulou": acum_col,
            "faixa1_ganhadores": f1_w,
            "faixa1_premio": f1_p,
            "faixa2_ganhadores": np.full(n, 300),
            "faixa2_premio": arr * 0.03 / 300.0,
        }
    )
    res = estimar_ev_concurso_ex_ante(LOTOFACIL, df_det, razao_popularidade=0.75)
    assert res["disponivel"] is True
    assert res["acumulado_anterior"] is False
    # Deve estimar fresh_f1 próximo ao real (~0.078), não o antigo hardcoded 0.16
    assert 0.065 <= res["fresh_f1_ratio_estimado"] <= 0.095
    assert np.isfinite(res["arrecadacao_estimada"]) and res["arrecadacao_estimada"] > 1e7
    assert 0.0 < res["ev_por_real_aleatorio"] < 1.0
    assert 0.0 <= res["percentil_historico_ev"] <= 100.0


def test_filtrar_detalhes_causais_estritamente_causal():
    det = pd.DataFrame({"valorArrecadado": [10.0, 20.0, 30.0, 40.0]}, index=pd.Index([10, 11, 12, 13], name="Concurso"))
    df_hist_parcial = pd.DataFrame({"bola 1": [1, 2]}, index=pd.Index([10, 11], name="Concurso"))
    df_hist_sem_overlap = pd.DataFrame({"bola 1": [1, 2]}, index=pd.Index([1, 2], name="Concurso"))

    recorte = filtrar_detalhes_causais(det, df_hist_parcial)
    assert list(recorte.index) == [10, 11]

    # Sem interseção: deve devolver DataFrame vazio, NUNCA vazar o futuro inteiro
    vazio = filtrar_detalhes_causais(det, df_hist_sem_overlap)
    assert vazio.empty
    assert filtrar_detalhes_causais(None, df_hist_parcial).empty
