import os
import sys
from pathlib import Path

# Add project root to sys.path so src.* modules can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure database is initialized in serverless environment
from src.core.database import init_db
try:
    init_db()
except Exception as e:
    print(f"Serverless DB init note: {e}")

from src.main import app
from starlette.types import ASGIApp, Scope, Receive, Send

class VercelPathMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            matched_path = headers.get(b"x-matched-path", b"").decode("utf-8")
            
            if matched_path:
                scope["path"] = matched_path
            elif scope["path"].startswith("/api/index.py"):
                remainder = scope["path"][len("/api/index.py"):]
                scope["path"] = remainder if remainder else "/"
            elif scope["path"].startswith("/api/index"):
                remainder = scope["path"][len("/api/index"):]
                scope["path"] = remainder if remainder else "/"

        await self.app(scope, receive, send)

app.add_middleware(VercelPathMiddleware)
