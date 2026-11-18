"""Testes de integração de LotteryService.validate, latência em cache e view do validador."""

import time

import numpy as np
import pytest

from app.core.lottery.catalog import LOTOFACIL, LOTOMANIA, MEGASENA, QUINA
from app.services.lottery_service import LotteryService
from app.ui.views.validator import _render_advanced_metrics


@pytest.fixture(scope="module")
def service():
    return LotteryService()


@pytest.mark.parametrize(
    "slug,amostra",
    [
        (MEGASENA.slug, [4, 15, 22, 35, 48, 57]),
        (QUINA.slug, [5, 19, 34, 51, 72]),
        (LOTOFACIL.slug, [1, 2, 4, 5, 7, 9, 10, 12, 14, 15, 17, 19, 21, 23, 25]),
    ],
)
def test_lottery_service_validate_popula_todos_os_sinais_cacheados(
    service, slug, amostra
):
    rep = service.validate(slug, amostra)

    assert rep["perfil_cluster"]["disponivel"] is True
    assert rep["bootstrap"]["disponivel"] is True
    assert rep["bootstrap"]["score_ajuste"] == 0

    metricas = rep["metricas"]
    assert isinstance(metricas["regressao_media"], dict)
    assert "correlacao" in metricas["regressao_media"]
    assert "popularidade_medida_percentil" in metricas
    assert "popularidade_medida_razao" in metricas
    assert "repetidas_ultimo_sorteio" in metricas
    assert "hamming_historico_min" in metricas
    assert "hamming_recente_100" in metricas
    assert metricas["modelo_nulo_version"] == "comb-null-v2"
    assert metricas["calibracao_score"]["modelo_version"] == "score-cal-v3"


def test_lottery_service_validate_lotomania_e_check_historical_matches(service):
    aposta = list(range(1, 101, 2))  # 50 números ímpares (k=20, bet=50)
    rep = service.validate(LOTOMANIA.slug, aposta)

    assert rep["perfil_cluster"]["disponivel"] is True
    assert rep["bootstrap"]["disponivel"] is True
    assert "popularidade_medida_percentil" in rep["metricas"]
    assert rep["metricas"].get("popularidade_medida_razao") is None
    assert rep["metricas"]["hamming_historico_min"] == "N/A"
    assert "repetidas_ultimo_sorteio" not in rep["metricas"]

    ctx = service.get_context(LOTOMANIA.slug)
    hist = service.check_historical_matches(LOTOMANIA.slug, aposta, targets=[20, 19, 0])
    assert set(hist.keys()) == {20, 19, 0}
    assert ctx.draws_bin is not None
    assert len(ctx.draws_bin) == len(ctx.df)


@pytest.mark.parametrize("cfg", [MEGASENA, QUINA, LOTOFACIL, LOTOMANIA])
def test_lottery_service_validate_latencia_baixa_com_cache(service, cfg):
    aposta = list(range(1, cfg.bet_size + 1))
    service.validate(cfg.slug, aposta)  # warmup de contexto + cache de calibração

    t0 = time.perf_counter()
    n_runs = 20
    for _ in range(n_runs):
        service.validate(cfg.slug, aposta)
    ms_por_jogo = (time.perf_counter() - t0) * 1000.0 / n_runs
    assert ms_por_jogo < 10.0, f"{cfg.slug} demorou {ms_por_jogo:.2f} ms/jogo"


def test_render_advanced_metrics_lida_com_hamming_zero_e_regressao_media(monkeypatch):
    import streamlit as st

    metricas_capturadas = []
    infos_capturadas = []

    class _DummyCtx:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class _DummyCol:
        def metric(self, label, value, help=None):
            metricas_capturadas.append((label, value))

    monkeypatch.setattr(st, "expander", lambda *a, **k: _DummyCtx())
    monkeypatch.setattr(st, "columns", lambda n: [_DummyCol() for _ in range(n)])
    monkeypatch.setattr(st, "caption", lambda *a, **k: None)
    monkeypatch.setattr(st, "info", lambda txt: infos_capturadas.append(txt))

    _render_advanced_metrics(
        {
            "hamming_min": 0,
            "hamming_historico_min": 0,
            "hamming_recente_100": 2,
            "similaridade_max": 1.0,
            "regressao_media": {
                "correlacao": 0.123,
                "taxa_retorno": 0.45,
                "interpretacao": "Fraca",
            },
        }
    )

    labels = [lbl for lbl, _ in metricas_capturadas]
    assert "Distância Mín. (Histórico)" in labels
    assert "Distância Mín. (Últimos 100)" in labels
    assert "Correlação ρ" in labels

    # Fallback para histórico insuficiente
    _render_advanced_metrics(
        {
            "hamming_historico_min": "N/A",
            "regressao_media": {
                "status": "Histórico insuficiente",
                "minimo_necessario": 100,
                "disponivel": 25,
            },
        }
    )
    assert any("Histórico insuficiente" in msg for msg in infos_capturadas)
