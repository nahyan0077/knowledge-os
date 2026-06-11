import logging
from typing import Any
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest_models

from knowledge_os.application.ports import VectorStorePort
from knowledge_os.config import Settings

logger = logging.getLogger(__name__)


class QdrantVectorStore(VectorStorePort):
    def __init__(self, settings: Settings) -> None:
        self.client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=settings.qdrant_timeout,
        )

    async def create_collection(self, collection_name: str, dimension: int) -> None:
        try:
            exists = self.client.collection_exists(collection_name)
            if not exists:
                logger.info(
                    f"Creating Qdrant collection: {collection_name} with dimension {dimension}"
                )
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=rest_models.VectorParams(
                        size=dimension,
                        distance=rest_models.Distance.COSINE,
                    ),
                )
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            raise e

    async def upsert_chunks(
        self,
        collection_name: str,
        vectors: list[list[float]],
        chunk_ids: list[UUID],
        organization_id: UUID,
        project_id: UUID,
        document_version_id: UUID,
    ) -> None:
        points = []
        for vector, chunk_id in zip(vectors, chunk_ids, strict=False):
            points.append(
                rest_models.PointStruct(
                    id=str(chunk_id),
                    vector=vector,
                    payload={
                        "chunk_id": str(chunk_id),
                        "organization_id": str(organization_id),
                        "project_id": str(project_id),
                        "document_version_id": str(document_version_id),
                    },
                )
            )
        try:
            logger.info(f"Upserting {len(points)} points into Qdrant collection {collection_name}")
            self.client.upsert(
                collection_name=collection_name,
                points=points,
            )
        except Exception as e:
            logger.error(f"Failed to upsert points to collection {collection_name}: {e}")
            raise e

    async def delete_chunks_by_version(
        self,
        collection_name: str,
        document_version_id: UUID,
    ) -> None:
        try:
            logger.info(
                f"Deleting points for version {document_version_id} "
                f"from collection {collection_name}"
            )
            self.client.delete(
                collection_name=collection_name,
                points_selector=rest_models.FilterSelector(
                    filter=rest_models.Filter(
                        must=[
                            rest_models.FieldCondition(
                                key="document_version_id",
                                match=rest_models.MatchValue(value=str(document_version_id)),
                            )
                        ]
                    )
                ),
            )
        except Exception as e:
            logger.error(f"Failed to delete points for version {document_version_id}: {e}")
            raise e

    async def fetch_chunk_metadata(
        self,
        collection_name: str,
        chunk_id: UUID,
    ) -> dict[str, Any] | None:
        try:
            res = self.client.retrieve(
                collection_name=collection_name,
                ids=[str(chunk_id)],
                with_payload=True,
                with_vectors=False,
            )
            if res:
                return res[0].payload
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve metadata for point {chunk_id}: {e}")
            return None

    async def search_chunks(
        self,
        collection_name: str,
        organization_id: UUID,
        project_id: UUID,
        query_embedding: list[float],
        top_k: int = 10,
    ) -> list[tuple[UUID, float]]:
        query_filter = rest_models.Filter(
            must=[
                rest_models.FieldCondition(
                    key="organization_id",
                    match=rest_models.MatchValue(value=str(organization_id)),
                ),
                rest_models.FieldCondition(
                    key="project_id",
                    match=rest_models.MatchValue(value=str(project_id)),
                ),
            ]
        )
        try:
            results = self.client.query_points(
                collection_name=collection_name,
                query=query_embedding,
                query_filter=query_filter,
                limit=top_k,
                with_payload=False,
                with_vectors=False,
            )
            return [(UUID(str(res.id)), res.score) for res in results.points]
        except Exception as e:
            logger.error(f"Failed to search collection {collection_name}: {e}")
            raise e
