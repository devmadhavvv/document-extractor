#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== Step 1: Build frontend ==="
cd frontend && npm run build && cd "$ROOT_DIR"

echo "=== Step 2: Cross-compile Python backend for Windows via Docker ==="
rm -rf dist/backend dist/run

# Create requirements.txt for the Docker image (cleaned up after build)
cat > requirements.txt << 'REQEOF'
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-multipart>=0.0.12
firebase-admin>=6.0.0
google-cloud-firestore>=2.0.0
google-api-core>=2.0.0
grpcio>=1.60.0
openpyxl>=3.1.0
httpx>=0.28.0
pyOpenSSL>=24.0.0
cachetools>=5.0.0
pdf2image>=1.17.0
REQEOF

# Check for Firebase key
FIREBASE_KEY=$(grep -E "^FIREBASE_CREDENTIALS_PATH=" .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || echo "")
ADD_DATA=""
if [ -n "$FIREBASE_KEY" ] && [ -f "$FIREBASE_KEY" ]; then
  ADD_DATA="--add-data $FIREBASE_KEY;."
  echo "Including Firebase key"
else
  echo "WARNING: No Firebase key found"
fi

# Build the PyInstaller command string
PYINSTALLER_ARGS="--onefile \
  --hidden-import uvicorn \
  --hidden-import uvicorn.loggers \
  --hidden-import uvicorn.loops \
  --hidden-import uvicorn.protocols \
  --hidden-import uvicorn.lifespan.on \
  --hidden-import firebase_admin \
  --hidden-import firebase_admin.firestore \
  --hidden-import google.cloud \
  --hidden-import google.cloud.firestore \
  --hidden-import google.api_core \
  --hidden-import google.api_core.grpc_helpers \
  --hidden-import grpc \
  --hidden-import grpc._cython.cygrpc \
  --hidden-import grpc._auth \
  --hidden-import google.auth \
  --hidden-import google.oauth2 \
  --hidden-import cachetools \
  --hidden-import pdf2image \
  --collect-all app \
  $ADD_DATA \
  --distpath dist/backend \
  --name onboarding-api \
  run.py"
# Collapse whitespace for the single-arg docker command
PYINSTALLER_CMD="pyinstaller $(echo "$PYINSTALLER_ARGS")"

echo "Pulling PyInstaller Docker image (first run downloads ~2GB)..."
docker pull cdrx/pyinstaller-windows:python3-3.12

docker run --rm \
  -v "$(pwd):/src" \
  cdrx/pyinstaller-windows:python3-3.12 \
  "$PYINSTALLER_CMD"

# Verify binary
if [ -f dist/backend/onboarding-api.exe ]; then
  echo "Windows backend binary ready at dist/backend/onboarding-api.exe"
else
  echo "ERROR: Binary not found at dist/backend/onboarding-api.exe"
  ls -la dist/backend/ 2>/dev/null || true
  exit 1
fi

echo "=== Step 3: Package Electron app for Windows ==="
cd electron && npm run dist -- --win && cd "$ROOT_DIR"

# Clean up temp file
rm -f requirements.txt

echo ""
echo "=== Done ==="
echo "Windows portable: electron/release/Onboarding HRMS 1.0.0 Portable.exe"
