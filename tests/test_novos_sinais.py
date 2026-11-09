"""Testes da ordem de saída e da popularidade medida (dados sintéticos)."""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from app.core.generator_objective import score_plausibility_batch
from app.core.lottery.catalog import MEGASENA, QUINA
from app.core.statistics import ordem_saida as os_
from app.core.statistics import popularidade_medida as pm
from app.core.validator import validar_jogo


def _sorteios(config, t, seed=0, vies=None):
    """Sorteios aleatórios na ordem de saída. `vies`: {numero: posicao_fixa}."""
    rng = np.random.default_rng(seed)
    linhas = []
    for _ in range(t):
        linha = list(rng.choice(np.arange(1, config.n_numbers + 1), config.k, replace=False))
        if vies:
            for numero, pos in vies.items():
                if numero in linha:
                    linha.remove(numero)
                    linha.insert(pos, numero)
        linhas.append(linha)
    df = pd.DataFrame(linhas, columns=config.draw_cols)
    df.index = pd.RangeIndex(1, t + 1, name="Concurso")
    return df


# ---------------- ordem de saída ----------------


def test_mascara_aceita_dados_na_ordem_de_saida():
    df = _sorteios(MEGASENA, 600)
    assert os_.mascara_ordem_de_saida(df, MEGASENA).all()


def test_mascara_descarta_bloco_antigo_ordenado():
    df = _sorteios(QUINA, 800, seed=1)
    df.iloc[:300] = np.sort(df.iloc[:300].to_numpy(), axis=1)  # como na Quina real
    mascara = os_.mascara_ordem_de_saida(df, QUINA)
    assert not mascara[:290].any()
    assert mascara[310:].all()


def test_auditoria_sem_vies_nao_acusa_desvio():
    df = _sorteios(MEGASENA, 3000, seed=2)
    res = os_.auditar_ordem_saida(df, MEGASENA)
    assert res["disponivel"] and res["linhas_ignoradas"] == 0
    assert res["significativos_fdr"] == 0
    assert "sem evidência" in res["conclusao"]


def test_auditoria_detecta_numero_que_sempre_sai_primeiro():
    df = _sorteios(MEGASENA, 3000, seed=3, vies={7: 0})
    res = os_.auditar_ordem_saida(df, MEGASENA)
    assert res["significativos_fdr"] >= 1
    assert "possível desvio" in res["conclusao"]


def test_percentil_posicional_em_faixa_valida_e_extremos():
    df = _sorteios(MEGASENA, 3000, seed=4, vies={7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0})
    perfil = os_.calcular_perfil_posicional(df, MEGASENA)
    cedo = os_.percentil_posicional([7, 8, 9, 10, 11, 12], perfil)
    assert 0 <= cedo <= 100
    assert cedo <= 10  # números que saem cedo ficam na ponta baixa
    lote = np.array([[1, 2, 3, 4, 5, 6], [20, 30, 40, 50, 55, 59]])
    pct = os_.percentil_posicional_batch(lote, perfil)
    assert pct.shape == (2,) and ((pct >= 0) & (pct <= 100)).all()


def test_perfil_none_com_poucos_dados():
    assert os_.calcular_perfil_posicional(_sorteios(MEGASENA, 20), MEGASENA) is None


# ---------------- popularidade medida ----------------


POPULARES = [3, 9, 14, 17, 22, 25, 31, 38, 41, 44, 52, 59]  # espalhados pelo volante
JOGO_POPULAR = [3, 17, 25, 38, 44, 59]
JOGO_RARO = [1, 6, 12, 28, 47, 55]


def _pesos_populares():
    pesos = np.zeros(60)
    pesos[np.array(POPULARES) - 1] = 0.5
    return pesos


def _detalhes(config, df, pesos_verdadeiros, seed=0, ruido_puro=False):
    rng = np.random.default_rng(seed)
    t = len(df)
    arrecadado = rng.lognormal(mean=17.0, sigma=0.4, size=t)
    soma_pesos = pesos_verdadeiros[df.to_numpy() - 1].sum(axis=1)
    taxa = 6000 * (arrecadado / 5e7) * (1.0 if ruido_puro else np.exp(soma_pesos))
    ganhadores = rng.poisson(taxa)
    det = pd.DataFrame(
        {
            "valorArrecadado": arrecadado,
            "faixa1_ganhadores": rng.poisson(0.1, t),
            "faixa2_ganhadores": rng.poisson(80, t),
            "faixa3_ganhadores": ganhadores,
        },
        index=df.index,
    )
    return det


def test_modelo_recupera_pesos_plantados_e_ordena_jogos():
    df = _sorteios(MEGASENA, 1500, seed=5)
    pesos = _pesos_populares()
    modelo = pm.treinar_modelo_popularidade(df, _detalhes(MEGASENA, df, pesos), MEGASENA)
    assert modelo is not None and modelo.faixa == 3
    assert modelo.r2_cv >= pm.R2_MINIMO
    assert np.corrcoef(modelo.pesos, pesos - pesos.mean())[0, 1] > 0.8

    popular = modelo.avaliar(JOGO_POPULAR)
    raro = modelo.avaliar(JOGO_RARO)
    assert popular["percentil"] > 90 > 40 > raro["percentil"]
    assert popular["razao_ganhadores"] > 1.5 > 0.8 > raro["razao_ganhadores"]


def test_modelo_nao_entra_quando_e_so_ruido():
    df = _sorteios(MEGASENA, 1500, seed=6)
    det = _detalhes(MEGASENA, df, np.zeros(60), seed=6, ruido_puro=True)
    assert pm.treinar_modelo_popularidade(df, det, MEGASENA) is None


def test_modelo_none_sem_dados_ou_com_poucos_concursos():
    df = _sorteios(MEGASENA, 1500, seed=7)
    assert pm.treinar_modelo_popularidade(df, None, MEGASENA) is None
    det = _detalhes(MEGASENA, df, np.zeros(60)).iloc[:100]
    assert pm.treinar_modelo_popularidade(df, det, MEGASENA) is None


def test_backtest_nao_vaza_futuro():
    """Só os concursos presentes no df entram no treino."""
    df = _sorteios(MEGASENA, 1500, seed=8)
    det = _detalhes(MEGASENA, df, _pesos_populares(), seed=8)
    modelo = pm.treinar_modelo_popularidade(df.iloc[:800], det, MEGASENA)
    assert modelo is not None and modelo.n_concursos == 800


def test_carregar_detalhes_le_csv(tmp_path):
    df = pd.DataFrame({"Concurso": [3, 2, 1], "valorArrecadado": [1.0, 2.0, 3.0]})
    df.to_csv(tmp_path / "megasena_detalhes.csv", index=False)
    det = pm.carregar_detalhes(MEGASENA, pasta=str(tmp_path))
    assert list(det.index) == [1, 2, 3]
    assert pm.carregar_detalhes(QUINA, pasta=str(tmp_path)) is None


# ---------------- integração: validador e gerador ----------------


@pytest.fixture(scope="module")
def sinais():
    df = _sorteios(MEGASENA, 1500, seed=9, vies={5: 0, 6: 0})
    modelo = pm.treinar_modelo_popularidade(
        df, _detalhes(MEGASENA, df, _pesos_populares(), seed=9), MEGASENA
    )
    perfil = os_.calcular_perfil_posicional(df, MEGASENA)
    assert modelo is not None and perfil is not None
    return modelo, perfil


def test_validador_penaliza_jogo_popular_so_quando_ha_modelo(sinais):
    modelo, perfil = sinais
    jogo = JOGO_POPULAR
    sem = validar_jogo(jogo, MEGASENA)
    com = validar_jogo(jogo, MEGASENA, perfil_posicional=perfil, modelo_popularidade=modelo)
    assert com["score"] < sem["score"]
    assert com["risco_divisao"] == "ALTO"
    assert com["metricas"]["popularidade_medida_percentil"] >= 95
    assert "ordem_saida_percentil" in com["metricas"]


def test_validador_igual_sem_os_novos_sinais():
    jogo = [3, 17, 25, 38, 44, 59]
    a = validar_jogo(jogo, MEGASENA)
    b = validar_jogo(jogo, MEGASENA, perfil_posicional=None, modelo_popularidade=None)
    assert a["score"] == b["score"]
    assert "popularidade_medida_percentil" not in a["metricas"]


def test_gerador_pontua_jogo_popular_abaixo_do_raro(sinais):
    modelo, perfil = sinais
    cands = np.array([JOGO_POPULAR, JOGO_RARO])
    base = dict(usar_calibracao_score=False, estrategia="pura", null_model_samples=2000)

    ctx_com = SimpleNamespace(config=MEGASENA, modelo_popularidade=modelo, perfil_posicional=perfil)
    ctx_sem = SimpleNamespace(config=MEGASENA)
    com = score_plausibility_batch(cands, ctx_com, **base)
    sem = score_plausibility_batch(cands, ctx_sem, **base)
    assert com[0] < sem[0]  # jogo popular perde pontos
    assert com[1] == pytest.approx(sem[1], abs=0.5)  # jogo raro quase não muda
    desligado = score_plausibility_batch(cands, ctx_com, usar_popularidade_medida=False, **base)
    assert desligado[0] == pytest.approx(sem[0])
