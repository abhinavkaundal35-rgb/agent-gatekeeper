"""Rule configuration loader with caching and dynamic reload support."""
import json
from pathlib import Path
from typing import Optional
from src.core.config import RULES_FILE_PATH
from src.engine.models import SecurityRulesConfig

class RuleLoader:
    _cached_config: Optional[SecurityRulesConfig] = None

    @classmethod
    def load_rules(cls, file_path: Optional[str] = None, force_reload: bool = False) -> SecurityRulesConfig:
        """Load and parse the declarative security rules JSON configuration."""
        if cls._cached_config is not None and not force_reload and file_path is None:
            return cls._cached_config

        target_file = Path(file_path) if file_path else Path(RULES_FILE_PATH)
        if not target_file.exists():
            raise FileNotFoundError(f"Security rules file not found: {target_file}")

        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        config = SecurityRulesConfig(**data)
        if file_path is None:
            cls._cached_config = config
        return config

    @classmethod
    def reload(cls, file_path: Optional[str] = None) -> SecurityRulesConfig:
        """Force reload the rules configuration."""
        return cls.load_rules(file_path=file_path, force_reload=True)
