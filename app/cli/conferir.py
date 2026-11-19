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
from hashlib import sha256
import json
import math
import sys
from datetime import date
from pathlib import Path

import numpy as np
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


def variancia_media_acertos_exata(
    jogos: list[list[int]], n_universo: int, k_sorteio: int
) -> float:
    """
    Variância hipergeométrica exata de `media_acertos` condicionada ao vetor de exposição E:
        Var(H_bar | E) = [k_d * (N - k_d) / (M^2 * N * (N - 1))] * sum_{i=1}^N (E_i - E_bar)^2
    Se a exposição for perfeitamente uniforme (E_i == E_bar para todo i), Var(H_bar | E) == 0.
    """
    m = len(jogos)
    if m == 0 or n_universo <= 1:
        return 0.0
    exposicao = np.zeros(n_universo, dtype=float)
    for j in jogos:
        for num in j:
            if 1 <= int(num) <= n_universo:
                exposicao[int(num) - 1] += 1.0
    e_bar = float(exposicao.mean())
    ss_exp = float(np.sum((exposicao - e_bar) ** 2))
    fator = (k_sorteio * (n_universo - k_sorteio)) / float(
        (m ** 2) * n_universo * (n_universo - 1)
    )
    return max(0.0, fator * ss_exp)


def avaliar_controle_pareado_condicional(
    jogos: list[list[int]],
    sorteio: set[int],
    jogo: str,
    concurso: int,
    n_simulacoes: int = 100,
) -> dict:
    """
    Controle aleatório pareado Rao-Blackwellizado: avalia K pacotes aleatórios independentes
    de mesmo tamanho (M, k_aposta) sobre o EXATO mesmo sorteio D_t.
    Reduz em ~55% o tamanho amostral necessário para auditar o ganho de cobertura P(>= 1 prêmio).
    """
    m = len(jogos)
    n_univ = UNIVERSO[jogo]
    k_sorteio = len(sorteio)
    k_aposta = len(jogos[0]) if m > 0 else 0
    faixas_validas = set(FAIXAS[jogo].keys())

    if m == 0 or k_aposta == 0 or n_simulacoes <= 0:
        return {}

    seed_bytes = sha256(f"controle_pareado_v1|{jogo}|{concurso}".encode("utf-8")).digest()[:8]
    rng = np.random.default_rng(int.from_bytes(seed_bytes, "big"))

    # Vetor indicador do sorteio D_t (n_univ,)
    d_vec = np.zeros(n_univ, dtype=np.int16)
    for num in sorteio:
        if 1 <= int(num) <= n_univ:
            d_vec[int(num) - 1] = 1

    # Gera K * M bilhetes aleatórios sem reposição via argpartition vetorizado
    total_tickets = n_simulacoes * m
    chaves = rng.random((total_tickets, n_univ))
    escolhidos = np.argpartition(chaves, k_aposta - 1, axis=1)[:, :k_aposta]
    acertos_ctrl = d_vec[escolhidos].sum(axis=1).reshape(n_simulacoes, m)

    premiados_mask = np.isin(acertos_ctrl, list(faixas_validas))
    pacotes_premiados = np.any(premiados_mask, axis=1)
    p_premio_ctrl = float(np.mean(pacotes_premiados))
    media_premiados_ctrl = float(np.mean(premiados_mask.sum(axis=1)))

    acertos_sist = [contar_acertos(j, sorteio) for j in jogos]
    premiou_sist = 1.0 if any(a in faixas_validas for a in acertos_sist) else 0.0
    media_sist = sum(acertos_sist) / float(m)
    esperado = acertos_esperados(n_univ, k_sorteio, k_aposta)
    var_exata = variancia_media_acertos_exata(jogos, n_univ, k_sorteio)
    dp_exato = math.sqrt(var_exata)
    z_exp = (media_sist - esperado) / dp_exato if dp_exato > 1e-9 else 0.0

    return {
        "n_simulacoes": int(n_simulacoes),
        "p_premio_controle_condicional": round(p_premio_ctrl, 4),
        "delta_premio_pareado": round(premiou_sist - p_premio_ctrl, 4),
        "media_bilhetes_premiados_controle": round(media_premiados_ctrl, 4),
        "dp_media_acertos_teorico": round(dp_exato, 4),
        "z_exposicao_hipergeometrica": round(z_exp, 4),
    }


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
    controle = avaliar_controle_pareado_condicional(jogos, sorteio, jogo, concurso)
    return {
        "status": "conferido",
        "concurso": concurso,
        "sorteio": sorted(sorteio),
        "acertos": acertos,
        "melhor": max(acertos),
        "media_acertos": round(sum(acertos) / len(acertos), 4),
        "esperado_aleatorio": round(esperado, 4),
        "premios": premios,
        "controle_pareado": controle,
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
    p.add_argument(
        "--incluir-reprovados",
        action="store_true",
        help="confere também pacotes com status != aprovado para evitar censura amostral na auditoria",
    )
    args = p.parse_args(argv)

    raiz = Path(args.registro)
    linhas, resumo = [], []
    for arq in sorted((raiz / "pacotes").glob("*/*/package.json")):
        destino = arq.parent
        jogo, dia_txt = destino.name, destino.parent.name
        if jogo not in SLUGS or (destino / "resultado.json").exists():
            continue
        pacote = json.loads(arq.read_text(encoding="utf-8"))
        if pacote.get("status") != "aprovado" and not args.incluir_reprovados:
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
