"""PDF upload validation, temp storage, and Firestore record creation."""

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeAlias

from fastapi import UploadFile
from firebase_admin import firestore

from app.core.config import Settings
from app.services.firestore_service import create_document, get_document, update_document

logger = logging.getLogger(__name__)

JsonObject: TypeAlias = dict[str, object]
UploadJob: TypeAlias = dict[str, str]
PDF_SIGNATURE = b"%PDF"
CHUNK_SIZE_BYTES = 1024 * 1024


class UploadValidationError(ValueError):
    """Raised when an uploaded file fails validation."""


class UploadProcessingError(RuntimeError):
    """Raised when upload processing fails unexpectedly."""


class BatchNotFoundForUploadError(ValueError):
    """Raised when trying to add files to a non-existent batch."""


async def process_pdf_uploads(
    files: list[UploadFile],
    settings: Settings,
) -> dict[str, object]:
    """Save PDFs, create records, and return API response payload."""
    response, _ = await process_pdf_uploads_with_jobs(files, settings)
    return response


async def add_files_to_batch(
    batch_id: str,
    files: list[UploadFile],
    settings: Settings,
) -> tuple[dict[str, object], list[UploadJob]]:
    """Add PDFs to an existing batch. Returns response payload and upload jobs."""
    if not files:
        raise UploadValidationError("At least one PDF file is required")

    existing = await get_document("batches", batch_id)
    if existing is None:
        raise BatchNotFoundForUploadError(f"Batch not found: {batch_id}")

    batch_dir = Path(settings.upload_temp_dir) / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)

    created_at = _utc_now()
    uploaded_files: list[dict[str, str]] = []
    upload_jobs: list[UploadJob] = []
    document_records: list[tuple[str, JsonObject]] = []

    try:
        for upload_file in files:
            document_id = uuid.uuid4().hex
            safe_filename = _safe_pdf_filename(upload_file.filename)
            destination = _unique_destination(batch_dir, safe_filename, document_id)
            await _save_valid_pdf(upload_file, destination, settings.max_upload_size_bytes)

            document_record: JsonObject = {
                "document_id": document_id,
                "batch_id": batch_id,
                "filename": safe_filename,
                "pdf_path": str(destination),
                "status": "QUEUED",
                "extracted_json": None,
                "verified_json": None,
                "approved": False,
                "error_message": None,
                "created_at": created_at,
            }
            document_records.append((document_id, document_record))
            uploaded_files.append({"document_id": document_id, "filename": safe_filename})
            upload_jobs.append({
                "batch_id": batch_id,
                "document_id": document_id,
                "pdf_path": str(destination),
                "original_pdf_filename": safe_filename,
            })

        for document_id, document_record in document_records:
            await create_document("documents", document_id, document_record)

        await update_document("batches", batch_id, {
            "total_files": firestore.Increment(len(files)),
            "status": "QUEUED",
        })
    except UploadValidationError:
        raise
    except Exception as exc:
        logger.exception("Failed to add files to batch")
        raise UploadProcessingError("Failed to add files to batch") from exc

    return {"batch_id": batch_id, "uploaded_files": uploaded_files}, upload_jobs


async def process_pdf_uploads_with_jobs(
    files: list[UploadFile],
    settings: Settings,
) -> tuple[dict[str, object], list[UploadJob]]:
    """Save PDFs temporarily and create Firestore batch/document records."""
    if not files:
        raise UploadValidationError("At least one PDF file is required")

    batch_id = uuid.uuid4().hex
    created_at = _utc_now()
    batch_dir = Path(settings.upload_temp_dir) / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)

    uploaded_files: list[dict[str, str]] = []
    upload_jobs: list[UploadJob] = []
    document_records: list[tuple[str, JsonObject]] = []

    try:
        for upload_file in files:
            document_id = uuid.uuid4().hex
            safe_filename = _safe_pdf_filename(upload_file.filename)
            destination = _unique_destination(batch_dir, safe_filename, document_id)
            await _save_valid_pdf(
                upload_file,
                destination,
                settings.max_upload_size_bytes,
            )

            document_record: JsonObject = {
                "document_id": document_id,
                "batch_id": batch_id,
                "filename": safe_filename,
                "pdf_path": str(destination),
                "status": "QUEUED",
                "extracted_json": None,
                "verified_json": None,
                "approved": False,
                "error_message": None,
                "created_at": created_at,
            }
            document_records.append((document_id, document_record))
            uploaded_files.append({"document_id": document_id, "filename": safe_filename})
            upload_jobs.append(
                {
                    "batch_id": batch_id,
                    "document_id": document_id,
                    "pdf_path": str(destination),
                    "original_pdf_filename": safe_filename,
                }
            )

        batch_record: JsonObject = {
            "batch_id": batch_id,
            "status": "QUEUED",
            "total_files": len(uploaded_files),
            "completed_files": 0,
            "failed_files": 0,
            "created_at": created_at,
        }

        await create_document("batches", batch_id, batch_record)
        for document_id, document_record in document_records:
            await create_document("documents", document_id, document_record)
    except UploadValidationError:
        raise
    except Exception as exc:
        logger.exception("Failed to process PDF upload batch")
        raise UploadProcessingError("Failed to process upload batch") from exc

    return {"batch_id": batch_id, "uploaded_files": uploaded_files}, upload_jobs


async def _save_valid_pdf(
    upload_file: UploadFile,
    destination: Path,
    max_size_bytes: int,
) -> None:
    total_size = 0
    first_chunk = True

    try:
        with destination.open("wb") as output_file:
            while True:
                chunk = await upload_file.read(CHUNK_SIZE_BYTES)
                if not chunk:
                    break

                if first_chunk:
                    first_chunk = False
                    if not chunk.startswith(PDF_SIGNATURE):
                        raise UploadValidationError("Only PDF files are supported")

                total_size += len(chunk)
                if total_size > max_size_bytes:
                    raise UploadValidationError(
                        f"File exceeds maximum size of {max_size_bytes} bytes"
                    )

                output_file.write(chunk)

        if total_size == 0:
            raise UploadValidationError("File is empty")
    except UploadValidationError:
        destination.unlink(missing_ok=True)
        raise


def _safe_pdf_filename(filename: str | None) -> str:
    if not filename:
        raise UploadValidationError("Filename is required")

    safe_name = Path(filename).name
    if not safe_name.lower().endswith(".pdf"):
        raise UploadValidationError("Only PDF files are supported")

    return safe_name


def _unique_destination(batch_dir: Path, filename: str, document_id: str) -> Path:
    destination = batch_dir / filename
    if not destination.exists():
        return destination

    return batch_dir / f"{document_id}_{filename}"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
