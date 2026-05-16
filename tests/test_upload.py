from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services import upload_service


def make_client(
    tmp_path: Path,
    monkeypatch,
    created_records: list[tuple[str, str | None, dict[str, object]]],
    max_size: int = 1024,
) -> TestClient:
    async def fake_create_document(
        collection_name: str,
        document_id: str | None,
        data: dict[str, object],
    ) -> dict[str, object]:
        created_records.append((collection_name, document_id, data))
        return {"id": document_id or "generated", **data}

    monkeypatch.setattr(upload_service, "create_document", fake_create_document)

    app = create_app(
        Settings(
            environment="test",
            cors_origins=["http://localhost:3000"],
            upload_temp_dir=str(tmp_path),
            max_upload_size_bytes=max_size,
        )
    )
    return TestClient(app)


def test_upload_multiple_pdfs_creates_batch_and_document_records(
    tmp_path: Path,
    monkeypatch,
) -> None:
    created_records: list[tuple[str, str | None, dict[str, object]]] = []
    client = make_client(tmp_path, monkeypatch, created_records)

    response = client.post(
        "/upload",
        files=[
            ("files", ("one.pdf", b"%PDF-1.4\none", "application/pdf")),
            ("files", ("two.pdf", b"%PDF-1.4\ntwo", "application/pdf")),
        ],
    )

    body = response.json()
    batch_id = body["batch_id"]

    assert response.status_code == 201
    assert len(body["uploaded_files"]) == 2
    assert body["uploaded_files"][0]["filename"] == "one.pdf"
    assert body["uploaded_files"][1]["filename"] == "two.pdf"
    assert (tmp_path / batch_id / "one.pdf").read_bytes() == b"%PDF-1.4\none"
    assert (tmp_path / batch_id / "two.pdf").read_bytes() == b"%PDF-1.4\ntwo"

    batch_records = [record for record in created_records if record[0] == "batches"]
    document_records = [record for record in created_records if record[0] == "documents"]

    assert len(batch_records) == 1
    assert batch_records[0][1] == batch_id
    assert batch_records[0][2]["batch_id"] == batch_id
    assert batch_records[0][2]["status"] == "QUEUED"
    assert batch_records[0][2]["total_files"] == 2
    assert batch_records[0][2]["completed_files"] == 0
    assert batch_records[0][2]["failed_files"] == 0

    assert len(document_records) == 2
    assert document_records[0][2]["batch_id"] == batch_id
    assert document_records[0][2]["filename"] == "one.pdf"
    assert document_records[0][2]["status"] == "QUEUED"
    assert document_records[0][2]["extracted_json"] is None
    assert document_records[0][2]["verified_json"] is None
    assert document_records[0][2]["approved"] is False
    assert document_records[0][2]["error_message"] is None


def test_upload_rejects_non_pdf(tmp_path: Path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch, [])

    response = client.post(
        "/upload",
        files=[("files", ("notes.txt", b"hello", "text/plain"))],
    )

    assert response.status_code == 400
    assert "Only PDF files are supported" in response.json()["detail"]


def test_upload_rejects_empty_pdf(tmp_path: Path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch, [])

    response = client.post(
        "/upload",
        files=[("files", ("empty.pdf", b"", "application/pdf"))],
    )

    assert response.status_code == 400
    assert "File is empty" in response.json()["detail"]


def test_upload_rejects_file_over_max_size(tmp_path: Path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch, [], max_size=8)

    response = client.post(
        "/upload",
        files=[("files", ("large.pdf", b"%PDF-1.4\nlarge", "application/pdf"))],
    )

    assert response.status_code == 400
    assert "exceeds maximum size" in response.json()["detail"]
