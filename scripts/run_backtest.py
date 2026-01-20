#!/usr/bin/env python3
# scripts/run_backtest.py

"""
Script de Backtest Científico (Walk-Forward + Monte Carlo).

Uso:
  python scripts/run_backtest.py --jogo mega_sena_sorteio --janelas 24 --jogos 20

Opcional (se você expôs esses parâmetros na função):
  --mc 500
  --seed 42
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Adiciona o diretório raiz ao path para importar 'app'
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.lottery import GAMES
from app.services.lottery_service import LotteryService
from app.core.statistics.backtest import executar_backtest_temporal


def main():
    parser = argparse.ArgumentParser(
        description="Backtest Científico Temporal (Monte Carlo)"
    )

    parser.add_argument(
        "--jogo",
        default="mega_sena_sorteio",
        choices=list(GAMES.keys()),
        help="Slug do jogo para testar (ex: mega_sena_sorteio, loto_facil_sorteio)",
    )

    parser.add_argument(
        "--janelas",
        type=int,
        default=24,
        help="Quantas janelas temporais testar (ex: 24 ~ últimos 2 anos aprox.)",
    )

    parser.add_argument(
        "--jogos",
        type=int,
        default=20,
        help="Quantos jogos gerar por janela para cada algoritmo",
    )

    parser.add_argument(
        "--mc",
        type=int,
        default=500,
        help="Simulações Monte Carlo por janela",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Semente aleatória para reprodutibilidade",
    )

    args = parser.parse_args()

    print(f"\n🚀 Iniciando Backtest para: {args.jogo}")
    print(f"📅 Janelas Temporais (solicitadas): {args.janelas}")
    print(f"🎲 Jogos por Janela: {args.jogos}")
    print(f"🎯 Monte Carlo por Janela: {args.mc}")
    print(f"🔁 Seed: {args.seed}")
    print("-" * 60)

    # Carrega dados
    service = LotteryService()
    try:
        # Tenta carregar do Excel/Cache
        ctx = service.get_context(args.jogo)
    except Exception as e:
        print(f"❌ Erro ao carregar dados: {e}")
        return

    # Executa Backtest
    inicio = datetime.now()
    resultado = executar_backtest_temporal(
        df_completo=ctx.df,
        config=ctx.config,
        n_janelas=args.janelas,
        jogos_por_janela=args.jogos,
        n_simulacoes_monte_carlo=args.mc,
        seed=args.seed,
    )
    fim = datetime.now()

    if "erro" in resultado:
        print(f"❌ Erro no Backtest: {resultado['erro']}")
        return

    meta = resultado.get("meta", {})
    stats = resultado["analise_estatistica"]
    hits = resultado["hits_absolutos_reais"]
    exp = resultado["hits_esperados_mc_media"]

    print("🏆 RESULTADOS (Walk-Forward + Monte Carlo):")
    print(f" Jogo: {meta.get('jogo', args.jogo)}")
    print(f" Janelas válidas: {meta.get('n_janelas_validas', 'N/A')}")
    print("-" * 60)

    print("🧬 Genético:")
    print(f"  Δ médio vs acaso: {stats['Genetico']['delta_medio_vs_acaso']}")
    print(f"  IC95 do Δ médio: {stats['Genetico']['ic95_delta_medio']}")
    print(f"  Mediana p-emp:   {stats['Genetico']['mediana_p_emp']}")
    print(f"  Win-rate vs MC:  {stats['Genetico']['win_rate_vs_media_mc']}")
    print()

    print("⚡ Vetorial:")
    print(f"  Δ médio vs acaso: {stats['Vetorial']['delta_medio_vs_acaso']}")
    print(f"  IC95 do Δ médio: {stats['Vetorial']['ic95_delta_medio']}")
    print(f"  Mediana p-emp:   {stats['Vetorial']['mediana_p_emp']}")
    print(f"  Win-rate vs MC:  {stats['Vetorial']['win_rate_vs_media_mc']}")
    print("-" * 60)

    print("🎯 HITS ABSOLUTOS (No período testado):")

    def formatar_linha(label, dados):
        # Ordena as chaves numericamente (ex: 4, 5, 6 ou 11, 12... 15)
        chaves = sorted(dados.keys(), key=lambda x: int(x) if x.isdigit() else 0)
        itens = [f"{k}={dados[k]}" for k in chaves]
        return f" {label:<10}: " + " | ".join(itens)

    print(formatar_linha("Genetico", hits["Genetico"]))
    print(formatar_linha("Vetorial", hits["Vetorial"]))
    print(formatar_linha("Esperado", exp))

    # Salva relatório JSON
    data_hoje = datetime.now().strftime("%Y-%m-%d")
    # output_dir = Path("relatorios_backtest")
    output_dir = Path("/app/data/relatorios_backtest")
    output_dir.mkdir(exist_ok=True)

    nome_arquivo = f"backtest_{args.jogo}_{data_hoje}.json"
    caminho_arquivo = output_dir / nome_arquivo

    relatorio_final = {
        "meta_execucao": {
            "data_execucao": data_hoje,
            "jogo": args.jogo,
            "configuracao_cli": {
                "janelas": args.janelas,
                "jogos_por_janela": args.jogos,
                "mc_por_janela": args.mc,
                "seed": args.seed,
            },
        },
        "resultado": resultado,
    }

    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        json.dump(relatorio_final, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n💾 Relatório Completo salvo em: {caminho_arquivo}")


if __name__ == "__main__":
    main()
