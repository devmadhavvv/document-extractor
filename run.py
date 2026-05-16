"""PyInstaller entry point for the packaged backend binary."""
import os
import sys

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    creds = os.environ.get("FIREBASE_CREDENTIALS_PATH", "")
    if creds:
        bundled = os.path.join(sys._MEIPASS, os.path.basename(creds))
        if os.path.exists(bundled):
            os.environ["FIREBASE_CREDENTIALS_PATH"] = bundled

import uvicorn
from app.main import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        workers=1,
        loop="asyncio",
    )
