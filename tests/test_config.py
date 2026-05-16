from app.core.config import Settings


def test_settings_parse_comma_separated_cors_origins() -> None:
    settings = Settings(cors_origins="http://localhost:3000, https://example.com")

    assert settings.cors_origins == ["http://localhost:3000", "https://example.com"]

