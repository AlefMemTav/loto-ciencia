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


def _prob_premio_bilhete_exata(
    n_universo: int, k_sorteio: int, k_aposta: int, faixas_validas: set[int]
) -> float:
    """Probabilidade hipergeométrica exata de um bilhete aleatório acertar qualquer faixa paga."""
    total = math.comb(n_universo, k_sorteio)
    if total <= 0:
        return 0.0
    p = 0.0
    rem_pool = n_universo - k_aposta
    for h in faixas_validas:
        rem_draw = k_sorteio - h
        if 0 <= h <= min(k_sorteio, k_aposta) and 0 <= rem_draw <= rem_pool:
            p += (math.comb(k_aposta, h) * math.comb(rem_pool, rem_draw)) / total
    return float(min(1.0, max(0.0, p)))


def avaliar_controle_pareado_condicional(
    jogos: list[list[int]],
    sorteio: set[int],
    jogo: str,
    concurso: int,
    n_simulacoes: int = 100,
) -> dict:
    """
    Controle aleatório pareado Rao-Blackwellizado:
    - Por simetria do universo, o limite exato K -> inf da probabilidade de um pacote
      aleatório de M jogos independentes premiar no sorteio D_t tem forma fechada:
      p_exato = 1 - (1 - p_1)^M, eliminando 100% da variância do braço de controle
      (redução de 50% na variância do estimador pareado frente a um controle único K = 1).
    - Também registra a estimativa empírica pareada de K pacotes aleatórios sobre o
      exato sorteio D_t para auditoria cruzada.
    """
    m = len(jogos)
    n_univ = UNIVERSO[jogo]
    sorteio_norm = {100 if (jogo == "loto_mania" and int(n) == 0) else int(n) for n in sorteio}
    k_sorteio = len(sorteio_norm)
    k_aposta = len(jogos[0]) if m > 0 else 0
    faixas_validas = set(FAIXAS[jogo].keys())

    if m == 0 or k_aposta == 0 or n_simulacoes <= 0:
        return {}

    p_1 = _prob_premio_bilhete_exata(n_univ, k_sorteio, k_aposta, faixas_validas)
    p_premio_exato = 1.0 - (1.0 - p_1) ** m
    media_premiados_exata = m * p_1

    seed_bytes = sha256(f"controle_pareado_v1|{jogo}|{concurso}".encode("utf-8")).digest()[:8]
    rng = np.random.default_rng(int.from_bytes(seed_bytes, "big"))

    # Vetor indicador do sorteio D_t (n_univ,)
    d_vec = np.zeros(n_univ, dtype=np.int16)
    for num in sorteio_norm:
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

    acertos_sist = [contar_acertos(j, sorteio_norm) for j in jogos]
    premiou_sist = 1.0 if any(a in faixas_validas for a in acertos_sist) else 0.0
    media_sist = sum(acertos_sist) / float(m)
    esperado = acertos_esperados(n_univ, k_sorteio, k_aposta)
    var_exata = variancia_media_acertos_exata(jogos, n_univ, k_sorteio)
    dp_exato = math.sqrt(var_exata)
    z_exp = (media_sist - esperado) / dp_exato if dp_exato > 1e-9 else 0.0

    return {
        "n_simulacoes": int(n_simulacoes),
        "p_premio_aleatorio_exato": round(p_premio_exato, 4),
        "media_bilhetes_premiados_exata": round(media_premiados_exata, 4),
        "p_premio_controle_condicional": round(p_premio_ctrl, 4),
        "delta_premio_pareado": round(premiou_sist - p_premio_exato, 4),
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
    bolas = {
        100 if (slug == "loto_mania_sorteio" and int(linha[c]) == 0) else int(linha[c])
        for c in cols
    }
    return int(linha["Concurso"]), bolas


_DETALHES_ARQUIVO = {
    "mega_sena": "megasena_detalhes.csv",
    "quina": "quina_detalhes.csv",
    "loto_facil": "lotofacil_detalhes.csv",
    "loto_mania": "lotomania_detalhes.csv",
}
_PRECO_BASE = {
    "mega_sena": 6.0,
    "quina": 3.0,
    "loto_facil": 3.5,
    "loto_mania": 3.0,
}
_FAIXA_COL_POR_ACERTO: dict[str, dict[int, int]] = {
    "mega_sena": {6: 1, 5: 2, 4: 3},
    "quina": {5: 1, 4: 2, 3: 3, 2: 4},
    "loto_facil": {15: 1, 14: 2, 13: 3, 12: 4, 11: 5},
    "loto_mania": {20: 1, 19: 2, 18: 3, 17: 4, 16: 5, 15: 6, 0: 7},
}
_FAIXA_BENCHMARK_POP = {
    "mega_sena": (3, 4),   # Quadra
    "quina": (3, 3),       # Terno
    "loto_facil": (2, 14), # 14 acertos
    "loto_mania": (5, 16), # 16 acertos
}


def _auditar_rateio_concurso(
    jogo: str,
    concurso: int,
    acertos: list[int],
    pacote: dict,
    pasta_dados: Path | None,
) -> dict:
    """
    Cruza os acertos do pacote com `data/detalhes/*_detalhes.csv` para rastrear:
    - prêmio bruto realizado pela Caixa, custo do pacote e retorno líquido,
    - razão observada de ganhadores do sorteio (`W_obs / W_esp`) na faixa de referência,
    - razão de ganhadores média prevista ex-ante para os bilhetes do pacote.
    """
    if pasta_dados is None:
        return {"disponivel": False, "motivo": "pasta_dados nao informada"}
    arq_nome = _DETALHES_ARQUIVO.get(jogo)
    if not arq_nome:
        return {"disponivel": False, "motivo": "modalidade sem arquivo de detalhes"}
    caminho = Path(pasta_dados) / "detalhes" / arq_nome
    if not caminho.exists():
        return {"disponivel": False, "motivo": f"arquivo ausente: {caminho.name}"}

    try:
        df_det = pd.read_csv(caminho)
        linha_df = df_det[df_det["Concurso"].astype(int) == int(concurso)]
        if linha_df.empty:
            return {"disponivel": False, "motivo": f"concurso {concurso} ausente em {caminho.name}"}
        row = linha_df.iloc[0]
    except Exception as exc:
        return {"disponivel": False, "motivo": f"erro ao ler detalhes: {exc}"}

    faixa_map = _FAIXA_COL_POR_ACERTO.get(jogo, {})
    premio_total = 0.0
    premios_por_faixa: dict[str, float] = {}
    for a in acertos:
        f_idx = faixa_map.get(int(a))
        if f_idx is None:
            continue
        col_p = f"faixa{f_idx}_premio"
        val_p = pd.to_numeric(row.get(col_p, 0.0), errors="coerce")
        if pd.notna(val_p) and float(val_p) > 0:
            premio_total += float(val_p)
            chave = FAIXAS[jogo].get(int(a), str(a))
            premios_por_faixa[chave] = round(premios_por_faixa.get(chave, 0.0) + float(val_p), 2)

    n_jogos = len(acertos)
    preco = float(_PRECO_BASE.get(jogo, 0.0))
    custo = n_jogos * preco
    arr = pd.to_numeric(row.get("valorArrecadado", 0.0), errors="coerce")
    arr_val = float(arr) if pd.notna(arr) and float(arr) > 0 else 0.0

    # Razão observada de ganhadores no sorteio (W_obs / W_esp) na faixa benchmark
    razao_sorteio_obs = None
    if arr_val > 0 and preco > 0 and jogo in _FAIXA_BENCHMARK_POP:
        f_bench, h_bench = _FAIXA_BENCHMARK_POP[jogo]
        w_obs = pd.to_numeric(row.get(f"faixa{f_bench}_ganhadores", np.nan), errors="coerce")
        if pd.notna(w_obs) and float(w_obs) > 0:
            n_ap_est = arr_val / preco
            k_sort = len(pacote.get("jogos", [[]])[0]) if jogo != "loto_mania" else 20
            k_ap = len(pacote.get("jogos", [[]])[0])
            p_bench = _prob_premio_bilhete_exata(UNIVERSO[jogo], k_sort, k_ap, {h_bench})
            w_esp = n_ap_est * p_bench
            if w_esp > 1e-6:
                razao_sorteio_obs = round(float(w_obs) / w_esp, 4)

    # Razão média prevista ex-ante nos bilhetes do pacote
    val_list = pacote.get("validacao") or []
    razoes_pkg = [
        float(v["razao_ganhadores"])
        for v in val_list
        if isinstance(v, dict) and v.get("razao_ganhadores") is not None
    ]
    razao_pkg_media = round(sum(razoes_pkg) / len(razoes_pkg), 4) if razoes_pkg else None
    retencao_esp = (
        round(1.0 / razao_pkg_media, 4)
        if razao_pkg_media is not None and razao_pkg_media > 1e-6
        else None
    )

    return {
        "disponivel": True,
        "arrecadacao": round(arr_val, 2),
        "custo_pacote": round(custo, 2),
        "premio_realizado_total": round(premio_total, 2),
        "retorno_liquido": round(premio_total - custo, 2),
        "premios_por_faixa": premios_por_faixa,
        "razao_ganhadores_sorteio_obs": razao_sorteio_obs,
        "razao_ganhadores_media_pacote": razao_pkg_media,
        "fator_retencao_esperado": retencao_esp,
    }


def conferir_pacote(
    jogo: str,
    pacote: dict,
    concurso: int,
    sorteio: set[int],
    pasta_dados: Path | None = None,
) -> dict:
    ultimo = (pacote.get("meta") or {}).get("ultimo_concurso")
    if ultimo is not None and ultimo >= concurso:
        return {"status": "invalido", "motivo": "pacote gerado depois do sorteio", "concurso": concurso}
    jogos = pacote.get("jogos") or []
    if not jogos:
        return {"status": "invalido", "motivo": "pacote sem jogos", "concurso": concurso}
    sorteio_norm = {100 if (jogo == "loto_mania" and int(n) == 0) else int(n) for n in sorteio}
    acertos = [contar_acertos(j, sorteio_norm) for j in jogos]
    faixas = FAIXAS[jogo]
    premios = [faixas[a] for a in acertos if a in faixas]
    esperado = acertos_esperados(UNIVERSO[jogo], len(sorteio_norm), len(jogos[0]))
    controle = avaliar_controle_pareado_condicional(jogos, sorteio_norm, jogo, concurso)
    res = {
        "status": "conferido",
        "concurso": concurso,
        "sorteio": sorted(sorteio_norm),
        "acertos": acertos,
        "melhor": max(acertos),
        "media_acertos": round(sum(acertos) / len(acertos), 4),
        "esperado_aleatorio": round(esperado, 4),
        "premios": premios,
        "controle_pareado": controle,
    }
    if pasta_dados is not None:
        res["auditoria_rateio"] = _auditar_rateio_concurso(
            jogo, concurso, acertos, pacote, pasta_dados
        )
    return res


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
    p.add_argument(
        "--auditar",
        action="store_true",
        help="exibe relatório sequencial anytime-valid (e-values + poder amostral) dos pacotes conferidos",
    )
    p.add_argument(
        "--jogo",
        default=None,
        choices=list(SLUGS.keys()),
        help="filtra a auditoria por uma modalidade específica (usado com --auditar)",
    )
    args = p.parse_args(argv)

    raiz = Path(args.registro)
    pasta_dados = Path(args.dados)
    linhas, resumo = [], []
    if (raiz / "pacotes").exists():
        for arq in sorted((raiz / "pacotes").glob("*/*/package.json")):
            destino = arq.parent
            jogo, dia_txt = destino.name, destino.parent.name
            if jogo not in SLUGS or (destino / "resultado.json").exists():
                continue
            pacote = json.loads(arq.read_text(encoding="utf-8"))
            if pacote.get("status") != "aprovado" and not args.incluir_reprovados:
                continue
            sorteio = achar_sorteio(SLUGS[jogo], date.fromisoformat(dia_txt), pasta_dados)
            if sorteio is None:
                print(f"[{jogo} {dia_txt}] sorteio ainda não está na planilha; fica pendente.")
                continue
            r = conferir_pacote(jogo, pacote, *sorteio, pasta_dados=pasta_dados)
            (destino / "resultado.json").write_text(
                json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8"
            )
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
    if resumo or not args.auditar:
        print("\n".join(resumo) or "Nada novo para conferir.")

    if args.auditar:
        from app.core.statistics.auditoria_registro import (
            auditar_historico_registro,
            formatar_relatorio_auditoria,
        )

        aud = auditar_historico_registro(raiz, jogo=args.jogo)
        print("\n" + formatar_relatorio_auditoria(aud))
    return 0


if __name__ == "__main__":
    sys.exit(main())
