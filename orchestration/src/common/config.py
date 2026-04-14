"""Application configuration management."""

import json
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv


class Environment(str, Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


def _get_environment() -> Environment:
    match os.getenv("APP_ENV", "development").lower():
        case "production" | "prod":
            return Environment.PRODUCTION
        case "staging" | "stage":
            return Environment.STAGING
        case "test":
            return Environment.TEST
        case _:
            return Environment.DEVELOPMENT


def _resolve_env_file(env: Environment) -> Optional[str]:
    """Return the highest-priority .env file that exists."""
    base_dir = Path(__file__).parent.parent.parent
    candidates = [
        base_dir / f".env.{env.value}.local",
        base_dir / f".env.{env.value}",
        base_dir / ".env.local",
        base_dir / ".env",
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return None


def _parse_str_list(v: Any) -> List[str]:
    """Parse a comma-separated string or JSON array into a list."""
    if isinstance(v, list):
        return [str(item).strip() for item in v if str(item).strip()]
    if isinstance(v, str):
        raw = v.strip()
        if raw.startswith("[") and raw.endswith("]"):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass
        return [item.strip() for item in raw.strip("\"'").split(",") if item.strip()]
    return []


def _getenv_list(key: str, default: List[str]) -> List[str]:
    """Read a list value from environment, falling back to default."""
    raw = os.getenv(key, "")
    return _parse_str_list(raw) if raw else default


def _getenv_bool(key: str, default: bool) -> bool:
    """Read a boolean value from environment, falling back to default."""
    raw = os.getenv(key, "")
    if not raw:
        return default
    return raw.lower() in ("true", "1", "t", "yes")


# Load .env file before reading any values
_CURRENT_ENV = _get_environment()
_ENV_FILE = _resolve_env_file(_CURRENT_ENV)
if _ENV_FILE:
    load_dotenv(_ENV_FILE, override=False)

# Environment-specific defaults applied when the env var is not explicitly set
_ENV_DEFAULTS: Dict[Environment, Dict[str, Any]] = {
    Environment.DEVELOPMENT: {
        "DEBUG": False,
        "LOG_LEVEL": "WARNING",
        "LOG_FORMAT": "console",
        "RATE_LIMIT_DEFAULT": ["1000 per day", "200 per hour"],
    },
    Environment.STAGING: {
        "DEBUG": False,
        "LOG_LEVEL": "INFO",
        "RATE_LIMIT_DEFAULT": ["500 per day", "100 per hour"],
    },
    Environment.PRODUCTION: {
        "DEBUG": False,
        "LOG_LEVEL": "WARNING",
        "RATE_LIMIT_DEFAULT": ["200 per day", "50 per hour"],
    },
    Environment.TEST: {
        "DEBUG": True,
        "LOG_LEVEL": "DEBUG",
        "LOG_FORMAT": "console",
        "RATE_LIMIT_DEFAULT": ["1000 per day", "1000 per hour"],
    },
}

_RATE_LIMIT_ENDPOINT_DEFAULTS: Dict[str, List[str]] = {
    "chat": ["30 per minute"],
    "chat_stream": ["20 per minute"],
    "messages": ["50 per minute"],
    "register": ["10 per hour"],
    "login": ["20 per minute"],
    "root": ["10 per minute"],
    "health": ["20 per minute"],
}


class Settings:
    """Application settings loaded from environment variables and .env files."""

    def __init__(self) -> None:
        """Initialize settings from environment variables."""
        # Environment
        self.ENVIRONMENT: Environment = _CURRENT_ENV

        # Application
        self.PROJECT_NAME: str = os.getenv("PROJECT_NAME", "FastAPI LangGraph Template")
        self.VERSION: str = os.getenv("VERSION", "1.0.0")
        self.DESCRIPTION: str = os.getenv(
            "DESCRIPTION", "A production-ready FastAPI template with LangGraph and Langfuse integration"
        )
        self.API_V1_STR: str = os.getenv("API_V1_STR", "/api/v1")
        self.DEBUG: bool = _getenv_bool("DEBUG", False)

        # CORS — production/staging must explicitly set ALLOWED_ORIGINS; development defaults to wildcard
        _cors_default = ["*"] if _CURRENT_ENV == Environment.DEVELOPMENT else []
        self.ALLOWED_ORIGINS: List[str] = _getenv_list("ALLOWED_ORIGINS", _cors_default)

        # Langfuse
        self.LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
        self.LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
        self.LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        self.LANGFUSE_ENABLED: bool = _getenv_bool("LANGFUSE_ENABLED", True)

        # LLM
        self.OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
        self.DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "gpt-5-mini")
        self.DEFAULT_LLM_TEMPERATURE: float = float(os.getenv("DEFAULT_LLM_TEMPERATURE", "0.2"))
        self.MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "2000"))
        self.MAX_LLM_CALL_RETRIES: int = int(os.getenv("MAX_LLM_CALL_RETRIES", "3"))

        # Voice / Audio
        self.OPENAI_TTS_MODEL: str = os.getenv("OPENAI_TTS_MODEL", "tts-1")
        self.OPENAI_TTS_VOICE: str = os.getenv("OPENAI_TTS_VOICE", "alloy")
        self.OPENAI_STT_MODEL: str = os.getenv("OPENAI_STT_MODEL", "whisper-1")
        self.AZURE_SPEECH_KEY: str = os.getenv("AZURE_SPEECH_KEY", "")
        self.AZURE_SPEECH_REGION: str = os.getenv("AZURE_SPEECH_REGION", "")

        # Long-term memory
        self.LONG_TERM_MEMORY_MODEL: str = os.getenv("LONG_TERM_MEMORY_MODEL", "gpt-4o-mini")
        self.LONG_TERM_MEMORY_EMBEDDER_MODEL: str = os.getenv(
            "LONG_TERM_MEMORY_EMBEDDER_MODEL", "text-embedding-3-small"
        )
        self.LONG_TERM_MEMORY_COLLECTION_NAME: str = os.getenv(
            "LONG_TERM_MEMORY_COLLECTION_NAME", "longterm_memory"
        )

        # JWT
        self.JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
        self.JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "10"))
        self.JWT_REFRESH_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_MINUTES", "10080"))

        # Logging
        self.LOG_DIR: Path = Path(os.getenv("LOG_DIR", "logs"))
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")

        # PostgreSQL
        self.POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
        self.POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
        self.POSTGRES_DB: str = os.getenv("POSTGRES_DB", "llm_db")
        self.POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
        self.POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
        self.POSTGRES_SCHEMA: str = os.getenv("POSTGRES_SCHEMA", "llmonl")
        self.POSTGRES_POOL_SIZE: int = int(os.getenv("POSTGRES_POOL_SIZE", "20"))
        self.POSTGRES_MAX_OVERFLOW: int = int(os.getenv("POSTGRES_MAX_OVERFLOW", "10"))
        self.CHECKPOINT_TABLES: List[str] = ["checkpoint_blobs", "checkpoint_writes", "checkpoints"]

        # Rate limiting
        self.RATE_LIMIT_DEFAULT: List[str] = _getenv_list("RATE_LIMIT_DEFAULT", ["200 per day", "50 per hour"])
        self.RATE_LIMIT_ENDPOINTS: Dict[str, List[str]] = {
            endpoint: _getenv_list(f"RATE_LIMIT_{endpoint.upper()}", default)
            for endpoint, default in _RATE_LIMIT_ENDPOINT_DEFAULTS.items()
        }

        # Evaluation
        self.EVALUATION_LLM: str = os.getenv("EVALUATION_LLM", "gpt-5")
        self.EVALUATION_BASE_URL: str = os.getenv("EVALUATION_BASE_URL", "https://api.openai.com/v1")
        self.EVALUATION_API_KEY: str = os.getenv("EVALUATION_API_KEY", "") or self.OPENAI_API_KEY
        self.EVALUATION_SLEEP_TIME: int = int(os.getenv("EVALUATION_SLEEP_TIME", "10"))
        self.MULTIPART_DEBUG: str = os.getenv("MULTIPART_DEBUG", "0")

        # Apply environment-specific defaults for vars not explicitly set
        self._apply_env_defaults()

        # Validate required settings (raises on critical misconfigurations)
        self._validate_required_settings()

    def _validate_required_settings(self) -> None:
        """Raise ValueError for missing critical settings in non-test environments."""
        if self.ENVIRONMENT == Environment.TEST:
            return
        errors: List[str] = []
        if not self.JWT_SECRET_KEY:
            errors.append("JWT_SECRET_KEY must not be empty")
        if not self.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY must not be empty")
        if self.ENVIRONMENT in (Environment.PRODUCTION, Environment.STAGING) and "*" in self.ALLOWED_ORIGINS:
            errors.append("ALLOWED_ORIGINS must not contain '*' in production/staging — set explicit origins")
        if errors:
            raise ValueError(f"Invalid configuration: {'; '.join(errors)}")

    def _apply_env_defaults(self) -> None:
        """Apply environment-specific defaults only when the env var was not set."""
        for key, value in _ENV_DEFAULTS.get(self.ENVIRONMENT, {}).items():
            if key not in os.environ:
                setattr(self, key, value)

    @property
    def langfuse_is_enabled(self) -> bool:
        """Return True when Langfuse credentials are present and the feature is enabled."""
        return self.LANGFUSE_ENABLED and bool(self.LANGFUSE_PUBLIC_KEY) and bool(self.LANGFUSE_SECRET_KEY)


# Backward-compatible exports
ENV_FILE = _ENV_FILE
settings = Settings()
