from pathlib import Path

import pytest

from app.core.config import Settings
from app.services import gemini_extractor
from app.services.gemini_extractor import GeminiExtractionError, extract_onboarding_json


@pytest.mark.anyio
async def test_extract_onboarding_json_retries_and_normalizes_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_path = tmp_path / "page-1.jpg"
    image_path.write_bytes(b"jpg")
    calls = {"count": 0}

    async def fake_call_gemini_generate_content(page_image_paths, settings):
        calls["count"] += 1
        if calls["count"] == 1:
            return "not-json"
        return """
        ```json
        {
          "candidate_name": {"value":"john doe","confidence":88},
          "father_name": {"value":"mark doe","confidence":77},
          "date_of_birth": {"value":"2000-12-31","confidence":80},
          "date_of_joining": {"value":"01-01-2025","confidence":79},
          "aadhaar_number": {"value":"1234 5678 9012","confidence":95},
          "pan_number": {"value":"abcde1234f","confidence":92},
          "bank_account_number": {"value":"0011223344","confidence":70},
          "ifsc_code": {"value":"hdfc0001234","confidence":66},
          "documents_found": ["Aadhaar", "PAN"],
          "cross_verification_notes": ["Marksheet name matches"],
          "overall_confidence": 83
        }
        ```
        """

    monkeypatch.setattr(
        gemini_extractor,
        "_call_gemini_generate_content",
        fake_call_gemini_generate_content,
    )

    settings = Settings(gemini_api_key="test-key", gemini_max_retries=2)
    result = await extract_onboarding_json(
        [str(image_path)],
        "emp-0099.pdf",
        settings=settings,
    )

    assert calls["count"] == 2
    assert result["employee_code"] == {"value": "emp-0099", "confidence": 100}
    assert result["candidate_name"]["value"] == "JOHN DOE"
    assert result["father_name"]["value"] == "MARK DOE"
    assert result["date_of_birth"]["value"] == "31/12/2000"
    assert result["date_of_joining"]["value"] == "01/01/2025"
    assert result["aadhaar_number"]["value"] == "123456789012"
    assert result["pan_number"]["value"] == "ABCDE1234F"
    assert result["ifsc_code"]["value"] == "HDFC0001234"
    assert result["overall_confidence"] == 83


@pytest.mark.anyio
async def test_extract_onboarding_json_rejects_invalid_pan_and_aadhaar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_path = tmp_path / "page-2.jpg"
    image_path.write_bytes(b"jpg")

    async def fake_call_gemini_generate_content(page_image_paths, settings):
        return """
        {
          "pan_number": {"value":"INVALIDPAN","confidence":90},
          "aadhaar_number": {"value":"1234","confidence":89}
        }
        """

    monkeypatch.setattr(
        gemini_extractor,
        "_call_gemini_generate_content",
        fake_call_gemini_generate_content,
    )

    settings = Settings(gemini_api_key="test-key")
    result = await extract_onboarding_json([str(image_path)], "x1.pdf", settings=settings)

    assert result["pan_number"] == {"value": None, "confidence": 0}
    assert result["aadhaar_number"] == {"value": None, "confidence": 0}


@pytest.mark.anyio
async def test_extract_onboarding_json_fails_after_retries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_path = tmp_path / "page-3.jpg"
    image_path.write_bytes(b"jpg")

    async def fake_call_gemini_generate_content(page_image_paths, settings):
        return "still invalid"

    monkeypatch.setattr(
        gemini_extractor,
        "_call_gemini_generate_content",
        fake_call_gemini_generate_content,
    )

    settings = Settings(gemini_api_key="test-key", gemini_max_retries=2)
    with pytest.raises(GeminiExtractionError, match="Failed to extract onboarding JSON"):
        await extract_onboarding_json([str(image_path)], "x2.pdf", settings=settings)
