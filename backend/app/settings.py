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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
