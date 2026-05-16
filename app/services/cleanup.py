"""Temp file cleanup service to prevent disk growth on free-tier hosts."""

import asyncio
import logging
import time
from pathlib import Path

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


def _is_older_than(path: Path, max_age_seconds: int) -> bool:
    try:
        mtime = path.stat().st_mtime
        return (time.time() - mtime) > max_age_seconds
    except OSError:
        return False


def _remove_path(path: Path) -> None:
    try:
        if path.is_file():
            path.unlink()
            logger.debug("Deleted temp file", extra={"path": str(path)})
        elif path.is_dir():
            for child in path.iterdir():
                _remove_path(child)
            path.rmdir()
            logger.debug("Deleted temp dir", extra={"path": str(path)})
    except OSError as exc:
        logger.warning(
            "Failed to remove temp path",
            extra={"path": str(path), "error": str(exc)},
        )


def clean_temp_files(
    temp_dir: str = "temp",
    max_age_hours: float = 1,
) -> int:
    """Delete temp files and folders older than max_age_hours.

    Returns the number of items removed.
    """
    root = Path(temp_dir)
    if not root.exists():
        return 0

    max_age_seconds = int(max_age_hours * 3600)
    now = time.time()
    removed = 0

    for entry in root.iterdir():
        if not entry.is_dir():
            continue

        if entry.name.startswith("pdf-images-"):
            if _is_older_than(entry, max_age_seconds):
                age_hours = round((now - entry.stat().st_mtime) / 3600, 2)
                items = sum(1 for _ in entry.rglob("*"))
                _remove_path(entry)
                removed += items + 1
                logger.info(
                    "Cleaned pdf-images dir",
                    extra={"path": str(entry), "age_hours": age_hours},
                )
            continue

        if entry.name == "exports":
            for child in entry.iterdir():
                if child.is_file() and child.suffix == ".xlsx" and _is_older_than(child, max_age_seconds):
                    child.unlink()
                    removed += 1
                    logger.debug("Cleaned exported Excel", extra={"path": str(child)})
            if not any(entry.iterdir()):
                entry.rmdir()
                removed += 1
            continue

        if entry.name == "exports":
            continue

        batch_files_removed = 0
        for child in entry.iterdir():
            if _is_older_than(child, max_age_seconds):
                _remove_path(child)
                batch_files_removed += 1

        if batch_files_removed > 0:
            logger.info(
                "Cleaned batch temp dir",
                extra={"path": str(entry), "files_removed": batch_files_removed},
            )
            removed += batch_files_removed

        if not any(entry.iterdir()):
            entry.rmdir()
            removed += 1

    return removed


async def run_periodic_cleanup(
    interval_seconds: int = 3600,
    temp_dir: str = "temp",
    max_age_hours: float = 1,
    stop_event: asyncio.Event | None = None,
) -> None:
    """Run temp file cleanup on a loop until stop_event is set."""
    logger.info(
        "Periodic cleanup started",
        extra={
            "event": "cleanup_started",
            "interval_seconds": interval_seconds,
            "max_age_hours": max_age_hours,
        },
    )
    while True:
        try:
            removed = await asyncio.to_thread(
                clean_temp_files,
                temp_dir=temp_dir,
                max_age_hours=max_age_hours,
            )
            if removed:
                logger.info(
                    "Periodic cleanup completed",
                    extra={"event": "cleanup_completed", "items_removed": removed},
                )
        except Exception:
            logger.exception("Periodic cleanup failed", extra={"event": "cleanup_failed"})

        if stop_event:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
                break
            except TimeoutError:
                pass
        else:
            await asyncio.sleep(interval_seconds)

    logger.info("Periodic cleanup stopped", extra={"event": "cleanup_stopped"})
