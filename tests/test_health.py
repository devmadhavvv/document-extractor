from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_check_returns_service_metadata() -> None:
    app = create_app(
        Settings(
            service_name="Test Onboarding API",
            environment="test",
            cors_origins=["http://localhost:3000"],
        )
    )

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Test Onboarding API",
        "environment": "test",
    }

