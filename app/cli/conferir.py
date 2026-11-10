"""Confere os pacotes gravados contra o sorteio do mesmo dia.

Uso:
    python -m app.cli.conferir --registro registro

Para cada `pacotes/<data>/<jogo>/package.json` sem `resultado.json`, procura na
planilha de `data/` o concurso com a mesma data, conta os acertos de cada jogo,
grava `resultado.json` e acrescenta uma linha em `historico.csv`.

Pacote sem sorteio na planilha ainda fica pendente (próxima rodada confere).
Pacote gerado depois do sorteio (último concurso do pacote >= concurso do dia)
é marcado como inválido e não entra na comparação.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

SLUGS = {
    "mega_sena": "mega_sena_sorteio",
    "quina": "quina_sorteio",
    "loto_facil": "loto_facil_sorteio",
    "loto_mania": "loto_mania_sorteio",
}
# Universo de dezenas e acertos que pagam prêmio.
UNIVERSO = {"mega_sena": 60, "quina": 80, "loto_facil": 25, "loto_mania": 100}
FAIXAS = {
    "mega_sena": {4: "quadra", 5: "quina", 6: "sena"},
    "quina": {3: "terno", 4: "quadra", 5: "quina"},
    "loto_facil": {11: "11", 12: "12", 13: "13", 14: "14", 15: "15"},
    "loto_mania": {0: "0", 15: "15", 16: "16", 17: "17", 18: "18", 19: "19", 20: "20"},
}
CAMPOS = [
    "data", "jogo", "concurso", "n_jogos", "melhor", "media_acertos",
    "esperado_aleatorio", "premiados", "faixas",
]


def acertos_esperados(n_universo: int, k_sorteio: int, k_aposta: int) -> float:
    """Média de acertos de um jogo qualquer (hipergeométrica)."""
    return k_aposta * k_sorteio / n_universo


def contar_acertos(jogo: list[int], sorteio: set[int]) -> int:
    return len(set(jogo) & sorteio)


def achar_sorteio(slug: str, dia: date, pasta_dados: Path) -> tuple[int, set[int]] | None:
    df = pd.read_excel(pasta_dados / f"{slug}.xlsx")
    df.columns = [str(c).strip() for c in df.columns]
    datas = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce").dt.date
    achados = df[datas == dia]
    if achados.empty:
        return None
    linha = achados.iloc[0]
    cols = [c for c in df.columns if c.lower().startswith("bola")]
    return int(linha["Concurso"]), {int(linha[c]) for c in cols}


def conferir_pacote(jogo: str, pacote: dict, concurso: int, sorteio: set[int]) -> dict:
    ultimo = (pacote.get("meta") or {}).get("ultimo_concurso")
    if ultimo is not None and ultimo >= concurso:
        return {"status": "invalido", "motivo": "pacote gerado depois do sorteio", "concurso": concurso}
    jogos = pacote["jogos"]
    acertos = [contar_acertos(j, sorteio) for j in jogos]
    faixas = FAIXAS[jogo]
    premios = [faixas[a] for a in acertos if a in faixas]
    esperado = acertos_esperados(UNIVERSO[jogo], len(sorteio), len(jogos[0]))
    return {
        "status": "conferido",
        "concurso": concurso,
        "sorteio": sorted(sorteio),
        "acertos": acertos,
        "melhor": max(acertos),
        "media_acertos": round(sum(acertos) / len(acertos), 4),
        "esperado_aleatorio": round(esperado, 4),
        "premios": premios,
    }


def _linha_historico(dia: str, jogo: str, n_jogos: int, r: dict) -> dict:
    return {
        "data": dia, "jogo": jogo, "concurso": r["concurso"], "n_jogos": n_jogos,
        "melhor": r["melhor"], "media_acertos": r["media_acertos"],
        "esperado_aleatorio": r["esperado_aleatorio"], "premiados": len(r["premios"]),
        "faixas": "|".join(r["premios"]),
    }


def _gravar_historico(arquivo: Path, linhas: list[dict]) -> None:
    novo = not arquivo.exists()
    with arquivo.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if novo:
            w.writeheader()
        w.writerows(linhas)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Confere pacotes contra o sorteio do dia.")
    p.add_argument("--registro", default="registro", help="pasta do branch registro")
    p.add_argument("--dados", default="data", help="pasta com as planilhas")
    args = p.parse_args(argv)

    raiz = Path(args.registro)
    linhas, resumo = [], []
    for arq in sorted((raiz / "pacotes").glob("*/*/package.json")):
        destino = arq.parent
        jogo, dia_txt = destino.name, destino.parent.name
        if jogo not in SLUGS or (destino / "resultado.json").exists():
            continue
        pacote = json.loads(arq.read_text(encoding="utf-8"))
        if pacote.get("status") != "aprovado":
            continue
        sorteio = achar_sorteio(SLUGS[jogo], date.fromisoformat(dia_txt), Path(args.dados))
        if sorteio is None:
            print(f"[{jogo} {dia_txt}] sorteio ainda não está na planilha; fica pendente.")
            continue
        r = conferir_pacote(jogo, pacote, *sorteio)
        (destino / "resultado.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        if r["status"] == "conferido":
            linhas.append(_linha_historico(dia_txt, jogo, len(pacote["jogos"]), r))
            resumo.append(
                f"- {dia_txt} {jogo}: melhor {r['melhor']} acertos, média {r['media_acertos']} "
                f"(aleatório {r['esperado_aleatorio']}), prêmios: {', '.join(r['premios']) or 'nenhum'}"
            )
        else:
            resumo.append(f"- {dia_txt} {jogo}: INVÁLIDO ({r['motivo']})")
    if linhas:
        _gravar_historico(raiz / "historico.csv", linhas)
    print("\n".join(resumo) or "Nada novo para conferir.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
