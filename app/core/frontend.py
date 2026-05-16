"""Mount built frontend dist as static files for production/Electron mode."""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)


def mount_frontend(app: FastAPI, dist_dir: str) -> None:
    """Serve the built Vue frontend from the backend.

    Must be called AFTER all API routes are registered so specific API
    paths match before this SPA catch-all. Handles SPA routing by
    returning index.html for any unmatched GET request.
    """
    dist = Path(dist_dir).resolve()
    if not dist.is_dir():
        logger.warning("Frontend dist not found at %s — skipping mount", dist_dir)
        return

    assets_dir = dist / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend_assets")
        logger.info("Mounted frontend assets from %s", assets_dir)

    index_path = dist / "index.html"
    if not index_path.is_file():
        logger.warning("Frontend index.html not found at %s", index_path)
        return

    @app.get("/")
    async def serve_index():
        return FileResponse(str(index_path))

    @app.api_route("/{path:path}", methods=["GET"])
    async def spa_fallback(path: str):
        file = (dist / path).resolve()
        if file.is_file() and str(file).startswith(str(dist)):
            return FileResponse(str(file))
        return FileResponse(str(index_path))

    logger.info("Frontend SPA mounted from %s", dist_dir)
