#!/usr/bin/env python3
# scripts/run_backtest.py
"""
Script para executar backtest do sistema de scoring.
Uso: python scripts/run_backtest.py [--jogo mega_sena_sorteio] [--amostras 1000]
"""
import sys
import json
from pathlib import Path

# Adiciona app ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.lottery import GAMES
from app.services.lottery_service import LotteryService
from app.core.statistics.backtest import (
    backtest_validator,
    comparar_estrategias_gerador,
    validar_regressao_media,
)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Backtest do Sistema")
    parser.add_argument(
        "--jogo",
        default="mega_sena_sorteio",
        choices=list(GAMES.keys()),
        help="Jogo para testar",
    )
    parser.add_argument(
        "--amostras", type=int, default=1000, help="Número de jogos aleatórios"
    )
    parser.add_argument(
        "--completo", action="store_true", help="Roda todos os testes (leva ~5 min)"
    )

    args = parser.parse_args()

    # Carrega contexto
    service = LotteryService()
    ctx = service.get_context(args.jogo)

    from datetime import datetime

    data_str = datetime.now().strftime("%Y%m%d")

    print("\n" + "=" * 100)
    print(f"🔬 BACKTEST - {ctx.config.name}")
    print("=" * 100 + "\n")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TESTE 1: Validação de Scoring
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n📊 TESTE 1: Validação de Scoring")
    print("-" * 100)

    resultado = backtest_validator(ctx.df, ctx.config, n_amostras=args.amostras)

    print(
        f"\n✅ Validação: {'PASSOU ✓' if resultado['validacao_passou'] else 'FALHOU ✗'}"
    )

    print(f"\n📈 Correlações:")

    # Hamming - usa p_value (com underscore)
    rho_hamming = resultado["correlacoes"]["hamming"]["rho"]
    p_hamming = resultado["correlacoes"]["hamming"]["p_value"]  # ← p_value!

    # n_alertas - usa p_value (com underscore)
    rho_alertas = resultado["correlacoes"]["n_alertas"]["rho"]  # ← n_alertas!
    p_alertas = resultado["correlacoes"]["n_alertas"]["p_value"]  # ← p_value!

    print(f"   Hamming:  ρ={rho_hamming:.3f}, p={p_hamming:.4f}")
    print(f"   Alertas:  ρ={rho_alertas:.3f}, p={p_alertas:.4f}")

    print(f"\n📋 Análise por Buckets:")
    for bucket, stats in resultado["buckets"].items():
        print(
            f"   {bucket:10} → Score: {stats['score_medio']:.1f}, "
            f"Hamming: {stats['hamming_medio']:.1f}, "
            f"Alertas: {stats['n_alertas_medio']:.1f}"  # ← n_alertas_medio!
        )

    print(f"\n💡 Interpretação:")
    for msg in resultado["interpretacao"]:
        print(f"   • {msg}")

    if not args.completo:
        print("\n💡 Use --completo para rodar testes 2 e 3 também")

        # Salva resultado parcial
        output_dir = Path("backtest_results")
        output_dir.mkdir(exist_ok=True)
        output_file = (
            output_dir / f"v1_{data_str}_{args.jogo}_{args.amostras}_amostras.json"
        )

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "jogo": args.jogo,
                    "amostras": args.amostras,
                    "validacao_scoring": resultado,
                },
                f,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        print(f"\n💾 Resultados salvos em: {output_file}")
        print("=" * 100 + "\n")
        return

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TESTE 2: Comparação de Estratégias
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n\n📊 TESTE 2: Comparação de Estratégias")
    print("-" * 100)

    resultado_estrategias = comparar_estrategias_gerador(
        ctx.df, ctx.config, n_jogos_por_estrategia=100
    )

    print(f"\n🏆 Melhor: {resultado_estrategias['melhor_estrategia']}")
    print(f"\n📈 Resultados:")
    for estrategia, stats in resultado_estrategias["resultados"].items():
        print(
            f"   {estrategia:15} → Média: {stats['score_medio']:.1f}, "
            f"Min: {stats['score_min']:.0f}, Max: {stats['score_max']:.0f}, "
            f"Excelentes: {stats['pct_excelente']:.1f}%"
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TESTE 3: Validação de Regressão à Média
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n\n📊 TESTE 3: Validação de Regressão à Média")
    print("-" * 100)

    resultado_regressao = validar_regressao_media(
        ctx.df, ctx.config, janelas=[50, 100, 200]
    )

    print(f"\n✅ Conclusão: {resultado_regressao['conclusao']}")
    print(f"\n💡 {resultado_regressao['recomendacao']}")
    print(f"\n📈 Por Janela:")

    # Usa p_value (com underscore)
    for janela, stats in resultado_regressao["resultados"].items():
        corr = stats.get("correlacao", 0)
        pval = stats.get("p_value", 1.0)  # ← p_value!

        sig = "✓" if pval < 0.05 else "✗"
        print(f"   {janela:12} → ρ={corr:.3f}, p={pval:.4f} {sig}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Salva resultados em JSON
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    output_dir = Path("backtest_results")
    output_dir.mkdir(exist_ok=True)

    output_file = (
        output_dir / f"v1_{data_str}_{args.jogo}_{args.amostras}_amostras.json"
    )

    relatorio_completo = {
        "jogo": args.jogo,
        "amostras": args.amostras,
        "validacao_scoring": resultado,
        "comparacao_estrategias": resultado_estrategias,
        "validacao_regressao": resultado_regressao,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(relatorio_completo, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n\n💾 Resultados salvos em: {output_file}")
    print("=" * 100 + "\n")


if __name__ == "__main__":
    main()
