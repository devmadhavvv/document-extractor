import pytest

from app.services import firestore_service
from app.services.firestore_service import (
    ALLOWED_COLLECTIONS,
    FirestoreServiceError,
    create_document,
    get_document,
    list_documents,
    update_document,
)


class FakeSnapshot:
    def __init__(self, document_id: str, data: dict[str, object] | None) -> None:
        self.id = document_id
        self._data = data
        self.exists = data is not None

    def to_dict(self) -> dict[str, object] | None:
        return self._data


class FakeDocumentReference:
    def __init__(self, collection: "FakeCollectionReference", document_id: str) -> None:
        self.collection = collection
        self.id = document_id

    def set(self, data: dict[str, object]) -> None:
        self.collection.documents[self.id] = dict(data)

    def update(self, data: dict[str, object]) -> None:
        if self.id not in self.collection.documents:
            raise RuntimeError("missing document")
        self.collection.documents[self.id].update(data)

    def get(self) -> FakeSnapshot:
        return FakeSnapshot(self.id, self.collection.documents.get(self.id))


class FakeCollectionReference:
    def __init__(self) -> None:
        self.documents: dict[str, dict[str, object]] = {}

    def document(self, document_id: str | None = None) -> FakeDocumentReference:
        return FakeDocumentReference(self, document_id or "generated-id")

    def limit(self, count: int) -> "FakeQuery":
        return FakeQuery(self, count)

    def stream(self) -> list[FakeSnapshot]:
        return [
            FakeSnapshot(document_id, data)
            for document_id, data in self.documents.items()
        ]


class FakeQuery:
    def __init__(self, collection: FakeCollectionReference, count: int) -> None:
        self.collection = collection
        self.count = count

    def stream(self) -> list[FakeSnapshot]:
        return self.collection.stream()[: self.count]


class FakeFirestoreClient:
    def __init__(self) -> None:
        self.collections = {
            collection_name: FakeCollectionReference()
            for collection_name in ALLOWED_COLLECTIONS
        }

    def collection(self, collection_name: str) -> FakeCollectionReference:
        return self.collections[collection_name]


@pytest.fixture()
def fake_client(monkeypatch: pytest.MonkeyPatch) -> FakeFirestoreClient:
    client = FakeFirestoreClient()
    monkeypatch.setattr(firestore_service, "get_firestore_client", lambda: client)
    return client


@pytest.mark.anyio
async def test_create_get_update_and_list_documents(fake_client: FakeFirestoreClient) -> None:
    created = await create_document("batches", "batch-1", {"name": "May onboarding"})
    fetched = await get_document("batches", "batch-1")

    updated = await update_document("batches", "batch-1", {"status": "processing"})
    listed = await list_documents("batches")

    assert created == {"id": "batch-1", "name": "May onboarding"}
    assert fetched == {"id": "batch-1", "name": "May onboarding"}
    assert updated == {
        "id": "batch-1",
        "name": "May onboarding",
        "status": "processing",
    }
    assert listed == [updated]


@pytest.mark.anyio
async def test_get_document_returns_none_when_missing(fake_client: FakeFirestoreClient) -> None:
    assert await get_document("documents", "missing") is None


@pytest.mark.anyio
async def test_rejects_unsupported_collection(fake_client: FakeFirestoreClient) -> None:
    with pytest.raises(ValueError, match="Unsupported Firestore collection"):
        await create_document("users", "user-1", {"name": "Nope"})


@pytest.mark.anyio
async def test_wraps_firestore_errors(fake_client: FakeFirestoreClient) -> None:
    with pytest.raises(FirestoreServiceError, match="Failed to update document"):
        await update_document("documents", "missing", {"status": "failed"})
