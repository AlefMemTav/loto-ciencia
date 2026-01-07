# app/api/routers/generator.py
from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_service
from app.api.schemas.generator import GenerateRequest, GenerateResponse, GeneratedGame

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
        out.append(GeneratedGame(numbers=g, validation=svc.validate(slug, g)))
    return {"games": out, "meta": body.model_dump()}
