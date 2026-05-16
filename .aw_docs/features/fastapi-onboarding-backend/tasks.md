# FastAPI Onboarding Backend Tasks

## Spec Brief

Build the initial FastAPI backend scaffold for an AI onboarding document extraction SaaS. Execution route: `/aw:build`.

## File Map

- Create `app/main.py`: application factory, CORS setup, router inclusion.
- Create `app/core/config.py`: dotenv-backed settings.
- Create `app/core/firebase.py`: Firebase Admin initialization and Firestore client helper.
- Create `app/services/firestore_service.py`: reusable async-friendly Firestore CRUD helpers.
- Create `app/api/router.py`: top-level API router composition.
- Create `app/api/routes/health.py`: async health endpoint.
- Create package placeholders in `services`, `models`, `schemas`, `utils`, and `workers`.
- Create `requirements.txt`, `README.md`, `.env.example`.
- Create focused tests under `tests/`.

## Phase 1

Outcome: project structure and runtime dependencies exist.

- [ ] Create package directories and `__init__.py` files.
- [ ] Add `requirements.txt` for FastAPI, Uvicorn, Firebase Admin, dotenv settings, and testing.
- [ ] Add `.env.example` without secrets.

## Phase 2

Outcome: application boots and exposes `/health`.

- [ ] Add settings model in `app/core/config.py`.
- [ ] Add Firebase initialization helper in `app/core/firebase.py`.
- [ ] Add health router and app factory.
- [ ] Add README with setup, env vars, and run commands.

## Phase 3

Outcome: focused verification passes.

- [ ] Add smoke tests for settings/app/health route.
- [ ] Run `python -m compileall app`.
- [ ] Run `python -m pytest`.

## Phase 4

Outcome: Firebase Admin SDK and Firestore helper surface are ready for SaaS data access.

- [ ] Add tests for allowed collection validation and helper behavior using mocked Firestore clients.
- [ ] Update Firebase initialization to require service account JSON credentials when creating a Firestore client.
- [ ] Add async-friendly helper functions for `create_document`, `update_document`, `get_document`, and `list_documents`.
- [ ] Limit helper collections to `batches` and `documents`.
- [ ] Update README with Firestore helper usage notes.
- [ ] Run `python -m compileall app` and `python -m pytest`.

## Phase 5

Outcome: clients can upload multiple PDFs and receive a Firestore-backed batch response.

- [ ] Add upload config for max PDF size and temp directory.
- [ ] Add response schemas for upload results.
- [ ] Add upload service that validates PDF extension/content, empty files, and max size while saving to temp storage.
- [ ] Add `POST /upload` route and include it in the API router.
- [ ] Create Firestore batch and document records with the requested schemas.
- [ ] Add tests for success, non-PDF rejection, empty files, and max size rejection.
- [ ] Update requirements for multipart upload support.
- [ ] Update README with upload usage.
- [ ] Run `python -m compileall app` and `python -m pytest`.

## Phase 6

Outcome: reusable Gemini Vision extractor produces strict onboarding JSON safely.

- [ ] Add Gemini config fields (API key/model/retries/timeout).
- [ ] Add `app/services/gemini_extractor.py` with reusable extraction function.
- [ ] Implement strict prompt and required schema with Aadhaar-first extraction guidance.
- [ ] Add retry logic for API failures and invalid JSON responses.
- [ ] Parse response safely (handle fenced text/noisy wrappers) and validate output.
- [ ] Enforce normalization and validation rules:
- [ ] employee code from PDF filename stem, name uppercase, date format `DD/MM/YYYY`, PAN regex, Aadhaar 12 digits.
- [ ] Add structured logging at request, retry, parse failure, and success points.
- [ ] Add focused tests for parsing, retries, and normalization behavior.
- [ ] Run `python -m compileall app` and `python -m pytest`.

## Phase 7

Outcome: uploaded PDFs process asynchronously with independent status tracking and resilient batch progress updates.

- [ ] Add reusable background pipeline service.
- [ ] Update upload route to enqueue one `BackgroundTasks` job per uploaded PDF.
- [ ] Update document lifecycle statuses to `QUEUED`, `PDF_CONVERSION`, `AI_PROCESSING`, `SUCCESS`, `FAILED`.
- [ ] Persist `error_message` for failed documents.
- [ ] Ensure one document failure does not fail whole batch processing.
- [ ] Dynamically update batch counters and final batch status based on processed documents.
- [ ] Add focused tests for success/failure background transitions.
- [ ] Update README pipeline documentation.
- [ ] Run `python -m compileall app` and `python -m pytest`.

## Phase 8

Outcome: frontend review UI can fetch one document's full review details.

- [ ] Add document details service.
- [ ] Add `GET /document/{document_id}` route.
- [ ] Return required fields for review UI.
- [ ] Add tests for success and not-found cases.
- [ ] Run `python -m compileall app` and `python -m pytest`.

## Phase 9

Outcome: frontend can edit and persist verification payloads without mutating extraction output.

- [ ] Add editable verification endpoint `PATCH /document/{document_id}`.
- [ ] Save `verified_json` separately.
- [ ] Preserve existing `extracted_json`.
- [ ] Add `updated_at` on verification updates.
- [ ] Add tests for success and not-found behaviors.
- [ ] Run `python -m compileall app` and `python -m pytest`.
