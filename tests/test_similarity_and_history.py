"""Testes para Hamming corrigido, varredura completa do histórico e repetição R_{t-1}."""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from app.core.generator_objective import score_plausibility_batch
from app.core.lottery.catalog import LOTOFACIL, MEGASENA, QUINA
from app.core.statistics.basic import build_draws_binary_matrix
from app.core.statistics.similarity import (
    calcular_distancia_minima_historico,
    distancia_hamming,
    penalizar_por_similaridade,
)
from app.core.validator import validar_jogo


def _df_from_rows(config, rows: list[list[int]]) -> pd.DataFrame:
    data = []
    for idx, nums in enumerate(rows, 1):
        row = {"Concurso": idx}
        for col, val in zip(config.draw_cols, sorted(nums)):
            row[col] = int(val)
        data.append(row)
    return pd.DataFrame(data).set_index("Concurso")


def test_distancia_hamming_mede_diferenca_real_de_dezenas():
    assert distancia_hamming([1, 2, 3, 4, 5, 6], [1, 2, 3, 7, 8, 9]) == 3
    assert distancia_hamming([1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 6]) == 0
    assert distancia_hamming([1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 7]) == 1
    assert distancia_hamming([1, 2, 3, 4, 5, 6], [11, 12, 13, 14, 15, 16]) == 6


def test_calcular_distancia_minima_historico_full_vs_recente():
    # Linha 1 (antiga, fora dos últimos 100) tem [1,2,3,4,5,6]
    # Linhas 2..150 usam apenas dezenas altas {41..60}
    rng = np.random.default_rng(12)
    rows = [[1, 2, 3, 4, 5, 6]]
    pool_alto = np.arange(41, 61)
    for _ in range(149):
        rows.append(sorted(rng.choice(pool_alto, size=6, replace=False).tolist()))
    df = _df_from_rows(MEGASENA, rows)

    candidato = [1, 2, 3, 4, 5, 39]  # difere em 1 número da linha antiga
    draws_bin, _ = build_draws_binary_matrix(df, MEGASENA)

    dist_full, sim_full = calcular_distancia_minima_historico(
        candidato, df, MEGASENA, top_n=None, draws_bin=draws_bin
    )
    dist_100, sim_100 = calcular_distancia_minima_historico(
        candidato, df, MEGASENA, top_n=100, draws_bin=draws_bin
    )

    assert dist_full == 1
    assert sim_full == pytest.approx(5 / 6)
    assert dist_100 == 6
    assert 0.0 <= sim_100 <= 1.0


def test_penalizar_por_similaridade_calibra_clone_antigo_recente_e_densos():
    rng = np.random.default_rng(42)
    rows = [[2, 14, 21, 33, 44, 55]]
    pool_outro = np.array([n for n in range(1, 61) if n not in {2, 14, 21, 33, 44, 55}])
    for _ in range(149):
        rows.append(sorted(rng.choice(pool_outro, size=6, replace=False).tolist()))
    df = _df_from_rows(MEGASENA, rows)
    draws_bin, _ = build_draws_binary_matrix(df, MEGASENA)

    # Quase-clone antigo (d_full=1, fora dos últimos 100)
    rep_antigo = {"score": 100, "msgs": [], "risco_divisao": "Baixo", "metricas": {}}
    penalizar_por_similaridade(
        rep_antigo, [2, 14, 21, 33, 44, 58], df, MEGASENA, draws_bin=draws_bin
    )
    assert rep_antigo["metricas"]["hamming_historico_min"] == 1
    assert rep_antigo["metricas"]["hamming_recente_100"] >= 2
    assert rep_antigo["score"] == 92

    # Quase-clone recente (d_100=1 no último concurso)
    clone_rec = sorted(rows[-1][:-1] + [2])
    rep_recente = {"score": 100, "msgs": [], "risco_divisao": "Baixo", "metricas": {}}
    penalizar_por_similaridade(
        rep_recente, clone_rec, df, MEGASENA, draws_bin=draws_bin
    )
    assert rep_recente["metricas"]["hamming_recente_100"] == 1
    assert rep_recente["risco_divisao"] == "ALTO"
    assert rep_recente["score"] == 75

    # Clone exato identificado só pelo histórico mesmo sem historico_jogos set
    rep_exact = validar_jogo(rows[0], MEGASENA, df_historico=df, draws_bin=draws_bin)
    assert rep_exact["ja_saiu"] is True
    assert rep_exact["score"] == 0


def test_penalizar_por_similaridade_sem_falsos_positivos_em_lotofacil():
    rng = np.random.default_rng(2026)
    rows = [
        sorted(rng.choice(np.arange(1, 26), size=15, replace=False).tolist())
        for _ in range(300)
    ]
    df = _df_from_rows(LOTOFACIL, rows)
    draws_bin, _ = build_draws_binary_matrix(df, LOTOFACIL)

    altos = 0
    for _ in range(80):
        cand = sorted(rng.choice(np.arange(1, 26), size=15, replace=False).tolist())
        if tuple(cand) in {tuple(r) for r in rows}:
            continue
        rep = {"score": 100, "msgs": [], "risco_divisao": "Baixo", "metricas": {}}
        penalizar_por_similaridade(rep, cand, df, LOTOFACIL, draws_bin=draws_bin)
        if rep["risco_divisao"] == "ALTO":
            altos += 1
    assert altos <= 2


def test_repetidas_ultimo_sorteio_registra_quantis_e_detecta_extremo():
    rng = np.random.default_rng(7)
    rows = [
        sorted(rng.choice(np.arange(1, 26), size=15, replace=False).tolist())
        for _ in range(200)
    ]
    df = _df_from_rows(LOTOFACIL, rows)
    draws_bin, _ = build_draws_binary_matrix(df, LOTOFACIL)

    ultimo = rows[-1]
    faltam = [n for n in range(1, 26) if n not in ultimo]
    extremo = sorted(ultimo[:14] + [faltam[0]])  # 14 repetidas do último sorteio

    rep = validar_jogo(extremo, LOTOFACIL, df_historico=df, draws_bin=draws_bin)
    rep_ult = rep["metricas"]["repetidas_ultimo_sorteio"]
    assert rep_ult["qtd"] == 14
    assert 0 <= rep_ult["p5"] <= rep_ult["media_historica"] <= rep_ult["p95"] <= 15
    assert any("Alta repetição do último concurso" in m for m in rep["msgs"])


def test_score_plausibility_guarda_suave_contra_quase_clone_ultimos_10():
    rows = [
        [2, 11, 23, 35, 47, 58],
        [4, 15, 22, 31, 43, 56],
        [5, 16, 25, 34, 48, 59],
        [6, 17, 26, 37, 49, 60],
        [7, 18, 28, 38, 50, 55],
        [8, 19, 29, 39, 51, 54],
        [9, 20, 30, 40, 52, 53],
        [3, 13, 24, 36, 44, 57],
        [1, 14, 27, 41, 45, 51],
        [7, 18, 29, 36, 44, 58],
    ]
    df = _df_from_rows(MEGASENA, rows)
    draws_bin, _ = build_draws_binary_matrix(df, MEGASENA)

    tabela = pd.DataFrame({"Z_Freq": np.zeros(60), "Z_Gap": np.zeros(60)})
    ctx_com = SimpleNamespace(
        config=MEGASENA,
        tabela=tabela,
        df=df,
        draws_bin=draws_bin,
        historico_set=set(),
    )
    ctx_sem = SimpleNamespace(
        config=MEGASENA,
        tabela=tabela,
        df=pd.DataFrame(),
        historico_set=set(),
    )

    cands = np.array(
        [
            [7, 18, 29, 36, 44, 59],  # 5/6 com o último concurso
            [3, 14, 26, 39, 48, 57],  # sem quase-clone nos últimos 10
        ],
        dtype=int,
    )
    com = score_plausibility_batch(
        cands, ctx_com, usar_calibracao_score=False, estrategia="pura", null_model_samples=1000
    )
    sem = score_plausibility_batch(
        cands, ctx_sem, usar_calibracao_score=False, estrategia="pura", null_model_samples=1000
    )

    assert com[0] == pytest.approx(sem[0] - 3.5)
    assert com[1] == pytest.approx(sem[1])
