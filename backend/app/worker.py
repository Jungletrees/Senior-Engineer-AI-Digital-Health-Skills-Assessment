"""Document ingestion worker entrypoint.

This module is the public worker surface used by upload/background tasks and
tests. The lower-level BC4 and BC5 implementations live in
``app.documents.processing`` and ``app.documents.chunking``.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from app.database import async_session
from app.documents.chunking import (
    EmbeddingClient,
    prepare_and_persist_document_chunks,
)
from app.documents.processing import process_document_structure, resolve_document_pdf_path
from app.models import Document

logger = logging.getLogger(__name__)

# Backward-compatible constant used by existing tests and BC3 upload storage.
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../uploads"))


async def process_document(
    document_id: UUID,
    embedding_client: EmbeddingClient | None = None,
) -> None:
    """Process one uploaded PDF through structure detection, chunking, and indexing."""
    logger.info("process_document.start document_id=%s", document_id)

    async with async_session() as db:
        logger.info("process_document.db_session.opened document_id=%s", document_id)
        try:
            logger.info("process_document.document.fetch.start document_id=%s", document_id)
            result = await db.execute(select(Document).where(Document.id == document_id))
            document = result.scalar_one_or_none()
            if document is None:
                logger.error("process_document.document.not_found document_id=%s", document_id)
                await db.rollback()
                logger.info("process_document.db.rollback.not_found document_id=%s", document_id)
                return

            logger.info(
                "process_document.document.loaded document_id=%s status=%s content_hash=%s",
                document.id,
                document.status,
                str(document.content_hash).strip(),
            )
            if document.status != "processing":
                logger.warning(
                    "process_document.document.skip_status document_id=%s status=%s",
                    document.id,
                    document.status,
                )
                await db.rollback()
                logger.info("process_document.db.rollback.skip_status document_id=%s", document.id)
                return

            pdf_path = resolve_document_pdf_path(document)
            logger.info(
                "process_document.file.resolve document_id=%s path=%s exists=%s",
                document.id,
                pdf_path,
                pdf_path.exists(),
            )
            if not pdf_path.exists():
                await _mark_document_failed(
                    db,
                    document,
                    f"Uploaded PDF not found at {pdf_path}",
                    stage="file_loading",
                )
                return

            file_size = _safe_file_size(pdf_path)
            logger.info(
                "process_document.file.loaded document_id=%s path=%s size_bytes=%s",
                document.id,
                pdf_path,
                file_size,
            )

            logger.info("process_document.pdf_parse.structure.start document_id=%s", document.id)
            structure_summary = await process_document_structure(db, document)
            logger.info(
                "process_document.pdf_parse.structure.complete "
                "document_id=%s processed_pages=%s rasterized_pages=%s table_pages=%s "
                "figure_pages=%s low_yield_pages=%s errors=%s",
                document.id,
                structure_summary.processed_pages,
                structure_summary.rasterized_pages,
                structure_summary.table_pages,
                structure_summary.figure_pages,
                structure_summary.low_yield_pages,
                structure_summary.errors,
            )
            if structure_summary.status == "failed":
                logger.error(
                    "process_document.structure.failed document_id=%s errors=%s",
                    document.id,
                    structure_summary.errors,
                )
                return

            logger.info("process_document.chunk_prepare.start document_id=%s", document.id)
            chunk_summary = await prepare_and_persist_document_chunks(
                db,
                document,
                embedding_client=embedding_client,
            )
            logger.info(
                "process_document.chunk_prepare.complete "
                "document_id=%s chunks=%s embeddings=%s model=%s",
                document.id,
                chunk_summary.chunk_count,
                chunk_summary.embedding_count,
                chunk_summary.embedding_model,
            )

            logger.info("process_document.status_update.start document_id=%s", document.id)
            document.status = "indexed"
            metadata = dict(document.metadata_ or {})
            metadata["chunking_status"] = "completed"
            metadata["embedding_model"] = chunk_summary.embedding_model
            metadata["indexed_chunk_count"] = chunk_summary.chunk_count
            document.metadata_ = metadata

            logger.info("process_document.db.commit.start document_id=%s", document.id)
            await db.commit()
            logger.info("process_document.db.commit.complete document_id=%s", document.id)
            logger.info("process_document.complete document_id=%s status=indexed", document.id)
        except Exception as exc:
            logger.exception(
                "process_document.exception document_id=%s stage=unhandled error=%s",
                document_id,
                exc,
            )
            await db.rollback()
            logger.info("process_document.db.rollback.exception document_id=%s", document_id)
            await _mark_document_failed_in_new_transaction(document_id, str(exc))
            raise
        finally:
            logger.info("process_document.db_session.closed document_id=%s", document_id)


async def _mark_document_failed(
    db,
    document: Document,
    message: str,
    stage: str,
) -> None:
    logger.error(
        "process_document.%s.failed document_id=%s error=%s",
        stage,
        document.id,
        message,
    )
    document.status = "failed"
    metadata = dict(document.metadata_ or {})
    metadata["processing_error"] = message
    metadata["processing_error_stage"] = stage
    document.metadata_ = metadata
    logger.info("process_document.db.commit.start document_id=%s status=failed", document.id)
    await db.commit()
    logger.info("process_document.db.commit.complete document_id=%s status=failed", document.id)


async def _mark_document_failed_in_new_transaction(document_id: UUID, message: str) -> None:
    async with async_session() as db:
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        if document is None:
            logger.error(
                "process_document.failure_mark.not_found document_id=%s error=%s",
                document_id,
                message,
            )
            return
        await _mark_document_failed(db, document, message, stage="exception")


def _safe_file_size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None
