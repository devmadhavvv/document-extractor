"""Background document processing pipeline."""

import logging
from typing import Any

from firebase_admin import firestore

from app.core.config import Settings, get_settings
from app.services.firestore_service import get_document, update_document
from app.services.gemini_extractor import extract_onboarding_json
from app.services.pdf_converter import convert_pdf_to_images

logger = logging.getLogger(__name__)

STATUS_QUEUED = "QUEUED"
STATUS_PDF_CONVERSION = "PDF_CONVERSION"
STATUS_AI_PROCESSING = "AI_PROCESSING"
STATUS_SUCCESS = "SUCCESS"
STATUS_FAILED = "FAILED"


async def process_document_background(
    batch_id: str,
    document_id: str,
    pdf_path: str,
    original_pdf_filename: str,
    settings: Settings | None = None,
) -> None:
    """Run PDF conversion and Gemini extraction for one document."""
    runtime_settings = settings or get_settings()
    success = False
    error_message: str | None = None

    try:
        await update_document(
            "documents",
            document_id,
            {"status": STATUS_PDF_CONVERSION, "error_message": None},
        )

        page_images = await convert_pdf_to_images(
            pdf_path=pdf_path,
            temp_dir=runtime_settings.upload_temp_dir,
        )
        page_paths = [str(page_image["image_path"]) for page_image in page_images]

        await update_document(
            "documents",
            document_id,
            {"status": STATUS_AI_PROCESSING},
        )

        extracted_json = await extract_onboarding_json(
            page_image_paths=page_paths,
            original_pdf_filename=original_pdf_filename,
            settings=runtime_settings,
        )

        await update_document(
            "documents",
            document_id,
            {
                "status": STATUS_SUCCESS,
                "extracted_json": extracted_json,
                "error_message": None,
            },
        )
        success = True
        logger.info(
            "Document processing completed",
            extra={
                "event": "document_processing_success",
                "batch_id": batch_id,
                "document_id": document_id,
            },
        )
    except Exception as exc:
        error_message = str(exc)
        logger.exception(
            "Document processing failed",
            extra={
                "event": "document_processing_failed",
                "batch_id": batch_id,
                "document_id": document_id,
            },
        )
        await _safe_mark_failed(document_id, error_message)
    finally:
        await _update_batch_progress(batch_id=batch_id, success=success)


async def _safe_mark_failed(document_id: str, error_message: str | None) -> None:
    try:
        await update_document(
            "documents",
            document_id,
            {
                "status": STATUS_FAILED,
                "error_message": error_message,
            },
        )
    except Exception:
        logger.exception(
            "Failed to persist document failure status",
            extra={
                "event": "document_failure_persist_failed",
                "document_id": document_id,
            },
        )


async def _update_batch_progress(batch_id: str, success: bool) -> None:
    increment_key = "completed_files" if success else "failed_files"
    increment_payload: dict[str, Any] = {
        increment_key: firestore.Increment(1),
        "status": STATUS_AI_PROCESSING,
    }
    await update_document("batches", batch_id, increment_payload)

    batch = await get_document("batches", batch_id)
    if batch is None:
        return

    total = int(batch.get("total_files", 0))
    completed = int(batch.get("completed_files", 0))
    failed = int(batch.get("failed_files", 0))
    processed = completed + failed

    if processed < total:
        return

    final_status = STATUS_SUCCESS if failed == 0 else STATUS_FAILED
    await update_document("batches", batch_id, {"status": final_status})

