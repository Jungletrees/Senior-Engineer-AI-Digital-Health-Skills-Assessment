"""Runtime settings for backend build cycles."""

from __future__ import annotations

import json
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized environment-backed settings used by agent orchestration."""

    agent_model: str = "claude-sonnet-5"
    ingestion_agent_max_iterations_hard_ceiling: int = 320
    agent_trace_logging_enabled: bool = True
    anthropic_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
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
    response_grading_sample_size: int = 50
    grading_job_cron: str = "0 2 * * *"
    anomaly_detection_zscore_threshold: float = 3.0
    anomaly_detection_baseline_lookback_days: int = 14
    scheduler_leader_lock_key: int = 91537
    model_pricing_json: str = (
        '{"claude-sonnet-5":{"input_per_mtok":3.0,"output_per_mtok":15.0},'
        '"claude-haiku-4-5":{"input_per_mtok":0.8,"output_per_mtok":4.0}}'
    )
    grounding_numeric_check_enabled: bool = True
    grounding_numeric_tolerance: float = 0.0
    # A factual answer with no surviving citation cannot be shown as grounded; it is
    # converted to the concise no-answer instead.
    require_sentence_citations: bool = True
    judge_model: str = "claude-haiku-4-5"
    judge_temperature: float = 0.0
    judge_rubric_version: int = 1
    grounding_tsvector_config: str = "english"
    gold_corpus_dir: str = "./gold_standard/corpus/files"
    gold_questions_path: str = "./gold_standard/questions.yaml"
    gold_rubric_path: str = "./gold_standard/rubric.yaml"
    gold_eval_judge_model: str | None = None
    gold_eval_concurrency: int = 2
    gold_eval_report_path: str = "./gold_standard/gold_eval_report.md"
    gold_eval_cron: str = "0 3 * * *"
    gold_eval_sample_size: int | None = None
    gold_eval_baseline_lookback_runs: int = 14
    gold_eval_min_overall_score: float = 90.0
    gold_eval_regression_points: float = 5.0
    gold_eval_deviation_abs_drop: float = 5.0
    gold_eval_deviation_zscore: float = 3.0
    gold_eval_alert_on_version_change: bool = False
    upload_storage_backend: str = "local"
    page_image_storage_backend: str = "local"
    s3_bucket_name: str | None = None
    aws_region: str | None = None
    s3_document_bucket: str | None = None
    s3_page_image_bucket: str | None = None

    @property
    def allowed_mime_type_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_mime_types.split(",") if item.strip()]

    @property
    def cors_allowed_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_allowed_origins.split(",") if item.strip()]

    @property
    def model_pricing(self) -> dict[str, dict[str, float]]:
        parsed: Any = json.loads(self.model_pricing_json or "{}")
        if not isinstance(parsed, dict):
            return {}
        pricing: dict[str, dict[str, float]] = {}
        for model, value in parsed.items():
            if not isinstance(model, str) or not isinstance(value, dict):
                continue
            try:
                pricing[model] = {
                    "input_per_mtok": float(value["input_per_mtok"]),
                    "output_per_mtok": float(value["output_per_mtok"]),
                }
            except (KeyError, TypeError, ValueError):
                continue
        return pricing

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
