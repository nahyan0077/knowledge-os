import logging
from typing import Any
from uuid import UUID

from knowledge_os.domain.common import NotFoundError
from knowledge_os.domain.entities import (
    ChunkEmbedding,
    DocumentChunk,
    DocumentVersionStatus,
    WorkflowEvent,
    WorkflowRunStatus,
    utc_now,
)
from knowledge_os.infrastructure.database.uow import SqlAlchemyUnitOfWork

logger = logging.getLogger(__name__)


async def _add_event(
    uow: SqlAlchemyUnitOfWork,
    workflow_run_id: UUID,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    event = WorkflowEvent(
        workflow_run_id=workflow_run_id,
        event_type=event_type,
        payload=payload,
    )
    await uow.workflow_events.add(event)


async def process_document_sync(payload: dict[str, Any]) -> None:
    document_id = UUID(payload["document_id"])
    version_id = UUID(payload["version_id"])
    workflow_run_id = UUID(payload["workflow_run_id"])
    user_id = UUID(payload["user_id"])
    organization_id = UUID(payload["organization_id"])
    project_id = UUID(payload["project_id"])

    logger.info(f"[sync] Processing document {document_id}")

    # 1. Validate & mark workflow as running
    async with SqlAlchemyUnitOfWork() as uow:
        run = await uow.workflow_runs.get_by_id(workflow_run_id)
        if run:
            run.status = WorkflowRunStatus.RUNNING
            await uow.workflow_runs.save(run)
        await _add_event(
            uow, workflow_run_id, "document_validation_started",
            {"document_id": str(document_id)},
        )
        await uow.commit()

    async with SqlAlchemyUnitOfWork() as uow:
        doc = await uow.documents.get_by_id(document_id, user_id)
        if not doc:
            raise NotFoundError("Document not found", "document_not_found")
        version = await uow.documents.get_version_by_id(version_id, user_id)
        if not version:
            raise NotFoundError("Document version not found", "version_not_found")
        if not version.blob_path:
            raise ValueError("Invalid blob path")
        await _add_event(uow, workflow_run_id, "document_validation_completed", {"status": "valid"})
        await uow.commit()

    # 2. Update status to processing
    await _update_status(version_id, user_id, workflow_run_id, DocumentVersionStatus.PROCESSING)

    # 3. Extract text
    from knowledge_os.application.services.extraction import TextExtractor
    from knowledge_os.config import get_settings
    from knowledge_os.infrastructure.storage.factory import StorageFactory

    settings = get_settings()
    extractor = TextExtractor()

    async with SqlAlchemyUnitOfWork() as uow:
        version = await uow.documents.get_version_by_id(version_id, user_id)
        if not version:
            raise NotFoundError("Version not found", "version_not_found")
        storage = StorageFactory.get_storage(settings, version.storage_provider)
        content_bytes = await storage.download(version.blob_path)
        result = extractor.extract_text_with_metadata(content_bytes, version.mime_type)
        extracted_text_path = f"extracted_text/{version_id}.txt"
        await storage.upload(extracted_text_path, result.text.encode("utf-8"), "text/plain")
        version.extracted_characters = result.extracted_characters
        version.page_count = result.page_count
        await uow.documents.save_version(version)
        await _add_event(uow, workflow_run_id, "document_text_extracted", {
            "extracted_text_path": extracted_text_path,
            "extracted_characters": result.extracted_characters,
            "page_count": result.page_count,
        })
        await uow.commit()

    # 4. Chunk document
    from knowledge_os.application.services.extraction import TextChunker

    chunker = TextChunker()

    async with SqlAlchemyUnitOfWork() as uow:
        version = await uow.documents.get_version_by_id(version_id, user_id)
        if not version:
            raise NotFoundError("Version not found", "version_not_found")
        storage = StorageFactory.get_storage(settings, version.storage_provider)
        content_bytes = await storage.download(extracted_text_path)
        text = content_bytes.decode("utf-8")
        chunks_data = chunker.chunk_text(text)
        chunks = [
            DocumentChunk(
                organization_id=organization_id,
                document_id=document_id,
                version_id=version_id,
                chunk_index=c["chunk_index"],
                content=c["content"],
                char_offset=c["char_offset"],
                token_count=c["token_count"],
                char_count=c["char_count"],
                page_start=c["page_start"] if version.mime_type == "application/pdf" else None,
                page_end=c["page_end"] if version.mime_type == "application/pdf" else None,
            )
            for c in chunks_data
        ]
        await uow.document_chunks.delete_for_version(version_id)
        await uow.document_chunks.add_batch(chunks)
        await _add_event(
            uow, workflow_run_id, "document_chunking_completed",
            {"chunk_count": len(chunks)},
        )
        await uow.commit()

    # 5. Generate embeddings & index to Qdrant
    from knowledge_os.infrastructure.ai.embeddings import EmbeddingProviderFactory
    from knowledge_os.infrastructure.search.qdrant import QdrantVectorStore

    provider = EmbeddingProviderFactory.get_provider(settings)
    vector_store = QdrantVectorStore(settings)

    async with SqlAlchemyUnitOfWork() as uow:
        chunks_list = list(await uow.document_chunks.list_for_version(version_id))
        if not chunks_list:
            logger.warning(f"[sync] No chunks found for version {version_id}")
            return

        texts = [c.content for c in chunks_list]
        embeddings_vectors = await provider.embed_batch(texts)

        collection_name = "document_chunks"
        await vector_store.create_collection(collection_name, provider.dimension)
        await vector_store.delete_chunks_by_version(collection_name, version_id)
        chunk_ids = [c.id for c in chunks_list]
        await vector_store.upsert_chunks(
            collection_name=collection_name,
            vectors=embeddings_vectors,
            chunk_ids=chunk_ids,
            organization_id=organization_id,
            project_id=project_id,
            document_version_id=version_id,
        )

        embedding_entities = [
            ChunkEmbedding(
                organization_id=organization_id,
                document_chunk_id=c.id,
                provider=provider.provider_name,
                model=provider.model_name,
                embedding_dimension=provider.dimension,
                embedding_version=provider.embedding_version,
                qdrant_point_id=c.id,
            )
            for c in chunks_list
        ]
        await uow.chunk_embeddings.delete_for_version(version_id, provider.embedding_version)
        await uow.chunk_embeddings.add_batch(embedding_entities)
        await _add_event(uow, workflow_run_id, "document_embedding_completed", {
            "chunk_count": len(chunks_list),
            "embedding_version": provider.embedding_version,
        })
        await uow.commit()

    # 6. Update status to indexed
    await _update_status(version_id, user_id, workflow_run_id, DocumentVersionStatus.INDEXED)

    # 7. Finalize workflow run
    async with SqlAlchemyUnitOfWork() as uow:
        run = await uow.workflow_runs.get_by_id(workflow_run_id)
        if run:
            run.status = WorkflowRunStatus.COMPLETED
            run.completed_at = utc_now()
            await uow.workflow_runs.save(run)
            await _add_event(uow, workflow_run_id, "workflow_finalized", {"status": "completed"})
            await uow.commit()

    logger.info(f"[sync] Document {document_id} processed successfully")


async def _update_status(
    version_id: UUID,
    user_id: UUID,
    workflow_run_id: UUID,
    status: DocumentVersionStatus,
) -> None:
    async with SqlAlchemyUnitOfWork() as uow:
        version = await uow.documents.get_version_by_id(version_id, user_id)
        if version:
            version.status = status
            await uow.documents.save_version(version)
        await _add_event(uow, workflow_run_id, "document_status_update_completed", {
            "status": status.value,
        })
        await uow.commit()
