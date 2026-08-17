from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # ── API ──────────────────────────────────────────
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8

    # ── PostgreSQL ───────────────────────────────────
    POSTGRES_USER: str = "travel"
    POSTGRES_PASSWORD: str = "travel123"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "travel_planner"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ── Redis ────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_CACHE_TTL: int = 3600

    # ── OpenAI / LLM ────────────────────────────────
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"

    # ── ChromaDB (PersistentClient) ─────────────────
    CHROMA_PERSIST_DIRECTORY: str = "../data/chromadb"
    CHROMA_COLLECTION_NAME: str = "travel_knowledge"

    # ── Embedding (bge-small-zh-v1.5) ───────────────
    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"

    # ── Third-party APIs ────────────────────────────
    WEATHER_API_KEY: Optional[str] = None
    MAPS_API_KEY: Optional[str] = None
    FLIGHTS_API_KEY: Optional[str] = None
    HOTELS_API_KEY: Optional[str] = None

    # ── CORS ─────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()