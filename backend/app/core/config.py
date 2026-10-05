"""Application settings, loaded from environment / `.env`.

Every value the platform needs is declared here; see `.env.example` for the
documented list. Nothing in this module performs I/O.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _split_csv(value: Any) -> Any:
    """Accept `a,b,c` for list-valued settings.

    pydantic-settings JSON-decodes complex types by default, which turns the
    usual comma-separated form into a validation error.
    """
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ core
    app_name: str = "Contexta Py"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = "insecure-development-key"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, value: Any) -> Any:
        return _split_csv(value)

    # -------------------------------------------------------------- postgres
    postgres_user: str = "contexta"
    postgres_password: str = "contexta"
    postgres_db: str = "contexta"
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    database_url: str = "postgresql+asyncpg://contexta:contexta@postgres:5432/contexta"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False

    # ----------------------------------------------------------- redis / arq
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_url: str = "redis://redis:6379/0"
    arq_job_timeout: int = 1800
    arq_max_jobs: int = 2

    # --------------------------------------------------------------- qdrant
    qdrant_url: str = "http://qdrant:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "contexta_chunks"
    qdrant_prefer_grpc: bool = False

    # --------------------------------------------------------- s3 / rustfs
    # `minio_endpoint` is container-internal; presigned URLs must be signed
    # against the browser-reachable host or the signature will not validate.
    minio_endpoint: str = "http://minio:9000"
    minio_public_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "contexta"
    minio_secret_key: str = "contexta123"
    minio_bucket: str = "contexta"
    minio_secure: bool = False
    minio_presign_expires: int = 3600
    minio_region: str = "us-east-1"

    # ------------------------------------------------------------ embeddings
    embedding_model: str = "BAAI/bge-base-en-v1.5"
    embedding_dim: int = 768
    embedding_batch_size: int = 32
    embedding_backend: Literal["fastembed", "hash"] = "fastembed"
    embedding_concurrency: int = 2
    model_cache_dir: str = "/models"
    #: bge retrieval models expect this prefix on the query side only.
    embedding_query_prefix: str = "query: "
    sparse_model: str = "Qdrant/bm25"

    # ------------------------------------------------------ parser / chunker
    parser: Literal["pymupdf", "docling"] = "pymupdf"
    chunk_parent_size: int = 2000
    chunk_child_size: int = 400
    chunk_child_overlap: int = 60
    chunk_min_size: int = 40
    #: A line repeated on more than this fraction of pages is a page artefact.
    header_footer_ratio: float = 0.6

    # ------------------------------------------------------------- retrieval
    retrieval_candidates: int = 40
    retrieval_top_k: int = 8
    retrieval_max_chars: int = 1500
    rrf_k: int = 60
    rerank_top_k: int = 5
    rerank_min_score: float = 0.0
    rerank_model: str = "ms-marco-MiniLM-L-12-v2"
    grader_threshold: int = 70
    grader_concurrency: int = 8
    multiquery_count: int = 3

    # ------------------------------------------------------------------- llm
    groq_api_key: str | None = None
    llm_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1500
    llm_backend: Literal["groq", "mock"] = "groq"
    llm_timeout: float = 60.0
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # ----------------------------------------------------------- web search
    tavily_api_key: str | None = None
    web_search_enabled: bool = True
    web_search_max_results: int = 5

    # ------------------------------------------------------------------ tts
    tts_enabled: bool = True
    tts_voice: str = "en-US-AriaNeural"
    tts_max_chars: int = 5000

    # ------------------------------------------------------------ ingestion
    worker_dispatch_enabled: bool = True
    model_download_on_startup: bool = True
    max_upload_bytes: int = 200 * 1024 * 1024
    allowed_upload_extensions: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [".pdf"]
    )

    @field_validator("allowed_upload_extensions", mode="before")
    @classmethod
    def _parse_extensions(cls, value: Any) -> Any:
        return _split_csv(value)

    # ----------------------------------------------------------------- chat
    chat_max_query_chars: int = 2000
    chat_rate_limit_per_minute: int = 20
    chat_heartbeat_seconds: int = 15

    @property
    def groq_configured(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def tavily_configured(self) -> bool:
        return bool(self.tavily_api_key) and self.web_search_enabled

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached accessor so the environment is parsed exactly once per process."""
    return Settings()
