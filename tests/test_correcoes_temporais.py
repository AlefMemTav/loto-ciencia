"""
Testes das correções em `temporal.py` e `advanced.py`.

Cada classe cobre um bug que existia:
- autocorrelação de frequências: a série analisada era constante (sempre NaN);
- transições anômalas: esperado errado por um fator N (todas as células "déficit");
- eletrocardiograma de somas: `Media_Movel` era a própria soma.
"""

import numpy as np
import pandas as pd
import pytest

from app.core.lottery.catalog import MEGASENA
from app.core.statistics.advanced import analisar_transicoes_anomalas
from app.core.statistics.temporal import (
    analise_temporal_somas,
    calcular_autocorrelacao_frequencias,
)


def _para_df(valores: np.ndarray, config=MEGASENA) -> pd.DataFrame:
    return pd.DataFrame(
        valores,
        columns=config.draw_cols,
        index=pd.RangeIndex(1, len(valores) + 1, name="Concurso"),
    )


def sorteios_iid(rng, n_sorteios: int, config=MEGASENA) -> pd.DataFrame:
    chaves = rng.random((n_sorteios, config.n_numbers))
    idx = np.argpartition(chaves, config.k - 1, axis=1)[:, : config.k] + 1
    return _para_df(rng.permuted(idx, axis=1), config)


class TestAutocorrelacaoFrequencias:
    def test_valores_finitos_e_sem_ciclo_em_sorteios_independentes(self):
        df = sorteios_iid(np.random.default_rng(11), 3000)
        r = calcular_autocorrelacao_frequencias(df, MEGASENA, max_lag=50, janela=10)
        assert np.all(np.isfinite(r["autocorrelacoes"]))
        assert len(r["autocorrelacoes"]) == 50
        assert r["ciclo_detectado"] is False
        assert r["lags_significativos"] == []

    def test_autocorrelacoes_centradas_em_zero_sob_independencia(self):
        df = sorteios_iid(np.random.default_rng(12), 3000)
        r = calcular_autocorrelacao_frequencias(df, MEGASENA, max_lag=50, janela=10)
        # sem a correção de viés a média ficaria perto de -1/W = -0,0033
        assert abs(np.mean(r["autocorrelacoes"])) < 0.002

    def test_limite_com_bonferroni_e_maior_que_sem_correcao(self):
        df = sorteios_iid(np.random.default_rng(13), 3000)
        r = calcular_autocorrelacao_frequencias(df, MEGASENA, max_lag=50, janela=10)
        sem_correcao = 1.96 / np.sqrt(r["n_janelas"] * MEGASENA.n_numbers)
        assert r["limite_significancia"] > sem_correcao

    def test_detecta_ciclo_plantado(self):
        # blocos de 10 sorteios alternando entre favorecer a metade baixa e a alta
        rng = np.random.default_rng(14)
        linhas = []
        for t in range(3000):
            favorecida = np.arange(1, 31) if (t // 10) % 2 == 0 else np.arange(31, 61)
            outra = np.setdiff1d(np.arange(1, 61), favorecida)
            linhas.append(
                rng.permutation(
                    np.concatenate(
                        [rng.choice(favorecida, 5, replace=False), rng.choice(outra, 1)]
                    )
                )
            )
        r = calcular_autocorrelacao_frequencias(_para_df(np.array(linhas)), MEGASENA, janela=10)
        assert r["ciclo_detectado"] is True
        assert r["periodo_ciclo"] % 2 == 0  # período de 2 janelas (ou múltiplo)
        assert 1 in r["lags_significativos"]  # alternância: lag 1 fortemente negativo
        assert r["autocorrelacoes"][0] < 0

    def test_sorteios_sempre_iguais_nao_tem_o_que_medir(self):
        df = _para_df(np.tile([1, 2, 3, 4, 5, 6], (100, 1)))
        assert calcular_autocorrelacao_frequencias(df, MEGASENA, janela=10) is None


class TestTransicoesAnomalas:
    def test_nada_a_reportar_em_sorteios_independentes(self):
        df = sorteios_iid(np.random.default_rng(21), 3000)
        assert analisar_transicoes_anomalas(df, MEGASENA, n_permutacoes=300, seed=1) == []

    def test_sem_correcao_nao_marca_tudo_como_deficit(self):
        # Bug antigo: esperado N vezes maior, e as 3600 células saíam como déficit
        df = sorteios_iid(np.random.default_rng(22), 3000)
        anomalias = analisar_transicoes_anomalas(
            df, MEGASENA, alfa=None, n_permutacoes=200, seed=1
        )
        tipos = {a["tipo"] for a in anomalias}
        assert 0 < len(anomalias) < 0.1 * MEGASENA.n_numbers**2
        assert tipos == {"excesso", "deficit"}

    def test_esperado_esta_na_ordem_do_teorico(self):
        # O esperado condiciona nas frequências observadas de cada número, então
        # varia em torno do teórico (T-1)·(k/N)² ≈ 30 (±~25% nas caudas). O bug
        # antigo dava ≈ 1850, 60 vezes maior.
        df = sorteios_iid(np.random.default_rng(23), 3000)
        anomalias = analisar_transicoes_anomalas(
            df, MEGASENA, alfa=None, n_permutacoes=200, seed=1
        )
        teorico = (len(df) - 1) * (MEGASENA.k / MEGASENA.n_numbers) ** 2
        assert anomalias
        assert all(abs(a["esperado"] - teorico) < 0.3 * teorico for a in anomalias)
        assert abs(np.mean([a["esperado"] for a in anomalias]) - teorico) < 0.1 * teorico

    def test_detecta_transicao_plantada(self):
        rng = np.random.default_rng(24)
        valores = sorteios_iid(rng, 3000).to_numpy().copy()
        for t in range(1, len(valores)):
            if 7 in valores[t - 1] and 14 not in valores[t]:
                valores[t, rng.integers(0, 6)] = 14
        anomalias = analisar_transicoes_anomalas(
            _para_df(valores), MEGASENA, n_permutacoes=300, seed=1
        )
        assert anomalias, "a transição 7 -> 14 plantada não foi detectada"
        primeira = anomalias[0]
        assert (primeira["de"], primeira["para"], primeira["tipo"]) == (7, 14, "excesso")
        assert primeira["p_ajustado"] < 0.05

    def test_estrutura_e_ordenacao(self):
        rng = np.random.default_rng(25)
        valores = sorteios_iid(rng, 2000).to_numpy().copy()
        for t in range(1, len(valores)):
            if 5 in valores[t - 1] and 20 not in valores[t]:
                valores[t, rng.integers(0, 6)] = 20
        anomalias = analisar_transicoes_anomalas(
            _para_df(valores), MEGASENA, alfa=None, threshold_zscore=3.0, n_permutacoes=200
        )
        chaves = {"de", "para", "observado", "esperado", "zscore", "p_valor", "p_ajustado", "tipo"}
        assert anomalias and all(chaves <= set(a) for a in anomalias)
        zs = [abs(a["zscore"]) for a in anomalias]
        assert zs == sorted(zs, reverse=True)
        assert all(0 < a["p_valor"] <= a["p_ajustado"] <= 1 for a in anomalias)

    def test_mesma_semente_mesmo_resultado(self):
        df = sorteios_iid(np.random.default_rng(26), 1500)
        a = analisar_transicoes_anomalas(df, MEGASENA, alfa=None, n_permutacoes=100, seed=5)
        b = analisar_transicoes_anomalas(df, MEGASENA, alfa=None, n_permutacoes=100, seed=5)
        assert a == b

    def test_entradas_pequenas(self):
        assert analisar_transicoes_anomalas(pd.DataFrame(), MEGASENA) == []
        assert analisar_transicoes_anomalas(sorteios_iid(np.random.default_rng(1), 1), MEGASENA) == []


class TestEletrocardiogramaDeSomas:
    def test_media_movel_e_media_dos_ultimos_concursos(self):
        df = sorteios_iid(np.random.default_rng(31), 40)
        r = analise_temporal_somas(df, MEGASENA, janela=10, janela_media=5)
        somas = df[MEGASENA.draw_cols].sum(axis=1)
        esperado = somas.rolling(5).mean().tail(10).round(1).tolist()
        assert len(r["dados"]) == 10
        assert [d["Media_Movel"] for d in r["dados"]] == pytest.approx(esperado)
        assert [d["Soma"] for d in r["dados"]] == somas.tail(10).tolist()

    def test_media_movel_nao_e_a_propria_soma(self):
        df = sorteios_iid(np.random.default_rng(32), 40)
        r = analise_temporal_somas(df, MEGASENA, janela=10)
        assert any(d["Media_Movel"] != d["Soma"] for d in r["dados"])

    def test_somas_constantes_dao_media_igual_a_soma(self):
        df = _para_df(np.tile([1, 2, 3, 4, 5, 6], (30, 1)))
        r = analise_temporal_somas(df, MEGASENA, janela=10)
        assert all(d["Media_Movel"] == d["Soma"] == 21 for d in r["dados"])

    def test_historico_menor_que_a_janela(self):
        df = sorteios_iid(np.random.default_rng(33), 3)
        r = analise_temporal_somas(df, MEGASENA, janela=10, janela_media=5)
        assert len(r["dados"]) == 3

    def test_historico_vazio(self):
        assert analise_temporal_somas(pd.DataFrame(), MEGASENA)["dados"] == []
