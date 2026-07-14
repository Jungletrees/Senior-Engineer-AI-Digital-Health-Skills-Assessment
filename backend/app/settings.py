"""Runtime settings for backend build cycles."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized environment-backed settings used by agent orchestration."""

    agent_model: str = "claude-sonnet-5"
    ingestion_agent_max_iterations_hard_ceiling: int = 320
    agent_trace_logging_enabled: bool = True
    anthropic_api_key: str = ""
    retrieval_top_k: int = 20
    hybrid_search_enabled: bool = True
    rrf_k: int = 60
    hnsw_ef_search: int = 40
    rerank_top_n: int = 5
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    rerank_provider: str = ""
    retrieval_agent_confidence_threshold: float = 0.55
    retrieval_agent_max_iterations: int = 3
    generation_model_primary: str = "claude-sonnet-5"
    generation_model_fast: str = "claude-haiku-4-5"
    exact_cache_ttl_seconds: int = 86400
    semantic_cache_enabled: bool = True
    semantic_cache_threshold: float = 0.92
    prompt_caching_enabled: bool = True
    cache_backend: str = "postgres"
    cache_eviction_cron: str = "0 * * * *"
    enable_scheduled_jobs: bool = True
    semantic_cache_max_rows: int = 5000
    conversation_window_turns: int = 6
    conversation_summary_trigger_tokens: int = 2000
    max_output_tokens_chat: int = 500
    max_output_tokens_summary: int = 200
    anonymous_chat_allowed: bool = True
    chainlit_auth_secret: str | None = None
    max_pdf_size_mb: int = 20
    max_pdf_pages: int = 300
    allowed_mime_types: str = "application/pdf"
    request_body_size_limit_bytes: int = 25 * 1024 * 1024
    cors_allowed_origins: str = "http://localhost:3000,http://localhost:8000"
    jwt_secret: str = "dev-only-change-me"
    session_token_expiry_minutes: int = 60
    rate_limit_per_session_per_hour: int = 30
    rate_limit_window_seconds: int = 3600
    rate_limit_per_ip_per_hour: int = 100

    @property
    def allowed_mime_type_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_mime_types.split(",") if item.strip()]

    @property
    def cors_allowed_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_allowed_origins.split(",") if item.strip()]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
