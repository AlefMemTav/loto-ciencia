# app/api/routers/closures.py
from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_service
from app.api.schemas.closures import ClosuresRequest, ClosuresResponse

router = APIRouter(tags=["closures"])


@router.post("/games/{slug}/closures", response_model=ClosuresResponse)
def closures(slug: str, body: ClosuresRequest, svc=Depends(get_service)):
    try:
        res = svc.closures(slug, body.numeros_base, body.max_combinacoes)
    except KeyError:
        raise HTTPException(404, "Game not found")

    if isinstance(res, dict) and "erro" in res:
        raise HTTPException(422, res["erro"])
    return {"games": res}
