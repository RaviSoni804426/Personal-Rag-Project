"""
Configuration management for DataMind application.
Handles environment variables, defaults, and runtime settings.
"""

import os
from typing import Optional
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=True)


class Settings:
    """Application settings loaded from environment variables."""

    # API Configuration
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    API_TITLE: str = "DataMind - Intelligent Document Intelligence Platform"
    API_VERSION: str = "1.0.0"

    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8080"))
    WORKERS: int = int(os.getenv("WORKERS", "4"))

    # Database Configuration
    DB_PATH: str = os.getenv("DB_PATH", "./data/datamind.db")
    CACHE_DIR: str = os.getenv("CACHE_DIR", "./data/cache")

    # Embeddings Configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_EMBEDDING_URL: str = os.getenv(
        "GROQ_EMBEDDING_URL", "https://api.groq.com/openai/v1/embeddings"
    )
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "embed-1")
    EMBEDDING_DIMENSION: int = 1536

    # LLM Configuration (Optional)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    GROQ_LLM_MODEL: str = os.getenv("GROQ_LLM_MODEL", "llama-3.1-8b-instant")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "512"))

    # Search Configuration
    DEFAULT_TOP_K: int = int(os.getenv("DEFAULT_TOP_K", "5"))
    MAX_TOP_K: int = int(os.getenv("MAX_TOP_K", "20"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.0"))

    # File Upload Configuration
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "52428800"))  # 50MB
    ALLOWED_EXTENSIONS: list = [".pdf", ".docx", ".txt", ".md", ".json", ".csv"]
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./data/uploads")

    # Performance Configuration
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "10"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "./logs/datamind.log")

    @classmethod
    def validate(cls) -> bool:
        """Validate critical settings.

        GROQ_API_KEY is optional for local development because the app
        supports a deterministic local embedding fallback. Warn if not set.
        """
        from datamind.utils import get_logger

        logger = get_logger(__name__)
        if not cls.GROQ_API_KEY:
            logger.warning("GROQ_API_KEY not set; using local embedding fallback")
        return True

    @classmethod
    def ensure_directories(cls) -> None:
        """Ensure all required directories exist."""
        for directory in [
            cls.DB_PATH,
            cls.CACHE_DIR,
            cls.UPLOAD_DIR,
            cls.LOG_FILE,
        ]:
            if directory:
                Path(directory).parent.mkdir(parents=True, exist_ok=True)


# Initialize settings
settings = Settings()
