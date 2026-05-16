"""Batch progress retrieval, listing, and approval service."""

import asyncio
import logging
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from google.cloud.firestore_v1.base_query import FieldFilter

from app.core.firebase import get_firestore_client
from app.services.excel_generator import generate_onboarding_excel
from app.services.firestore_service import get_document, update_document

logger = logging.getLogger(__name__)


class BatchNotFoundError(ValueError):
    """Raised when a batch does not exist."""


class BatchApprovalError(RuntimeError):
    """Raised when batch approval fails."""


class BatchServiceError(RuntimeError):
    """Raised when batch progress retrieval fails."""


def _compute_status_counts(documents: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for doc in documents:
        counts[doc.get("status", "UNKNOWN")] += 1
    return dict(counts)


async def list_batches() -> list[dict[str, Any]]:
    """List all batches, latest first, each with document status counts."""
    try:
        batches = await asyncio.to_thread(_list_all_batches_sync)
    except Exception as exc:
        logger.exception("Failed to list batches", extra={"event": "batches_list_failed"})
        raise BatchServiceError("Failed to list batches") from exc

    result: list[dict[str, Any]] = []
    for batch in batches:
        try:
            documents = await asyncio.to_thread(_list_batch_documents_sync, batch["batch_id"])
        except Exception:
            documents = []

        result.append({
            "batch_id": batch["batch_id"],
            "status": batch.get("status"),
            "total_files": int(batch.get("total_files", 0)),
            "completed_files": int(batch.get("completed_files", 0)),
            "failed_files": int(batch.get("failed_files", 0)),
            "created_at": batch.get("created_at"),
            "status_counts": _compute_status_counts(documents),
        })

    return result


async def get_batch_progress(batch_id: str) -> dict[str, Any]:
    """Fetch batch-level progress plus per-document status details."""
    batch = await get_document("batches", batch_id)
    if batch is None:
        raise BatchNotFoundError(f"Batch not found: {batch_id}")

    try:
        documents = await asyncio.to_thread(_list_batch_documents_sync, batch_id)
    except Exception as exc:
        logger.exception(
            "Failed to list batch documents",
            extra={"event": "batch_documents_list_failed", "batch_id": batch_id},
        )
        raise BatchServiceError("Failed to fetch batch documents") from exc

    return {
        "batch_id": batch.get("batch_id", batch_id),
        "status": batch.get("status"),
        "total_files": int(batch.get("total_files", 0)),
        "completed_files": int(batch.get("completed_files", 0)),
        "failed_files": int(batch.get("failed_files", 0)),
        "created_at": batch.get("created_at"),
        "excel_exported_at": batch.get("excel_exported_at"),
        "status_counts": _compute_status_counts(documents),
        "documents": documents,
    }


async def approve_all_documents(batch_id: str) -> dict[str, Any]:
    """Approve all eligible documents in a batch and generate Excel.

    Only documents with status=SUCCESS and non-null verified_json
    are approved. Returns a summary of what was approved.
    """
    batch = await get_document("batches", batch_id)
    if batch is None:
        raise BatchNotFoundError(f"Batch not found: {batch_id}")

    try:
        documents = await asyncio.to_thread(_list_batch_documents_sync, batch_id)
    except Exception as exc:
        logger.exception(
            "Failed to list batch documents for approval",
            extra={"event": "batch_approval_list_failed", "batch_id": batch_id},
        )
        raise BatchApprovalError("Failed to fetch batch documents") from exc

    eligible = [
        doc
        for doc in documents
        if doc.get("status") == "SUCCESS" and doc.get("verified_json") is not None
    ]

    now = datetime.now(UTC).isoformat()
    approved_ids: list[str] = []
    for doc in eligible:
        doc_id = doc.get("document_id")
        if not doc_id:
            continue
        await update_document(
            "documents",
            doc_id,
            {
                "approved": True,
                "approved_at": now,
                "updated_at": now,
            },
        )
        approved_ids.append(doc_id)

    excel_path: str | None = None
    if approved_ids:
        try:
            excel_path = generate_onboarding_excel(eligible, batch_id)
        except Exception as exc:
            logger.exception(
                "Excel generation failed after batch approval",
                extra={"event": "batch_approval_excel_failed", "batch_id": batch_id},
            )

    total_docs = len(documents)
    skipped = total_docs - len(eligible)

    return {
        "batch_id": batch_id,
        "total_documents": total_docs,
        "approved_count": len(approved_ids),
        "skipped_count": skipped,
        "excel_file_path": excel_path,
    }


def _list_all_batches_sync() -> list[dict[str, Any]]:
    client = get_firestore_client()
    query = client.collection("batches").order_by("created_at", direction="DESCENDING")
    snapshots = query.stream()

    batches: list[dict[str, Any]] = []
    for snapshot in snapshots:
        data = snapshot.to_dict() or {}
        batches.append({
            "batch_id": data.get("batch_id", snapshot.id),
            "status": data.get("status"),
            "total_files": int(data.get("total_files", 0)),
            "completed_files": int(data.get("completed_files", 0)),
            "failed_files": int(data.get("failed_files", 0)),
            "created_at": data.get("created_at"),
        })
    return batches


def _list_batch_documents_sync(batch_id: str) -> list[dict[str, Any]]:
    client = get_firestore_client()
    query = client.collection("documents").where(
        filter=FieldFilter("batch_id", "==", batch_id)
    )
    snapshots = query.stream()

    documents: list[dict[str, Any]] = []
    for snapshot in snapshots:
        data = snapshot.to_dict() or {}
        documents.append(
            {
                "document_id": data.get("document_id", snapshot.id),
                "filename": data.get("filename"),
                "status": data.get("status"),
                "extracted_json": data.get("extracted_json"),
                "verified_json": data.get("verified_json"),
                "approved": bool(data.get("approved", False)),
                "approved_at": data.get("approved_at"),
                "error_message": data.get("error_message"),
            }
        )
    return documents
