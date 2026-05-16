import pytest

from app.core.config import Settings
from app.services import background_processor
from app.services.background_processor import process_document_background


@pytest.mark.anyio
async def test_process_document_background_success_updates_statuses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    update_calls: list[tuple[str, str, dict[str, object]]] = []

    async def fake_update_document(collection_name, document_id, data):
        update_calls.append((collection_name, document_id, data))
        return {"id": document_id, **data}

    async def fake_get_document(collection_name, document_id):
        assert collection_name == "batches"
        return {"id": document_id, "total_files": 1, "completed_files": 1, "failed_files": 0}

    async def fake_convert_pdf_to_images(pdf_path, temp_dir):
        return [{"page_number": 1, "image_path": "/tmp/page-1.jpg"}]

    async def fake_extract_onboarding_json(page_image_paths, original_pdf_filename, settings):
        return {"employee_code": {"value": "E1", "confidence": 100}, "overall_confidence": 88}

    monkeypatch.setattr(background_processor, "update_document", fake_update_document)
    monkeypatch.setattr(background_processor, "get_document", fake_get_document)
    monkeypatch.setattr(background_processor, "convert_pdf_to_images", fake_convert_pdf_to_images)
    monkeypatch.setattr(background_processor, "extract_onboarding_json", fake_extract_onboarding_json)

    await process_document_background(
        batch_id="batch-1",
        document_id="doc-1",
        pdf_path="/tmp/file.pdf",
        original_pdf_filename="file.pdf",
        settings=Settings(gemini_api_key="test-key"),
    )

    assert any(
        call[0] == "documents" and call[2].get("status") == "PDF_CONVERSION"
        for call in update_calls
    )
    assert any(
        call[0] == "documents" and call[2].get("status") == "AI_PROCESSING"
        for call in update_calls
    )
    assert any(call[0] == "documents" and call[2].get("status") == "SUCCESS" for call in update_calls)
    assert any(call[0] == "batches" and call[2].get("status") == "SUCCESS" for call in update_calls)


@pytest.mark.anyio
async def test_process_document_background_failure_marks_failed_and_updates_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    update_calls: list[tuple[str, str, dict[str, object]]] = []

    async def fake_update_document(collection_name, document_id, data):
        update_calls.append((collection_name, document_id, data))
        return {"id": document_id, **data}

    async def fake_get_document(collection_name, document_id):
        return {"id": document_id, "total_files": 1, "completed_files": 0, "failed_files": 1}

    async def fake_convert_pdf_to_images(pdf_path, temp_dir):
        raise RuntimeError("conversion failed")

    monkeypatch.setattr(background_processor, "update_document", fake_update_document)
    monkeypatch.setattr(background_processor, "get_document", fake_get_document)
    monkeypatch.setattr(background_processor, "convert_pdf_to_images", fake_convert_pdf_to_images)

    await process_document_background(
        batch_id="batch-2",
        document_id="doc-2",
        pdf_path="/tmp/file.pdf",
        original_pdf_filename="file.pdf",
        settings=Settings(gemini_api_key="test-key"),
    )

    assert any(call[0] == "documents" and call[2].get("status") == "FAILED" for call in update_calls)
    assert any(call[0] == "batches" and call[2].get("status") == "FAILED" for call in update_calls)
