import inspect

import numpy as np
import pytest

from app.core.generator_fast import gerar_jogos_vetorizado
from app.core.generator_objective import score_plausibility_batch
from app.core.statistics.popularidade_medida import LIMIAR_RAZAO_GANHADORES
from app.services.lottery_service import LotteryService

SLUGS_COM_CORTE = ["mega_sena_sorteio", "quina_sorteio"]


@pytest.fixture(scope="module")
def service():
    return LotteryService()


@pytest.fixture(scope="module")
def contextos(service):
    """Constrói cada contexto uma única vez (é a parte cara dos testes)."""
    cache = {}

    def obter(slug):
        if slug not in cache:
            cache[slug] = service.get_context(slug)
        return cache[slug]

    return obter


@pytest.mark.parametrize("slug", SLUGS_COM_CORTE)
def test_corte_popularidade_respeita_limiar(service, contextos, slug):
    ctx = contextos(slug)
    assert ctx.modelo_popularidade is not None
    jogos = service.generate(
        slug,
        {"quantidade": 10, "estrategia": "balanceada", "seed": 11, "null_model_samples": 2000},
        ctx=ctx,
    )
    razoes = ctx.modelo_popularidade.razao_ganhadores_batch(np.array(jogos))
    assert len(jogos) == 10
    assert (razoes <= LIMIAR_RAZAO_GANHADORES[slug] + 1e-9).all(), razoes


def test_razao_batch_igual_a_avaliar(contextos):
    ctx = contextos("mega_sena_sorteio")
    jogo = [3, 17, 33, 41, 52, 58]
    em_lote = ctx.modelo_popularidade.razao_ganhadores_batch(np.array([jogo]))[0]
    assert em_lote == pytest.approx(ctx.modelo_popularidade.avaliar(jogo)["razao_ganhadores"])


def test_corte_pode_ser_desligado(contextos):
    ctx = contextos("mega_sena_sorteio")
    cands = np.sort(
        np.array([np.random.default_rng(i).choice(np.arange(1, 61), 6, replace=False) for i in range(400)]),
        axis=1,
    )
    com = score_plausibility_batch(cands, ctx, null_model_samples=2000)
    sem = score_plausibility_batch(cands, ctx, null_model_samples=2000, usar_corte_popularidade=False)
    acima = ctx.modelo_popularidade.razao_ganhadores_batch(cands) > LIMIAR_RAZAO_GANHADORES["mega_sena_sorteio"]
    assert acima.any() and (~acima).any()
    assert np.allclose(com[~acima], sem[~acima])
    assert (com[acima] < sem[acima] - 50).all()


def test_sem_corte_na_lotofacil(service):
    assert "loto_facil_sorteio" not in LIMIAR_RAZAO_GANHADORES
    assert "loto_mania_sorteio" not in LIMIAR_RAZAO_GANHADORES


def test_sinais_sem_evidencia_desligados_por_padrao():
    params = inspect.signature(gerar_jogos_vetorizado).parameters
    for nome in ("usar_quentes", "usar_atrasados", "usar_markov", "usar_ciclo"):
        assert params[nome].default is False, nome
    params = inspect.signature(score_plausibility_batch).parameters
    for nome in ("usar_quentes", "usar_atrasados"):
        assert params[nome].default is False, nome


def test_sinais_podem_ser_religados(service, contextos):
    ctx = contextos("loto_facil_sorteio")
    base = {"quantidade": 3, "estrategia": "balanceada", "seed": 5, "null_model_samples": 1000}
    desligado = service.generate("loto_facil_sorteio", base, ctx=ctx)
    ligado = service.generate(
        "loto_facil_sorteio",
        {**base, "usar_quentes": True, "usar_atrasados": True, "usar_markov": True, "usar_ciclo": True},
        ctx=ctx,
    )
    assert len(desligado) == len(ligado) == 3
    assert desligado != ligado
