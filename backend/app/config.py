"""
Centralized configuration management for PolicyDesk Backend.
Loads environment variables with sensible defaults and strict validation.
"""
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self) -> None:
        self.APP_NAME: str = os.getenv("APP_NAME", "PolicyDesk RAG Document Assistant")
        self.APP_ENV: str = os.getenv("APP_ENV", "development")
        self.DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
        self.PORT: int = int(os.getenv("PORT", "8000"))

        raw_origins = os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173",
        )
        self.ALLOWED_ORIGINS: List[str] = [
            origin.strip() for origin in raw_origins.split(",") if origin.strip()
        ]

        # Database URL (normalizes postgres:// to postgresql+psycopg2:// for Render/Neon compatibility)
        raw_db_url = os.getenv("DATABASE_URL", "sqlite:///./policydesk.db")
        if raw_db_url.startswith("postgres://"):
            raw_db_url = raw_db_url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif raw_db_url.startswith("postgresql://") and "+psycopg2" not in raw_db_url:
            raw_db_url = raw_db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        self.DATABASE_URL: str = raw_db_url

        # Authentication & Security
        self.JWT_SECRET_KEY: str = os.getenv(
            "JWT_SECRET_KEY",
            "dev-only-insecure-jwt-secret-key-replace-in-production-64bytes!",
        )
        self.JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480")
        )
        self.PASSWORD_HASH_SCHEME: str = os.getenv("PASSWORD_HASH_SCHEME", "argon2")

        # Initial Seed Accounts
        self.INITIAL_ADMIN_NAME: str = os.getenv(
            "INITIAL_ADMIN_NAME", "PolicyDesk System Admin"
        )
        self.INITIAL_ADMIN_EMAIL: str = os.getenv(
            "INITIAL_ADMIN_EMAIL", "admin@policydesk.io"
        )
        self.INITIAL_ADMIN_PASSWORD: str = os.getenv("INITIAL_ADMIN_PASSWORD", "")

        self.INITIAL_USER_NAME: str = os.getenv("INITIAL_USER_NAME", "Alex Rivera")
        self.INITIAL_USER_EMAIL: str = os.getenv(
            "INITIAL_USER_EMAIL", "user@policydesk.io"
        )
        self.INITIAL_USER_PASSWORD: str = os.getenv("INITIAL_USER_PASSWORD", "")

        # Google Gemini AI Settings
        self.GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
        self.GEMINI_LLM_MODEL = os.getenv("GEMINI_LLM_MODEL", "gemini-3.8-flash")
        self.GEMINI_EMBEDDING_MODEL: str = os.getenv(
            "GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"
        )
        self.GEMINI_EMBEDDING_DIMENSIONS: int = int(
            os.getenv("GEMINI_EMBEDDING_DIMENSIONS", "768")
        )
        self.GEMINI_TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", "0.1"))

        # Document Ingestion & RAG Parameters
        self.MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "20"))
        self.MAX_UPLOAD_SIZE_BYTES: int = self.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        self.CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
        self.CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
        self.RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "5"))
        self.SIMILARITY_THRESHOLD: float = float(
            os.getenv("SIMILARITY_THRESHOLD", "0.35")
        )


def get_settings() -> Settings:
    """Return a freshly initialized Settings instance."""
    return Settings()


settings = get_settings()
