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
