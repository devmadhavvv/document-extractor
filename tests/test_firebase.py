import pytest

from app.core import firebase
from app.core.config import Settings
from app.core.firebase import FirebaseInitializationError, initialize_firebase


def test_initialize_firebase_requires_service_account_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(firebase.firebase_admin, "get_app", lambda: (_ for _ in ()).throw(ValueError()))

    with pytest.raises(FirebaseInitializationError, match="FIREBASE_CREDENTIALS_PATH"):
        initialize_firebase(Settings(firebase_credentials_path=None))


def test_initialize_firebase_uses_service_account_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}

    monkeypatch.setattr(firebase.firebase_admin, "get_app", lambda: (_ for _ in ()).throw(ValueError()))
    monkeypatch.setattr(
        firebase.credentials,
        "Certificate",
        lambda path: calls.setdefault("credential_path", path) or "credential",
    )

    def fake_initialize_app(credential: object, options: dict[str, object]) -> str:
        calls["credential"] = credential
        calls["options"] = options
        return "firebase-app"

    monkeypatch.setattr(firebase.firebase_admin, "initialize_app", fake_initialize_app)

    app = initialize_firebase(
        Settings(
            firebase_credentials_path="/secure/service-account.json",
            firebase_project_id="onboarding-dev",
            firebase_storage_bucket="onboarding-dev.appspot.com",
        )
    )

    assert app == "firebase-app"
    assert calls == {
        "credential_path": "/secure/service-account.json",
        "credential": "/secure/service-account.json",
        "options": {
            "projectId": "onboarding-dev",
            "storageBucket": "onboarding-dev.appspot.com",
        },
    }
