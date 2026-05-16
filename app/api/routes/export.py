"""Excel export route."""

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.services.batch_service import _list_batch_documents_sync
from app.services.excel_export import ExcelExportError, export_approved_documents

router = APIRouter()


@router.get("/export/{batch_id}")
async def export_batch_excel(batch_id: str):
    """Generate and download an Excel file of approved documents in a batch."""
    try:
        documents = await asyncio.to_thread(_list_batch_documents_sync, batch_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch batch documents",
        ) from exc

    approved = [d for d in documents if d.get("approved")]

    if not approved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No approved documents found in batch: {batch_id}",
        )

    try:
        file_path = export_approved_documents(approved)
    except ExcelExportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    filename = Path(file_path).name
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )
