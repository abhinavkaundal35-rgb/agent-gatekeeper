"""Core configuration for Agent Gatekeeper."""
import os
import tempfile
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"

# Detect Vercel / AWS Lambda / Read-only Serverless environments
IS_SERVERLESS = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("NOW_REGION"))

if IS_SERVERLESS:
    DATA_DIR = Path(tempfile.gettempdir())
    DEFAULT_DB_PATH = DATA_DIR / "gatekeeper.db"
else:
    DATA_DIR = BASE_DIR / "data"
    try:
        DATA_DIR.mkdir(exist_ok=True)
        DEFAULT_DB_PATH = DATA_DIR / "gatekeeper.db"
    except (PermissionError, OSError):
        DATA_DIR = Path(tempfile.gettempdir())
        DEFAULT_DB_PATH = DATA_DIR / "gatekeeper.db"

DEFAULT_RULES_PATH = CONFIG_DIR / "security_rules.json"

# Environment / Defaults
DB_PATH = os.getenv("GATEKEEPER_DB_PATH", str(DEFAULT_DB_PATH))
RULES_FILE_PATH = os.getenv("GATEKEEPER_RULES_PATH", str(DEFAULT_RULES_PATH))

# System metadata
PROJECT_NAME = "Agent Gatekeeper"
BUSINESS_CATEGORY = "Online Store (Amazon India Reference)"
VERSION = "1.0.0"
