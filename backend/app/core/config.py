from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/rag_app"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "documents"
    llm_api_key: str | None = None
    embedding_api_key: str | None = None
    max_upload_size_mb: int = 100
    max_chat_history: int = 10
    hf_token: str | None = None
    hf_chat_model: str = "meta-llama/Llama-3.1-8B-Instruct"
    hf_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    hf_provider: str = "auto"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
