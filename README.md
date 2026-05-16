# AI Onboarding Document Extraction API

FastAPI backend scaffold for an AI onboarding document extraction SaaS. The service is organized for future document upload, extraction, review, and worker workflows.

## Stack

- Python 3.11
- FastAPI
- Firebase Firestore via Firebase Admin SDK
- Optional Firebase Storage configuration for later document uploads
- Dotenv-based environment configuration

## Project Structure

```text
app/
  api/
    routes/
  core/
  models/
  schemas/
  services/
  utils/
  workers/
tests/
```

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set Firebase values in `.env` when you need Firestore access. Do not commit service account JSON files or secrets.

```env
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_CREDENTIALS_PATH=/absolute/path/to/service-account.json
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
```

## Firestore

Firebase Admin SDK initialization uses `FIREBASE_CREDENTIALS_PATH`, which must point to a service account JSON file. Firestore access is intentionally lazy, so the app and `/health` can start before credentials are configured.

Reusable async-friendly helpers live in `app.services.firestore_service` and currently allow the `batches` and `documents` collections:

```python
from app.services.firestore_service import (
    create_document,
    get_document,
    list_documents,
    update_document,
)

batch = await create_document("batches", "batch-001", {"status": "created"})
saved_batch = await get_document("batches", "batch-001")
updated_batch = await update_document("batches", "batch-001", {"status": "processing"})
all_batches = await list_documents("batches", limit=20)
```

## Upload PDFs

Upload one or more PDFs with multipart field name `files`:

```bash
curl -X POST http://localhost:8000/upload \
  -F "files=@/path/to/offer-letter.pdf;type=application/pdf" \
  -F "files=@/path/to/id-document.pdf;type=application/pdf"
```

The API validates `.pdf` filenames, PDF file signatures, empty files, and `MAX_UPLOAD_SIZE_BYTES`. Valid files are saved temporarily under `UPLOAD_TEMP_DIR/<batch_id>/`, then one `batches` record and one `documents` record per file are created in Firestore.

Response:

```json
{
  "batch_id": "generated-batch-id",
  "uploaded_files": [
    {
      "document_id": "generated-document-id",
      "filename": "offer-letter.pdf"
    }
  ]
}
```

## Gemini Extraction Service

Gemini extraction is exposed as a reusable backend service in `app/services/gemini_extractor.py`.

Set configuration in `.env`:

```env
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash
GEMINI_REQUEST_TIMEOUT_SECONDS=60
GEMINI_MAX_RETRIES=3
```

The service accepts a list of page image paths and a PDF filename, then returns strict onboarding JSON with per-field confidence, retrying on invalid JSON or transient API failures.

## Background Processing Pipeline

`POST /upload` now queues each document for independent background processing using FastAPI `BackgroundTasks`.

Per-document pipeline:
1. `PDF_CONVERSION`
2. `AI_PROCESSING`
3. `SUCCESS` or `FAILED`

Document statuses:
- `QUEUED`
- `PDF_CONVERSION`
- `AI_PROCESSING`
- `SUCCESS`
- `FAILED`

Failure isolation:
- each PDF is processed independently
- one document failure does not stop other documents in the same batch
- `error_message` is stored on failed documents
- batch counters (`completed_files`, `failed_files`) are updated dynamically

## Polling APIs

Batch progress:

```bash
curl http://localhost:8000/batch/<batch_id>
```

Document details for review UI:

```bash
curl http://localhost:8000/document/<document_id>
```

Update verification payload:

```bash
curl -X PATCH http://localhost:8000/document/<document_id> \
  -H "Content-Type: application/json" \
  -d '{"verified_json":{"candidate_name":{"value":"JOHN DOE","confidence":98}}}'
```

## Run

```bash
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "AI Onboarding Document Extraction API",
  "environment": "development"
}
```

## Test

```bash
python -m compileall app
python -m pytest
```
