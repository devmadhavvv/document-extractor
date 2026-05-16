# FastAPI Onboarding Backend Spec

## Implementation Goal

Create a Python 3.11 FastAPI backend scaffold for an AI onboarding document extraction SaaS.

## Current State

The repository is empty except for Git metadata, so the implementation should establish the initial backend structure and conventions.

## Scope

- FastAPI application entrypoint.
- Modular `app/` package with `api`, `services`, `models`, `schemas`, `utils`, `core`, and `workers`.
- Environment-driven settings loaded with dotenv.
- Firebase Admin SDK initialization for Firestore using service account JSON credentials.
- Reusable Firestore client helpers for `batches` and `documents` collections.
- Multiple PDF upload endpoint that writes temp files and creates Firestore batch/document records.
- Gemini Vision extraction service for onboarding JSON with confidence scoring.
- Async background document processing pipeline with status transitions and batch progress updates.
- Document details API for frontend review screens.
- Editable document verification API for frontend review workflow.
- CORS middleware.
- Async health check endpoint at `GET /health`.
- Requirements and README.
- Focused smoke tests for app creation and health route.

## Non-Goals

- Authentication, tenant scoping, and document extraction workflows.
- Firebase Storage implementation beyond leaving configuration room for later.
- Deployment configuration.

## Assumptions And Constraints

- Python runtime target is 3.11.
- Firebase credentials are supplied through environment variables and are not committed.
- Health check must work even when Firebase credentials are not configured.
- CORS should default to local development origins, with production origins set by environment variable.

## Technical Approach

- Keep `app/main.py` as the ASGI application factory and exported `app`.
- Keep environment settings in `app/core/config.py` using `pydantic-settings`.
- Keep Firebase setup in `app/core/firebase.py`, with lazy initialization and explicit error propagation when Firestore is requested without credentials.
- Keep reusable async-friendly Firestore document operations in `app/services/firestore_service.py`.
- Keep upload validation, temporary file persistence, and Firestore record orchestration in `app/services/upload_service.py`.
- Keep Gemini prompt construction, retry logic, response parsing, and schema normalization in `app/services/gemini_extractor.py`.
- Keep per-document async pipeline orchestration in `app/services/background_processor.py`.
- Use `asyncio.to_thread` for Firestore Admin SDK calls so FastAPI async routes can call helpers without blocking the event loop directly.
- Keep routes under `app/api/routes/` and compose them via `app/api/router.py`.
- Use Python `logging`, not print statements.

## Interfaces

- `GET /health`
  - Async endpoint.
  - Returns `{"status": "ok", "service": "...", "environment": "..."}`.
- Firestore helpers:
  - `create_document(collection_name, document_id, data)`
  - `update_document(collection_name, document_id, data)`
  - `get_document(collection_name, document_id)`
  - `list_documents(collection_name, limit=None)`
  - Allowed collections: `batches`, `documents`.
- `POST /upload`
  - Multipart field: `files`.
  - Accepts multiple PDF files only.
  - Rejects empty files and files over configured max size.
  - Saves files under configured temp directory.
  - Creates one `batches` document and one `documents` record per uploaded PDF.
  - Returns `{"batch_id": "...", "uploaded_files": [{"document_id": "...", "filename": "..."}]}`.
- Gemini extractor input:
  - list of PDF page image paths
  - original PDF filename
- Gemini extractor output:
  - strict onboarding JSON with `{value, confidence}` fields
  - confidence range 0-100
  - validation/normalization for PAN, Aadhaar, names, and dates
- Background pipeline:
  - convert PDF to images
  - extract onboarding JSON via Gemini
  - update document status lifecycle
  - save extracted JSON / failure error message
  - update batch progress counters dynamically
- `GET /document/{document_id}`
  - Returns document-level review payload with extraction and verification fields.
- `PATCH /document/{document_id}`
  - Updates `verified_json` and `updated_at`.
  - Preserves original `extracted_json`.

## Verification Targets

- `python -m compileall app`
- `python -m pytest`
