# app/api/routers/stats.py
from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.deps import get_service
from app.api.schemas.stats import (
    PoissonFinalItem,
    Chi2Out,
    IntervaloConfiancaOut,
    CoefVariacaoOut,
    AtrasosItem,
    FrequenciaItem,
    InteligenciaItem,
)
from app.src.statistics import analise_poisson

router = APIRouter(tags=["stats"])


def _ctx_or_503(svc, slug: str):
    """Helper: retorna contexto ou levanta 404/503."""
    try:
        ctx = svc.get_context(slug)
    except KeyError:
        raise HTTPException(404, "Game not found")
    if ctx.df is None or ctx.df.empty:
        raise HTTPException(503, "History not loaded")
    return ctx


@router.get("/games/{slug}/stats/frequencia", response_model=list[FrequenciaItem])
def stats_frequencia(
    slug: str,
    top: int = Query(60, ge=1, le=200, description="Quantidade de números a retornar"),
    svc=Depends(get_service),
):
    """Retorna frequência dos números (quentes)."""
    ctx = _ctx_or_503(svc, slug)
    s = ctx.freq.head(top)
    return [{"numero": int(i), "frequencia": int(v)} for i, v in s.items()]


@router.get("/games/{slug}/stats/poisson-finais", response_model=list[PoissonFinalItem])
def stats_poisson_finais(
    slug: str,
    alpha: float = Query(0.05, gt=0.0, lt=1.0, description="Nível de significância"),
    svc=Depends(get_service),
):
    """
    Retorna análise de Poisson dos dígitos finais.

    Se alpha=0.05 (padrão), usa resultado cacheado.
    Caso contrário, recalcula com novo alpha.
    """
    ctx = _ctx_or_503(svc, slug)

    # Se alpha é o padrão, usa cache
    if alpha == 0.05:
        return ctx.poisson_finais

    # Caso contrário, recalcula com alpha customizado
    return analise_poisson(ctx.df, ctx.config, alpha=alpha)


@router.get("/games/{slug}/stats/atrasos", response_model=list[AtrasosItem])
def stats_atrasos(
    slug: str,
    top: int = Query(60, ge=1, le=200, description="Quantidade de números a retornar"),
    svc=Depends(get_service),
):
    """Retorna números mais atrasados (gap desde última aparição)."""
    ctx = _ctx_or_503(svc, slug)
    s = ctx.atrasos.head(top)
    return [{"numero": int(i), "atraso": int(v)} for i, v in s.items()]


@router.get(
    "/games/{slug}/stats/intelligence-table", response_model=list[InteligenciaItem]
)
def stats_intelligence_table(slug: str, svc=Depends(get_service)):
    """
    Retorna tabela de inteligência completa:
    frequência, atraso, z-scores, pesos para geração.
    """
    ctx = _ctx_or_503(svc, slug)
    tabela = ctx.tabela
    if tabela is None or tabela.empty:
        return []

    # Reset index para expor 'numero' como coluna
    tabela = tabela.reset_index().rename(columns={"index": "numero"})
    return tabela.to_dict(orient="records")


@router.get("/games/{slug}/stats/chi2", response_model=Chi2Out)
def stats_chi2(slug: str, svc=Depends(get_service)):
    """
    Retorna teste de aleatoriedade (Chi² e Kolmogorov-Smirnov).
    Indica se o sorteio é estatisticamente honesto.
    """
    ctx = _ctx_or_503(svc, slug)
    if ctx.chi2 is None:
        raise HTTPException(503, "Not enough data")
    return ctx.chi2


@router.get("/games/{slug}/stats/coef-variacao", response_model=CoefVariacaoOut)
def stats_coef_variacao(slug: str, svc=Depends(get_service)):
    """
    Retorna coeficiente de variação da frequência.
    Mede uniformidade da distribuição dos números.
    """
    ctx = _ctx_or_503(svc, slug)
    if ctx.coef_variacao is None:
        raise HTTPException(503, "Not enough data")
    return ctx.coef_variacao


@router.get("/games/{slug}/stats/ic-soma", response_model=IntervaloConfiancaOut)
def stats_ic_soma(slug: str, svc=Depends(get_service)):
    """
    Retorna intervalos de confiança da soma dos números sorteados.
    Usado para validar se a soma de um jogo está na faixa histórica.
    """
    ctx = _ctx_or_503(svc, slug)
    if ctx.ic_info is None:
        raise HTTPException(503, "Not enough data")

    # Copia dict e converte tuplas para listas (JSON-friendly)
    res = dict(ctx.ic_info)
    res["ic_50"] = list(res["ic_50"])
    res["ic_80"] = list(res["ic_80"])
    res["ic_95"] = list(res["ic_95"])
    return res


@router.get("/games/{slug}/stats/reis-sequencia", response_model=list[int])
def stats_reis_sequencia(slug: str, svc=Depends(get_service)):
    """
    Retorna números que mais formam sequências (pares consecutivos).
    Ex: se 23-24 apareceu muito no histórico, ambos aparecem aqui.
    """
    ctx = _ctx_or_503(svc, slug)
    return ctx.reis_sequencia
