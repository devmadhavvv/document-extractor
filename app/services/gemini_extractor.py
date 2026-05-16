"""Gemini Vision onboarding extraction service."""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

JSONField = dict[str, Any]

FIELD_NAMES = (
    "employee_code",
    "candidate_name",
    "father_name",
    "date_of_birth",
    "date_of_joining",
    "aadhaar_number",
    "pan_number",
    "gender",
    "marital_status",
    "address",
    "bank_account_number",
    "ifsc_code",
)

PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
AADHAAR_REGEX = re.compile(r"^[0-9]{12}$")


class GeminiExtractionError(RuntimeError):
    """Raised when Gemini extraction fails after retries."""


async def extract_onboarding_json(
    page_image_paths: list[str],
    original_pdf_filename: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Extract onboarding fields from PDF page images using Gemini Vision."""
    runtime_settings = settings or get_settings()
    if not runtime_settings.gemini_api_key:
        raise GeminiExtractionError("GEMINI_API_KEY is required for Gemini extraction")
    if not page_image_paths:
        raise GeminiExtractionError("At least one page image path is required")

    logger.info(
        "Starting Gemini onboarding extraction",
        extra={
            "event": "gemini_extraction_start",
            "image_count": len(page_image_paths),
            "model": runtime_settings.gemini_model,
        },
    )

    last_error: Exception | None = None
    for attempt in range(1, runtime_settings.gemini_max_retries + 1):
        try:
            raw_text = await _call_gemini_generate_content(
                page_image_paths=page_image_paths,
                settings=runtime_settings,
            )
            parsed = _parse_json_response(raw_text)
            normalized = _normalize_output(parsed, original_pdf_filename)
            logger.info(
                "Gemini onboarding extraction succeeded",
                extra={
                    "event": "gemini_extraction_success",
                    "attempt": attempt,
                    "overall_confidence": normalized["overall_confidence"],
                },
            )
            return normalized
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Gemini extraction attempt failed",
                extra={
                    "event": "gemini_extraction_retry",
                    "attempt": attempt,
                    "max_retries": runtime_settings.gemini_max_retries,
                    "error_type": exc.__class__.__name__,
                },
            )
            if attempt == runtime_settings.gemini_max_retries:
                break

    logger.exception(
        "Gemini extraction failed after retries",
        extra={
            "event": "gemini_extraction_failed",
            "max_retries": runtime_settings.gemini_max_retries,
        },
    )
    raise GeminiExtractionError("Failed to extract onboarding JSON from Gemini") from last_error


async def _call_gemini_generate_content(
    page_image_paths: list[str],
    settings: Settings,
) -> str:
    api_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    parts: list[dict[str, Any]] = [{"text": _build_prompt()}]
    for image_path in page_image_paths:
        path = Path(image_path)
        if not path.exists():
            raise GeminiExtractionError(f"Image path does not exist: {image_path}")
        mime_type = _guess_mime_type(path)
        parts.append(
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": path.read_bytes().hex(),
                }
            }
        )

    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }

    payload = _replace_hex_with_base64(payload)

    async with httpx.AsyncClient(timeout=settings.gemini_request_timeout_seconds) as client:
        response = await client.post(
            api_url,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": settings.gemini_api_key,
            },
            json=payload,
        )

    if response.status_code >= 400:
        response_text = response.text
        raise GeminiExtractionError(
            f"Gemini API request failed with status {response.status_code}: {response_text}"
        )

    response_json = response.json()
    candidates = response_json.get("candidates", [])
    if not candidates:
        raise GeminiExtractionError("Gemini response did not include candidates")

    parts = candidates[0].get("content", {}).get("parts", [])
    text_chunks = [part.get("text", "") for part in parts if part.get("text")]
    raw_text = "\n".join(text_chunks).strip()
    if not raw_text:
        raise GeminiExtractionError("Gemini response text is empty")

    return raw_text


def _build_prompt() -> str:
    return (
        "Extract onboarding details from provided document images. "
        "Return STRICT JSON only, no markdown, no explanation. "
        "Use null for missing fields. "
        "Use Aadhaar card as primary source for candidate identity details and address. "
        "Ignore marksheets except for cross-verification notes. "
        "Employee code must come from filename stem. "
        "candidate_name and father_name must be uppercase. "
        "date_of_birth and date_of_joining must be DD/MM/YYYY. "
        "Extract handwritten date_of_joining carefully. "
        "Extract bank account_number and ifsc_code. "
        "Validate PAN format ABCDE1234F and Aadhaar as 12 digits. "
        "Every field must include value and confidence (0-100). "
        "Output keys must exactly match required schema."
    )


def _replace_hex_with_base64(payload: dict[str, Any]) -> dict[str, Any]:
    import base64

    parts = payload["contents"][0]["parts"]
    for part in parts:
        inline_data = part.get("inline_data")
        if inline_data:
            inline_data["data"] = base64.b64encode(bytes.fromhex(inline_data["data"])).decode()
    return payload


def _guess_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    return "image/jpeg"


def _parse_json_response(raw_text: str) -> dict[str, Any]:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]

    return json.loads(cleaned)


def _normalize_output(raw: dict[str, Any], original_pdf_filename: str) -> dict[str, Any]:
    result: dict[str, Any] = _default_output()
    for field in FIELD_NAMES:
        result[field] = _normalize_field(raw.get(field))

    employee_code = Path(original_pdf_filename).stem
    result["employee_code"] = {"value": employee_code, "confidence": 100}

    result["candidate_name"] = _uppercase_field(result["candidate_name"])
    result["father_name"] = _uppercase_field(result["father_name"])
    result["date_of_birth"] = _normalize_date_field(result["date_of_birth"])
    result["date_of_joining"] = _normalize_date_field(result["date_of_joining"])
    result["pan_number"] = _normalize_pan_field(result["pan_number"])
    result["aadhaar_number"] = _normalize_aadhaar_field(result["aadhaar_number"])
    result["ifsc_code"] = _uppercase_field(result["ifsc_code"])

    result["documents_found"] = _normalize_string_list(raw.get("documents_found"))
    result["cross_verification_notes"] = _normalize_string_list(
        raw.get("cross_verification_notes")
    )
    result["overall_confidence"] = _normalize_overall_confidence(
        raw.get("overall_confidence"),
        result,
    )
    return result


def _default_output() -> dict[str, Any]:
    return {
        "employee_code": {"value": None, "confidence": 100},
        "candidate_name": {"value": None, "confidence": 0},
        "father_name": {"value": None, "confidence": 0},
        "date_of_birth": {"value": None, "confidence": 0},
        "date_of_joining": {"value": None, "confidence": 0},
        "aadhaar_number": {"value": None, "confidence": 0},
        "pan_number": {"value": None, "confidence": 0},
        "gender": {"value": None, "confidence": 0},
        "marital_status": {"value": None, "confidence": 0},
        "address": {"value": None, "confidence": 0},
        "bank_account_number": {"value": None, "confidence": 0},
        "ifsc_code": {"value": None, "confidence": 0},
        "documents_found": [],
        "cross_verification_notes": [],
        "overall_confidence": 0,
    }


def _normalize_field(value: Any) -> JSONField:
    if not isinstance(value, dict):
        if value is None:
            return {"value": None, "confidence": 0}
        return {"value": str(value), "confidence": 0}

    field_value = value.get("value")
    confidence = _clamp_confidence(value.get("confidence", 0))
    if field_value is None:
        return {"value": None, "confidence": confidence}
    return {"value": str(field_value).strip(), "confidence": confidence}


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _clamp_confidence(value: Any) -> int:
    try:
        numeric = int(float(value))
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, numeric))


def _uppercase_field(field: JSONField) -> JSONField:
    if field["value"] is None:
        return field
    field["value"] = str(field["value"]).upper()
    return field


def _normalize_date_field(field: JSONField) -> JSONField:
    if field["value"] is None:
        return field
    parsed = _format_date_ddmmyyyy(str(field["value"]))
    if parsed is None:
        field["value"] = None
        field["confidence"] = 0
        return field
    field["value"] = parsed
    return field


def _normalize_pan_field(field: JSONField) -> JSONField:
    if field["value"] is None:
        return field
    candidate = str(field["value"]).upper().replace(" ", "")
    if not PAN_REGEX.match(candidate):
        field["value"] = None
        field["confidence"] = 0
        return field
    field["value"] = candidate
    return field


def _normalize_aadhaar_field(field: JSONField) -> JSONField:
    if field["value"] is None:
        return field
    digits = re.sub(r"\D", "", str(field["value"]))
    if not AADHAAR_REGEX.match(digits):
        field["value"] = None
        field["confidence"] = 0
        return field
    field["value"] = digits
    return field


def _normalize_overall_confidence(value: Any, result: dict[str, Any]) -> int:
    normalized = _clamp_confidence(value)
    if normalized > 0:
        return normalized

    confidences = [
        result[field_name]["confidence"]
        for field_name in FIELD_NAMES
        if field_name != "employee_code"
    ]
    if not confidences:
        return 0
    return int(sum(confidences) / len(confidences))


def _format_date_ddmmyyyy(raw: str) -> str | None:
    value = raw.strip()
    formats = (
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d %m %Y",
    )
    for fmt in formats:
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.strftime("%d/%m/%Y")
        except ValueError:
            continue

    digits = re.sub(r"[^0-9]", "", value)
    if len(digits) == 8:
        day = digits[0:2]
        month = digits[2:4]
        year = digits[4:8]
        try:
            parsed = datetime.strptime(f"{day}/{month}/{year}", "%d/%m/%Y")
            return parsed.strftime("%d/%m/%Y")
        except ValueError:
            return None
    return None
