"""Document details retrieval service."""

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.services.firestore_service import (
    delete_document,
    get_document,
    update_document,
)

logger = logging.getLogger(__name__)


class DocumentNotFoundError(ValueError):
    """Raised when a document record does not exist."""


class DocumentNotFailedError(ValueError):
    """Raised when retrying a document that is not in FAILED status."""


class DocumentRetryMissingFieldsError(ValueError):
    """Raised when a FAILED document is missing pdf_path or batch_id."""


def _format_document_response(document: dict[str, Any], document_id: str) -> dict[str, Any]:
    return {
        "document_id": document.get("document_id", document_id),
        "batch_id": document.get("batch_id"),
        "filename": document.get("filename"),
        "pdf_path": document.get("pdf_path"),
        "status": document.get("status"),
        "extracted_json": document.get("extracted_json"),
        "verified_json": document.get("verified_json"),
        "approved": bool(document.get("approved", False)),
        "approved_at": document.get("approved_at"),
        "error_message": document.get("error_message"),
    }


async def get_document_details(document_id: str) -> dict[str, Any]:
    """Fetch one document detail payload for the review UI."""
    document = await get_document("documents", document_id)
    if document is None:
        raise DocumentNotFoundError(f"Document not found: {document_id}")

    return _format_document_response(document, document_id)


async def approve_document(document_id: str) -> dict[str, Any]:
    """Mark a document as approved with a timestamp."""
    existing = await get_document("documents", document_id)
    if existing is None:
        raise DocumentNotFoundError(f"Document not found: {document_id}")

    if existing.get("approved"):
        return _format_document_response(existing, document_id)

    updated = await update_document(
        "documents",
        document_id,
        {
            "approved": True,
            "approved_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        },
    )
    return _format_document_response(updated, document_id)


async def update_document_verification(
    document_id: str,
    verified_json: dict[str, Any],
) -> dict[str, Any]:
    """Update review payload while preserving extracted_json."""
    existing = await get_document("documents", document_id)
    if existing is None:
        raise DocumentNotFoundError(f"Document not found: {document_id}")

    updated = await update_document(
        "documents",
        document_id,
        {
            "verified_json": verified_json,
            "updated_at": datetime.now(UTC).isoformat(),
        },
    )
    return _format_document_response(updated, document_id)


async def delete_single_document(document_id: str) -> None:
    """Delete a document record and its PDF file from disk."""
    existing = await get_document("documents", document_id)
    if existing is None:
        raise DocumentNotFoundError(f"Document not found: {document_id}")

    pdf_path: str | None = existing.get("pdf_path")
    if pdf_path:
        pdf_file = Path(pdf_path)
        if pdf_file.is_file():
            try:
                pdf_file.unlink()
            except OSError as exc:
                logger.warning(
                    "Failed to delete PDF file %s: %s", pdf_path, exc,
                )

    await delete_document("documents", document_id)

    batch_id = existing.get("batch_id")
    if batch_id:
        try:
            from app.services.firestore_service import get_document as get_batch

            batch = await get_batch("batches", batch_id)
            if batch:
                total = int(batch.get("total_files", 0))
                completed = int(batch.get("completed_files", 0))
                failed = int(batch.get("failed_files", 0))
                old_status = batch.get("status")
                decrement = max(total - 1, 0)
                new_completed = max(completed - 1, 0)
                new_failed = max(failed - 1, 0)
                await update_document("batches", batch_id, {
                    "total_files": decrement,
                    "completed_files": new_completed,
                    "failed_files": new_failed,
                })
                if decrement == 0 and old_status in ("SUCCESS", "FAILED"):
                    from datetime import UTC, datetime
                    await update_document("batches", batch_id, {
                        "status": "COMPLETED" if old_status == "SUCCESS" else "FAILED",
                        "completed_files": 0,
                        "failed_files": 0,
                    })
        except Exception as exc:
            logger.warning(
                "Failed to update batch counters after doc delete: %s", exc,
            )


async def retry_document(document_id: str) -> dict[str, Any]:
    """Reset a FAILED document to QUEUED and return processing info.

    Returns dict with batch_id, document_id, pdf_path, filename needed for
    background processing.
    """
    existing = await get_document("documents", document_id)
    if existing is None:
        raise DocumentNotFoundError(f"Document not found: {document_id}")

    if existing.get("status") != "FAILED":
        raise DocumentNotFailedError(f"Document {document_id} is not in FAILED status")

    pdf_path = existing.get("pdf_path")
    batch_id = existing.get("batch_id")
    filename = existing.get("filename")

    if not pdf_path or not batch_id:
        raise DocumentRetryMissingFieldsError(
            f"Document {document_id} is missing pdf_path or batch_id"
        )

    await update_document(
        "documents",
        document_id,
        {
            "status": "QUEUED",
            "error_message": None,
            "extracted_json": None,
            "verified_json": None,
            "approved": False,
            "updated_at": datetime.now(UTC).isoformat(),
        },
    )

    batch = await get_document("batches", batch_id)
    if batch:
        current_failed = int(batch.get("failed_files", 0))
        current_completed = int(batch.get("completed_files", 0))
        await update_document("batches", batch_id, {
            "failed_files": max(current_failed - 1, 0),
            "status": "QUEUED",
        })

    return {
        "document_id": document_id,
        "batch_id": batch_id,
        "pdf_path": pdf_path,
        "filename": filename,
    }
