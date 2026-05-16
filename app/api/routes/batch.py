"""Batch progress route."""

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse

from app.services.batch_service import (
    BatchApprovalError,
    BatchNotFoundError,
    BatchServiceError,
    _list_batch_documents_sync,
    approve_all_documents,
    get_batch_progress,
    list_batches,
)
from app.services.excel_export import ExcelExportError, export_approved_documents
from app.services.firestore_service import update_document

router = APIRouter()


@router.post("/batch/{batch_id}/upload", status_code=status.HTTP_201_CREATED)
async def upload_to_batch(
    batch_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
) -> dict[str, object]:
    """Upload additional PDFs to an existing batch."""
    from app.core.config import Settings, get_settings
    from app.services.background_processor import process_document_background
    from app.services.upload_service import (
        BatchNotFoundForUploadError,
        UploadProcessingError,
        UploadValidationError,
        add_files_to_batch,
    )

    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        settings = get_settings()

    try:
        response_payload, upload_jobs = await add_files_to_batch(batch_id, files, settings)
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
    except BatchNotFoundForUploadError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except UploadProcessingError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/batches")
async def get_batches() -> list[dict[str, object]]:
    """List all batches, latest first, with status counts."""
    try:
        return await list_batches()
    except BatchServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/batch/{batch_id}")
async def get_batch(batch_id: str) -> dict[str, object]:
    """Return batch progress details for frontend polling."""
    try:
        return await get_batch_progress(batch_id)
    except BatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BatchServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch batch progress",
        ) from exc


@router.post("/batch/{batch_id}/approve-all")
async def approve_all_batch_documents(batch_id: str) -> dict[str, object]:
    """Approve all eligible documents in a batch and generate Excel."""
    try:
        return await approve_all_documents(batch_id)
    except BatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BatchApprovalError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/batch/{batch_id}/download-excel")
async def download_batch_excel(batch_id: str) -> FileResponse:
    """Generate and download an Excel file of approved documents."""
    try:
        documents = _list_batch_documents_sync(batch_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch batch documents",
        ) from exc

    approved = [d for d in documents if d.get("approved")]
    if not approved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No approved documents in batch: {batch_id}",
        )

    try:
        file_path = export_approved_documents(approved)
    except ExcelExportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    await update_document(
        "batches",
        batch_id,
        {"excel_exported_at": datetime.now(UTC).isoformat()},
    )

    filename = Path(file_path).name
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )

