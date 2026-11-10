#!/usr/bin/env python3
"""Run a reproducible strategy x seed backtest matrix."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.strategies import APELIDOS, ESTRATEGIAS
from app.core.lottery import GAMES
from app.core.statistics.strategy_matrix import (
    DEFAULT_SEEDS,
    DEFAULT_STRATEGIES,
    executar_matriz,
    montar_relatorio_matriz,
    render_markdown_report,
)
from app.core.statistics.prize_model import parse_prize_table, resolve_prize_table
from app.services.lottery_service import LotteryService


def _build_payload_overrides(args) -> dict:
    overrides = {
        "percentil_min": args.percentil_min,
        "percentil_max": args.percentil_max,
        "historical_signal_strength": args.historical_strength,
        "usar_quentes": args.com_quentes,
        "usar_atrasados": args.com_atrasados,
        "usar_markov": args.com_markov,
        "usar_ciclo": args.com_ciclo,
        "usar_coocorrencia": not args.sem_coocorrencia,
        "frequencia_recente": not args.sem_frequencia_recente,
        "usar_calibracao_score": not args.sem_calibracao_score,
        "calibration_strength": args.calibration_strength,
        "calibration_target": args.calibration_target,
    }
    if args.null_model_samples is not None:
        overrides["null_model_samples"] = args.null_model_samples
    return overrides


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bancada cientifica estrategia x seed para loterias suportadas."
    )
    parser.add_argument(
        "--jogo",
        default="mega_sena_sorteio",
        choices=list(GAMES.keys()),
        help="Jogo a testar.",
    )
    parser.add_argument(
        "--estrategias",
        nargs="+",
        default=DEFAULT_STRATEGIES,
        choices=[*ESTRATEGIAS, *APELIDOS],
        help="Estrategias a comparar.",
    )
    parser.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=DEFAULT_SEEDS,
        help="Seeds a executar para cada estrategia.",
    )
    parser.add_argument("--janelas", type=int, default=24)
    parser.add_argument("--jogos", type=int, default=20)
    parser.add_argument("--mc", type=int, default=500)
    parser.add_argument("--tamanho-teste", type=int, default=10)
    parser.add_argument("--step", type=int, default=20)
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--percentil-min", type=float, default=5.0)
    parser.add_argument("--percentil-max", type=float, default=95.0)
    parser.add_argument("--null-model-samples", type=int, default=None)
    parser.add_argument("--historical-strength", type=float, default=1.0)
    parser.add_argument("--sem-calibracao-score", action="store_true")
    parser.add_argument("--calibration-strength", type=float, default=1.0)
    parser.add_argument(
        "--calibration-target",
        choices=["historico_nulo", "historico", "nulo"],
        default="historico_nulo",
    )
    parser.add_argument("--com-quentes", action="store_true")
    parser.add_argument("--com-atrasados", action="store_true")
    parser.add_argument("--com-markov", action="store_true")
    parser.add_argument("--com-ciclo", action="store_true")
    parser.add_argument("--sem-coocorrencia", action="store_true")
    parser.add_argument("--sem-frequencia-recente", action="store_true")
    parser.add_argument("--output-dir", default="backtest_results")
    parser.add_argument(
        "--premio",
        action="append",
        default=[],
        help="Sobrescreve/adiciona premio por faixa no ROI: acertos=valor.",
    )
    parser.add_argument(
        "--salvar-runs-individuais",
        action="store_true",
        help="Tambem salva um JSON bruto por estrategia/seed.",
    )
    return parser


def _save_individual_runs(
    runs: list[dict],
    output_dir: Path,
    jogo: str,
    timestamp: str,
) -> None:
    for run in runs:
        estrategia = run.get("estrategia", "estrategia")
        seed = run.get("seed", "seed")
        path = output_dir / f"matrix_run_{jogo}_{estrategia}_seed{seed}_{timestamp}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(run, f, indent=2, ensure_ascii=False, default=str)


def main() -> None:
    parser = _parser()
    args = parser.parse_args()

    payload_overrides = _build_payload_overrides(args)
    prize_overrides = parse_prize_table(args.premio)
    service = LotteryService()
    ctx = service.get_context(args.jogo)

    inicio = datetime.now()
    print("\nIniciando matriz de estrategias")
    print(f"Jogo: {args.jogo}")
    print(f"Estrategias: {', '.join(args.estrategias)}")
    print(f"Seeds: {', '.join(str(s) for s in args.seeds)}")
    print(f"Janelas: {args.janelas} | Jogos: {args.jogos} | MC: {args.mc}")
    print(f"Tabela ROI: {resolve_prize_table(ctx.config, prize_overrides)}")
    print("-" * 60)

    runs = executar_matriz(
        df_completo=ctx.df,
        config=ctx.config,
        estrategias=list(args.estrategias),
        seeds=[int(seed) for seed in args.seeds],
        n_janelas=args.janelas,
        jogos_por_janela=args.jogos,
        n_simulacoes_monte_carlo=args.mc,
        tamanho_teste=args.tamanho_teste,
        step=args.step,
        n_bootstrap=args.bootstrap,
        payload_overrides=payload_overrides,
        prize_table=prize_overrides,
    )
    fim = datetime.now()

    meta_execucao = {
        "data_execucao": fim.strftime("%Y-%m-%d"),
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "duracao": str(fim - inicio),
        "jogo": args.jogo,
        "estrategias": list(args.estrategias),
        "seeds": [int(seed) for seed in args.seeds],
        "janelas": args.janelas,
        "jogos_por_janela": args.jogos,
        "mc_por_janela": args.mc,
        "tamanho_teste": args.tamanho_teste,
        "step": args.step,
        "bootstrap": args.bootstrap,
        "opcoes_gerador": payload_overrides,
        "tabela_premios": {
            str(k): round(float(v), 2)
            for k, v in sorted(resolve_prize_table(ctx.config, prize_overrides).items())
        },
    }
    report = montar_relatorio_matriz(meta_execucao=meta_execucao, runs=runs)
    markdown = render_markdown_report(report)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = fim.strftime("%Y-%m-%d_%H%M%S")
    json_path = output_dir / f"matrix_{args.jogo}_{timestamp}.json"
    md_path = output_dir / f"matrix_{args.jogo}_{timestamp}.md"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    md_path.write_text(markdown, encoding="utf-8")

    if args.salvar_runs_individuais:
        _save_individual_runs(runs, output_dir, args.jogo, timestamp)

    print("\nRanking geral:")
    for entry in report.get("ranking_geral", [])[:10]:
        print(
            "#{rank} {motor:<8} {estrategia:<18} score={score_composto:.3f} "
            "quadras={quadras_media:.2f} delta={delta_acertos_media:.5f} "
            "roi={roi_media:.4f}".format(
                **entry
            )
        )
    print(f"\nJSON consolidado: {json_path}")
    print(f"Markdown resumo:  {md_path}")


if __name__ == "__main__":
    main()
