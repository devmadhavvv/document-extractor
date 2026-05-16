"""Document details route."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import FileResponse

from app.core.config import Settings, get_settings
from app.services.document_service import (
    DocumentNotFailedError,
    DocumentNotFoundError,
    DocumentRetryMissingFieldsError,
    approve_document,
    delete_single_document,
    get_document_details,
    retry_document,
    update_document_verification,
)

router = APIRouter()


class DocumentVerificationUpdateRequest(BaseModel):
    verified_json: dict[str, Any]


@router.get("/document/{document_id}")
async def get_document(document_id: str) -> dict[str, object]:
    """Return one document detail payload for frontend review UI."""
    try:
        return await get_document_details(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/document/{document_id}/approve")
async def approve_document_endpoint(document_id: str) -> dict[str, object]:
    """Mark a document as approved."""
    try:
        return await approve_document(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/document/{document_id}")
async def patch_document_verification(
    document_id: str,
    payload: DocumentVerificationUpdateRequest,
) -> dict[str, object]:
    """Save verified JSON separately while preserving extracted JSON."""
    try:
        return await update_document_verification(document_id, payload.verified_json)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/document/{document_id}/retry")
async def retry_document_endpoint(
    document_id: str,
    background_tasks: BackgroundTasks,
) -> dict[str, object]:
    """Reset a FAILED document to QUEUED and re-process it."""
    from app.services.background_processor import process_document_background

    try:
        info = await retry_document(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DocumentNotFailedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except DocumentRetryMissingFieldsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    settings = get_settings()
    background_tasks.add_task(
        process_document_background,
        info["batch_id"],
        info["document_id"],
        info["pdf_path"],
        info["filename"],
        settings,
    )

    return {"status": "QUEUED", "document_id": document_id, "batch_id": info["batch_id"]}


@router.delete("/document/{document_id}")
async def delete_document_endpoint(document_id: str) -> dict[str, object]:
    """Delete a single document and its PDF file."""
    try:
        await delete_single_document(document_id)
        return {"status": "deleted", "document_id": document_id}
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/document/{document_id}/pdf")
async def get_document_pdf(document_id: str) -> FileResponse:
    """Serve the uploaded PDF file for browser viewing."""
    try:
        details = await get_document_details(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    pdf_path: str | None = details.get("pdf_path")
    pdf_file: Path | None = None

    if pdf_path:
        candidate = Path(pdf_path)
        if candidate.is_file():
            pdf_file = candidate

    if pdf_file is None:
        settings = get_settings()
        batch_id = details.get("batch_id")
        filename = details.get("filename")
        if batch_id and filename:
            base_dir = Path(settings.upload_temp_dir) / batch_id
            candidates = [
                base_dir / filename,
                base_dir / f"{document_id}_{filename}",
            ]
            for candidate in candidates:
                if candidate.is_file():
                    pdf_file = candidate
                    break

    if pdf_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF file not found on disk",
        )

    return FileResponse(pdf_file, media_type="application/pdf", filename=details.get("filename"))
