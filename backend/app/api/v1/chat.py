"""BC12 chat endpoint with idempotency, cache, guardrails, and rate limiting."""

from __future__ import annotations

import asyncio
import time
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import bindparam, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import RetrievalUnavailableError, assemble_generation_payload
from app.cache.exact import lookup_exact_cache, write_exact_cache
from app.cache.exact import CacheHit
from app.cache.semantic import lookup_semantic_cache, write_semantic_cache
from app.chat.conversation import load_conversation_context
from app.chainlit_steps import chainlit_step
from app.core.cost import compute_cost
from app.core.errors import RateLimitExceededError, ValidationError
from app.database import get_db
from app.generation.client import GenerationClient, get_generation_client
from app.retrieval.models import RetrievalCandidate
from app.security.auth import require_auth
from app.security.guardrails import filter_output, validate_chat_message_for_audit
from app.security.rate_limit import enforce_chat_rate_limit, get_client_ip
from app.settings import settings

router = APIRouter(prefix="/api/v1", tags=["chat"])

UPLOAD_FIRST_MESSAGE = "Upload and index a PDF before starting chat so I can answer from your documents."
RETRIEVAL_UNAVAILABLE_MESSAGE = (
    "Retrieval is temporarily unavailable, so I cannot produce a grounded answer for this question."
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: UUID | None = None


class Citation(BaseModel):
    number: int
    chunk_id: UUID
    document_id: UUID
    document_title: str
    page_number: int | None = None
    section_path: str | None = None
    snippet: str | None = None


class ChatResponse(BaseModel):
    session_id: UUID
    answer: str
    cache_status: str
    source_chunk_ids: list[UUID]
    citations: list[Citation] = Field(default_factory=list)
    query_audit_log_id: UUID
    output_filter_status: str
    output_filter_reason: str | None = None


@router.post("/chat", response_model=None)
async def chat(
    payload: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse | JSONResponse:
    if not settings.anonymous_chat_allowed:
        await require_auth(request.headers.get("authorization"))

    started = time.monotonic()
    generation_client = _generation_client(request)
    session_id = await _ensure_session(db, payload.session_id)

    turn_seq = await _next_turn_seq(db, session_id)
    idempotency_key = f"{session_id}:{turn_seq}"
    client_ip = get_client_ip(request)
    try:
        audit_id = await _claim_audit_row(db, session_id, idempotency_key, payload.message, client_ip)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return await _wait_for_duplicate(db, session_id, idempotency_key)

    try:
        await validate_chat_message_for_audit(payload.message)
    except ValidationError:
        await _finalize_audit(
            db,
            audit_id=audit_id,
            cache_status="validation_rejected",
            input_validation_status="rejected",
            latency_ms=_latency(started),
        )
        await db.commit()
        raise

    try:
        await enforce_chat_rate_limit(db, session_id, client_ip)
    except RateLimitExceededError:
        await _finalize_audit(
            db,
            audit_id=audit_id,
            cache_status="rate_limited",
            latency_ms=_latency(started),
        )
        await db.commit()
        raise

    cache_hit = await _lookup_cache(db, payload.message, embedding_client=_embedding_client(request))
    if cache_hit is not None:
        return await _finalize_cached_hit(
            db,
            started,
            session_id,
            audit_id,
            payload.message,
            cache_hit.answer,
            cache_hit.cache_status,
        )

    indexed_count = await _indexed_document_count(db)
    if indexed_count == 0:
        return await _finalize_no_retrieval(
            db,
            started,
            session_id,
            audit_id,
            payload.message,
            UPLOAD_FIRST_MESSAGE,
            cache_status="miss",
        )

    conversation = await load_conversation_context(db, session_id, generation_client)
    try:
        payload_for_generation = await assemble_generation_payload(
            query=payload.message,
            session_id=session_id,
            db=db,
            retrieval_agent=getattr(request.app.state, "retrieval_agent", None),
            query_audit_log_id=audit_id,
            embedding_client=_embedding_client(request),
            reranker=getattr(request.app.state, "reranker", None),
            expansion_model_client=getattr(request.app.state, "expansion_model_client", None),
        )
    except RetrievalUnavailableError:
        return await _finalize_no_retrieval(
            db,
            started,
            session_id,
            audit_id,
            payload.message,
            RETRIEVAL_UNAVAILABLE_MESSAGE,
            cache_status="miss",
            grounded=False,
        )

    _inject_conversation_context(payload_for_generation.messages, conversation.messages)
    generated = await generation_client.generate(payload_for_generation, max_tokens=settings.max_output_tokens_chat)
    filtered = await filter_output(generated.answer, payload_for_generation.source_chunks)
    citations = _build_citations(payload_for_generation.source_chunks)
    source_doc_ids = sorted({chunk.document_id for chunk in payload_for_generation.source_chunks}, key=str)
    eligible = filtered.status == "passed"
    await write_exact_cache(db, payload.message, filtered.answer, source_doc_ids, eligible=eligible)
    await write_semantic_cache(
        db,
        payload.message,
        filtered.answer,
        source_doc_ids,
        eligible=eligible,
        embedding_client=_embedding_client(request),
    )
    await _insert_turn_messages(
        db,
        session_id,
        payload.message,
        filtered.answer,
        payload_for_generation.source_chunk_ids,
    )
    await _finalize_audit(
        db,
        audit_id=audit_id,
        cache_status="miss",
        retrieved_chunk_ids=payload_for_generation.source_chunk_ids,
        reranked=True,
        retrieval_mode=payload_for_generation.retrieval_mode,
        generation_model=generated.model,
        grounded=filtered.grounded,
        output_filter_status=filtered.status,
        output_filter_reason=filtered.reason,
        latency_ms=_latency(started),
        token_input=generated.token_input,
        token_output=generated.token_output,
        cost_usd=compute_cost(generated.model, generated.token_input, generated.token_output),
    )
    await db.commit()
    return ChatResponse(
        session_id=session_id,
        answer=filtered.answer,
        cache_status="miss",
        source_chunk_ids=payload_for_generation.source_chunk_ids,
        citations=citations,
        query_audit_log_id=audit_id,
        output_filter_status=filtered.status,
        output_filter_reason=filtered.reason,
    )


def _generation_client(request: Request) -> GenerationClient:
    return getattr(request.app.state, "generation_client", None) or get_generation_client()


def _embedding_client(request: Request) -> Any:
    return getattr(request.app.state, "embedding_client", None)


@chainlit_step("cache check", "tool")
async def _lookup_cache(
    db: AsyncSession,
    query: str,
    embedding_client: Any,
) -> CacheHit | None:
    exact_hit = await lookup_exact_cache(db, query)
    if exact_hit is not None:
        return exact_hit
    return await lookup_semantic_cache(db, query, embedding_client=embedding_client)


async def _ensure_session(db: AsyncSession, requested: UUID | None) -> UUID:
    if requested is None:
        row = (await db.execute(text("INSERT INTO chat_sessions DEFAULT VALUES RETURNING id"))).mappings().one()
        return row["id"]
    await db.execute(
        text("INSERT INTO chat_sessions (id) VALUES (:id) ON CONFLICT (id) DO NOTHING"),
        {"id": requested},
    )
    return requested


async def _next_turn_seq(db: AsyncSession, session_id: UUID) -> int:
    return int(
        (
            await db.execute(
                text("SELECT count(*) + 1 FROM chat_messages WHERE session_id = :session_id AND role = 'user'"),
                {"session_id": session_id},
            )
        ).scalar_one()
    )


async def _claim_audit_row(
    db: AsyncSession,
    session_id: UUID,
    idempotency_key: str,
    query: str,
    client_ip: str,
) -> UUID:
    row = (
        await db.execute(
            text(
                """
                INSERT INTO query_audit_log (session_id, idempotency_key, query, client_ip)
                VALUES (:session_id, :idempotency_key, :query, CAST(:client_ip AS inet))
                RETURNING id
                """
            ),
            {
                "session_id": session_id,
                "idempotency_key": idempotency_key,
                "query": query,
                "client_ip": client_ip,
            },
        )
    ).mappings().one()
    return row["id"]


async def _wait_for_duplicate(db: AsyncSession, session_id: UUID, idempotency_key: str) -> ChatResponse | JSONResponse:
    for _ in range(40):
        completed = await _completed_response_for_key(db, session_id, idempotency_key)
        if completed is not None:
            await db.rollback()
            return completed
        await db.rollback()
        await asyncio.sleep(0.25)
    return JSONResponse(
        status_code=202,
        headers={"Retry-After": "2"},
        content={"session_id": str(session_id), "status": "in_flight"},
    )


async def _completed_response_for_key(db: AsyncSession, session_id: UUID, idempotency_key: str) -> ChatResponse | None:
    audit = (
        await db.execute(
            text(
                """
                SELECT id, cache_status, output_filter_status, output_filter_reason, retrieved_chunk_ids, latency_ms
                FROM query_audit_log
                WHERE idempotency_key = :idempotency_key
                """
            ),
            {"idempotency_key": idempotency_key},
        )
    ).mappings().first()
    if audit is None or audit["latency_ms"] is None:
        return None
    answer = await _latest_assistant_answer(db, session_id)
    if answer is None:
        return None
    source_chunk_ids = list(audit["retrieved_chunk_ids"] or answer["source_chunk_ids"] or [])
    return ChatResponse(
        session_id=session_id,
        answer=answer["content"],
        cache_status=str(audit["cache_status"] or "miss"),
        source_chunk_ids=source_chunk_ids,
        citations=await _citations_for_chunk_ids(db, source_chunk_ids),
        query_audit_log_id=audit["id"],
        output_filter_status=str(audit["output_filter_status"]),
        output_filter_reason=audit["output_filter_reason"],
    )


async def _finalize_cached_hit(
    db: AsyncSession,
    started: float,
    session_id: UUID,
    audit_id: UUID,
    query: str,
    answer: str,
    cache_status: str,
) -> ChatResponse:
    await _insert_turn_messages(db, session_id, query, answer, [])
    await _finalize_audit(
        db,
        audit_id=audit_id,
        cache_status=cache_status,
        retrieved_chunk_ids=[],
        reranked=False,
        retrieval_mode="cache",
        generation_model=None,
        grounded=True,
        output_filter_status="passed",
        latency_ms=_latency(started),
        token_input=0,
        token_output=0,
        cost_usd=Decimal("0"),
    )
    await db.commit()
    return ChatResponse(
        session_id=session_id,
        answer=answer,
        cache_status=cache_status,
        source_chunk_ids=[],
        citations=[],
        query_audit_log_id=audit_id,
        output_filter_status="passed",
    )


async def _finalize_no_retrieval(
    db: AsyncSession,
    started: float,
    session_id: UUID,
    audit_id: UUID,
    query: str,
    answer: str,
    cache_status: str,
    grounded: bool = False,
) -> ChatResponse:
    await _insert_turn_messages(db, session_id, query, answer, [])
    await _finalize_audit(
        db,
        audit_id=audit_id,
        cache_status=cache_status,
        retrieved_chunk_ids=[],
        reranked=False,
        retrieval_mode="unavailable",
        generation_model=None,
        grounded=grounded,
        output_filter_status="passed",
        latency_ms=_latency(started),
        token_input=0,
        token_output=0,
        cost_usd=Decimal("0"),
    )
    await db.commit()
    return ChatResponse(
        session_id=session_id,
        answer=answer,
        cache_status=cache_status,
        source_chunk_ids=[],
        citations=[],
        query_audit_log_id=audit_id,
        output_filter_status="passed",
    )


async def _insert_turn_messages(
    db: AsyncSession,
    session_id: UUID,
    user_message: str,
    assistant_message: str,
    source_chunk_ids: list[UUID],
) -> None:
    await db.execute(
        text(
            """
            INSERT INTO chat_messages (session_id, role, content)
            VALUES (:session_id, 'user', :content)
            """
        ),
        {"session_id": session_id, "content": user_message},
    )
    await db.execute(
        text(
            """
            INSERT INTO chat_messages (session_id, role, content, source_chunk_ids)
            VALUES (:session_id, 'assistant', :content, :source_chunk_ids)
            """
        ),
        {"session_id": session_id, "content": assistant_message, "source_chunk_ids": source_chunk_ids},
    )
    await db.execute(
        text("UPDATE chat_sessions SET last_active_at = now() WHERE id = :session_id"),
        {"session_id": session_id},
    )


async def _finalize_audit(db: AsyncSession, audit_id: UUID, **fields: Any) -> None:
    assignments = ", ".join(f"{key} = :{key}" for key in fields)
    await db.execute(
        text(f"UPDATE query_audit_log SET {assignments} WHERE id = :audit_id"),
        {"audit_id": audit_id, **fields},
    )


async def _indexed_document_count(db: AsyncSession) -> int:
    return int((await db.execute(text("SELECT count(*) FROM documents WHERE status = 'indexed'"))).scalar_one())


async def _latest_assistant_answer(db: AsyncSession, session_id: UUID) -> dict[str, Any] | None:
    return (
        await db.execute(
            text(
                """
                SELECT content, source_chunk_ids
                FROM chat_messages
                WHERE session_id = :session_id AND role = 'assistant'
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """
            ),
            {"session_id": session_id},
        )
    ).mappings().first()


def _build_citations(chunks: list[RetrievalCandidate]) -> list[Citation]:
    citations: list[Citation] = []
    seen: set[UUID] = set()
    for chunk in chunks:
        if chunk.chunk_id in seen:
            continue
        seen.add(chunk.chunk_id)
        citations.append(
            Citation(
                number=len(citations) + 1,
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_title=chunk.document_filename,
                page_number=chunk.page_number,
                section_path=chunk.section_path,
                snippet=_citation_snippet(chunk.content),
            )
        )
    return citations


async def _citations_for_chunk_ids(db: AsyncSession, chunk_ids: list[UUID]) -> list[Citation]:
    if not chunk_ids:
        return []
    stmt = text(
        """
        SELECT c.id AS chunk_id, c.document_id, d.filename AS document_title,
               c.page_number, c.section_path, c.content
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.id IN :chunk_ids
        """
    ).bindparams(bindparam("chunk_ids", expanding=True))
    rows = (await db.execute(stmt, {"chunk_ids": chunk_ids})).mappings().all()
    by_id = {row["chunk_id"]: row for row in rows}
    citations: list[Citation] = []
    seen: set[UUID] = set()
    for chunk_id in chunk_ids:
        if chunk_id in seen:
            continue
        seen.add(chunk_id)
        row = by_id.get(chunk_id)
        if row is None:
            continue
        citations.append(
            Citation(
                number=len(citations) + 1,
                chunk_id=row["chunk_id"],
                document_id=row["document_id"],
                document_title=str(row["document_title"]),
                page_number=row["page_number"],
                section_path=row["section_path"],
                snippet=_citation_snippet(str(row["content"])),
            )
        )
    return citations


def _citation_snippet(content: str, limit: int = 240) -> str:
    normalized = " ".join(content.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1].rstrip()}..."


def _inject_conversation_context(messages: list[dict[str, Any]], conversation_messages: list[dict[str, str]]) -> None:
    if not conversation_messages or not messages:
        return
    content = messages[0].get("content")
    if not isinstance(content, list):
        return
    rendered = "\n".join(f"{item['role']}: {item['content']}" for item in conversation_messages)
    content.insert(0, {"type": "text", "text": f"Conversation history:\n{rendered}"})


def _latency(started: float) -> int:
    return int((time.monotonic() - started) * 1000)
