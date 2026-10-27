import numpy as np
import pandas as pd

from app.core.lottery.catalog import MEGASENA
from app.core.statistics.score_calibration import (
    BUCKET_LABELS,
    get_score_calibration_model,
    score_calibration_diagnostics,
    score_structural_batch,
    summarize_score_calibration,
)


def _history_df():
    return pd.DataFrame(
        [
            [4, 10, 23, 31, 45, 59],
            [7, 18, 29, 36, 44, 58],
            [2, 13, 24, 35, 46, 57],
            [8, 19, 27, 33, 42, 55],
        ],
        columns=MEGASENA.draw_cols,
    )


def test_score_calibration_distributions_sum_to_100():
    model = get_score_calibration_model(
        MEGASENA,
        df_historico=_history_df(),
        n_samples=1000,
    )

    for dist in (
        model.history_distribution,
        model.null_distribution,
        model.target_distribution,
    ):
        assert set(dist) == set(BUCKET_LABELS)
        assert abs(sum(dist.values()) - 100.0) < 0.001


def test_structural_score_penalizes_obvious_sequence():
    scores = score_structural_batch(
        np.array(
            [
                [1, 2, 3, 4, 5, 6],
                [7, 18, 29, 36, 44, 58],
            ],
            dtype=int,
        ),
        MEGASENA,
        n_samples=1000,
    )

    assert 0 <= scores[0] <= 100
    assert 0 <= scores[1] <= 100
    assert scores[0] < 40
    assert scores[1] > scores[0]


def test_validator_summary_fields_are_available():
    summary = summarize_score_calibration(
        [1, 2, 3, 4, 5, 6],
        MEGASENA,
        df_historico=_history_df(),
        n_samples=1000,
    )

    assert summary["bucket"] == "0-39"
    assert summary["freq_historica"] >= 0
    assert summary["freq_modelo_nulo"] >= 0
    assert summary["freq_alvo"] >= 0
    assert summary["modelo_version"]


def test_score_calibration_diagnostics_reports_divergence():
    diagnostics = score_calibration_diagnostics(
        [
            [1, 2, 3, 4, 5, 6],
            [7, 18, 29, 36, 44, 58],
        ],
        MEGASENA,
        df_historico=_history_df(),
        n_samples=1000,
    )

    assert diagnostics["distribuicao_gerada"]
    assert diagnostics["js_vs_alvo"] >= 0
    assert diagnostics["chi_square_vs_alvo"] >= 0
