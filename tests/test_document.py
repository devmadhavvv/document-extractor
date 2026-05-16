from fastapi.testclient import TestClient

from app.api.routes import document as document_route
from app.core.config import Settings
from app.main import create_app
from app.services.document_service import DocumentNotFoundError


def test_get_document_endpoint_returns_document_details(monkeypatch) -> None:
    async def fake_get_document_details(document_id: str):
        assert document_id == "doc-123"
        return {
            "document_id": "doc-123",
            "filename": "offer.pdf",
            "status": "SUCCESS",
            "extracted_json": {"employee_code": {"value": "E1", "confidence": 100}},
            "verified_json": None,
            "approved": False,
            "error_message": None,
        }

    monkeypatch.setattr(document_route, "get_document_details", fake_get_document_details)
    app = create_app(Settings(environment="test", cors_origins=["http://localhost:3000"]))
    response = TestClient(app).get("/document/doc-123")

    assert response.status_code == 200
    assert response.json()["document_id"] == "doc-123"
    assert response.json()["filename"] == "offer.pdf"


def test_get_document_endpoint_returns_404_when_missing(monkeypatch) -> None:
    async def fake_get_document_details(document_id: str):
        raise DocumentNotFoundError(f"Document not found: {document_id}")

    monkeypatch.setattr(document_route, "get_document_details", fake_get_document_details)
    app = create_app(Settings(environment="test", cors_origins=["http://localhost:3000"]))
    response = TestClient(app).get("/document/missing")

    assert response.status_code == 404
    assert "Document not found" in response.json()["detail"]


def test_approve_document_marks_as_approved(monkeypatch) -> None:
    async def fake_approve_document(document_id: str):
        assert document_id == "doc-123"
        return {
            "document_id": "doc-123",
            "filename": "offer.pdf",
            "status": "SUCCESS",
            "extracted_json": {"employee_code": {"value": "E1", "confidence": 100}},
            "verified_json": None,
            "approved": True,
            "approved_at": "2026-01-15T10:00:00+00:00",
            "error_message": None,
        }

    monkeypatch.setattr(document_route, "approve_document", fake_approve_document)
    app = create_app(Settings(environment="test", cors_origins=["http://localhost:3000"]))
    response = TestClient(app).post("/document/doc-123/approve")

    assert response.status_code == 200
    assert response.json()["approved"] is True
    assert response.json()["approved_at"] == "2026-01-15T10:00:00+00:00"


def test_approve_document_returns_404_when_missing(monkeypatch) -> None:
    async def fake_approve_document(document_id: str):
        raise DocumentNotFoundError(f"Document not found: {document_id}")

    monkeypatch.setattr(document_route, "approve_document", fake_approve_document)
    app = create_app(Settings(environment="test", cors_origins=["http://localhost:3000"]))
    response = TestClient(app).post("/document/missing/approve")

    assert response.status_code == 404
    assert "Document not found" in response.json()["detail"]


def test_patch_document_verification_updates_verified_json(monkeypatch) -> None:
    async def fake_update_document_verification(document_id: str, verified_json: dict):
        assert document_id == "doc-123"
        assert verified_json == {"candidate_name": {"value": "JOHN", "confidence": 99}}
        return {
            "document_id": "doc-123",
            "filename": "offer.pdf",
            "status": "SUCCESS",
            "extracted_json": {"candidate_name": {"value": "JOHN", "confidence": 90}},
            "verified_json": {"candidate_name": {"value": "JOHN", "confidence": 99}},
            "approved": False,
            "error_message": None,
        }

    monkeypatch.setattr(
        document_route,
        "update_document_verification",
        fake_update_document_verification,
    )
    app = create_app(Settings(environment="test", cors_origins=["http://localhost:3000"]))
    response = TestClient(app).patch(
        "/document/doc-123",
        json={"verified_json": {"candidate_name": {"value": "JOHN", "confidence": 99}}},
    )

    assert response.status_code == 200
    assert response.json()["document_id"] == "doc-123"
    assert response.json()["verified_json"]["candidate_name"]["confidence"] == 99
    assert response.json()["extracted_json"]["candidate_name"]["confidence"] == 90


def test_patch_document_verification_returns_404_when_missing(monkeypatch) -> None:
    async def fake_update_document_verification(document_id: str, verified_json: dict):
        raise DocumentNotFoundError(f"Document not found: {document_id}")

    monkeypatch.setattr(
        document_route,
        "update_document_verification",
        fake_update_document_verification,
    )
    app = create_app(Settings(environment="test", cors_origins=["http://localhost:3000"]))
    response = TestClient(app).patch(
        "/document/missing",
        json={"verified_json": {"field": {"value": "x", "confidence": 80}}},
    )

    assert response.status_code == 404
    assert "Document not found" in response.json()["detail"]
