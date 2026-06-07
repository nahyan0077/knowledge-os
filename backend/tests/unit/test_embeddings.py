from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from knowledge_os.config import Settings
from knowledge_os.infrastructure.ai.embeddings import OpenAIEmbeddingProvider
from knowledge_os.infrastructure.search.qdrant import QdrantVectorStore


@pytest.mark.asyncio
async def test_openai_embedding_provider_basic(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(openai_api_key="fake-key")
    provider = OpenAIEmbeddingProvider(settings)

    assert provider.provider_name == "openai"
    assert provider.model_name == "text-embedding-3-small"
    assert provider.dimension == 1536
    assert provider.embedding_version == 1

    mock_response = MagicMock()
    mock_item1 = MagicMock()
    mock_item1.index = 0
    mock_item1.embedding = [0.1] * 1536
    mock_item2 = MagicMock()
    mock_item2.index = 1
    mock_item2.embedding = [0.2] * 1536
    mock_response.data = [mock_item2, mock_item1]

    mock_embeddings_create = AsyncMock(return_value=mock_response)
    monkeypatch.setattr(provider.client.embeddings, "create", mock_embeddings_create)

    vectors = await provider.embed_batch(["text1", "text2"])
    assert len(vectors) == 2
    assert vectors[0] == [0.1] * 1536
    assert vectors[1] == [0.2] * 1536

    mock_embeddings_create.assert_called_once_with(
        model="text-embedding-3-small",
        input=["text1", "text2"],
    )


@pytest.mark.asyncio
async def test_qdrant_vector_store_operations(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(qdrant_url="http://fake-qdrant:6333")
    store = QdrantVectorStore(settings)

    mock_client = MagicMock()
    mock_client.collection_exists.return_value = False
    mock_client.create_collection.return_value = None
    mock_client.upsert.return_value = None
    mock_client.delete.return_value = None
    mock_client.retrieve.return_value = [MagicMock(payload={"chunk_id": "fake-chunk-id"})]

    store.client = mock_client

    # 1. Test Create Collection
    await store.create_collection("document_chunks", 1536)
    mock_client.collection_exists.assert_called_once_with("document_chunks")
    mock_client.create_collection.assert_called_once()

    # 2. Test Upsert Chunks
    chunk_id = uuid4()
    org_id = uuid4()
    project_id = uuid4()
    version_id = uuid4()
    await store.upsert_chunks(
        collection_name="document_chunks",
        vectors=[[0.5] * 1536],
        chunk_ids=[chunk_id],
        organization_id=org_id,
        project_id=project_id,
        document_version_id=version_id,
    )
    mock_client.upsert.assert_called_once()

    # 3. Test Delete
    await store.delete_chunks_by_version("document_chunks", version_id)
    mock_client.delete.assert_called_once()

    # 4. Test Fetch Metadata
    metadata = await store.fetch_chunk_metadata("document_chunks", chunk_id)
    assert metadata == {"chunk_id": "fake-chunk-id"}
    mock_client.retrieve.assert_called_once()
