"""
Strategy matrix for reproducible lottery generator experiments.

This module keeps the ranking logic outside the generators.  The composite
score is diagnostic only: it helps compare backtest reports, but it must not be
used as a generation objective.
"""

from __future__ import annotations

from datetime import datetime
from statistics import mean, median, pstdev
from time import perf_counter
from typing import Any, Iterable

from app.core.statistics.backtest import executar_backtest_temporal


DEFAULT_STRATEGIES = [
    "agressiva",
    "cauda_agressiva",
    "cauda_convexa",
    "cauda_controlada",
    "balanceada",
    "pura",
]
DEFAULT_SEEDS = [7, 21, 42, 77, 101]
MOTORS = ("Vetorial", "Genetico")


def _num(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _get_path(data: dict[str, Any], path: Iterable[str], default: Any = None) -> Any:
    cur: Any = data
    for part in path:
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def _metric_stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {
            "media": 0.0,
            "mediana": 0.0,
            "desvio": 0.0,
            "min": 0.0,
            "max": 0.0,
        }
    return {
        "media": round(float(mean(values)), 6),
        "mediana": round(float(median(values)), 6),
        "desvio": round(float(pstdev(values)), 6) if len(values) > 1 else 0.0,
        "min": round(float(min(values)), 6),
        "max": round(float(max(values)), 6),
    }


def normalizar_run(run: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten one matrix run into per-motor comparable records."""
    if run.get("status") != "ok":
        return []

    resultado = run.get("resultado", {})
    records: list[dict[str, Any]] = []
    for motor in MOTORS:
        stats = _get_path(resultado, ["analise_estatistica", motor], {}) or {}
        acertos = _get_path(resultado, ["diagnostico_acertos", motor], {}) or {}
        portfolio = (
            _get_path(resultado, ["diagnostico_portfolio", motor, "medias"], {})
            or {}
        )
        calibracao = (
            _get_path(resultado, ["diagnostico_calibracao_score", motor, "medias"], {})
            or {}
        )
        financeiro = _get_path(resultado, ["diagnostico_financeiro", motor], {}) or {}
        hits = _get_path(resultado, ["hits_absolutos_reais", motor], {}) or {}

        ic_acertos = stats.get("ic95_delta_medio_acertos") or [0.0, 0.0]
        if len(ic_acertos) < 2:
            ic_acertos = [0.0, 0.0]

        record = {
            "estrategia": run.get("estrategia"),
            "seed": int(run.get("seed", 0)),
            "motor": motor,
            "jogo": _get_path(resultado, ["meta", "jogo"], ""),
            "delta_medio_vs_acaso": _num(stats.get("delta_medio_vs_acaso")),
            "delta_medio_acertos_vs_mc": _num(
                stats.get("delta_medio_acertos_vs_mc")
            ),
            "ic95_delta_acertos_low": _num(ic_acertos[0]),
            "ic95_delta_acertos_high": _num(ic_acertos[1]),
            "mediana_p_emp": _num(stats.get("mediana_p_emp")),
            "mediana_p_emp_media_acertos": _num(
                stats.get("mediana_p_emp_media_acertos")
            ),
            "win_rate_vs_media_mc": _num(stats.get("win_rate_vs_media_mc")),
            "win_rate_media_acertos_vs_mc": _num(
                stats.get("win_rate_media_acertos_vs_mc")
            ),
            "hit_4": _num(hits.get("4")),
            "hit_5": _num(hits.get("5")),
            "hit_6": _num(hits.get("6")),
            "media_acertos": _num(acertos.get("media_acertos")),
            "max_acertos_observado": _num(acertos.get("max_acertos_observado")),
            "max_exposicao": _num(portfolio.get("max_exposicao")),
            "overlap_medio": _num(portfolio.get("overlap_medio")),
            "overlap_max": _num(portfolio.get("overlap_max")),
            "pares_repetidos": _num(portfolio.get("pares_repetidos")),
            "pares_repetidos_acima_2": _num(
                portfolio.get("pares_repetidos_acima_2")
            ),
            "max_repeticao_par": _num(portfolio.get("max_repeticao_par")),
            "trincas_repetidas": _num(portfolio.get("trincas_repetidas")),
            "max_repeticao_trinca": _num(portfolio.get("max_repeticao_trinca")),
            "quadras_repetidas": _num(portfolio.get("quadras_repetidas")),
            "max_repeticao_quadra": _num(portfolio.get("max_repeticao_quadra")),
            "coocorrencia_media": _num(portfolio.get("coocorrencia_media")),
            "soma_desvio": _num(
                portfolio.get("dispersao_features.soma.desvio")
            ),
            "span_desvio": _num(
                portfolio.get("dispersao_features.span.desvio")
            ),
            "pares_desvio": _num(
                portfolio.get("dispersao_features.pares.desvio")
            ),
            "gap_medio_desvio": _num(
                portfolio.get("dispersao_features.gap_medio.desvio")
            ),
            "calibracao_score_medio": _num(calibracao.get("score_medio")),
            "calibracao_js_vs_alvo": _num(calibracao.get("js_vs_alvo")),
            "calibracao_chi_square_vs_alvo": _num(
                calibracao.get("chi_square_vs_alvo")
            ),
            "roi": _num(financeiro.get("roi")),
            "fator_retorno": _num(financeiro.get("fator_retorno")),
            "receita_bruta": _num(financeiro.get("receita_bruta")),
            "custo_total": _num(financeiro.get("custo_total")),
            "lucro_liquido": _num(financeiro.get("lucro_liquido")),
            "delta_medio_receita_vs_mc": _num(
                stats.get("delta_medio_receita_vs_mc")
            ),
            "win_rate_receita_vs_mc": _num(stats.get("win_rate_receita_vs_mc")),
            "mediana_p_emp_receita": _num(stats.get("mediana_p_emp_receita")),
        }
        records.append(record)
    return records


def _safe_mean(metrics: dict[str, dict[str, float]], key: str) -> float:
    return _num(metrics.get(key, {}).get("media"))


def _safe_std(metrics: dict[str, dict[str, float]], key: str) -> float:
    return _num(metrics.get(key, {}).get("desvio"))


def _score_composto(
    metrics: dict[str, dict[str, float]], records: list[dict[str, Any]]
) -> float:
    hit4 = _safe_mean(metrics, "hit_4")
    hit5 = _safe_mean(metrics, "hit_5")
    hit6 = _safe_mean(metrics, "hit_6")
    delta_acertos = _safe_mean(metrics, "delta_medio_acertos_vs_mc")
    max_acertos = _safe_mean(metrics, "max_acertos_observado")
    win_acertos = _safe_mean(metrics, "win_rate_media_acertos_vs_mc")
    ic_low = _safe_mean(metrics, "ic95_delta_acertos_low")
    macro_delta = _safe_mean(metrics, "delta_medio_vs_acaso")
    roi = _safe_mean(metrics, "roi")
    delta_receita = _safe_mean(metrics, "delta_medio_receita_vs_mc")
    win_receita = _safe_mean(metrics, "win_rate_receita_vs_mc")

    max_exposure = _safe_mean(metrics, "max_exposicao")
    overlap_max = _safe_mean(metrics, "overlap_max")
    pair_reuse_heavy = _safe_mean(metrics, "pares_repetidos_acima_2")
    triples = _safe_mean(metrics, "trincas_repetidas")
    quads = _safe_mean(metrics, "quadras_repetidas")
    calibration_js = _safe_mean(metrics, "calibracao_js_vs_alvo")
    roi = _safe_mean(metrics, "roi")

    score = 0.0
    score += hit4 * 7.0
    score += hit5 * 70.0
    score += hit6 * 500.0
    score += max_acertos * 2.0
    score += delta_acertos * 120.0
    score += win_acertos * 4.0
    score += max(0.0, ic_low) * 80.0
    score += macro_delta / 80.0
    score += max(-1.0, roi) * 1.5
    score += delta_receita / 50.0
    score += win_receita * 1.5

    if ic_low <= 0:
        score -= 2.0

    score -= _safe_std(metrics, "hit_4") * 0.75
    score -= _safe_std(metrics, "delta_medio_acertos_vs_mc") * 60.0
    score -= max(0.0, max_exposure - 6.0) * 1.6
    score -= max(0.0, overlap_max - 3.0) * 1.2
    score -= max(0.0, pair_reuse_heavy - 30.0) * 0.03
    score -= triples * 0.08
    score -= quads * 1.5
    score -= calibration_js * 3.0

    if len(records) < 2:
        score -= 1.0

    return round(float(score), 6)


def _gerar_alertas_agregado(
    estrategia: str,
    motor: str,
    metrics: dict[str, dict[str, float]],
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []

    def add(tipo: str, severidade: str, mensagem: str) -> None:
        alerts.append(
            {
                "estrategia": estrategia,
                "motor": motor,
                "tipo": tipo,
                "severidade": severidade,
                "mensagem": mensagem,
            }
        )

    ic_low = _safe_mean(metrics, "ic95_delta_acertos_low")
    hit4_mean = _safe_mean(metrics, "hit_4")
    hit4_std = _safe_std(metrics, "hit_4")
    exposure = _safe_mean(metrics, "max_exposicao")
    overlap = _safe_mean(metrics, "overlap_max")
    triples = _safe_mean(metrics, "trincas_repetidas")
    quads = _safe_mean(metrics, "quadras_repetidas")
    calibration_js = _safe_mean(metrics, "calibracao_js_vs_alvo")
    roi = _safe_mean(metrics, "roi")
    n_runs = len(records)
    jogo = str(records[0].get("jogo", "") if records else "").lower()
    dense_game = "lotof" in jogo or "mania" in jogo
    exposure_threshold = 15 if dense_game else 6
    overlap_threshold = 12 if dense_game else 3

    if n_runs < 2:
        add("poucas_seeds", "media", "Ranking baseado em menos de 2 seeds.")
    if ic_low <= 0:
        add(
            "ic_cruza_zero",
            "alta",
            "IC95 medio do delta de acertos cruza ou toca zero.",
        )
    if hit4_mean > 0 and hit4_std / max(1.0, abs(hit4_mean)) > 0.75:
        add(
            "dependencia_seed",
            "media",
            "Quadras variam muito entre seeds; resultado pode ser instavel.",
        )
    if exposure > exposure_threshold:
        add(
            "concentracao_excessiva",
            "alta",
            f"Max exposicao media acima de {exposure_threshold} ({exposure:.2f}).",
        )
    if overlap > overlap_threshold:
        add(
            "overlap_excessivo",
            "media",
            f"Overlap maximo medio acima de {overlap_threshold} ({overlap:.2f}).",
        )
    if triples > 0:
        add(
            "trincas_repetidas",
            "media",
            f"Ha trincas repetidas em media ({triples:.2f}).",
        )
    if quads > 0:
        add(
            "quadras_repetidas",
            "alta",
            f"Ha quadras repetidas em media ({quads:.2f}).",
        )
    if calibration_js > 0.15:
        add(
            "calibracao_artificial",
            "media",
            f"Distribuicao de score estrutural distante do alvo (JS {calibration_js:.3f}).",
        )
    if roi < 0:
        add(
            "roi_negativo",
            "baixa",
            f"ROI medio negativo no modelo de premios configurado ({roi:.3f}).",
        )

    return alerts


def agregar_registros(records: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in records:
        key = (str(record["estrategia"]), str(record["motor"]))
        groups.setdefault(key, []).append(record)

    metricas_agregadas: dict[str, dict[str, Any]] = {}
    todos_alertas: list[dict[str, Any]] = []

    numeric_keys = sorted(
        {
            key
            for record in records
            for key, value in record.items()
            if isinstance(value, (int, float)) and key != "seed"
        }
    )

    for (estrategia, motor), recs in sorted(groups.items()):
        metrics = {
            key: _metric_stats([float(rec.get(key, 0.0)) for rec in recs])
            for key in numeric_keys
        }
        score = _score_composto(metrics, recs)
        alerts = _gerar_alertas_agregado(estrategia, motor, metrics, recs)
        todos_alertas.extend(alerts)

        metricas_agregadas.setdefault(estrategia, {})[motor] = {
            "score_composto": score,
            "n_runs": len(recs),
            "seeds": sorted(int(rec["seed"]) for rec in recs),
            "metricas": metrics,
            "runs": [
                {
                    "seed": int(rec["seed"]),
                    "metricas_brutas": {
                        key: rec[key]
                        for key in numeric_keys
                        if key in rec
                    },
                }
                for rec in sorted(recs, key=lambda item: int(item["seed"]))
            ],
            "alertas": alerts,
        }

    ranking_por_motor: dict[str, list[dict[str, Any]]] = {}
    ranking_geral: list[dict[str, Any]] = []
    for estrategia, by_motor in metricas_agregadas.items():
        for motor, aggregate in by_motor.items():
            entry = _ranking_entry(estrategia, motor, aggregate)
            ranking_por_motor.setdefault(motor, []).append(entry)
            ranking_geral.append(entry)

    for motor in ranking_por_motor:
        ranking_por_motor[motor] = sorted(
            ranking_por_motor[motor],
            key=lambda item: (
                -item["score_composto"],
                item["estrategia"],
            ),
        )
        for pos, item in enumerate(ranking_por_motor[motor], start=1):
            item["rank"] = pos

    ranking_geral = sorted(
        ranking_geral,
        key=lambda item: (
            -item["score_composto"],
            item["motor"],
            item["estrategia"],
        ),
    )
    for pos, item in enumerate(ranking_geral, start=1):
        item["rank"] = pos

    return {
        "metricas_agregadas": metricas_agregadas,
        "ranking_por_motor": ranking_por_motor,
        "ranking_geral": ranking_geral,
        "alertas": todos_alertas,
        "recomendacao_experimental": _recomendacao(ranking_por_motor, ranking_geral),
    }


def _ranking_entry(
    estrategia: str, motor: str, aggregate: dict[str, Any]
) -> dict[str, Any]:
    metrics = aggregate.get("metricas", {})
    return {
        "rank": 0,
        "estrategia": estrategia,
        "motor": motor,
        "score_composto": aggregate.get("score_composto", 0.0),
        "n_runs": aggregate.get("n_runs", 0),
        "seeds": aggregate.get("seeds", []),
        "quadras_media": _safe_mean(metrics, "hit_4"),
        "quinas_media": _safe_mean(metrics, "hit_5"),
        "senas_media": _safe_mean(metrics, "hit_6"),
        "delta_acertos_media": _safe_mean(metrics, "delta_medio_acertos_vs_mc"),
        "ic95_delta_acertos_low_media": _safe_mean(
            metrics,
            "ic95_delta_acertos_low",
        ),
        "win_rate_acertos_media": _safe_mean(
            metrics,
            "win_rate_media_acertos_vs_mc",
        ),
        "max_acertos_media": _safe_mean(metrics, "max_acertos_observado"),
        "max_exposicao_media": _safe_mean(metrics, "max_exposicao"),
        "overlap_max_media": _safe_mean(metrics, "overlap_max"),
        "trincas_repetidas_media": _safe_mean(metrics, "trincas_repetidas"),
        "quadras_repetidas_media": _safe_mean(metrics, "quadras_repetidas"),
        "calibracao_js_vs_alvo_media": _safe_mean(
            metrics,
            "calibracao_js_vs_alvo",
        ),
        "roi_media": _safe_mean(metrics, "roi"),
        "fator_retorno_media": _safe_mean(metrics, "fator_retorno"),
        "lucro_liquido_media": _safe_mean(metrics, "lucro_liquido"),
        "delta_receita_media": _safe_mean(metrics, "delta_medio_receita_vs_mc"),
        "win_rate_receita_media": _safe_mean(metrics, "win_rate_receita_vs_mc"),
        "alertas_count": len(aggregate.get("alertas", [])),
    }


def _recomendacao(
    ranking_por_motor: dict[str, list[dict[str, Any]]],
    ranking_geral: list[dict[str, Any]],
) -> dict[str, Any]:
    por_motor = {
        motor: entries[0] if entries else None
        for motor, entries in sorted(ranking_por_motor.items())
    }
    return {
        "geral": ranking_geral[0] if ranking_geral else None,
        "por_motor": por_motor,
        "nota": (
            "Ranking experimental. Use as metricas brutas e alertas antes de "
            "promover qualquer estrategia."
        ),
    }


def montar_relatorio_matriz(
    *,
    meta_execucao: dict[str, Any],
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for run in runs:
        records.extend(normalizar_run(run))

    agregados = agregar_registros(records)
    return {
        "meta_execucao": meta_execucao,
        "runs": runs,
        **agregados,
    }


def executar_matriz(
    *,
    df_completo: Any,
    config: Any,
    estrategias: list[str],
    seeds: list[int],
    n_janelas: int,
    jogos_por_janela: int,
    n_simulacoes_monte_carlo: int,
    tamanho_teste: int,
    step: int,
    n_bootstrap: int,
    payload_overrides: dict[str, Any],
    prize_table: dict[int, float] | None = None,
) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for estrategia in estrategias:
        for seed in seeds:
            runs.append(
                executar_backtest_individual(
                    df_completo=df_completo,
                    config=config,
                    estrategia=estrategia,
                    seed=int(seed),
                    n_janelas=n_janelas,
                    jogos_por_janela=jogos_por_janela,
                    n_simulacoes_monte_carlo=n_simulacoes_monte_carlo,
                    tamanho_teste=tamanho_teste,
                    step=step,
                    n_bootstrap=n_bootstrap,
                    payload_overrides=payload_overrides,
                    prize_table=prize_table,
                )
            )
    return runs


def executar_backtest_individual(
    *,
    df_completo: Any,
    config: Any,
    estrategia: str,
    seed: int,
    n_janelas: int,
    jogos_por_janela: int,
    n_simulacoes_monte_carlo: int,
    tamanho_teste: int,
    step: int,
    n_bootstrap: int,
    payload_overrides: dict[str, Any],
    prize_table: dict[int, float] | None = None,
) -> dict[str, Any]:
    """Execute one strategy/seed backtest and wrap it as a matrix run."""
    started = perf_counter()
    run: dict[str, Any] = {
        "estrategia": estrategia,
        "seed": int(seed),
        "inicio": datetime.now().isoformat(),
        "status": "ok",
    }
    try:
        resultado = executar_backtest_temporal(
            df_completo=df_completo,
            config=config,
            n_janelas=n_janelas,
            jogos_por_janela=jogos_por_janela,
            n_simulacoes_monte_carlo=n_simulacoes_monte_carlo,
            tamanho_teste=tamanho_teste,
            step=step,
            seed=int(seed),
            n_bootstrap=n_bootstrap,
            estrategia=estrategia,
            payload_overrides=payload_overrides,
            prize_table=prize_table,
        )
        if isinstance(resultado, dict) and "erro" in resultado:
            run["status"] = "erro"
            run["erro"] = resultado["erro"]
        run["resultado"] = resultado
    except Exception as exc:  # pragma: no cover - defensive CLI guard
        run["status"] = "erro"
        run["erro"] = str(exc)
    finally:
        run["fim"] = datetime.now().isoformat()
        run["duracao_segundos"] = round(perf_counter() - started, 4)
    return run


def render_markdown_report(report: dict[str, Any]) -> str:
    meta = report.get("meta_execucao", {})
    lines = [
        "# Bancada Cientifica de Estrategias",
        "",
        f"- Jogo: `{meta.get('jogo', '-')}`",
        f"- Estrategias: `{', '.join(meta.get('estrategias', []))}`",
        f"- Seeds: `{', '.join(str(s) for s in meta.get('seeds', []))}`",
        f"- Janelas: `{meta.get('janelas', '-')}`",
        f"- Jogos por janela: `{meta.get('jogos_por_janela', '-')}`",
        f"- Monte Carlo por janela: `{meta.get('mc_por_janela', '-')}`",
        "",
        "## Ranking Geral",
        "",
        _markdown_ranking_table(report.get("ranking_geral", [])),
        "",
    ]

    for motor, entries in sorted(report.get("ranking_por_motor", {}).items()):
        lines.extend(
            [
                f"## Ranking {motor}",
                "",
                _markdown_ranking_table(entries),
                "",
            ]
        )

    alerts = report.get("alertas", [])
    lines.extend(["## Alertas", ""])
    if alerts:
        lines.append("| Estrategia | Motor | Severidade | Tipo | Mensagem |")
        lines.append("|---|---|---|---|---|")
        for alert in alerts:
            lines.append(
                "| {estrategia} | {motor} | {severidade} | {tipo} | {mensagem} |".format(
                    **{
                        key: str(alert.get(key, "")).replace("|", "\\|")
                        for key in (
                            "estrategia",
                            "motor",
                            "severidade",
                            "tipo",
                            "mensagem",
                        )
                    }
                )
            )
    else:
        lines.append("Nenhum alerta gerado.")

    rec = report.get("recomendacao_experimental", {})
    lines.extend(["", "## Recomendacao Experimental", ""])
    geral = rec.get("geral")
    if geral:
        lines.append(
            "Geral: `{estrategia}` com motor `{motor}` "
            "(score `{score_composto}`).".format(**geral)
        )
    for motor, entry in sorted((rec.get("por_motor") or {}).items()):
        if entry:
            lines.append(
                f"- {motor}: `{entry['estrategia']}` "
                f"(score `{entry['score_composto']}`)"
            )
    lines.append("")
    lines.append(
        "> O score composto e diagnostico; ele nao deve alimentar o gerador."
    )
    return "\n".join(lines)


def _markdown_ranking_table(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return "Sem dados."

    lines = [
        "| Rank | Estrategia | Motor | Score | Quadras | Delta acertos | ROI | Retorno | Delta receita | Max exp | Alertas |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in entries:
        lines.append(
            "| {rank} | {estrategia} | {motor} | {score_composto:.3f} | "
            "{quadras_media:.3f} | {delta_acertos_media:.6f} | "
            "{roi_media:.6f} | {fator_retorno_media:.6f} | "
            "{delta_receita_media:.3f} | {max_exposicao_media:.3f} | "
            "{alertas_count} |".format(**item)
        )
    return "\n".join(lines)
