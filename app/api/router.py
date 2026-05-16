"""Top-level API router composition."""

from fastapi import APIRouter

from app.api.routes.batch import router as batch_router
from app.api.routes.document import router as document_router
from app.api.routes.health import router as health_router
from app.api.routes.export import router as export_router
from app.api.routes.upload import router as upload_router
from app.api.routes.settings import router as settings_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(upload_router, tags=["upload"])
api_router.include_router(batch_router, tags=["batch"])
api_router.include_router(document_router, tags=["document"])
api_router.include_router(export_router, tags=["export"])
api_router.include_router(settings_router, tags=["settings"])
