"""
Testes da auditoria de independência entre sorteios e da correção de múltiplos testes.

Dois tipos de verificação:
- sorteios independentes (hipótese nula verdadeira) não devem ser rejeitados;
- dependências plantadas de propósito devem ser detectadas.
"""

import numpy as np
import pandas as pd
import pytest

from app.core.lottery.catalog import LOTOFACIL, MEGASENA
from app.core.statistics.auditoria_independencia import (
    AuditoriaIndependencia,
    ResultadoTeste,
    auditar_independencia,
)
from app.core.statistics.multiple_testing import benjamini_hochberg, holm_bonferroni


def _para_df(valores: np.ndarray, config) -> pd.DataFrame:
    return pd.DataFrame(
        valores,
        columns=config.draw_cols,
        index=pd.RangeIndex(1, len(valores) + 1, name="Concurso"),
    )


def sorteios_iid(rng, n_sorteios: int, config) -> pd.DataFrame:
    """Sorteios independentes, com a ordem de saída das bolas também aleatória."""
    chaves = rng.random((n_sorteios, config.n_numbers))
    idx = np.argpartition(chaves, config.k - 1, axis=1)[:, : config.k] + 1
    return _para_df(rng.permuted(idx, axis=1), config)


def sorteios_com_repeticao(rng, n_sorteios: int, config, repetem: int = 3) -> pd.DataFrame:
    """Cada sorteio repete `repetem` números do anterior (dependência plantada)."""
    universo = np.arange(1, config.n_numbers + 1)
    linhas = [rng.choice(universo, config.k, replace=False)]
    for _ in range(n_sorteios - 1):
        mantidos = rng.choice(linhas[-1], repetem, replace=False)
        novos = rng.choice(np.setdiff1d(universo, mantidos), config.k - repetem, replace=False)
        linhas.append(rng.permutation(np.concatenate([mantidos, novos])))
    return _para_df(np.array(linhas), config)


def sorteios_com_soma_persistente(rng, n_sorteios: int) -> pd.DataFrame:
    """Mega-Sena em que a faixa sorteada deriva devagar: a soma tem memória."""
    centro, linhas = 30.0, []
    for _ in range(n_sorteios):
        centro = 30.0 + 0.95 * (centro - 30.0) + rng.normal(0, 4)
        inicio = int(np.clip(round(centro) - 15, 1, 31))
        linhas.append(rng.choice(np.arange(inicio, inicio + 30), 6, replace=False))
    return _para_df(np.array(linhas), MEGASENA)


def sorteios_com_ordem_viciada(rng, n_sorteios: int, config) -> pd.DataFrame:
    """Bolas tendem a sair em ordem crescente, mas sem formar linhas ordenadas."""
    base = sorteios_iid(rng, n_sorteios, config).to_numpy()
    chaves = base + rng.normal(0, 15, base.shape)
    ordem = np.argsort(chaves, axis=1)
    return _para_df(np.take_along_axis(base, ordem, axis=1), config)


def _nomes_rejeitados(auditoria: AuditoriaIndependencia) -> set[str]:
    return {t.nome for t in auditoria.rejeitados}


class TestMultiplosTestes:
    def test_holm_valores_conhecidos(self):
        ajustado = holm_bonferroni(np.array([0.01, 0.04, 0.03]))
        assert ajustado == pytest.approx([0.03, 0.06, 0.06])

    def test_benjamini_hochberg_valores_conhecidos(self):
        ajustado = benjamini_hochberg(np.array([0.01, 0.04, 0.03]))
        assert ajustado == pytest.approx([0.03, 0.04, 0.04])

    def test_holm_e_mais_conservador_que_bh(self):
        p = np.random.default_rng(0).uniform(0, 0.2, 40)
        assert np.all(holm_bonferroni(p) >= benjamini_hochberg(p) - 1e-12)

    @pytest.mark.parametrize("funcao", [holm_bonferroni, benjamini_hochberg])
    def test_limites_e_vazio(self, funcao):
        p = np.array([0.0, 0.5, 1.0, 0.2])
        ajustado = funcao(p)
        assert np.all(ajustado >= p) and np.all(ajustado <= 1.0)
        assert len(funcao(np.array([]))) == 0


@pytest.fixture(scope="module")
def auditoria():
    df = sorteios_iid(np.random.default_rng(1), 1500, MEGASENA)
    return auditar_independencia(df, MEGASENA, n_permutacoes=300, seed=3)


class TestAuditoriaEstrutura:
    def test_retorna_none_com_historico_curto(self):
        df = sorteios_iid(np.random.default_rng(1), 50, MEGASENA)
        assert auditar_independencia(df, MEGASENA) is None

    def test_retorna_none_com_df_vazio(self):
        assert auditar_independencia(pd.DataFrame(), MEGASENA) is None

    def test_oito_testes_com_nomes_esperados(self, auditoria):
        assert [t.nome for t in auditoria.testes] == [
            "soma_autocorrelacao_lag1",
            "soma_variacao_absoluta",
            "soma_ljung_box_10",
            "soma_transicao_tercis",
            "soma_runs_mediana",
            "repeticao_sorteio_anterior",
            "ordem_posicao_x_valor",
            "ordem_posicao_do_minimo",
        ]
        assert all(isinstance(t, ResultadoTeste) for t in auditoria.testes)

    def test_p_valores_validos_e_ajuste_nunca_diminui(self, auditoria):
        for t in auditoria.testes:
            assert 0.0 < t.p_valor <= 1.0
            assert t.p_valor <= t.p_ajustado <= 1.0

    def test_contagens(self, auditoria):
        assert auditoria.n_sorteios == 1500
        assert auditoria.n_sorteios_ordem == 1500

    def test_dataframe_e_dict(self, auditoria):
        df = auditoria.para_dataframe()
        assert list(df.columns) == [
            "teste", "estatistica", "p_valor", "p_ajustado", "rejeita", "descricao",
        ]
        assert len(df) == 8
        d = auditoria.para_dict()
        assert d["jogo"] == "Mega-Sena"
        assert len(d["testes"]) == 8
        assert d["n_rejeitados"] == auditoria.n_rejeitados

    def test_mesma_semente_mesmo_resultado(self):
        df = sorteios_iid(np.random.default_rng(1), 800, MEGASENA)
        a = auditar_independencia(df, MEGASENA, n_permutacoes=200, seed=9)
        b = auditar_independencia(df, MEGASENA, n_permutacoes=200, seed=9)
        assert [t.p_valor for t in a.testes] == [t.p_valor for t in b.testes]

    def test_ajuste_invalido(self):
        df = sorteios_iid(np.random.default_rng(1), 300, MEGASENA)
        with pytest.raises(ValueError):
            auditar_independencia(df, MEGASENA, ajuste="inexistente")

    def test_ajuste_bh_disponivel(self):
        df = sorteios_iid(np.random.default_rng(1), 300, MEGASENA)
        assert auditar_independencia(df, MEGASENA, n_permutacoes=100, ajuste="bh").ajuste == "bh"


class TestHipoteseNulaVerdadeira:
    @pytest.mark.parametrize("config", [MEGASENA, LOTOFACIL], ids=["mega", "lotofacil"])
    def test_sorteios_independentes_nao_sao_rejeitados(self, config):
        df = sorteios_iid(np.random.default_rng(2026), 2000, config)
        auditoria = auditar_independencia(df, config, n_permutacoes=500, seed=0)
        assert auditoria.n_rejeitados == 0
        assert "sem evidência" in auditoria.conclusao()


class TestDependenciaPlantada:
    def test_detecta_repeticao_do_sorteio_anterior(self):
        df = sorteios_com_repeticao(np.random.default_rng(4), 1000, MEGASENA)
        auditoria = auditar_independencia(df, MEGASENA, n_permutacoes=300)
        assert "repeticao_sorteio_anterior" in _nomes_rejeitados(auditoria)
        assert "possível dependência" in auditoria.conclusao()

    def test_detecta_memoria_na_soma(self):
        df = sorteios_com_soma_persistente(np.random.default_rng(5), 1500)
        nomes = _nomes_rejeitados(auditar_independencia(df, MEGASENA, n_permutacoes=300))
        assert {"soma_autocorrelacao_lag1", "soma_ljung_box_10"} <= nomes

    def test_detecta_ordem_de_saida_viciada(self):
        df = sorteios_com_ordem_viciada(np.random.default_rng(6), 1500, MEGASENA)
        auditoria = auditar_independencia(df, MEGASENA, n_permutacoes=300)
        assert auditoria.n_sorteios_ordem == 1500  # não foi descartado como "ordenado"
        assert "ordem_posicao_x_valor" in _nomes_rejeitados(auditoria)

    def test_linhas_antigas_ordenadas_sao_ignoradas_nos_testes_de_ordem(self):
        rng = np.random.default_rng(7)
        df = sorteios_iid(rng, 1000, MEGASENA)
        valores = df.to_numpy().copy()
        valores[:300] = np.sort(valores[:300], axis=1)  # bloco antigo em ordem crescente
        auditoria = auditar_independencia(_para_df(valores, MEGASENA), MEGASENA, n_permutacoes=200)
        assert auditoria.n_sorteios_ordem == 700
        assert "ordem_posicao_x_valor" not in _nomes_rejeitados(auditoria)
