#!/usr/bin/env python3
# scripts/run_backtest.py

"""
Script de Backtest Científico (Walk-Forward + Monte Carlo).

Uso:
  python scripts/run_backtest.py --jogo mega_sena_sorteio --janelas 24 --jogos 20

Teste rápido do novo gerador calibrado:
  python scripts/run_backtest.py --jogo mega_sena_sorteio --janelas 2 --jogos 5 \
    --mc 50 --null-model-samples 5000 --estrategia pura
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


def _build_payload_overrides(args):
    overrides = {
        "percentil_min": args.percentil_min,
        "percentil_max": args.percentil_max,
        "historical_signal_strength": args.historical_strength,
        "usar_quentes": not args.sem_quentes,
        "usar_atrasados": not args.sem_atrasados,
        "usar_markov": not args.sem_markov,
        "usar_ciclo": not args.sem_ciclo,
        "usar_coocorrencia": not args.sem_coocorrencia,
        "frequencia_recente": not args.sem_frequencia_recente,
    }
    if args.null_model_samples is not None:
        overrides["null_model_samples"] = args.null_model_samples
    return overrides


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
        "--estrategia",
        default="balanceada",
        choices=["pura", "balanceada", "conservadora", "agressiva"],
        help="Estratégia do gerador a ser testada",
    )

    parser.add_argument(
        "--tamanho-teste",
        type=int,
        default=10,
        help="Quantidade de sorteios futuros usados como gabarito em cada janela",
    )

    parser.add_argument(
        "--step",
        type=int,
        default=20,
        help="Distância entre cortes temporais do walk-forward",
    )

    parser.add_argument(
        "--bootstrap",
        type=int,
        default=2000,
        help="Reamostragens bootstrap para IC95 do delta médio",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Semente aleatória para reprodutibilidade",
    )

    parser.add_argument(
        "--percentil-min",
        type=float,
        default=5.0,
        help="Percentil mínimo combinatório aceito pelo objetivo do gerador",
    )

    parser.add_argument(
        "--percentil-max",
        type=float,
        default=95.0,
        help="Percentil máximo combinatório aceito pelo objetivo do gerador",
    )

    parser.add_argument(
        "--null-model-samples",
        type=int,
        default=None,
        help="Amostras do modelo nulo combinatório. Use menor para smoke test.",
    )

    parser.add_argument(
        "--historical-strength",
        type=float,
        default=1.0,
        help="Força dos sinais históricos opcionais, limitada internamente pelo gerador",
    )

    parser.add_argument(
        "--sem-quentes",
        action="store_true",
        help="Desliga inclinação por números quentes/frequência recente",
    )
    parser.add_argument(
        "--sem-atrasados",
        action="store_true",
        help="Desliga inclinação por atraso",
    )
    parser.add_argument(
        "--sem-markov",
        action="store_true",
        help="Desliga inclinação por transição Markov no gerador vetorial",
    )
    parser.add_argument(
        "--sem-ciclo",
        action="store_true",
        help="Desliga inclinação por ciclo no gerador vetorial",
    )
    parser.add_argument(
        "--sem-coocorrencia",
        action="store_true",
        help="Desliga inclinação por coocorrência",
    )
    parser.add_argument(
        "--sem-frequencia-recente",
        action="store_true",
        help="Desliga o portão de frequência recente usado junto com quentes",
    )

    parser.add_argument(
        "--output-dir",
        default="backtest_results",
        help="Diretório onde o relatório JSON será salvo",
    )

    args = parser.parse_args()
    payload_overrides = _build_payload_overrides(args)

    print(f"\n🚀 Iniciando Backtest para: {args.jogo}")
    print(f"📅 Janelas Temporais (solicitadas): {args.janelas}")
    print(f"🎲 Jogos por Janela: {args.jogos}")
    print(f"🎯 Monte Carlo por Janela: {args.mc}")
    print(f"🧭 Estratégia: {args.estrategia}")
    print(
        f"📊 Percentis combinatórios: {args.percentil_min:.1f} a {args.percentil_max:.1f}"
    )
    print(
        "🧪 Amostras do modelo nulo: "
        f"{args.null_model_samples if args.null_model_samples is not None else 'padrão'}"
    )
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
        tamanho_teste=args.tamanho_teste,
        step=args.step,
        seed=args.seed,
        n_bootstrap=args.bootstrap,
        estrategia=args.estrategia,
        payload_overrides=payload_overrides,
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
    print(f" Duração: {fim - inicio}")
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
    timestamp = datetime.now().strftime("%H%M%S")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    nome_arquivo = f"backtest_{args.jogo}_{args.estrategia}_{data_hoje}_{timestamp}.json"
    caminho_arquivo = output_dir / nome_arquivo

    relatorio_final = {
        "meta_execucao": {
            "data_execucao": data_hoje,
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "duracao": str(fim - inicio),
            "jogo": args.jogo,
            "configuracao_cli": {
                "janelas": args.janelas,
                "jogos_por_janela": args.jogos,
                "mc_por_janela": args.mc,
                "seed": args.seed,
                "estrategia": args.estrategia,
                "tamanho_teste": args.tamanho_teste,
                "step": args.step,
                "bootstrap": args.bootstrap,
                "output_dir": str(output_dir),
                "opcoes_gerador": payload_overrides,
            },
        },
        "resultado": resultado,
    }

    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        json.dump(relatorio_final, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n💾 Relatório Completo salvo em: {caminho_arquivo}")


if __name__ == "__main__":
    main()
