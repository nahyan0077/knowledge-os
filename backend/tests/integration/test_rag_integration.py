from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from knowledge_os.application.context_builder import ContextBuilder
from knowledge_os.application.rag import RagService
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
async def test_rag_integration_e2e(db_session) -> None:
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
        content="Grounded facts: RAG is amazing.",
        char_offset=0,
        token_count=10,
        char_count=30,
    )
    await chunk_repo.add_batch([chunk_a])
    await db_session.commit()

    # 2. Setup dependencies and RAG Service
    mock_provider = MagicMock()
    mock_provider.embed_batch = AsyncMock(return_value=[[0.1] * 1536])

    mock_vector_store = MagicMock()
    mock_vector_store.search_chunks = AsyncMock(return_value=[(chunk_a_id, 0.95)])

    from knowledge_os.infrastructure.database.uow import SqlAlchemyUnitOfWork

    class TestUOW(SqlAlchemyUnitOfWork):
        async def __aenter__(self):
            self.session = db_session
            from knowledge_os.infrastructure.repositories.sqlalchemy import (
                SqlAlchemyDocumentChunkRepository,
                SqlAlchemyProjectRepository,
            )

            self.projects = SqlAlchemyProjectRepository(self.session)
            self.document_chunks = SqlAlchemyDocumentChunkRepository(self.session)
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    retrieval_service = RetrievalService(
        uow_factory=TestUOW,
        embedding_provider=mock_provider,
        vector_store=mock_vector_store,
    )

    context_builder = ContextBuilder(default_token_budget=100)

    mock_chat_agent = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Answer: RAG is amazing."
    mock_chat_agent.generate = AsyncMock(return_value=mock_response)

    rag_service = RagService(
        retrieval_service=retrieval_service,
        context_builder=context_builder,
        chat_agent=mock_chat_agent,
    )

    # 3. Perform Ask
    answer, citations = await rag_service.ask(
        project_id=project_a_id,
        user_id=user_a_id,
        question="Is RAG amazing?",
    )

    # 4. Assertions
    assert answer == "Answer: RAG is amazing."
    assert len(citations) == 1
    assert citations[0].chunk_id == chunk_a_id
    assert citations[0].document_version_id == version_a_id
    assert citations[0].score == 0.95

    # 5. Verify tenant isolation (Unauthorized User B)
    user_b_id = uuid4()
    with pytest.raises(NotFoundError):
        await rag_service.ask(
            project_id=project_a_id,
            user_id=user_b_id,
            question="Is RAG amazing?",
        )
