from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from knowledge_os.application.retrieval import RetrievalService
from knowledge_os.domain.entities import DocumentChunk, MembershipRole, Project, ProjectMembership
from tests.unit.fakes import FakeUnitOfWork, Store


@pytest.mark.asyncio
async def test_retrieval_service_search_success() -> None:
    store = Store()
    org_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    # Pre-populate store
    project = Project(
        id=project_id,
        organization_id=org_id,
        name="Test Project",
        created_by=user_id,
    )
    store.projects[project_id] = project
    store.project_memberships.append(
        ProjectMembership(
            organization_id=org_id,
            project_id=project_id,
            user_id=user_id,
            role=MembershipRole.OWNER,
        )
    )

    chunk_id_1 = uuid4()
    chunk_id_2 = uuid4()

    chunk1 = DocumentChunk(
        id=chunk_id_1,
        organization_id=org_id,
        document_id=uuid4(),
        version_id=uuid4(),
        chunk_index=1,
        content="This is chunk 1 content",
        char_offset=0,
        token_count=5,
        char_count=23,
    )
    chunk2 = DocumentChunk(
        id=chunk_id_2,
        organization_id=org_id,
        document_id=uuid4(),
        version_id=uuid4(),
        chunk_index=2,
        content="This is chunk 2 content",
        char_offset=23,
        token_count=5,
        char_count=23,
    )
    store.document_chunks.extend([chunk1, chunk2])

    # Mocks
    mock_provider = MagicMock()
    mock_provider.embed_batch = AsyncMock(return_value=[[0.1] * 1536])

    mock_vector_store = MagicMock()
    mock_vector_store.search_chunks = AsyncMock(
        return_value=[(chunk_id_2, 0.95), (chunk_id_1, 0.85)]
    )

    def uow_factory():
        return FakeUnitOfWork(store)

    service = RetrievalService(
        uow_factory=uow_factory,
        embedding_provider=mock_provider,
        vector_store=mock_vector_store,
    )

    results = await service.search(
        project_id=project_id,
        user_id=user_id,
        query="test query",
        top_k=5,
    )

    assert len(results) == 2
    # Verify order matches score descending (chunk 2 then chunk 1)
    assert results[0].chunk_id == chunk_id_2
    assert results[0].score == 0.95
    assert results[0].content == "This is chunk 2 content"
    assert results[0].chunk_number == 2

    assert results[1].chunk_id == chunk_id_1
    assert results[1].score == 0.85
    assert results[1].content == "This is chunk 1 content"
    assert results[1].chunk_number == 1

    mock_provider.embed_batch.assert_called_once_with(["test query"])
    mock_vector_store.search_chunks.assert_called_once_with(
        collection_name="document_chunks",
        organization_id=org_id,
        project_id=project_id,
        query_embedding=[0.1] * 1536,
        top_k=5,
    )


@pytest.mark.asyncio
async def test_retrieval_service_tenant_isolation_boundary() -> None:
    store = Store()
    org_id = uuid4()
    other_org_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    # Pre-populate store
    project = Project(
        id=project_id,
        organization_id=org_id,
        name="Test Project",
        created_by=user_id,
    )
    store.projects[project_id] = project
    store.project_memberships.append(
        ProjectMembership(
            organization_id=org_id,
            project_id=project_id,
            user_id=user_id,
            role=MembershipRole.OWNER,
        )
    )

    chunk_id_1 = uuid4()
    chunk_id_2 = uuid4()  # Cross-tenant chunk

    chunk1 = DocumentChunk(
        id=chunk_id_1,
        organization_id=org_id,
        document_id=uuid4(),
        version_id=uuid4(),
        chunk_index=1,
        content="Tenant chunk content",
        char_offset=0,
        token_count=5,
        char_count=20,
    )
    chunk2 = DocumentChunk(
        id=chunk_id_2,
        organization_id=other_org_id,  # Other tenant!
        document_id=uuid4(),
        version_id=uuid4(),
        chunk_index=2,
        content="Cross-tenant chunk content",
        char_offset=0,
        token_count=5,
        char_count=26,
    )
    store.document_chunks.extend([chunk1, chunk2])

    mock_provider = MagicMock()
    mock_provider.embed_batch = AsyncMock(return_value=[[0.1] * 1536])

    mock_vector_store = MagicMock()
    # Mock returns both, but service must filter out the cross-tenant one
    mock_vector_store.search_chunks = AsyncMock(
        return_value=[(chunk_id_1, 0.95), (chunk_id_2, 0.85)]
    )

    def uow_factory():
        return FakeUnitOfWork(store)

    service = RetrievalService(
        uow_factory=uow_factory,
        embedding_provider=mock_provider,
        vector_store=mock_vector_store,
    )

    results = await service.search(
        project_id=project_id,
        user_id=user_id,
        query="test query",
        top_k=5,
    )

    assert len(results) == 1
    assert results[0].chunk_id == chunk_id_1
    assert results[0].score == 0.95
