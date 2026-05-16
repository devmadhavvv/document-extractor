"""Document details retrieval service."""

from datetime import UTC, datetime
from typing import Any

from app.services.firestore_service import get_document, update_document


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

    return {
        "document_id": document_id,
        "batch_id": batch_id,
        "pdf_path": pdf_path,
        "filename": filename,
    }
