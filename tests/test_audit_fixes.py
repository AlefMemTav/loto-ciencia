import inspect
import itertools
import math
from collections import Counter

import numpy as np
import pandas as pd
import pytest

from app.cli.game_day import checar_pacote
from app.core.generator_fast import gerar_jogos_vetorizado
from app.core.generator_objective import portfolio_diagnostics, score_plausibility_batch
from app.core.lottery.catalog import LOTOFACIL, LOTOMANIA, MEGASENA, QUINA
from app.core.matrices import get_matriz_fechamento
from app.core.real_game_mode import _coverage_ratio, generate_real_game_package
from app.core.statistics.advanced import (
    get_pares_mais_frequentes,
    get_pares_que_se_repelem,
    matriz_coocorrencia_numeros,
)
from app.core.statistics.basic import calcular_probabilidade_vitoria
from app.core.statistics.distributions import calcular_chi_quadrado
from app.core.statistics.geometry import avaliar_jogo_geometria_estatistica
from app.core.statistics.similarity import (
    avaliar_quadrantes_estatistico,
    calcular_taxa_regressao,
)
from app.core.statistics.temporal import detectar_tendencia_frequencia
from app.core.validator import validar_jogo
from app.services.lottery_service import LotteryService


def _mock_draws_df(config, n_draws: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for idx in range(1, n_draws + 1):
        nums = sorted(
            rng.choice(
                np.arange(1, config.n_numbers + 1), size=config.k, replace=False
            ).tolist()
        )
        row = {"Concurso": idx}
        for col, val in zip(config.draw_cols, nums):
            row[col] = int(val)
        rows.append(row)
    return pd.DataFrame(rows).set_index("Concurso")


def _brute_force_portfolio_counts(games: np.ndarray):
    overlaps = [
        len(set(games[i]) & set(games[j]))
        for i in range(len(games))
        for j in range(i + 1, len(games))
    ]
    pair_counts = Counter()
    triple_counts = Counter()
    quad_counts = Counter()
    for row in games:
        s = sorted(int(x) for x in row)
        pair_counts.update(itertools.combinations(s, 2))
        triple_counts.update(itertools.combinations(s, 3))
        quad_counts.update(itertools.combinations(s, 4))
    return overlaps, pair_counts, triple_counts, quad_counts


def test_jogos_densos_uniformes_nao_disparam_alto_excessivo():
    rng = np.random.default_rng(2025)
    for cfg in (LOTOFACIL, LOTOMANIA):
        altos = 0
        for _ in range(60):
            jogo = sorted(
                rng.choice(
                    np.arange(1, cfg.n_numbers + 1), size=cfg.bet_size, replace=False
                ).tolist()
            )
            rep = validar_jogo(jogo, cfg)
            assert "entropia" in rep["metricas"]
            if rep["risco_divisao"] == "ALTO":
                altos += 1
        assert altos <= 9, f"{cfg.slug} disparou risco ALTO em {altos}/60 uniformes"


def test_pa_sintetica_lotofacil_continua_penalizada_e_com_baixa_entropia():
    rep = validar_jogo(list(range(1, 16)), LOTOFACIL)
    assert rep["score"] < 40
    assert rep["risco_divisao"] == "ALTO"
    comp = rep["metricas"]["compressibilidade"]
    assert "baixa_entropia" in comp["flags_ativas"]


def test_paridade_megasena_quatro_pares_aceita():
    # 4/6 = 66.7%, com ceil(6*0.65)=4 deve estar na faixa equilibrada
    rep = validar_jogo([2, 4, 11, 24, 38, 53], MEGASENA)
    assert any("Distribuição Par/Ímpar equilibrada" in m for m in rep["msgs"])


@pytest.mark.parametrize("cfg,n_games", [(MEGASENA, 6), (LOTOFACIL, 4)])
def test_portfolio_diagnostics_e_coverage_equivalentes_forca_bruta(cfg, n_games):
    rng = np.random.default_rng(99)
    games = np.array(
        [
            sorted(
                rng.choice(
                    np.arange(1, cfg.n_numbers + 1), size=cfg.bet_size, replace=False
                )
            )
            for _ in range(n_games)
        ]
    )
    diag = portfolio_diagnostics(games, cfg)
    overlaps, pair_c, triple_c, quad_c = _brute_force_portfolio_counts(games)

    assert diag["overlap_medio"] == pytest.approx(float(np.mean(overlaps)), abs=1e-4)
    assert diag["overlap_max"] == max(overlaps)
    assert diag["pares_repetidos"] == sum(1 for c in pair_c.values() if c >= 2)
    assert diag["pares_repetidos_acima_2"] == sum(1 for c in pair_c.values() if c >= 3)
    assert diag["max_repeticao_par"] == max(pair_c.values())
    assert diag["trincas_repetidas"] == sum(1 for c in triple_c.values() if c >= 2)
    assert diag["max_repeticao_trinca"] == max(triple_c.values())
    assert diag["quadras_repetidas"] == sum(1 for c in quad_c.values() if c >= 2)
    assert diag["max_repeticao_quadra"] == max(quad_c.values())

    total_2 = len(games) * math.comb(cfg.bet_size, 2)
    total_3 = len(games) * math.comb(cfg.bet_size, 3)
    cov2_bf = len(pair_c) / total_2
    cov3_bf = len(triple_c) / total_3
    assert _coverage_ratio(games, 2, n_numbers=cfg.n_numbers) == pytest.approx(
        cov2_bf, rel=1e-12
    )
    assert _coverage_ratio(games, 3, n_numbers=cfg.n_numbers) == pytest.approx(
        cov3_bf, rel=1e-12
    )


def test_portfolio_diagnostics_fallback_para_linhas_com_duplicados():
    malformed = np.array(
        [
            [1, 1, 2, 3, 4, 5],
            [1, 2, 3, 4, 5, 6],
        ]
    )
    diag = portfolio_diagnostics(malformed, MEGASENA)
    assert diag["max_repeticao_par"] == 3
    assert diag["pares_repetidos"] >= 1


def test_estatisticas_vetorizadas_equivalentes_referencia():
    df = _mock_draws_df(MEGASENA, n_draws=120, seed=7)

    # Referência força bruta para co-ocorrência normalizada
    ref_raw = np.zeros((MEGASENA.n_numbers, MEGASENA.n_numbers), dtype=float)
    for row in df[MEGASENA.draw_cols].to_numpy(dtype=int):
        for a, b in itertools.combinations(sorted(row), 2):
            ref_raw[a - 1, b - 1] += 1
            ref_raw[b - 1, a - 1] += 1
    prob_esp = math.comb(MEGASENA.n_numbers - 2, MEGASENA.k - 2) / math.comb(
        MEGASENA.n_numbers, MEGASENA.k
    )
    ref_mat = ref_raw / (len(df) * prob_esp + 1e-9)

    mat = matriz_coocorrencia_numeros(df, MEGASENA)
    assert np.allclose(mat, ref_mat, atol=1e-12)

    pares_freq = get_pares_mais_frequentes(df, MEGASENA, top_n=10)
    assert len(pares_freq) == 10
    pares_rep = get_pares_que_se_repelem(df, MEGASENA, top_n=10)
    assert len(pares_rep) == 10

    # Regressão de atrasos
    reg = calcular_taxa_regressao(df, MEGASENA, janela=30)
    assert reg is not None
    assert 0.0 <= reg["taxa_retorno"] <= 1.0

    # Tendência temporal vs cálculo manual de blocos
    tend = detectar_tendencia_frequencia(df, MEGASENA, numero=7, janela=20)
    assert tend is not None
    draws_arr = df[MEGASENA.draw_cols].to_numpy(dtype=int)
    ref_freqs = [
        float(np.mean([7 in row for row in draws_arr[i : i + 20]]))
        for i in range(0, len(df) - 19, 20)
    ]
    assert np.allclose(tend["frequencias_janela"], ref_freqs)


def test_lotomania_probabilidade_fechamento_e_game_day():
    total, chance = calcular_probabilidade_vitoria(LOTOMANIA)
    esperado = math.comb(100, 20) / math.comb(50, 20)
    assert total == round(esperado)
    assert chance == pytest.approx(esperado, rel=1e-12)

    total_ms, chance_ms = calcular_probabilidade_vitoria(MEGASENA)
    assert total_ms == 50_063_860
    assert chance_ms == 50_063_860.0

    matriz = get_matriz_fechamento(list(range(1, 52)), LOTOMANIA)
    assert len(matriz) > 0
    assert all(len(j) == LOTOMANIA.bet_size for j in matriz)

    rng = np.random.default_rng(10)
    jogos = [
        sorted(rng.choice(np.arange(1, 101), size=50, replace=False).tolist())
        for _ in range(3)
    ]
    vals = [validar_jogo(j, LOTOMANIA) for j in jogos]
    # Força status baixo caso algum sorteio sintético acidental caia em alto
    for v in vals:
        if v["risco_divisao"] == "ALTO":
            v["risco_divisao"] = "Baixo"
    diag = portfolio_diagnostics(np.array(jogos), LOTOMANIA)
    erros, _ = checar_pacote(
        jogos,
        vals,
        diag,
        k=LOTOMANIA.bet_size,
        n_numbers=LOTOMANIA.n_numbers,
        overlap_limit=LOTOMANIA.get_overlap_limit(),
        esparso=bool(LOTOMANIA.is_sparse),
        quantidade=3,
    )
    assert erros == []


def test_fator_hipergeometrico_geometria_e_quadrantes():
    from app.core.statistics.geometry import GeometricDistribution

    # Lotomania: k=20, bet_size=50, N=100 -> fator variancia = (50/20) * (50/80) = 1.5625, std = 1.25x
    fator_esp = (50 / 20) * (100 - 50) / (100 - 20)
    std_base = 2.0
    grupos = {"Metade": list(range(1, 51))}
    dist = {
        "Metade": GeometricDistribution(
            mean=10.0,
            std=std_base,
            percentiles={5: 6.0, 95: 14.0},
            z_scores=np.array([]),
        )
    }
    jogo_desv = list(range(1, 29)) + list(range(51, 73))  # 28 em Metade vs media ajustada 25
    res_geom2 = avaliar_jogo_geometria_estatistica(jogo_desv, grupos, dist, LOTOMANIA)
    assert res_geom2["detalhes"]["Metade"]["media_historica"] == pytest.approx(25.0)
    assert res_geom2["detalhes"]["Metade"]["z_score"] == pytest.approx(
        3.0 / (std_base * math.sqrt(fator_esp)), rel=1e-3
    )

    stats_q = {
        q: {"mean": 5.0, "std": std_base} for q in (1, 2, 3, 4)
    }
    res_q = avaliar_quadrantes_estatistico(jogo_desv, LOTOMANIA, stats_q)
    q1 = res_q["detalhes"]["Q1"]
    assert q1["esperado"] == pytest.approx(12.5)
    assert q1["z_score"] == pytest.approx(
        (q1["presentes"] - 12.5) / (std_base * math.sqrt(fator_esp)), abs=0.02
    )


@pytest.mark.parametrize("cfg", [MEGASENA, QUINA, LOTOFACIL, LOTOMANIA])
def test_chi_quadrado_e_ks_discreto_nao_rejeitam_sorteios_uniformes(cfg):
    df = _mock_draws_df(cfg, n_draws=600, seed=42)
    res = calcular_chi_quadrado(df, cfg)
    assert res is not None
    assert res["p_chi"] > 0.05
    assert res["p_ks"] > 0.05


def test_usar_coocorrencia_desligado_por_padrao():
    for fn in (
        gerar_jogos_vetorizado,
        score_plausibility_batch,
        generate_real_game_package,
    ):
        sig = inspect.signature(fn).parameters
        if "usar_coocorrencia" in sig:
            assert sig["usar_coocorrencia"].default is False
