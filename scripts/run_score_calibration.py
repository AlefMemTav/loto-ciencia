#!/usr/bin/env python3
"""Audit structural-score calibration for history, null model and generators."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.strategies import APELIDOS, ESTRATEGIAS
from app.core.lottery import GAMES
from app.core.statistics.score_calibration import (
    BUCKET_LABELS,
    get_score_calibration_model,
    score_calibration_diagnostics,
)
from app.core.statistics.strategy_matrix import DEFAULT_SEEDS, DEFAULT_STRATEGIES
from app.services.lottery_service import LotteryService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Auditoria de calibracao do score estrutural."
    )
    parser.add_argument(
        "--jogo",
        default="mega_sena_sorteio",
        choices=list(GAMES.keys()),
        help="Jogo a auditar.",
    )
    parser.add_argument(
        "--estrategias",
        nargs="+",
        default=DEFAULT_STRATEGIES,
        choices=[*ESTRATEGIAS, *APELIDOS],
    )
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--jogos", type=int, default=20)
    parser.add_argument("--null-model-samples", type=int, default=50000)
    parser.add_argument("--calibration-target", default="historico_nulo")
    parser.add_argument("--calibration-strength", type=float, default=1.0)
    parser.add_argument("--sem-calibracao-score", action="store_true")
    parser.add_argument("--historical-strength", type=float, default=1.0)
    parser.add_argument("--output-dir", default="backtest_results")
    return parser


def _average_distributions(items: list[dict]) -> dict[str, float]:
    if not items:
        return {label: 0.0 for label in BUCKET_LABELS}
    return {
        label: round(float(mean(float(item.get(label, 0.0)) for item in items)), 6)
        for label in BUCKET_LABELS
    }


def _aggregate_runs(runs: list[dict]) -> dict:
    by_strategy: dict[str, list[dict]] = {}
    for run in runs:
        by_strategy.setdefault(run["estrategia"], []).append(run)

    aggregated = {}
    for strategy, strategy_runs in sorted(by_strategy.items()):
        diagnostics = [run["diagnostico"] for run in strategy_runs]
        aggregated[strategy] = {
            "n_runs": len(strategy_runs),
            "seeds": [int(run["seed"]) for run in strategy_runs],
            "score_medio": round(
                float(mean(diag.get("score_medio", 0.0) for diag in diagnostics)),
                6,
            ),
            "js_vs_alvo_media": round(
                float(mean(diag.get("js_vs_alvo", 0.0) for diag in diagnostics)),
                6,
            ),
            "js_vs_historico_media": round(
                float(mean(diag.get("js_vs_historico", 0.0) for diag in diagnostics)),
                6,
            ),
            "js_vs_nulo_media": round(
                float(mean(diag.get("js_vs_nulo", 0.0) for diag in diagnostics)),
                6,
            ),
            "chi_square_vs_alvo_media": round(
                float(mean(diag.get("chi_square_vs_alvo", 0.0) for diag in diagnostics)),
                6,
            ),
            "distribuicao_gerada_media": _average_distributions(
                [diag.get("distribuicao_gerada", {}) for diag in diagnostics]
            ),
        }

    ranking = sorted(
        (
            {
                "rank": 0,
                "estrategia": strategy,
                "js_vs_alvo_media": data["js_vs_alvo_media"],
                "score_medio": data["score_medio"],
                "chi_square_vs_alvo_media": data["chi_square_vs_alvo_media"],
            }
            for strategy, data in aggregated.items()
        ),
        key=lambda item: (item["js_vs_alvo_media"], item["chi_square_vs_alvo_media"]),
    )
    for idx, item in enumerate(ranking, start=1):
        item["rank"] = idx

    return {
        "por_estrategia": aggregated,
        "ranking_calibracao": ranking,
    }


def _render_markdown(report: dict) -> str:
    meta = report.get("meta_execucao", {})
    model = report.get("modelo_calibracao", {})
    lines = [
        "# Auditoria de Calibracao do Score Estrutural",
        "",
        f"- Jogo: `{meta.get('jogo', '-')}`",
        f"- Estrategias: `{', '.join(meta.get('estrategias', []))}`",
        f"- Seeds: `{', '.join(str(s) for s in meta.get('seeds', []))}`",
        f"- Jogos por run: `{meta.get('jogos', '-')}`",
        f"- Amostras nulas: `{meta.get('null_model_samples', '-')}`",
        "",
        "## Distribuicoes de Referencia",
        "",
        "| Bucket | Historico | Nulo | Alvo |",
        "|---|---:|---:|---:|",
    ]
    for label in BUCKET_LABELS:
        lines.append(
            "| {label} | {hist:.2f}% | {null:.2f}% | {target:.2f}% |".format(
                label=label,
                hist=float(model.get("historico", {}).get(label, 0.0)),
                null=float(model.get("nulo", {}).get(label, 0.0)),
                target=float(model.get("alvo", {}).get(label, 0.0)),
            )
        )

    lines.extend(
        [
            "",
            "## Ranking por Aderencia ao Alvo",
            "",
            "| Rank | Estrategia | JS vs alvo | Chi-square | Score medio |",
            "|---:|---|---:|---:|---:|",
        ]
    )
    for item in report.get("ranking_calibracao", []):
        lines.append(
            "| {rank} | {estrategia} | {js:.6f} | {chi:.6f} | {score:.2f} |".format(
                rank=item["rank"],
                estrategia=item["estrategia"],
                js=item["js_vs_alvo_media"],
                chi=item["chi_square_vs_alvo_media"],
                score=item["score_medio"],
            )
        )

    lines.extend(
        [
            "",
            "## Nota",
            "",
            "Esta auditoria mede calibracao de perfil, nao retorno financeiro nem chance garantida.",
            "Use junto com walk-forward, Monte Carlo e ROI real.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = _parser()
    args = parser.parse_args()
    if args.calibration_target not in {"historico_nulo", "historico", "nulo"}:
        parser.error("--calibration-target deve ser historico_nulo, historico ou nulo.")

    service = LotteryService()
    ctx = service.get_context(args.jogo)
    inicio = datetime.now()

    model = get_score_calibration_model(
        ctx.config,
        df_historico=ctx.df,
        n_samples=args.null_model_samples,
        target=args.calibration_target,
    )

    runs = []
    for estrategia in args.estrategias:
        for seed in args.seeds:
            payload = {
                "quantidade": args.jogos,
                "estrategia": estrategia,
                "seed": int(seed),
                "null_model_samples": args.null_model_samples,
                "historical_signal_strength": args.historical_strength,
                "usar_calibracao_score": not args.sem_calibracao_score,
                "calibration_strength": args.calibration_strength,
                "calibration_target": args.calibration_target,
            }
            games = service.generate(args.jogo, payload, ctx=ctx)
            diag = score_calibration_diagnostics(
                games,
                ctx.config,
                df_historico=ctx.df,
                n_samples=args.null_model_samples,
                target=args.calibration_target,
            )
            runs.append(
                {
                    "estrategia": estrategia,
                    "seed": int(seed),
                    "jogos": games,
                    "diagnostico": diag,
                }
            )

    fim = datetime.now()
    aggregates = _aggregate_runs(runs)
    report = {
        "meta_execucao": {
            "data_execucao": fim.strftime("%Y-%m-%d"),
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "duracao": str(fim - inicio),
            "jogo": args.jogo,
            "estrategias": list(args.estrategias),
            "seeds": [int(seed) for seed in args.seeds],
            "jogos": int(args.jogos),
            "null_model_samples": int(args.null_model_samples),
            "calibration_target": args.calibration_target,
            "calibration_strength": float(args.calibration_strength),
            "usar_calibracao_score": not args.sem_calibracao_score,
        },
        "modelo_calibracao": {
            "version": model.version,
            "n_historico": model.n_history,
            "n_nulo": model.n_null,
            "historico": model.history_distribution,
            "nulo": model.null_distribution,
            "alvo": model.target_distribution,
        },
        "runs": runs,
        **aggregates,
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = fim.strftime("%Y-%m-%d_%H%M%S")
    json_path = output_dir / f"score_calibration_{args.jogo}_{timestamp}.json"
    md_path = output_dir / f"score_calibration_{args.jogo}_{timestamp}.md"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    md_path.write_text(_render_markdown(report), encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    print("Ranking por aderencia ao alvo:")
    for item in report["ranking_calibracao"]:
        print(
            f"{item['rank']:02d}. {item['estrategia']} "
            f"JS={item['js_vs_alvo_media']:.6f} "
            f"chi={item['chi_square_vs_alvo_media']:.6f}"
        )


if __name__ == "__main__":
    main()
