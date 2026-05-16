"""Firebase Admin SDK initialization helpers."""

import logging
from typing import Any

import firebase_admin
from firebase_admin import credentials, firestore, storage

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)
_firestore_client: firestore.Client | None = None


class FirebaseInitializationError(RuntimeError):
    """Raised when Firebase cannot be initialized from configured credentials."""


def initialize_firebase(settings: Settings | None = None) -> firebase_admin.App:
    """Initialize and return the Firebase application."""
    runtime_settings = settings or get_settings()

    try:
        return firebase_admin.get_app()
    except ValueError:
        pass

    options: dict[str, Any] = {}
    if runtime_settings.firebase_project_id:
        options["projectId"] = runtime_settings.firebase_project_id
    if runtime_settings.firebase_storage_bucket:
        options["storageBucket"] = runtime_settings.firebase_storage_bucket

    if not runtime_settings.firebase_credentials_path:
        raise FirebaseInitializationError(
            "FIREBASE_CREDENTIALS_PATH must point to a service account JSON file"
        )

    try:
        credential = credentials.Certificate(runtime_settings.firebase_credentials_path)
        app = firebase_admin.initialize_app(credential, options or None)
    except Exception:
        logger.exception("Failed to initialize Firebase Admin SDK")
        raise

    logger.info("Firebase Admin SDK initialized")
    return app


def get_firestore_client() -> firestore.Client:
    """Return a Firestore client using the initialized Firebase app."""
    global _firestore_client
    if _firestore_client is not None:
        return _firestore_client

    app = initialize_firebase()
    _firestore_client = firestore.client(app=app)
    return _firestore_client


def get_storage_bucket() -> storage.bucket:
    """Return the configured Firebase Storage bucket for future document uploads."""
    app = initialize_firebase()
    return storage.bucket(app=app)
