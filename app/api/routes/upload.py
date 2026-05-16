"""PDF upload route."""

import logging

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from fastapi import BackgroundTasks

from app.core.config import Settings, get_settings
from app.schemas.upload import UploadResponse
from app.services.background_processor import process_document_background
from app.services.upload_service import (
    UploadProcessingError,
    UploadValidationError,
    process_pdf_uploads_with_jobs,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_pdfs(
    request: Request,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
) -> dict[str, object]:
    """Upload multiple PDFs and create a Firestore processing batch."""
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        settings = get_settings()

    try:
        response_payload, upload_jobs = await process_pdf_uploads_with_jobs(files, settings)
        if settings.environment != "test":
            for upload_job in upload_jobs:
                background_tasks.add_task(
                    process_document_background,
                    upload_job["batch_id"],
                    upload_job["document_id"],
                    upload_job["pdf_path"],
                    upload_job["original_pdf_filename"],
                    settings,
                )
        return response_payload
    except UploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except UploadProcessingError as exc:
        logger.exception("Upload processing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process upload batch",
        ) from exc
