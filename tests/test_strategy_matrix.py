from app.core.statistics.strategy_matrix import (
    agregar_registros,
    montar_relatorio_matriz,
    normalizar_run,
    render_markdown_report,
)


def _motor_result(
    *,
    hit4=0,
    hit5=0,
    hit6=0,
    delta=0.0,
    ic_low=0.0,
    ic_high=0.0,
    win=0.0,
    max_acertos=3,
    max_exposicao=5,
    overlap_max=2,
    trincas=0,
    quadras=0,
):
    return {
        "stats": {
            "delta_medio_vs_acaso": hit4 * 100,
            "ic95_delta_medio": [0.0, 0.0],
            "mediana_p_emp": 1.0,
            "win_rate_vs_media_mc": 0.5,
            "delta_medio_acertos_vs_mc": delta,
            "ic95_delta_medio_acertos": [ic_low, ic_high],
            "mediana_p_emp_media_acertos": 0.4,
            "win_rate_media_acertos_vs_mc": win,
        },
        "hits": {
            "4": hit4,
            "5": hit5,
            "6": hit6,
        },
        "acertos": {
            "media_acertos": 0.6 + delta,
            "max_acertos_observado": max_acertos,
            "comparacoes": 100,
        },
        "portfolio": {
            "medias": {
                "max_exposicao": max_exposicao,
                "overlap_max": overlap_max,
                "overlap_medio": 1.0,
                "pares_repetidos": 30,
                "pares_repetidos_acima_2": 2,
                "max_repeticao_par": 3,
                "trincas_repetidas": trincas,
                "quadras_repetidas": quadras,
                "coocorrencia_media": 17.0,
                "dispersao_features.soma.desvio": 30.0,
                "dispersao_features.span.desvio": 8.0,
                "dispersao_features.pares.desvio": 1.0,
                "dispersao_features.gap_medio.desvio": 1.5,
            }
        },
    }


def _run(strategy, seed, vet=None, gen=None):
    vet = vet or _motor_result()
    gen = gen or _motor_result()
    return {
        "estrategia": strategy,
        "seed": seed,
        "status": "ok",
        "resultado": {
            "analise_estatistica": {
                "Vetorial": vet["stats"],
                "Genetico": gen["stats"],
            },
            "hits_absolutos_reais": {
                "Vetorial": vet["hits"],
                "Genetico": gen["hits"],
            },
            "diagnostico_acertos": {
                "Vetorial": vet["acertos"],
                "Genetico": gen["acertos"],
            },
            "diagnostico_portfolio": {
                "Vetorial": vet["portfolio"],
                "Genetico": gen["portfolio"],
            },
        },
    }


def test_strategy_matrix_aggregates_multiple_seeds():
    runs = [
        _run("a", 1, vet=_motor_result(hit4=2, delta=0.02)),
        _run("a", 2, vet=_motor_result(hit4=4, delta=0.04)),
    ]
    records = [record for run in runs for record in normalizar_run(run)]

    aggregated = agregar_registros(records)
    metrics = aggregated["metricas_agregadas"]["a"]["Vetorial"]["metricas"]

    assert metrics["hit_4"]["media"] == 3.0
    assert metrics["delta_medio_acertos_vs_mc"]["media"] == 0.03
    assert aggregated["metricas_agregadas"]["a"]["Vetorial"]["n_runs"] == 2


def test_strategy_matrix_penalizes_ic_crossing_zero():
    runs = [
        _run(
            "positive_ic",
            1,
            vet=_motor_result(hit4=3, delta=0.03, ic_low=0.01, ic_high=0.05),
        ),
        _run(
            "crosses_zero",
            1,
            vet=_motor_result(hit4=3, delta=0.03, ic_low=-0.01, ic_high=0.05),
        ),
    ]
    report = montar_relatorio_matriz(
        meta_execucao={"jogo": "mega_sena_sorteio"},
        runs=runs,
    )
    ranking = report["ranking_por_motor"]["Vetorial"]

    assert ranking[0]["estrategia"] == "positive_ic"
    assert any(alert["tipo"] == "ic_cruza_zero" for alert in report["alertas"])


def test_strategy_matrix_penalizes_excessive_concentration():
    runs = [
        _run(
            "unsafe",
            1,
            vet=_motor_result(
                hit4=5,
                delta=0.04,
                ic_low=0.01,
                ic_high=0.06,
                max_exposicao=20,
                overlap_max=6,
                trincas=50,
                quadras=10,
            ),
        ),
        _run(
            "safe",
            1,
            vet=_motor_result(
                hit4=4,
                delta=0.04,
                ic_low=0.01,
                ic_high=0.06,
                max_exposicao=5,
                overlap_max=2,
            ),
        ),
    ]
    report = montar_relatorio_matriz(
        meta_execucao={"jogo": "mega_sena_sorteio"},
        runs=runs,
    )
    ranking = report["ranking_por_motor"]["Vetorial"]

    assert ranking[0]["estrategia"] == "safe"
    assert any(
        alert["tipo"] == "concentracao_excessiva" for alert in report["alertas"]
    )


def test_strategy_matrix_preserves_raw_metrics_and_renders_markdown():
    run = _run(
        "a",
        42,
        vet=_motor_result(hit4=3, delta=0.03, ic_low=0.01, ic_high=0.05),
    )
    report = montar_relatorio_matriz(
        meta_execucao={
            "jogo": "mega_sena_sorteio",
            "estrategias": ["a"],
            "seeds": [42],
        },
        runs=[run],
    )
    raw = report["metricas_agregadas"]["a"]["Vetorial"]["runs"][0][
        "metricas_brutas"
    ]
    markdown = render_markdown_report(report)

    assert raw["hit_4"] == 3.0
    assert raw["delta_medio_acertos_vs_mc"] == 0.03
    assert "Ranking Geral" in markdown
    assert "a" in markdown
