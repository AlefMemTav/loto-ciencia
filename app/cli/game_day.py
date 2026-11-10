"""Gera e valida o pacote do dia de jogo (uma única fonte de verdade).

Uso:
    python -m app.cli.game_day --game hoje
    python -m app.cli.game_day --game mega_sena --quantidade 10 --effort forte

Roda no GitHub Actions (`.github/workflows/game-day.yml`) e no notebook, com o
mesmo código. Usa o histórico até o último sorteio já gravado em `data/`.

Saída em `out/AAAA-MM-DD/<jogo>/`:
    package.json  pacote, validação por bilhete, checagens e metadados
    report.md     resumo legível

Idempotente: se `package.json` do dia já existir, pula (use --force para refazer).
Código de saída: 0 ok (ou nada a fazer), 1 pacote reprovado nas checagens, 2 uso.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")

JOGOS: dict[str, str] = {
    "mega_sena": "mega_sena_sorteio",
    "quina": "quina_sorteio",
    "loto_facil": "loto_facil_sorteio",
    "loto_mania": "loto_mania_sorteio",
}

# Dias de sorteio (segunda=0 ... domingo=6), todos às 20h (calendário Caixa, mai/2026).
# Feriados podem mudar o calendário: nesses casos use --game <jogo> manualmente.
DIAS_SORTEIO: dict[str, tuple[int, ...]] = {
    "mega_sena": (1, 3, 5),
    "quina": (0, 1, 2, 3, 4, 5),
    "loto_facil": (0, 1, 2, 3, 4, 5),
    "loto_mania": (0, 2, 4),
}

MAX_TENTATIVAS = 5
DIAS_MAX_SEM_ATUALIZAR = 4  # maior intervalo normal entre sorteios é 3 dias


def jogos_do_dia(hoje: date) -> list[str]:
    """Jogos que têm sorteio na data informada."""
    return [j for j, dias in DIAS_SORTEIO.items() if hoje.weekday() in dias]


def checar_pacote(
    jogos: list[list[int]],
    validacoes: list[dict],
    diag: dict,
    *,
    k: int,
    n_numbers: int,
    overlap_limit: int,
    esparso: bool,
    quantidade: int,
) -> tuple[list[str], list[str]]:
    """Devolve (erros, avisos). Erros reprovam o pacote; avisos só aparecem no relatório."""
    erros: list[str] = []
    avisos: list[str] = []

    if len(jogos) != quantidade:
        erros.append(f"Pacote tem {len(jogos)} jogos, esperado {quantidade}.")
    for i, jogo in enumerate(jogos, 1):
        if len(set(jogo)) != k or not all(1 <= n <= n_numbers for n in jogo):
            erros.append(f"Jogo {i} inválido: precisa de {k} dezenas distintas em 1..{n_numbers}.")
    if len({tuple(sorted(j)) for j in jogos}) != len(jogos):
        erros.append("Há jogos repetidos no pacote.")

    for i, val in enumerate(validacoes, 1):
        if val.get("ja_saiu"):
            erros.append(f"Jogo {i} já foi sorteado antes.")
        if val.get("risco_divisao") == "ALTO":
            erros.append(f"Jogo {i} com risco ALTO de dividir o prêmio.")

    # Avisos. Trincas repetidas só fazem sentido em jogos esparsos: na Lotofácil
    # (15 de 25) é impossível não repetir trincas num pacote de 10 jogos.
    if diag.get("overlap_max", 0) > overlap_limit:
        avisos.append(f"Maior sobreposição entre dois jogos: {diag['overlap_max']} (limite {overlap_limit}).")
    if esparso:
        if diag.get("max_repeticao_par", 0) > 3:
            avisos.append(f"Algum par de dezenas aparece {diag['max_repeticao_par']} vezes (limite 3).")
        if diag.get("trincas_repetidas", 0) > 0:
            avisos.append(f"{diag['trincas_repetidas']} trinca(s) repetida(s) no pacote.")
    return erros, avisos


def _validar_pacote(slug: str, jogos: list[list[int]]) -> list[dict]:
    from app.services.lottery_service import LotteryService

    servico = LotteryService()
    saida = []
    for jogo in jogos:
        r = servico.validate(slug, sorted(int(n) for n in jogo))
        saida.append(
            {
                "jogo": sorted(int(n) for n in jogo),
                "score": r.get("score"),
                "risco_divisao": r.get("risco_divisao"),
                "ja_saiu": bool(r.get("ja_saiu")),
            }
        )
    return saida


def _ultimo_concurso(ctx) -> tuple[int | None, str | None]:
    df = ctx.df
    try:
        if "Concurso" in df.columns:
            idx = df["Concurso"].astype(int).idxmax()
            return int(df.loc[idx, "Concurso"]), (str(df.loc[idx, "Data"]) if "Data" in df.columns else None)
        return int(df.index.max()), None
    except Exception:
        return None, None


def _dias_desde(data_txt: str | None, hoje: date) -> int | None:
    if not data_txt:
        return None
    try:
        return (hoje - datetime.strptime(data_txt[:10], "%d/%m/%Y").date()).days
    except ValueError:
        return None


def _git_sha() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        return None


def _render_relatorio(pacote: dict) -> str:
    m = pacote["meta"]
    rel = pacote["relatorio"]
    linhas = [
        f"# Pacote do dia — {m['jogo']} — {m['data']}",
        "",
        f"- Histórico até o concurso **{m['ultimo_concurso']}** ({m['data_ultimo_concurso']})",
        f"- Estratégia: `{rel['estrategia_base']}` · esforço: `{rel['perfil_esforco']}` · seed: `{m['seed']}` · tentativas: {m['tentativas']}",
        f"- Status: **{pacote['status'].upper()}**",
        "",
        "## Jogos",
        "",
        "| # | Dezenas | Nota | Risco de dividir | Razão de ganhadores* |",
        "|---|---------|------|------------------|----------------------|",
    ]
    for i, v in enumerate(pacote["validacao"], 1):
        razao = v.get("razao_ganhadores")
        linhas.append(
            f"| {i} | {' '.join(f'{n:02d}' for n in v['jogo'])} | {v['score']} | {v['risco_divisao']} | "
            f"{'—' if razao is None else f'{razao:.2f}'} |"
        )
    linhas += [
        "",
        "\\* Previsão do modelo de popularidade (1,00 = jogo médio; menor = tende a dividir o prêmio com menos gente). "
        "Só existe para Mega-Sena e Quina.",
        "",
    ]
    if pacote["erros"]:
        linhas += ["## Erros (pacote reprovado)", ""] + [f"- {e}" for e in pacote["erros"]] + [""]
    if pacote["avisos"]:
        linhas += ["## Avisos", ""] + [f"- {a}" for a in pacote["avisos"]] + [""]
    linhas += [
        "## Como ler",
        "",
        "- Todos os jogos têm a mesma chance de acertar. O pacote evita jogos raros e jogos populares; "
        "não aumenta a chance de acerto.",
        f"- O percentil contra Monte Carlo ({rel['percentil_vs_monte_carlo']}) compara o pacote com pacotes "
        "aleatórios na própria métrica que o gerador otimiza; não mede chance de acerto.",
        "",
    ]
    return "\n".join(linhas)


def gerar(jogo: str, hoje: date, quantidade: int, esforco: str, saida: Path, force: bool) -> bool:
    """Gera, valida e grava o pacote de um jogo. Devolve True se aprovado (ou já existente)."""
    destino = saida / hoje.isoformat() / jogo
    arquivo = destino / "package.json"
    if arquivo.exists() and not force:
        print(f"[{jogo}] já existe {arquivo}; nada a fazer (use --force para refazer).")
        return True

    from app.core.real_game_mode import generate_real_game_package
    from app.core.statistics.popularidade_medida import LIMIAR_RAZAO_GANHADORES
    from app.services.lottery_service import LotteryService

    slug = JOGOS[jogo]
    ctx = LotteryService().get_context(slug)
    config = ctx.config
    ultimo, data_ultimo = _ultimo_concurso(ctx)
    seed_base = int(hoje.strftime("%Y%m%d")) * 10 + list(JOGOS).index(jogo)

    pacote_gerado, validacoes, erros, avisos, tentativa = {}, [], [], [], 0
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        pacote_gerado = generate_real_game_package(
            ctx, quantidade=quantidade, perfil_esforco=esforco, seed=seed_base + tentativa - 1
        )
        jogos = pacote_gerado["jogos"]
        validacoes = _validar_pacote(slug, jogos)
        erros, avisos = checar_pacote(
            jogos,
            validacoes,
            pacote_gerado["relatorio"]["diagnostico_portfolio"],
            k=config.k,
            n_numbers=config.n_numbers,
            overlap_limit=config.get_overlap_limit(),
            esparso=bool(config.is_sparse),
            quantidade=quantidade,
        )
        if not erros:
            break
        print(f"[{jogo}] tentativa {tentativa}/{MAX_TENTATIVAS} reprovada: {'; '.join(erros)}")

    modelo = getattr(ctx, "modelo_popularidade", None)
    if modelo is not None and slug in LIMIAR_RAZAO_GANHADORES:
        import numpy as np

        razoes = modelo.razao_ganhadores_batch(np.array(pacote_gerado["jogos"]))
        for v, r in zip(validacoes, razoes):
            v["razao_ganhadores"] = round(float(r), 4)

    atraso = _dias_desde(data_ultimo, hoje)
    if atraso is not None and atraso > DIAS_MAX_SEM_ATUALIZAR:
        avisos.append(
            f"Histórico desatualizado: último sorteio gravado é de {data_ultimo} ({atraso} dias). "
            "Confira o workflow de atualização."
        )

    pacote = {
        "status": "reprovado" if erros else "aprovado",
        "meta": {
            "jogo": jogo,
            "data": hoje.isoformat(),
            "ultimo_concurso": ultimo,
            "data_ultimo_concurso": data_ultimo,
            "seed": seed_base + tentativa - 1,
            "tentativas": tentativa,
            "commit": _git_sha(),
        },
        "jogos": pacote_gerado["jogos"],
        "validacao": validacoes,
        "erros": erros,
        "avisos": avisos,
        "relatorio": pacote_gerado["relatorio"],
    }
    destino.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(json.dumps(pacote, ensure_ascii=False, indent=2, default=int), encoding="utf-8")
    texto = _render_relatorio(pacote)
    (destino / "report.md").write_text(texto, encoding="utf-8")
    if resumo := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(resumo, "a", encoding="utf-8") as f:
            f.write(texto + "\n")
    print(f"[{jogo}] {pacote['status']} -> {destino}")
    return not erros


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Gera e valida o pacote do dia de jogo.")
    p.add_argument("--game", default="hoje", choices=["hoje", *JOGOS], help="jogo, ou 'hoje' para os jogos com sorteio hoje (BRT)")
    p.add_argument("--quantidade", type=int, default=10, help="jogos no pacote (1 a 50)")
    p.add_argument("--effort", default="forte", choices=["rapido", "forte", "maximo"])
    p.add_argument("--out", default="out", help="pasta de saída")
    p.add_argument("--force", action="store_true", help="refaz mesmo que o pacote do dia já exista")
    p.add_argument("--data", help="data AAAA-MM-DD (padrão: hoje em America/Sao_Paulo)")
    args = p.parse_args(argv)

    if not 1 <= args.quantidade <= 50:
        print("--quantidade deve estar entre 1 e 50.", file=sys.stderr)
        return 2
    try:
        hoje = date.fromisoformat(args.data) if args.data else datetime.now(FUSO).date()
    except ValueError:
        print("--data inválida (use AAAA-MM-DD).", file=sys.stderr)
        return 2

    jogos = jogos_do_dia(hoje) if args.game == "hoje" else [args.game]
    if not jogos:
        print(f"Nenhum sorteio em {hoje.isoformat()}; nada a gerar.")
        return 0

    aprovados = [gerar(j, hoje, args.quantidade, args.effort, Path(args.out), args.force) for j in jogos]
    return 0 if all(aprovados) else 1


if __name__ == "__main__":
    sys.exit(main())
