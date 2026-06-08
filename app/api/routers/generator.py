# app/api/routers/generator.py
from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_service
from app.api.schemas.generator import (
    GenerateRequest,
    GenerateResponse,
    GeneratedGame,
    RealGameRequest,
    RealGameResponse,
)

router = APIRouter(tags=["generator"])


@router.post("/games/{slug}/generate", response_model=GenerateResponse)
def generate(slug: str, body: GenerateRequest, svc=Depends(get_service)):
    try:
        games = svc.generate(slug, body.model_dump())
    except KeyError:
        raise HTTPException(404, "Game not found")
    except ValueError as e:
        raise HTTPException(422, str(e))

    out = []
    for g in games:
        validation = svc.validate(slug, g) if body.validar_resultado else None
        out.append(GeneratedGame(numbers=g, validation=validation))
    return {"games": out, "meta": body.model_dump()}


@router.post("/games/{slug}/real-game", response_model=RealGameResponse)
def real_game(slug: str, body: RealGameRequest, svc=Depends(get_service)):
    try:
        result = svc.generate_real_game(slug, body.model_dump())
    except KeyError:
        raise HTTPException(404, "Game not found")
    except ValueError as e:
        raise HTTPException(422, str(e))

    out = []
    for g in result["jogos"]:
        validation = svc.validate(slug, g) if body.validar_resultado else None
        out.append(GeneratedGame(numbers=g, validation=validation))
    return {
        "games": out,
        "meta": body.model_dump(),
        "report": result["relatorio"],
    }
