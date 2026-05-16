from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.gemini_extractor import get_active_model, set_active_model

router = APIRouter()


class ModelUpdate(BaseModel):
    model: str


@router.get("/settings/model")
async def get_model() -> dict[str, str]:
    settings = get_settings()
    active = get_active_model() or settings.gemini_model
    return {"model": active}


@router.patch("/settings/model")
async def update_model(payload: ModelUpdate) -> dict[str, str]:
    set_active_model(payload.model)
    return {"model": payload.model}
