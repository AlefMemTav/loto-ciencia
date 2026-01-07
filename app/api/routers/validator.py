# app/api/routers/validator.py
from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_service
from app.api.schemas.validator import ValidateRequest, ValidateResponse

router = APIRouter(tags=["validator"])


@router.post("/games/{slug}/validate", response_model=ValidateResponse)
def validate(slug: str, body: ValidateRequest, svc=Depends(get_service)):
    try:
        result = svc.validate(slug, body.numbers)
    except KeyError:
        raise HTTPException(404, "Game not found")
    return result
