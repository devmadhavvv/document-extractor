import pytest
from fastapi.testclient import TestClient

from app.api.routes import batch as batch_route
from app.core.config import Settings
from app.main import create_app

from app.services import batch_service as bs
from app.services.batch_service import BatchApprovalError, BatchNotFoundError, approve_all_documents


def test_get_batch_progress_endpoint_returns_batch_data(
    monkeypatch,
) -> None:
    async def fake_get_batch_progress(batch_id: str):
        assert batch_id == "batch-123"
        return {
            "batch_id": "batch-123",
            "status": "AI_PROCESSING",
            "total_files": 2,
            "completed_files": 1,
            "failed_files": 0,
            "created_at": "2026-01-15T10:00:00+00:00",
            "status_counts": {"SUCCESS": 1, "AI_PROCESSING": 1},
            "documents": [
                {
                    "document_id": "doc-1",
                    "filename": "one.pdf",
                    "status": "SUCCESS",
                    "error_message": None,
                },
                {
                    "document_id": "doc-2",
                    "filename": "two.pdf",
                    "status": "AI_PROCESSING",
                    "error_message": None,
                },
            ],
        }

    monkeypatch.setattr(batch_route, "get_batch_progress", fake_get_batch_progress)
    app = create_app(Settings(environment="test", cors_origins=["http://localhost:3000"]))
    response = TestClient(app).get("/batch/batch-123")

    assert response.status_code == 200
    assert response.json()["batch_id"] == "batch-123"
    assert response.json()["created_at"] == "2026-01-15T10:00:00+00:00"
    assert response.json()["status_counts"] == {"SUCCESS": 1, "AI_PROCESSING": 1}
    assert len(response.json()["documents"]) == 2


def test_get_batch_progress_endpoint_returns_404_when_missing(
    monkeypatch,
) -> None:
    async def fake_get_batch_progress(batch_id: str):
        raise bs.BatchNotFoundError(f"Batch not found: {batch_id}")

    monkeypatch.setattr(batch_route, "get_batch_progress", fake_get_batch_progress)
    app = create_app(Settings(environment="test", cors_origins=["http://localhost:3000"]))
    response = TestClient(app).get("/batch/missing")

    assert response.status_code == 404
    assert "Batch not found" in response.json()["detail"]


def test_approve_all_approves_eligible_documents(monkeypatch) -> None:
    async def fake_approve_all(batch_id: str):
        assert batch_id == "batch-123"
        return {
            "batch_id": "batch-123",
            "total_documents": 3,
            "approved_count": 2,
            "skipped_count": 1,
            "excel_file_path": "temp/batch-123/onboarding_data_20260115_100000.xlsx",
        }

    monkeypatch.setattr(batch_route, "approve_all_documents", fake_approve_all)
    app = create_app(Settings(environment="test", cors_origins=["http://localhost:3000"]))
    response = TestClient(app).post("/batch/batch-123/approve-all")

    assert response.status_code == 200
    data = response.json()
    assert data["batch_id"] == "batch-123"
    assert data["approved_count"] == 2
    assert data["skipped_count"] == 1
    assert data["excel_file_path"] is not None


def test_approve_all_returns_404_when_batch_missing(monkeypatch) -> None:
    async def fake_approve_all(batch_id: str):
        raise BatchNotFoundError(f"Batch not found: {batch_id}")

    monkeypatch.setattr(batch_route, "approve_all_documents", fake_approve_all)
    app = create_app(Settings(environment="test", cors_origins=["http://localhost:3000"]))
    response = TestClient(app).post("/batch/missing/approve-all")

    assert response.status_code == 404
    assert "Batch not found" in response.json()["detail"]


def test_approve_all_skips_docs_without_verified_json(monkeypatch) -> None:
    async def fake_approve_all(batch_id: str):
        assert batch_id == "batch-123"
        return {
            "batch_id": "batch-123",
            "total_documents": 2,
            "approved_count": 0,
            "skipped_count": 2,
            "excel_file_path": None,
        }

    monkeypatch.setattr(batch_route, "approve_all_documents", fake_approve_all)
    app = create_app(Settings(environment="test", cors_origins=["http://localhost:3000"]))
    response = TestClient(app).post("/batch/batch-123/approve-all")

    assert response.status_code == 200
    data = response.json()
    assert data["approved_count"] == 0
    assert data["skipped_count"] == 2
    assert data["excel_file_path"] is None


@pytest.mark.anyio
async def test_approve_all_service_approves_eligible_only(monkeypatch) -> None:
    async def fake_get_document(collection: str, doc_id: str):
        if collection == "batches":
            return {"batch_id": "batch-123", "status": "SUCCESS"}
        return None

    update_calls: list[tuple[str, str, dict]] = []

    async def fake_update_document(collection: str, doc_id: str, data: dict):
        update_calls.append((collection, doc_id, data))

    def fake_list_sync(batch_id: str):
        return [
            {"document_id": "doc-1", "status": "SUCCESS", "verified_json": {"name": {"value": "A"}}, "filename": "a.pdf"},
            {"document_id": "doc-2", "status": "SUCCESS", "verified_json": None, "filename": "b.pdf"},
            {"document_id": "doc-3", "status": "FAILED", "verified_json": {"name": {"value": "C"}}, "filename": "c.pdf"},
        ]

    monkeypatch.setattr(bs, "get_document", fake_get_document)
    monkeypatch.setattr(bs, "update_document", fake_update_document)
    monkeypatch.setattr(bs, "_list_batch_documents_sync", fake_list_sync)
    monkeypatch.setattr(bs, "generate_onboarding_excel", lambda docs, batch_id: "/tmp/test.xlsx")

    result = await approve_all_documents("batch-123")

    assert result["total_documents"] == 3
    assert result["approved_count"] == 1
    assert result["skipped_count"] == 2
    assert result["excel_file_path"] == "/tmp/test.xlsx"
    assert len(update_calls) == 1
    assert update_calls[0][0] == "documents"
    assert update_calls[0][1] == "doc-1"
    assert update_calls[0][2]["approved"] is True
    assert "approved_at" in update_calls[0][2]


@pytest.mark.anyio
async def test_approve_all_service_raises_404_for_missing_batch(monkeypatch) -> None:
    async def fake_get_document(collection: str, doc_id: str):
        return None

    monkeypatch.setattr(bs, "get_document", fake_get_document)

    try:
        await approve_all_documents("missing")
        assert False, "Expected BatchNotFoundError"
    except BatchNotFoundError:
        pass


@pytest.mark.anyio
async def test_approve_all_service_returns_500_on_list_error(monkeypatch) -> None:
    async def fake_get_document(collection: str, doc_id: str):
        return {"batch_id": "batch-123"}

    monkeypatch.setattr(bs, "get_document", fake_get_document)
    monkeypatch.setattr(bs, "_list_batch_documents_sync", lambda batch_id: (_ for _ in ()).throw(Exception("DB down")))

    try:
        await approve_all_documents("batch-123")
        assert False, "Expected BatchApprovalError"
    except BatchApprovalError:
        pass


def test_approve_all_returns_500_on_service_error(monkeypatch) -> None:
    async def fake_approve_all(batch_id: str):
        raise BatchApprovalError("Failed to fetch batch documents")

    monkeypatch.setattr(batch_route, "approve_all_documents", fake_approve_all)
    app = create_app(Settings(environment="test", cors_origins=["http://localhost:3000"]))
    response = TestClient(app).post("/batch/batch-123/approve-all")

    assert response.status_code == 500
    assert "Failed to fetch batch documents" in response.json()["detail"]


def test_list_batches_endpoint_returns_batches_ordered(monkeypatch) -> None:
    async def fake_list_batches():
        return [
            {
                "batch_id": "batch-3",
                "status": "SUCCESS",
                "total_files": 5,
                "completed_files": 5,
                "failed_files": 0,
                "created_at": "2026-01-20T10:00:00+00:00",
                "status_counts": {"SUCCESS": 5},
            },
            {
                "batch_id": "batch-2",
                "status": "AI_PROCESSING",
                "total_files": 3,
                "completed_files": 2,
                "failed_files": 0,
                "created_at": "2026-01-18T10:00:00+00:00",
                "status_counts": {"SUCCESS": 2, "AI_PROCESSING": 1},
            },
            {
                "batch_id": "batch-1",
                "status": "FAILED",
                "total_files": 1,
                "completed_files": 0,
                "failed_files": 1,
                "created_at": "2026-01-15T10:00:00+00:00",
                "status_counts": {"FAILED": 1},
            },
        ]

    monkeypatch.setattr(batch_route, "list_batches", fake_list_batches)
    app = create_app(Settings(environment="test", cors_origins=["http://localhost:3000"]))
    response = TestClient(app).get("/batches")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["batch_id"] == "batch-3"
    assert data[1]["batch_id"] == "batch-2"
    assert data[2]["batch_id"] == "batch-1"
    assert data[0]["status_counts"] == {"SUCCESS": 5}
    assert data[2]["status_counts"] == {"FAILED": 1}


def test_list_batches_endpoint_handles_empty(monkeypatch) -> None:
    async def fake_list_batches():
        return []

    monkeypatch.setattr(batch_route, "list_batches", fake_list_batches)
    app = create_app(Settings(environment="test", cors_origins=["http://localhost:3000"]))
    response = TestClient(app).get("/batches")

    assert response.status_code == 200
    assert response.json() == []


def test_list_batches_returns_500_on_service_error(monkeypatch) -> None:
    async def fake_list_batches():
        raise bs.BatchServiceError("Failed to list batches")

    monkeypatch.setattr(batch_route, "list_batches", fake_list_batches)
    app = create_app(Settings(environment="test", cors_origins=["http://localhost:3000"]))
    response = TestClient(app).get("/batches")

    assert response.status_code == 500
    assert "Failed to list batches" in response.json()["detail"]


@pytest.mark.anyio
async def test_list_batches_service_includes_status_counts(monkeypatch) -> None:
    def fake_list_all_sync():
        return [
            {"batch_id": "b1", "status": "SUCCESS", "total_files": 2, "completed_files": 2, "failed_files": 0, "created_at": "2026-01-20T10:00:00+00:00"},
            {"batch_id": "b2", "status": "AI_PROCESSING", "total_files": 1, "completed_files": 0, "failed_files": 0, "created_at": "2026-01-18T10:00:00+00:00"},
        ]

    def fake_list_docs_sync(batch_id: str):
        if batch_id == "b1":
            return [
                {"document_id": "d1", "status": "SUCCESS"},
                {"document_id": "d2", "status": "SUCCESS"},
            ]
        return [{"document_id": "d3", "status": "QUEUED"}]

    monkeypatch.setattr(bs, "_list_all_batches_sync", fake_list_all_sync)
    monkeypatch.setattr(bs, "_list_batch_documents_sync", fake_list_docs_sync)

    result = await bs.list_batches()

    assert len(result) == 2
    assert result[0]["batch_id"] == "b1"
    assert result[0]["status_counts"] == {"SUCCESS": 2}
    assert result[1]["batch_id"] == "b2"
    assert result[1]["status_counts"] == {"QUEUED": 1}


@pytest.mark.anyio
async def test_list_batches_service_handles_list_error(monkeypatch) -> None:
    monkeypatch.setattr(bs, "_list_all_batches_sync", lambda: (_ for _ in ()).throw(Exception("DB down")))

    try:
        await bs.list_batches()
        assert False, "Expected BatchServiceError"
    except bs.BatchServiceError:
        pass
