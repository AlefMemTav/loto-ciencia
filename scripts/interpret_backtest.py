#!/usr/bin/env python3
"""
Interpretador Automático de Backtest.
Lê o JSON gerado e emite um veredito técnico sem necessidade de IA externa.
"""

import json
import sys
import argparse
from pathlib import Path


def carregar_json(caminho):
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Erro ao abrir arquivo: {e}")
        sys.exit(1)


def formatar_numero(n):
    if isinstance(n, (int, float)):
        return f"{n:.4f}"
    return str(n)


def analisar_modelo(nome, stats, hits_reais, hits_esperados):
    print(f"\n🔍 ANÁLISE DO MODELO: {nome.upper()}")

    # 1. Análise do Delta (Lucro sobre o Acaso)
    delta = stats["delta_medio_vs_acaso"]
    ic_min, ic_max = stats["ic95_delta_medio"]

    print(f"   📊 Delta Médio: {delta:.2f}")
    print(f"   📏 Intervalo Confiança (95%): [{ic_min:.2f}, {ic_max:.2f}]")

    # Veredito sobre Delta
    if ic_min > 0:
        veredito_delta = "✅ SUCESSO ESTATÍSTICO (Vantagem Real Confirmada)"
        cor_delta = "\033[92m"  # Verde
    elif ic_max < 0:
        veredito_delta = "❌ PIOR QUE O ACASO (Estratégia Prejudicial)"
        cor_delta = "\033[91m"  # Vermelho
    else:
        veredito_delta = "⚠️ INCONCLUSIVO (Empate Técnico com o Acaso)"
        cor_delta = "\033[93m"  # Amarelo

    print(f"   ⚖️  Veredito Estatístico: {cor_delta}{veredito_delta}\033[0m")

    # 2. Análise de Win Rate
    win_rate = stats["win_rate_vs_media_mc"] * 100
    print(f"   🏆 Win Rate (vs Monte Carlo): {win_rate:.1f}%")

    # 3. Análise de Hits (Prêmios)
    print("   🎯 Comparativo de Prêmios (Real vs Esperado):")

    # Filtra chaves relevantes e ordena
    chaves = sorted(
        [
            k
            for k in hits_reais.keys()
            if hits_reais[k] > 0 or hits_esperados.get(k, 0) > 0
        ],
        key=lambda x: int(x) if x.isdigit() else 0,
    )

    for k in chaves:
        real = hits_reais.get(k, 0)
        esp = hits_esperados.get(k, 0)
        diff = real - esp

        # Formatação visual
        if real > esp:
            sinal = "🟢 ACIMA"
        elif real < esp:
            sinal = "🔴 ABAIXO"
        else:
            sinal = "⚪ IGUAL"

        print(
            f"      - {k} Acertos: Real={real} | Esperado={esp:.2f} -> {sinal} ({diff:+.2f})"
        )

    return ic_min > 0  # Retorna True se passou no teste rigoroso


def main():
    parser = argparse.ArgumentParser(description="Auditor Automático de Resultados")
    parser.add_argument("arquivo", help="Caminho do arquivo JSON de backtest")
    args = parser.parse_args()

    dados = carregar_json(args.arquivo)

    meta = dados["meta_execucao"]
    resultado = dados["resultado"]
    meta_res = resultado["meta"]
    stats = resultado["analise_estatistica"]
    hits = resultado["hits_absolutos_reais"]
    exp = resultado["hits_esperados_mc_media"]

    print("=" * 60)
    print(f"📑 RELATÓRIO AUTOMÁTICO DE AUDITORIA")
    print(f"📅 Data: {meta['data_execucao']}")
    print(f"🎰 Jogo: {meta['jogo']}")
    print(f"⏱️ Janelas Testadas: {meta_res['n_janelas_validas']}")
    print("=" * 60)

    # Analisa Genético
    passou_gen = analisar_modelo("Genético", stats["Genetico"], hits["Genetico"], exp)

    print("-" * 60)

    # Analisa Vetorial
    passou_vet = analisar_modelo("Vetorial", stats["Vetorial"], hits["Vetorial"], exp)

    print("\n" + "=" * 60)
    print("📢 CONCLUSÃO FINAL DO SISTEMA")

    melhor_modelo = None
    if (
        stats["Vetorial"]["delta_medio_vs_acaso"]
        > stats["Genetico"]["delta_medio_vs_acaso"]
    ):
        melhor_modelo = "Vetorial ⚡"
    else:
        melhor_modelo = "Genético 🧬"

    print(f"🥇 Melhor Desempenho Técnico: {melhor_modelo}")

    if passou_gen or passou_vet:
        print("\n🚀 RECOMENDAÇÃO: \033[92mESTRATÉGIA APROVADA PARA USO\033[0m")
        if passou_gen and passou_vet:
            print("   Ambos os modelos superaram o acaso com confiança de 95%.")
        elif passou_gen:
            print("   Apenas o Genético superou o acaso consistentemente.")
        else:
            print("   Apenas o Vetorial superou o acaso consistentemente.")
    else:
        print("\n🛑 RECOMENDAÇÃO: \033[91mREVISAR ESTRATÉGIA (Alto Risco)\033[0m")
        print(
            "   Nenhum modelo bateu o mercado de forma estatisticamente significante."
        )
        print("   O resultado pode ser fruto de sorte ou variância.")

    print("=" * 60)


if __name__ == "__main__":
    main()
