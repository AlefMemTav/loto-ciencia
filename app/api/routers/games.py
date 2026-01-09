# app/api/routers/games.py
from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_service
from app.api.schemas.games import GameSummary, GameConfigOut, ContextOut

router = APIRouter(tags=["games"])


@router.get("/games", response_model=list[GameSummary])
def list_games(svc=Depends(get_service)):
    from app.core.games import GAMES

    return [{"slug": slug, "name": cfg.name} for slug, cfg in GAMES.items()]


@router.get("/games/{slug}/config", response_model=GameConfigOut)
def get_config(slug: str, svc=Depends(get_service)):
    try:
        cfg = svc.get_config(slug)
    except KeyError:
        raise HTTPException(404, "Game not found")
    return {
        "slug": cfg.slug,
        "name": cfg.name,
        "n_numbers": cfg.n_numbers,
        "k": cfg.k,
        "bet_size": cfg.bet_size,
        "odds_text": cfg.odds_text,
        "game_price": cfg.game_price,
        "how_to_play": cfg.how_to_play,
        "layout": {
            "rows": cfg.layout.rows,
            "cols": cfg.layout.cols,
            "n_numbers": cfg.layout.n_numbers,
        },
    }


@router.get("/games/{slug}/context", response_model=ContextOut)
def get_context(slug: str, svc=Depends(get_service)):
    try:
        ctx = svc.get_context(slug)
    except KeyError:
        raise HTTPException(404, "Game not found")

    df = ctx.df
    if df is None or df.empty:
        raise HTTPException(503, "History not loaded")

    # freq_top: serializa top N
    top = ctx.freq.head(10)
    freq_top = [{"numero": int(i), "freq": int(v)} for i, v in top.items()]

    return {
        "slug": slug,
        "total_concursos": int(len(df)),
        "ultimo_concurso": int(df.index.max()),
        "freq_top": freq_top,
        "poisson_finais": ctx.poisson_finais,
    }


@router.post("/games/{slug}/context:refresh")
def refresh_context(slug: str, svc=Depends(get_service)):
    svc.refresh_context(slug)
    return {"ok": True}
