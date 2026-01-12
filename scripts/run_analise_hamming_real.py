#!/usr/bin/env python3
# scripts/analise_hamming_real.py
"""
Análise de Hamming REAL do histórico de loterias.
Descobre qual é a unicidade NATURAL dos sorteios reais.
Funciona para QUALQUER jogo (Mega-Sena, Quina, Lotofácil, etc).
Uso: python scripts/analise_hamming_real.py [--jogo mega_sena_sorteio]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.lottery import GAMES
import pandas as pd
import numpy as np
import random
import json
from datetime import datetime
import argparse
from app.services.lottery_service import LotteryService


def hamming_distance(jogo1, jogo2):
    """Calcula distância de Hamming entre dois jogos."""
    set1 = set(jogo1)
    set2 = set(jogo2)
    return len(set1.symmetric_difference(set2))


def main():
    parser = argparse.ArgumentParser(description="Análise de Hamming REAL do Sistema")
    parser.add_argument(
        "--jogo",
        default="mega_sena_sorteio",
        choices=list(GAMES.keys()),
        help="Jogo para testar",
    )

    args = parser.parse_args()
    service = LotteryService()
    ctx = service.get_context(args.jogo)
    df = ctx.df
    config = ctx.config

    data_str = datetime.now().strftime("%Y%m%d")

    print("=" * 100)
    print(f"🔬 ANÁLISE DE HAMMING - HISTÓRICO REAL")
    print(f"   Jogo: {config.name}")
    print(f"   Universo: {config.n_numbers} números")
    print(f"   Aposta: {config.bet_size} números")
    print("=" * 100 + "\n")

    bet_size = config.bet_size  # Quantos números sorteia
    n_numbers = config.n_numbers  # Universo de números

    # Extrai todos os jogos históricos
    jogos = []
    for _, row in df.iterrows():
        jogo = []
        for i in range(1, bet_size + 1):  # ← Usa bet_size!
            col_name = f"D{i}"
            if col_name in row and pd.notna(row[col_name]):
                jogo.append(int(row[col_name]))
        if len(jogo) == bet_size:
            jogos.append(sorted(jogo))

    print(f"📊 Total de sorteios analisados: {len(jogos)}\n")

    if len(jogos) == 0:
        print(
            "❌ ERRO: Nenhum sorteio histórico foi carregado. Verifique o arquivo de dados e o mapeamento de colunas."
        )
        print("⚠️ Encerrando análise. Nenhuma estatística será gerada.")
        return

    if len(jogos) < 100:
        print(
            "⚠️ AVISO: Histórico muito pequeno (<100 sorteios). Resultados podem ser imprecisos."
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ANÁLISE 1: Hamming entre sorteios CONSECUTIVOS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("📈 ANÁLISE 1: Hamming entre Sorteios Consecutivos")
    print("-" * 100)

    hamming_consecutivos = []
    for i in range(len(jogos) - 1):
        h = hamming_distance(jogos[i], jogos[i + 1])
        hamming_consecutivos.append(h)

    df_consec = pd.DataFrame({"hamming": hamming_consecutivos})

    print(f"\n  Média: {df_consec['hamming'].mean():.2f}")
    print(f"  Mediana: {df_consec['hamming'].median():.1f}")
    print(f"  Desvio padrão: {df_consec['hamming'].std():.2f}")
    print(f"  Mínimo: {df_consec['hamming'].min():.0f}")
    print(f"  Máximo: {df_consec['hamming'].max():.0f}")

    print(f"\n  Distribuição:")
    print(f"    25% dos casos: Hamming ≤ {df_consec['hamming'].quantile(0.25):.0f}")
    print(f"    50% dos casos: Hamming ≤ {df_consec['hamming'].quantile(0.50):.0f}")
    print(f"    75% dos casos: Hamming ≤ {df_consec['hamming'].quantile(0.75):.0f}")
    print(f"    90% dos casos: Hamming ≤ {df_consec['hamming'].quantile(0.90):.0f}")
    print(f"    95% dos casos: Hamming ≤ {df_consec['hamming'].quantile(0.95):.0f}")

    stats_consec = {
        "media": float(df_consec["hamming"].mean()),
        "mediana": float(df_consec["hamming"].median()),
        "std": float(df_consec["hamming"].std()),
        "min": int(df_consec["hamming"].min()),
        "max": int(df_consec["hamming"].max()),
        "q25": float(df_consec["hamming"].quantile(0.25)),
        "q50": float(df_consec["hamming"].quantile(0.50)),
        "q75": float(df_consec["hamming"].quantile(0.75)),
        "q90": float(df_consec["hamming"].quantile(0.90)),
        "q95": float(df_consec["hamming"].quantile(0.95)),
    }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ANÁLISE 2: Hamming MÍNIMO de cada sorteio vs TODOS anteriores
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n\n📈 ANÁLISE 2: Hamming MÍNIMO vs Histórico (como no backtest)")
    print("-" * 100)

    min_historico = min(50, len(jogos) // 2)  # Adaptativo
    hamming_minimos = []

    for i in range(min_historico, len(jogos)):
        jogo_atual = jogos[i]
        historico = jogos[:i]
        min_hamming = min(hamming_distance(jogo_atual, j_hist) for j_hist in historico)
        hamming_minimos.append(min_hamming)

    df_minimos = pd.DataFrame({"hamming_min": hamming_minimos})

    print(f"\n  Média: {df_minimos['hamming_min'].mean():.2f}")
    print(f"  Mediana: {df_minimos['hamming_min'].median():.1f}")
    print(f"  Desvio padrão: {df_minimos['hamming_min'].std():.2f}")
    print(f"  Mínimo: {df_minimos['hamming_min'].min():.0f}")
    print(f"  Máximo: {df_minimos['hamming_min'].max():.0f}")

    print(f"\n  Distribuição:")
    print(
        f"    25% dos casos: Hamming ≤ {df_minimos['hamming_min'].quantile(0.25):.0f}"
    )
    print(
        f"    50% dos casos: Hamming ≤ {df_minimos['hamming_min'].quantile(0.50):.0f}"
    )
    print(
        f"    75% dos casos: Hamming ≤ {df_minimos['hamming_min'].quantile(0.75):.0f}"
    )
    print(
        f"    90% dos casos: Hamming ≤ {df_minimos['hamming_min'].quantile(0.90):.0f}"
    )
    print(
        f"    95% dos casos: Hamming ≤ {df_minimos['hamming_min'].quantile(0.95):.0f}"
    )

    # Casos extremos (dinâmico por jogo)
    print(f"\n  🔍 Casos Raros:")
    for hamming_val in [2, 3, 4, 5]:
        if hamming_val < bet_size:
            count = (df_minimos["hamming_min"] == hamming_val).sum()
            pct = (df_minimos["hamming_min"] == hamming_val).mean() * 100
            n_iguais = bet_size - (hamming_val // 2)
            print(
                f"    Hamming = {hamming_val} (~{n_iguais} números iguais): {count} vezes ({pct:.2f}%)"
            )

    stats_minimos = {
        "media": float(df_minimos["hamming_min"].mean()),
        "mediana": float(df_minimos["hamming_min"].median()),
        "std": float(df_minimos["hamming_min"].std()),
        "min": int(df_minimos["hamming_min"].min()),
        "max": int(df_minimos["hamming_min"].max()),
        "q25": float(df_minimos["hamming_min"].quantile(0.25)),
        "q50": float(df_minimos["hamming_min"].quantile(0.50)),
        "q75": float(df_minimos["hamming_min"].quantile(0.75)),
        "q90": float(df_minimos["hamming_min"].quantile(0.90)),
        "q95": float(df_minimos["hamming_min"].quantile(0.95)),
    }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ANÁLISE 3: Comparação com Aleatório
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n\n📈 ANÁLISE 3: Comparação Real vs Aleatório")
    print("-" * 100)

    random.seed(42)

    jogos_aleatorios = []
    for _ in range(500):
        jogo_alea = sorted(
            random.sample(
                range(1, n_numbers + 1),  # ← Universo dinâmico!
                bet_size,  # ← Tamanho dinâmico!
            )
        )
        jogos_aleatorios.append(jogo_alea)

    hamming_aleatorios = []
    for jogo_alea in jogos_aleatorios:
        min_h = min(hamming_distance(jogo_alea, j_hist) for j_hist in jogos)
        hamming_aleatorios.append(min_h)

    df_alea = pd.DataFrame({"hamming_aleatorio": hamming_aleatorios})

    print(f"\n  📊 HISTÓRICO REAL:")
    print(f"     Média: {df_minimos['hamming_min'].mean():.2f}")
    print(f"     Mediana: {df_minimos['hamming_min'].median():.1f}")

    print(f"\n  🎲 JOGOS ALEATÓRIOS:")
    print(f"     Média: {df_alea['hamming_aleatorio'].mean():.2f}")
    print(f"     Mediana: {df_alea['hamming_aleatorio'].median():.1f}")

    diferenca = df_alea["hamming_aleatorio"].mean() - df_minimos["hamming_min"].mean()
    print(f"\n  📈 DIFERENÇA:")
    print(
        f"     Aleatórios são {abs(diferenca):.2f} {'MAIS' if diferenca > 0 else 'MENOS'} únicos que sorteios reais"
    )

    stats_alea = {
        "media": float(df_alea["hamming_aleatorio"].mean()),
        "mediana": float(df_alea["hamming_aleatorio"].median()),
        "std": float(df_alea["hamming_aleatorio"].std()),
        "min": int(df_alea["hamming_aleatorio"].min()),
        "max": int(df_alea["hamming_aleatorio"].max()),
        "q25": float(df_alea["hamming_aleatorio"].quantile(0.25)),
        "q50": float(df_alea["hamming_aleatorio"].quantile(0.50)),
        "q75": float(df_alea["hamming_aleatorio"].quantile(0.75)),
        "q90": float(df_alea["hamming_aleatorio"].quantile(0.90)),
        "q95": float(df_alea["hamming_aleatorio"].quantile(0.95)),
    }

    # Conclusão adaptada
    if diferenca > 0.2:
        print(f"\n  ✅ CONCLUSÃO: Jogos aleatórios JÁ SÃO mais únicos que histórico!")
        print(f"     → Sistema atual está CORRETO")
        print(f"     → NÃO precisa forçar Hamming ainda mais alto")
    elif diferenca < -0.2:
        print(f"\n  ⚠️ CONCLUSÃO: Jogos aleatórios são MENOS únicos que histórico")
        print(f"     → Considere adicionar bônus para Hamming alto")
    else:
        print(f"\n  ➡️ CONCLUSÃO: Aleatórios e histórico são equivalentes")
        print(f"     → Critério atual está adequado")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # RESUMO E RECOMENDAÇÕES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n\n" + "=" * 100)
    print("🎯 RESUMO E RECOMENDAÇÕES")
    print("=" * 100 + "\n")

    hamming_real_medio = df_minimos["hamming_min"].mean()
    hamming_alea_medio = df_alea["hamming_aleatorio"].mean()

    try:
        # Tenta carregar backtest mais recente
        backtest_files = list(
            Path("backtest_results").glob(f"{args.jogo}_*_amostras.json")
        )
        if backtest_files:
            latest = max(backtest_files, key=lambda p: p.stat().st_mtime)
            with open(latest) as f:
                backtest_data = json.load(f)

            # Calcula média dos buckets
            buckets = backtest_data["validacao_scoring"]["buckets"]
            hamming_backtest = np.mean([b["hamming_medio"] for b in buckets.values()])
        else:
            hamming_backtest = None
    except:
        hamming_backtest = None

    print(f"  1. Hamming médio (sorteios reais vs histórico): {hamming_real_medio:.2f}")
    print(
        f"  2. Hamming médio (jogos aleatórios vs histórico): {hamming_alea_medio:.2f}"
    )
    if hamming_backtest:
        print(f"  3. Hamming médio (backtest - buckets): {hamming_backtest:.2f}")
    else:
        print(f"  3. Hamming médio (backtest): N/A (rode backtest primeiro)")

    print(f"\n  📊 Interpretação:")

    if hamming_backtest and hamming_backtest >= hamming_real_medio:
        print(f"     ✅ Sistema gera jogos tão únicos quanto a própria loteria")
        print(
            f"     ✅ Hamming {hamming_backtest:.1f} é ADEQUADO (≥ {hamming_real_medio:.1f})"
        )
        print(f"     ✅ Critério ρ > 0.2 pode ser DESNECESSÁRIO para {config.name}")
        print(f"\n  💡 RECOMENDAÇÃO:")
        print(f"     → ACEITE o resultado do backtest como válido")
        print(f"     → Flexibilize critério para jogos de baixa densidade")
        print(f"     → Foque em ρ(alertas) < -0.5")
    elif hamming_backtest:
        print(f"     ⚠️ Sistema gera jogos MENOS únicos que sorteios reais")
        print(f"     ⚠️ Hamming {hamming_backtest:.1f} < {hamming_real_medio:.1f}")
        print(f"\n  💡 RECOMENDAÇÃO:")
        print(f"     → Adicione bônus para Hamming alto")
        print(f"     → Alvo: Hamming médio ≥ {hamming_real_medio:.1f}")
    else:
        print(f"     ℹ️ Rode o backtest para comparação completa")

    # Salva JSON
    output_dir = Path("backtest_results")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"v1_{data_str}_{args.jogo}_hamming_analysis.json"

    resultado_json = {
        "jogo": config.name,
        "slug": args.jogo,
        "config": {
            "bet_size": bet_size,
            "n_numbers": n_numbers,
            "density": config.density,
        },
        "data": data_str,
        "total_sorteios": len(jogos),
        "consecutivos": stats_consec,
        "minimos": stats_minimos,
        "aleatorios": stats_alea,
        "diferenca_alea_vs_real": float(diferenca),
        "hamming_backtest": float(hamming_backtest) if hamming_backtest else None,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(resultado_json, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Resultados salvos em: {output_file}")
    print("\n" + "=" * 100 + "\n")


if __name__ == "__main__":
    main()
