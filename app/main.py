"""FastAPI application entrypoint."""

import asyncio
import logging
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.frontend import mount_frontend
from app.services.cleanup import clean_temp_files, run_periodic_cleanup

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings: Settings = app.state.settings

    Path(settings.upload_temp_dir).mkdir(parents=True, exist_ok=True)

    await asyncio.to_thread(
        clean_temp_files,
        temp_dir=settings.upload_temp_dir,
        max_age_hours=settings.cleanup_max_age_hours,
    )

    stop_event = asyncio.Event()
    cleanup_task = asyncio.create_task(
        run_periodic_cleanup(
            interval_seconds=settings.cleanup_interval_seconds,
            temp_dir=settings.upload_temp_dir,
            max_age_hours=settings.cleanup_max_age_hours,
            stop_event=stop_event,
        )
    )

    yield

    stop_event.set()
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    runtime_settings = settings or get_settings()

    application = FastAPI(
        title=runtime_settings.service_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.settings = runtime_settings
    configure_cors(application, runtime_settings.cors_origins)
    application.include_router(api_router, prefix=runtime_settings.api_prefix)

    if runtime_settings.frontend_dist_dir:
        mount_frontend(application, runtime_settings.frontend_dist_dir)

    return application


def configure_cors(application: FastAPI, allowed_origins: Sequence[str]) -> None:
    """Attach CORS middleware to the application."""
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


app = create_app()
