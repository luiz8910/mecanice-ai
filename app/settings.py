import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM (chat/completions)
    # allow legacy/openai env names as fallbacks (e.g. OPENAI_API_KEY)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai_compatible")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    # Use OPENAI_MODEL_PRIMARY as the primary fallback for LLM_MODEL
    LLM_MODEL: str = os.getenv("LLM_MODEL", os.getenv("OPENAI_MODEL_PRIMARY", "gpt-4.1-mini"))
    LLM_TIMEOUT_SECONDS: int = 30

    # Embeddings
    EMBEDDINGS_PROVIDER: str = os.getenv("EMBEDDINGS_PROVIDER", "openai_compatible")  # openai_compatible | dummy
    EMBEDDINGS_BASE_URL: str = os.getenv("EMBEDDINGS_BASE_URL", "https://api.openai.com/v1")
    EMBEDDINGS_API_KEY: str = os.getenv("EMBEDDINGS_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    EMBEDDINGS_MODEL: str = os.getenv("EMBEDDINGS_MODEL", os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))  # 1536 dims

    # Database (Postgres + pgvector)
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/mecanice"

    # Simple Admin auth (MVP)
    ADMIN_TOKEN: str = "change-me"

    # Cache
    CACHE_TTL_SECONDS: int = 60 * 60 * 24 * 30  # 30 days

    # RAG
    RAG_TOP_K: int = 6
    RAG_MAX_CHUNKS_IN_PROMPT: int = 10

    LLM_TIMEOUT_SECONDS: int = 30


settings = Settings()
