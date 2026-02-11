"""Application settings loaded from environment / .env file."""

from __future__ import annotations

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── LLM (chat / completions) ──────────────────────────────────────
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai_compatible")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    LLM_MODEL: str = os.getenv(
        "LLM_MODEL", os.getenv("OPENAI_MODEL_PRIMARY", "gpt-4.1-mini")
    )
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_TEMPERATURE: float = 0.2

    # ── Embeddings ────────────────────────────────────────────────────
    EMBEDDINGS_PROVIDER: str = os.getenv("EMBEDDINGS_PROVIDER", "openai_compatible")
    EMBEDDINGS_BASE_URL: str = os.getenv(
        "EMBEDDINGS_BASE_URL", "https://api.openai.com/v1"
    )
    EMBEDDINGS_API_KEY: str = os.getenv(
        "EMBEDDINGS_API_KEY", os.getenv("OPENAI_API_KEY", "")
    )
    EMBEDDINGS_MODEL: str = os.getenv(
        "EMBEDDINGS_MODEL",
        os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    )

    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/mecanice"

    # ── Auth (MVP) ────────────────────────────────────────────────────
    ADMIN_TOKEN: str = "change-me"

    # ── RAG ───────────────────────────────────────────────────────────
    RAG_TOP_K: int = 6
    RAG_MAX_CHUNKS_IN_PROMPT: int = 10


settings = Settings()
