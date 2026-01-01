from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM (chat/completions)
    LLM_PROVIDER: str = "openai_compatible"
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4.1-mini"
    LLM_TIMEOUT_SECONDS: int = 30

    # Embeddings
    EMBEDDINGS_PROVIDER: str = "openai_compatible"  # openai_compatible | dummy
    EMBEDDINGS_BASE_URL: str = "https://api.openai.com/v1"
    EMBEDDINGS_API_KEY: str = ""
    EMBEDDINGS_MODEL: str = "text-embedding-3-small"  # 1536 dims

    # Database (Postgres + pgvector)
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/mecanice"

    # Cache
    CACHE_TTL_SECONDS: int = 60 * 60 * 24 * 30  # 30 days

    # RAG
    RAG_TOP_K: int = 6
    RAG_MAX_CHUNKS_IN_PROMPT: int = 10


settings = Settings()
