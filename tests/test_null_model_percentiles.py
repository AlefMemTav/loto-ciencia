import numpy as np

from app.core.lottery.catalog import MEGASENA, QUINA, LOTOFACIL, LOTOMANIA
from app.core.statistics.feature_percentiles import summarize_feature_percentiles
from app.core.statistics.null_model import get_null_model


def test_null_model_builds_for_all_games_with_sorted_metrics():
    for config in [MEGASENA, QUINA, LOTOFACIL, LOTOMANIA]:
        model = get_null_model(config, n_samples=1000)

        assert model.n_samples == 1000
        assert "soma" in model.metrics
        assert "span" in model.metrics
        assert len(model.metrics["soma"]) == 1000
        assert np.all(model.metrics["soma"][:-1] <= model.metrics["soma"][1:])


def test_null_model_cache_reuses_instance():
    model_a = get_null_model(MEGASENA, n_samples=1000)
    model_b = get_null_model(MEGASENA, n_samples=1000)

    assert model_a is model_b


def test_feature_percentiles_are_bounded_and_report_rare_tails():
    result = summarize_feature_percentiles(
        [1, 2, 3, 4, 5, 6],
        MEGASENA,
        n_samples=1000,
    )

    percentiles = result["percentis_combinatorios"]

    assert percentiles
    assert all(0 <= value <= 100 for value in percentiles.values())
    assert result["caudas_raras"]
