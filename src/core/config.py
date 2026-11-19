"""Core configuration for Agent Gatekeeper."""
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DEFAULT_RULES_PATH = CONFIG_DIR / "security_rules.json"
DEFAULT_DB_PATH = DATA_DIR / "gatekeeper.db"

# Environment / Defaults
DB_PATH = os.getenv("GATEKEEPER_DB_PATH", str(DEFAULT_DB_PATH))
RULES_FILE_PATH = os.getenv("GATEKEEPER_RULES_PATH", str(DEFAULT_RULES_PATH))

# System metadata
PROJECT_NAME = "Agent Gatekeeper"
BUSINESS_CATEGORY = "Online Store (Amazon India Reference)"
VERSION = "1.0.0"
