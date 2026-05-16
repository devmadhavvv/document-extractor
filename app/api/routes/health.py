"""Health check route."""

from fastapi import APIRouter, Request

from app.core.config import Settings, get_settings

router = APIRouter()


@router.get("/health")
async def health_check(request: Request) -> dict[str, str]:
    """Return service health metadata."""
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        settings = get_settings()

    return {
        "status": "ok",
        "service": settings.service_name,
        "environment": settings.environment,
    }
