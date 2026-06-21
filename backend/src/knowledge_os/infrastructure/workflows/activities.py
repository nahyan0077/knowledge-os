from typing import Any
from uuid import UUID

from temporalio import activity

from knowledge_os.domain.common import NotFoundError
from knowledge_os.domain.entities import (
    DocumentChunk,
    DocumentVersionStatus,
    WorkflowEvent,
    WorkflowRunStatus,
    utc_now,
)
from knowledge_os.infrastructure.database.uow import SqlAlchemyUnitOfWork


@activity.defn
async def validate_document(payload: dict[str, Any]) -> dict[str, Any]:
    document_id = UUID(payload["document_id"])
    version_id = UUID(payload["version_id"])
    workflow_run_id = UUID(payload["workflow_run_id"])
    user_id = UUID(payload["user_id"])

    activity.logger.info(f"Validating document {document_id}")

    async with SqlAlchemyUnitOfWork() as uow:
        # Update workflow run status to RUNNING
        run = await uow.workflow_runs.get_by_id(workflow_run_id)
        if run:
            run.status = WorkflowRunStatus.RUNNING
            await uow.workflow_runs.save(run)

        event = WorkflowEvent(
            workflow_run_id=workflow_run_id,
            event_type="document_validation_started",
            payload={"document_id": str(document_id)},
        )
        await uow.workflow_events.add(event)
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

        event = WorkflowEvent(
            workflow_run_id=workflow_run_id,
            event_type="document_validation_completed",
            payload={"status": "valid"},
        )
        await uow.workflow_events.add(event)
        await uow.commit()

    return {"valid": True}


@activity.defn
async def extract_document_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    document_id = UUID(payload["document_id"])
    version_id = UUID(payload["version_id"])
    workflow_run_id = UUID(payload["workflow_run_id"])
    user_id = UUID(payload["user_id"])

    activity.logger.info(f"Extracting metadata for document {document_id}")

    async with SqlAlchemyUnitOfWork() as uow:
        event = WorkflowEvent(
            workflow_run_id=workflow_run_id,
            event_type="metadata_extraction_started",
            payload={"version_id": str(version_id)},
        )
        await uow.workflow_events.add(event)
        await uow.commit()

    async with SqlAlchemyUnitOfWork() as uow:
        version = await uow.documents.get_version_by_id(version_id, user_id)
        if not version:
            raise NotFoundError("Version not found", "version_not_found")

        metadata = {
            "filename": version.source_filename,
            "size_bytes": version.size_bytes,
            "mime_type": version.mime_type,
            "sha256": version.sha256,
        }

        event = WorkflowEvent(
            workflow_run_id=workflow_run_id,
            event_type="metadata_extraction_completed",
            payload=metadata,
        )
        await uow.workflow_events.add(event)
        await uow.commit()

    return metadata


@activity.defn
async def update_document_status(payload: dict[str, Any]) -> dict[str, Any]:
    document_id = UUID(payload["document_id"])
    version_id = UUID(payload["version_id"])
    workflow_run_id = UUID(payload["workflow_run_id"])
    user_id = UUID(payload["user_id"])
    new_status_str = payload["status"]

    activity.logger.info(f"Updating document {document_id} status to {new_status_str}")

    try:
        new_status = DocumentVersionStatus(new_status_str)
    except ValueError as err:
        raise ValueError(f"Invalid status: {new_status_str}") from err

    async with SqlAlchemyUnitOfWork() as uow:
        event = WorkflowEvent(
            workflow_run_id=workflow_run_id,
            event_type="document_status_update_started",
            payload={"target_status": new_status_str},
        )
        await uow.workflow_events.add(event)
        await uow.commit()

    async with SqlAlchemyUnitOfWork() as uow:
        version = await uow.documents.get_version_by_id(version_id, user_id)
        if not version:
            raise NotFoundError("Version not found", "version_not_found")

        version.status = new_status
        await uow.documents.save_version(version)

        event = WorkflowEvent(
            workflow_run_id=workflow_run_id,
            event_type="document_status_update_completed",
            payload={"status": new_status_str},
        )
        await uow.workflow_events.add(event)
        await uow.commit()

    return {"updated": True}


@activity.defn
async def finalize_workflow_run(payload: dict[str, Any]) -> dict[str, Any]:
    workflow_run_id = UUID(payload["workflow_run_id"])
    status_str = payload["status"]
    error_message = payload.get("error_message")

    activity.logger.info(f"Finalizing workflow run {workflow_run_id} to status {status_str}")

    try:
        status = WorkflowRunStatus(status_str)
    except ValueError as err:
        raise ValueError(f"Invalid status: {status_str}") from err

    async with SqlAlchemyUnitOfWork() as uow:
        run = await uow.workflow_runs.get_by_id(workflow_run_id)
        if run:
            run.status = status
            run.completed_at = utc_now()
            run.error_message = error_message
            await uow.workflow_runs.save(run)

            event = WorkflowEvent(
                workflow_run_id=workflow_run_id,
                event_type="workflow_finalized",
                payload={"status": status_str, "error_message": error_message},
            )
            await uow.workflow_events.add(event)
            await uow.commit()

    return {"finalized": True}


@activity.defn
async def extract_document_text(payload: dict[str, Any]) -> dict[str, Any]:
    document_id = UUID(payload["document_id"])
    version_id = UUID(payload["version_id"])
    workflow_run_id = UUID(payload["workflow_run_id"])
    user_id = UUID(payload["user_id"])

    activity.logger.info(f"Extracting text for document {document_id}")

    from knowledge_os.application.services.extraction import TextExtractor
    from knowledge_os.config import get_settings
    from knowledge_os.infrastructure.storage.factory import StorageFactory

    settings = get_settings()
    extractor = TextExtractor()

    # 1. Record extraction started event
    async with SqlAlchemyUnitOfWork() as uow:
        event = WorkflowEvent(
            workflow_run_id=workflow_run_id,
            event_type="document_extraction_started",
            payload={"version_id": str(version_id)},
        )
        await uow.workflow_events.add(event)
        await uow.commit()

    # 2. Retrieve version properties
    async with SqlAlchemyUnitOfWork() as uow:
        version = await uow.documents.get_version_by_id(version_id, user_id)
        if not version:
            raise NotFoundError("Version not found", "version_not_found")
        blob_path = version.blob_path
        mime_type = version.mime_type
        storage = StorageFactory.get_storage(settings, version.storage_provider)

    # 3. Download binary contents
    content_bytes = await storage.download(blob_path)

    # 4. Extract text with metadata
    result = extractor.extract_text_with_metadata(content_bytes, mime_type)
    extracted_text = result.text

    # 5. Save/upload extracted text to storage
    extracted_text_path = f"extracted_text/{version_id}.txt"
    await storage.upload(extracted_text_path, extracted_text.encode("utf-8"), "text/plain")

    # 6. Record extraction completed event and save version metadata
    async with SqlAlchemyUnitOfWork() as uow:
        version = await uow.documents.get_version_by_id(version_id, user_id)
        if version:
            version.extracted_characters = result.extracted_characters
            version.page_count = result.page_count
            await uow.documents.save_version(version)

        event = WorkflowEvent(
            workflow_run_id=workflow_run_id,
            event_type="document_text_extracted",
            payload={
                "extracted_text_path": extracted_text_path,
                "extracted_characters": result.extracted_characters,
                "page_count": result.page_count,
            },
        )
        await uow.workflow_events.add(event)
        await uow.commit()

    return {"extracted_text_path": extracted_text_path}


@activity.defn
async def chunk_document(payload: dict[str, Any]) -> dict[str, Any]:
    organization_id = UUID(payload["organization_id"])
    document_id = UUID(payload["document_id"])
    version_id = UUID(payload["version_id"])
    workflow_run_id = UUID(payload["workflow_run_id"])
    user_id = UUID(payload["user_id"])
    extracted_text_path = payload["extracted_text_path"]

    activity.logger.info(f"Chunking document {document_id} from {extracted_text_path}")

    from knowledge_os.application.services.extraction import TextChunker
    from knowledge_os.config import get_settings
    from knowledge_os.infrastructure.storage.factory import StorageFactory

    settings = get_settings()
    chunker = TextChunker()

    # 1. Record chunking started event
    async with SqlAlchemyUnitOfWork() as uow:
        event = WorkflowEvent(
            workflow_run_id=workflow_run_id,
            event_type="document_chunking_started",
            payload={"version_id": str(version_id)},
        )
        await uow.workflow_events.add(event)
        await uow.commit()

    # 2. Retrieve version properties
    async with SqlAlchemyUnitOfWork() as uow:
        version = await uow.documents.get_version_by_id(version_id, user_id)
        if not version:
            raise NotFoundError("Version not found", "version_not_found")
        storage = StorageFactory.get_storage(settings, version.storage_provider)

    # 3. Download extracted text
    content_bytes = await storage.download(extracted_text_path)
    text = content_bytes.decode("utf-8")

    # 3. Generate chunks
    chunks_data = chunker.chunk_text(text)

    # 4. Create chunk domain objects
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

    # 5. Persist chunks to DB and update run events (idempotent delete-and-insert batch)
    async with SqlAlchemyUnitOfWork() as uow:
        # Idempotency safety: delete any existing chunks for this version first
        await uow.document_chunks.delete_for_version(version_id)

        # Save new chunks
        await uow.document_chunks.add_batch(chunks)

        # Record completion event
        event = WorkflowEvent(
            workflow_run_id=workflow_run_id,
            event_type="document_chunking_completed",
            payload={"chunk_count": len(chunks)},
        )
        await uow.workflow_events.add(event)
        await uow.commit()

    return {"chunk_count": len(chunks)}


@activity.defn
async def generate_chunk_embeddings(payload: dict[str, Any]) -> dict[str, Any]:
    organization_id = UUID(payload["organization_id"])
    project_id = UUID(payload["project_id"])
    version_id = UUID(payload["version_id"])
    workflow_run_id = UUID(payload["workflow_run_id"])

    activity.logger.info(f"Generating chunk embeddings for version {version_id}")

    from knowledge_os.config import get_settings
    from knowledge_os.domain.entities import ChunkEmbedding
    from knowledge_os.infrastructure.ai.embeddings import EmbeddingProviderFactory
    from knowledge_os.infrastructure.search.qdrant import QdrantVectorStore

    settings = get_settings()
    provider = EmbeddingProviderFactory.get_provider(settings)
    vector_store = QdrantVectorStore(settings)

    # 1. Record embedding started event
    async with SqlAlchemyUnitOfWork() as uow:
        event = WorkflowEvent(
            workflow_run_id=workflow_run_id,
            event_type="document_embedding_started",
            payload={"version_id": str(version_id)},
        )
        await uow.workflow_events.add(event)
        await uow.commit()

    # 2. Load chunks for the version from PostgreSQL
    async with SqlAlchemyUnitOfWork() as uow:
        chunks = await uow.document_chunks.list_for_version(version_id)
        if not chunks:
            return {"chunk_count": 0, "embedding_count": 0}

    # 3. Extract text strings for batch embedding
    texts = [c.content for c in chunks]

    # 4. Generate embeddings via provider
    embeddings_vectors = await provider.embed_batch(texts)

    # 5. Create Qdrant collection (if not exists)
    collection_name = "document_chunks"
    await vector_store.create_collection(collection_name, provider.dimension)

    # 6. Idempotency safety: delete old vectors from Qdrant first
    await vector_store.delete_chunks_by_version(collection_name, version_id)

    # 7. Store new vectors in Qdrant
    chunk_ids = [c.id for c in chunks]
    await vector_store.upsert_chunks(
        collection_name=collection_name,
        vectors=embeddings_vectors,
        chunk_ids=chunk_ids,
        organization_id=organization_id,
        project_id=project_id,
        document_version_id=version_id,
    )

    # 8. Create and persist ChunkEmbedding metadata to PostgreSQL
    embedding_entities = []
    for chunk in chunks:
        qdrant_point_id = chunk.id
        embedding_entities.append(
            ChunkEmbedding(
                organization_id=organization_id,
                document_chunk_id=chunk.id,
                provider=provider.provider_name,
                model=provider.model_name,
                embedding_dimension=provider.dimension,
                embedding_version=provider.embedding_version,
                qdrant_point_id=qdrant_point_id,
            )
        )

    async with SqlAlchemyUnitOfWork() as uow:
        await uow.chunk_embeddings.delete_for_version(version_id, provider.embedding_version)
        await uow.chunk_embeddings.add_batch(embedding_entities)

        # Record completion event
        event = WorkflowEvent(
            workflow_run_id=workflow_run_id,
            event_type="document_embedding_completed",
            payload={
                "chunk_count": len(chunks),
                "embedding_version": provider.embedding_version,
            },
        )
        await uow.workflow_events.add(event)
        await uow.commit()

    return {"chunk_count": len(chunks), "embedding_count": len(embedding_entities)}
