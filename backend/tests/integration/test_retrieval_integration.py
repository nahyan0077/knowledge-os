from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from knowledge_os.application.retrieval import RetrievalService
from knowledge_os.domain.common import NotFoundError
from knowledge_os.domain.entities import (
    Document,
    DocumentChunk,
    DocumentVersion,
    DocumentVersionStatus,
    MembershipRole,
    OrganizationType,
)
from knowledge_os.infrastructure.database.models import (
    Base,
    OrganizationMemberModel,
    OrganizationModel,
    ProjectMemberModel,
    ProjectModel,
    UserModel,
)
from knowledge_os.infrastructure.repositories.sqlalchemy import (
    SqlAlchemyDocumentChunkRepository,
    SqlAlchemyDocumentRepository,
)


@pytest.fixture(scope="session")
def postgres_container():
    container = PostgresContainer("postgres:16-alpine")
    container.start()
    try:
        yield container
    finally:
        container.stop()


@pytest_asyncio.fixture
async def db_session(postgres_container):
    host_port = postgres_container.get_exposed_port(5432)
    db_url = f"postgresql+asyncpg://test:test@localhost:{host_port}/test"

    engine = create_async_engine(db_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_retrieval_integration_with_db_hydration_and_tenant_isolation(
    db_session,
) -> None:
    # 1. Setup Tenant A
    user_a_id = uuid4()
    org_a_id = uuid4()
    project_a_id = uuid4()
    doc_a_id = uuid4()
    version_a_id = uuid4()
    chunk_a_id = uuid4()

    db_session.add(
        UserModel(
            id=user_a_id,
            email="user_a@example.com",
            display_name="User A",
            password_hash="hash",
            status="active",
        )
    )
    db_session.add(
        OrganizationModel(
            id=org_a_id,
            name="Org A",
            slug="org-a",
            type=OrganizationType.PERSONAL,
        )
    )
    await db_session.flush()

    db_session.add(
        OrganizationMemberModel(
            organization_id=org_a_id, user_id=user_a_id, role=MembershipRole.OWNER
        )
    )
    db_session.add(
        ProjectModel(
            id=project_a_id,
            organization_id=org_a_id,
            name="Project A",
            created_by=user_a_id,
        )
    )
    await db_session.flush()

    db_session.add(
        ProjectMemberModel(
            organization_id=org_a_id,
            project_id=project_a_id,
            user_id=user_a_id,
            role=MembershipRole.OWNER,
        )
    )
    await db_session.flush()

    doc_repo = SqlAlchemyDocumentRepository(db_session)
    doc_a = Document(
        id=doc_a_id,
        organization_id=org_a_id,
        project_id=project_a_id,
        name="Doc A",
        created_by=user_a_id,
    )
    await doc_repo.add(doc_a)
    await db_session.flush()

    ver_a = DocumentVersion(
        id=version_a_id,
        organization_id=org_a_id,
        document_id=doc_a_id,
        version_number=1,
        blob_path="path/to/blob/a",
        source_filename="doc_a.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        sha256="hasha",
        etag="etaga",
        status=DocumentVersionStatus.UPLOADED,
    )
    await doc_repo.add_version(ver_a)
    await db_session.flush()

    chunk_repo = SqlAlchemyDocumentChunkRepository(db_session)
    chunk_a = DocumentChunk(
        id=chunk_a_id,
        organization_id=org_a_id,
        document_id=doc_a_id,
        version_id=version_a_id,
        chunk_index=0,
        content="This is chunk A content from Org A.",
        char_offset=0,
        token_count=8,
        char_count=36,
    )
    await chunk_repo.add_batch([chunk_a])
    await db_session.flush()

    # 2. Setup Tenant B (Cross Tenant)
    user_b_id = uuid4()
    org_b_id = uuid4()
    project_b_id = uuid4()
    doc_b_id = uuid4()
    version_b_id = uuid4()
    chunk_b_id = uuid4()

    db_session.add(
        UserModel(
            id=user_b_id,
            email="user_b@example.com",
            display_name="User B",
            password_hash="hash",
            status="active",
        )
    )
    db_session.add(
        OrganizationModel(
            id=org_b_id,
            name="Org B",
            slug="org-b",
            type=OrganizationType.PERSONAL,
        )
    )
    await db_session.flush()

    db_session.add(
        OrganizationMemberModel(
            organization_id=org_b_id, user_id=user_b_id, role=MembershipRole.OWNER
        )
    )
    db_session.add(
        ProjectModel(
            id=project_b_id,
            organization_id=org_b_id,
            name="Project B",
            created_by=user_b_id,
        )
    )
    await db_session.flush()

    doc_b = Document(
        id=doc_b_id,
        organization_id=org_b_id,
        project_id=project_b_id,
        name="Doc B",
        created_by=user_b_id,
    )
    await doc_repo.add(doc_b)
    await db_session.flush()

    ver_b = DocumentVersion(
        id=version_b_id,
        organization_id=org_b_id,
        document_id=doc_b_id,
        version_number=1,
        blob_path="path/to/blob/b",
        source_filename="doc_b.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        sha256="hashb",
        etag="etagb",
        status=DocumentVersionStatus.UPLOADED,
    )
    await doc_repo.add_version(ver_b)
    await db_session.flush()

    chunk_b = DocumentChunk(
        id=chunk_b_id,
        organization_id=org_b_id,
        document_id=doc_b_id,
        version_id=version_b_id,
        chunk_index=0,
        content="This is chunk B content from Org B.",
        char_offset=0,
        token_count=8,
        char_count=36,
    )
    await chunk_repo.add_batch([chunk_b])
    await db_session.commit()

    # 3. Setup RetrievalService with Mocks
    mock_provider = MagicMock()
    mock_provider.embed_batch = AsyncMock(return_value=[[0.2] * 1536])

    mock_vector_store = MagicMock()
    # Mock search_chunks returns both chunk_a_id and chunk_b_id.
    # The service must filter out chunk_b_id because it belongs to Org B.
    mock_vector_store.search_chunks = AsyncMock(
        return_value=[(chunk_a_id, 0.95), (chunk_b_id, 0.85)]
    )

    from knowledge_os.infrastructure.database.uow import SqlAlchemyUnitOfWork

    class TestUOW(SqlAlchemyUnitOfWork):
        async def __aenter__(self):
            self.session = db_session
            # Override repositories to use the active session
            from knowledge_os.infrastructure.repositories.sqlalchemy import (
                SqlAlchemyDocumentChunkRepository,
                SqlAlchemyDocumentRepository,
                SqlAlchemyProjectRepository,
            )

            self.projects = SqlAlchemyProjectRepository(self.session)
            self.document_chunks = SqlAlchemyDocumentChunkRepository(self.session)
            self.documents = SqlAlchemyDocumentRepository(self.session)
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    service = RetrievalService(
        uow_factory=TestUOW,
        embedding_provider=mock_provider,
        vector_store=mock_vector_store,
    )

    # 4. Perform search as User A for Project A
    results = await service.search(
        project_id=project_a_id,
        user_id=user_a_id,
        query="retrieval test",
        top_k=5,
    )

    # 5. Assert database hydration and tenant isolation
    assert len(results) == 1
    assert results[0].chunk_id == chunk_a_id
    assert results[0].score == 0.95
    assert results[0].content == "This is chunk A content from Org A."
    assert results[0].document_version_id == version_a_id
    assert results[0].chunk_number == 0

    # 6. Verify cross-tenant access is prohibited (User B attempting to read Project A)
    with pytest.raises(NotFoundError):
        await service.search(
            project_id=project_a_id,
            user_id=user_b_id,
            query="unauthorized search",
            top_k=5,
        )
