"""Async-friendly Firestore document helpers."""

import asyncio
import logging
from collections.abc import Mapping
from typing import TypeAlias

from google.cloud.firestore_v1.base_query import FieldFilter

from app.core.firebase import get_firestore_client

logger = logging.getLogger(__name__)

FirestoreData: TypeAlias = dict[str, object]
FirestoreInput: TypeAlias = Mapping[str, object]

ALLOWED_COLLECTIONS = frozenset({"batches", "documents"})


class FirestoreServiceError(RuntimeError):
    """Raised when a Firestore document operation fails."""


def validate_collection_name(collection_name: str) -> None:
    """Ensure helpers only access known SaaS collections."""
    if collection_name not in ALLOWED_COLLECTIONS:
        allowed = ", ".join(sorted(ALLOWED_COLLECTIONS))
        raise ValueError(
            f"Unsupported Firestore collection '{collection_name}'. "
            f"Allowed collections: {allowed}."
        )


async def create_document(
    collection_name: str,
    document_id: str | None,
    data: FirestoreInput,
) -> FirestoreData:
    """Create or replace a Firestore document and return its stored data."""
    validate_collection_name(collection_name)

    try:
        return await asyncio.to_thread(
            _create_document_sync,
            collection_name,
            document_id,
            dict(data),
        )
    except Exception as exc:
        logger.exception("Failed to create document in Firestore")
        raise FirestoreServiceError("Failed to create document") from exc


async def update_document(
    collection_name: str,
    document_id: str,
    data: FirestoreInput,
) -> FirestoreData:
    """Update a Firestore document and return its stored data."""
    validate_collection_name(collection_name)

    try:
        return await asyncio.to_thread(
            _update_document_sync,
            collection_name,
            document_id,
            dict(data),
        )
    except Exception as exc:
        logger.exception("Failed to update document in Firestore")
        raise FirestoreServiceError("Failed to update document") from exc


async def get_document(collection_name: str, document_id: str) -> FirestoreData | None:
    """Fetch a Firestore document by ID."""
    validate_collection_name(collection_name)

    try:
        return await asyncio.to_thread(_get_document_sync, collection_name, document_id)
    except Exception as exc:
        logger.exception("Failed to get document from Firestore")
        raise FirestoreServiceError("Failed to get document") from exc


async def delete_document(
    collection_name: str,
    document_id: str,
) -> None:
    """Delete a Firestore document by ID."""
    validate_collection_name(collection_name)

    try:
        return await asyncio.to_thread(
            _delete_document_sync,
            collection_name,
            document_id,
        )
    except Exception as exc:
        logger.exception("Failed to delete document from Firestore")
        raise FirestoreServiceError("Failed to delete document") from exc


async def list_documents(
    collection_name: str,
    limit: int | None = None,
) -> list[FirestoreData]:
    """List documents in a Firestore collection."""
    validate_collection_name(collection_name)

    try:
        return await asyncio.to_thread(_list_documents_sync, collection_name, limit)
    except Exception as exc:
        logger.exception("Failed to list documents from Firestore")
        raise FirestoreServiceError("Failed to list documents") from exc


def _create_document_sync(
    collection_name: str,
    document_id: str | None,
    data: FirestoreData,
) -> FirestoreData:
    client = get_firestore_client()
    document_ref = client.collection(collection_name).document(document_id)
    document_ref.set(data)
    return _snapshot_to_document(document_ref.get())


def _update_document_sync(
    collection_name: str,
    document_id: str,
    data: FirestoreData,
) -> FirestoreData:
    client = get_firestore_client()
    document_ref = client.collection(collection_name).document(document_id)
    document_ref.update(data)
    return _snapshot_to_document(document_ref.get())


def _get_document_sync(collection_name: str, document_id: str) -> FirestoreData | None:
    client = get_firestore_client()
    snapshot = client.collection(collection_name).document(document_id).get()
    if not snapshot.exists:
        return None

    return _snapshot_to_document(snapshot)


def _delete_document_sync(
    collection_name: str,
    document_id: str,
) -> None:
    client = get_firestore_client()
    client.collection(collection_name).document(document_id).delete()


def _delete_documents_by_field_sync(
    collection_name: str,
    field_name: str,
    field_value: str,
) -> list[str]:
    client = get_firestore_client()
    query = client.collection(collection_name).where(
        filter=FieldFilter(field_name, "==", field_value),
    )
    snapshots = query.stream()
    deleted_ids: list[str] = []
    for snapshot in snapshots:
        snapshot.reference.delete()
        deleted_ids.append(snapshot.id)
    return deleted_ids


def _list_documents_sync(
    collection_name: str,
    limit: int | None,
) -> list[FirestoreData]:
    client = get_firestore_client()
    query = client.collection(collection_name)
    if limit is not None:
        query = query.limit(limit)

    return [_snapshot_to_document(snapshot) for snapshot in query.stream()]


def _snapshot_to_document(snapshot: object) -> FirestoreData:
    data = snapshot.to_dict()
    if data is None:
        data = {}

    return {"id": snapshot.id, **data}
