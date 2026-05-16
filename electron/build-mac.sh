#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# Detect Python venv
if [ -f .venv/bin/python3 ]; then
  PYTHON=".venv/bin/python3"
  echo "Using venv: .venv"
elif [ -f venv/bin/python3 ]; then
  PYTHON="venv/bin/python3"
  echo "Using venv: venv"
else
  PYTHON="python3"
  echo "No venv found, using system python3"
fi

echo "=== Step 1: Build frontend ==="
cd frontend
npm run build
cd "$ROOT_DIR"

echo "=== Step 2: Install PyInstaller ==="
$PYTHON -m pip install pyinstaller

echo "=== Step 3: Bundle Python backend ==="
rm -rf dist/backend dist/run

# Bundle Firebase service account key inside the binary
FIREBASE_KEY=""
if [ -f .env ]; then
  FIREBASE_KEY=$(grep -E "^FIREBASE_CREDENTIALS_PATH=" .env | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || echo "")
fi
if [ -n "$FIREBASE_KEY" ] && [ -f "$FIREBASE_KEY" ]; then
  KEY_FILENAME=$(basename "$FIREBASE_KEY")
  ADD_DATA="--add-data $FIREBASE_KEY:."
  echo "Including Firebase key: $FIREBASE_KEY → ./$KEY_FILENAME"
else
  ADD_DATA=""
  echo "WARNING: No Firebase key found. Set FIREBASE_CREDENTIALS_PATH in .env"
fi

$PYTHON -m PyInstaller --onefile \
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
  --collect-all app \
  $ADD_DATA \
  --distpath dist/backend \
  --name onboarding-api \
  run.py

echo "Making binary executable..."
chmod +x dist/backend/onboarding-api

echo "Verifying binary..."
ls -lh dist/backend/onboarding-api
file dist/backend/onboarding-api

echo "=== Step 4: Package Electron app for macOS ==="
cd electron
npm run dist -- --mac
cd "$ROOT_DIR"

echo ""
echo "=== Done ==="
echo "macOS DMG: electron/release/Onboarding HRMS-1.0.0.dmg"
