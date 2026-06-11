from collections.abc import Callable, Sequence
from dataclasses import dataclass
from uuid import UUID

from knowledge_os.application.ports import EmbeddingProvider, VectorStorePort
from knowledge_os.domain.common import NotFoundError
from knowledge_os.domain.repositories import UnitOfWork


@dataclass(slots=True)
class ScoredChunk:
    chunk_id: UUID
    score: float
    content: str
    document_version_id: UUID
    chunk_number: int
    token_count: int


class RetrievalService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStorePort,
    ) -> None:
        self._uow_factory = uow_factory
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store

    async def search(
        self,
        project_id: UUID,
        user_id: UUID,
        query: str,
        top_k: int = 10,
        document_ids: Sequence[UUID] | None = None,
    ) -> list[ScoredChunk]:
        async with self._uow_factory() as uow:
            # 1. Authorize user has read access to the project
            project = await uow.projects.get_for_user(project_id, user_id)
            if project is None:
                raise NotFoundError("Project not found", "project_not_found")

            # Get organization_id from project
            organization_id = project.organization_id

        # Resolve document_ids to version_ids
        document_version_ids = None
        if document_ids is not None:
            document_version_ids = []
            async with self._uow_factory() as uow:
                for doc_id in document_ids:
                    doc = await uow.documents.get_by_id(doc_id, user_id)
                    if doc and doc.current_version_id:
                        document_version_ids.append(doc.current_version_id)
            if not document_version_ids:
                return []

        # 2. Generate embedding for query
        query_embeddings = await self._embedding_provider.embed_batch([query])
        if not query_embeddings:
            return []
        query_embedding = query_embeddings[0]

        # 3. Search Qdrant for candidate chunk IDs and similarity scores
        candidates = await self._vector_store.search_chunks(
            collection_name="document_chunks",
            organization_id=organization_id,
            project_id=project_id,
            query_embedding=query_embedding,
            top_k=top_k,
            document_version_ids=document_version_ids,
        )
        if not candidates:
            return []

        # Keep a mapping of chunk_id -> score for ordering and scoring
        scores_map = {chunk_id: score for chunk_id, score in candidates}
        chunk_ids = list(scores_map.keys())

        # 4. Hydrate chunk content from PostgreSQL
        async with self._uow_factory() as uow:
            chunks = await uow.document_chunks.list_by_ids(chunk_ids)

        # 5. Build results, preserving Qdrant search score order
        scored_chunks = []
        for chunk in chunks:
            # Verify the chunk belongs to the project/organization
            if chunk.organization_id != organization_id:
                continue
            score = scores_map.get(chunk.id, 0.0)
            scored_chunks.append(
                ScoredChunk(
                    chunk_id=chunk.id,
                    score=score,
                    content=chunk.content,
                    document_version_id=chunk.version_id,
                    chunk_number=chunk.chunk_index,
                    token_count=chunk.token_count,
                )
            )

        # Sort the hydrated chunks descending by score to match vector search results
        scored_chunks.sort(key=lambda x: x.score, reverse=True)
        return scored_chunks
