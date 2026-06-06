from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

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
async def test_sqlalchemy_document_chunk_repository_lifecycle(db_session) -> None:
    user_id = uuid4()
    org_id = uuid4()
    project_id = uuid4()
    doc_id = uuid4()
    version_id = uuid4()

    # Pre-populate required foreign keys
    db_session.add(
        UserModel(
            id=user_id,
            email="chunk_integration@example.com",
            display_name="Chunk Integration",
            password_hash="hash",
            status="active",
        )
    )
    db_session.add(
        OrganizationModel(
            id=org_id,
            name="Test Org",
            slug="test-org",
            type=OrganizationType.PERSONAL,
        )
    )
    await db_session.flush()

    db_session.add(
        OrganizationMemberModel(organization_id=org_id, user_id=user_id, role=MembershipRole.OWNER)
    )
    db_session.add(
        ProjectModel(
            id=project_id,
            organization_id=org_id,
            name="Test Project",
            created_by=user_id,
        )
    )
    await db_session.flush()

    db_session.add(
        ProjectMemberModel(
            organization_id=org_id,
            project_id=project_id,
            user_id=user_id,
            role=MembershipRole.OWNER,
        )
    )
    await db_session.flush()

    doc_repo = SqlAlchemyDocumentRepository(db_session)
    doc = Document(
        id=doc_id,
        organization_id=org_id,
        project_id=project_id,
        name="Reports",
        created_by=user_id,
    )
    await doc_repo.add(doc)
    await db_session.flush()

    ver = DocumentVersion(
        id=version_id,
        organization_id=org_id,
        document_id=doc.id,
        version_number=1,
        blob_path="path/to/blob",
        source_filename="report.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        sha256="hash123",
        etag="etag123",
        status=DocumentVersionStatus.UPLOADED,
    )
    await doc_repo.add_version(ver)
    await db_session.flush()

    chunk_repo = SqlAlchemyDocumentChunkRepository(db_session)

    # 1. Add batch of chunks
    chunk_1 = DocumentChunk(
        organization_id=org_id,
        document_id=doc_id,
        version_id=version_id,
        chunk_index=0,
        content="This is chunk 0",
        char_offset=0,
        token_count=4,
    )
    chunk_2 = DocumentChunk(
        organization_id=org_id,
        document_id=doc_id,
        version_id=version_id,
        chunk_index=1,
        content="This is chunk 1",
        char_offset=15,
        token_count=4,
    )
    await chunk_repo.add_batch([chunk_1, chunk_2])
    await db_session.flush()

    # 2. List and Assert
    chunks = await chunk_repo.list_for_version(version_id)
    assert len(chunks) == 2
    assert chunks[0].chunk_index == 0
    assert chunks[0].content == "This is chunk 0"
    assert chunks[0].char_offset == 0
    assert chunks[0].token_count == 4
    assert chunks[1].chunk_index == 1
    assert chunks[1].content == "This is chunk 1"
    assert chunks[1].char_offset == 15
    assert chunks[1].token_count == 4

    # 3. Delete and Assert
    await chunk_repo.delete_for_version(version_id)
    await db_session.flush()

    deleted_chunks = await chunk_repo.list_for_version(version_id)
    assert len(deleted_chunks) == 0
