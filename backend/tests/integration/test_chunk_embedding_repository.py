from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from knowledge_os.domain.entities import (
    ChunkEmbedding,
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
    SqlAlchemyChunkEmbeddingRepository,
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
async def test_sqlalchemy_chunk_embedding_repository_lifecycle(db_session) -> None:
    user_id = uuid4()
    org_id = uuid4()
    project_id = uuid4()
    doc_id = uuid4()
    version_id = uuid4()
    chunk_id = uuid4()

    # Pre-populate required foreign keys
    db_session.add(
        UserModel(
            id=user_id,
            email="embedding_integration@example.com",
            display_name="Embedding Integration",
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
        name="Embedding Test Doc",
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
        source_filename="embedding_test.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        sha256="hash123",
        etag="etag123",
        status=DocumentVersionStatus.UPLOADED,
    )
    await doc_repo.add_version(ver)
    await db_session.flush()

    chunk_repo = SqlAlchemyDocumentChunkRepository(db_session)
    chunk = DocumentChunk(
        id=chunk_id,
        organization_id=org_id,
        document_id=doc_id,
        version_id=version_id,
        chunk_index=0,
        content="This is text to be embedded.",
        char_offset=0,
        token_count=6,
        char_count=29,
    )
    await chunk_repo.add_batch([chunk])
    await db_session.flush()

    embedding_repo = SqlAlchemyChunkEmbeddingRepository(db_session)

    # 1. Add embedding batch
    point_id = uuid4()
    embedding = ChunkEmbedding(
        organization_id=org_id,
        document_chunk_id=chunk_id,
        provider="openai",
        model="text-embedding-3-small",
        embedding_dimension=1536,
        embedding_version=1,
        qdrant_point_id=point_id,
    )
    await embedding_repo.add_batch([embedding])
    await db_session.flush()

    # 2. List and Assert
    embeddings = await embedding_repo.list_for_version(version_id, 1)
    assert len(embeddings) == 1
    assert embeddings[0].document_chunk_id == chunk_id
    assert embeddings[0].provider == "openai"
    assert embeddings[0].model == "text-embedding-3-small"
    assert embeddings[0].embedding_dimension == 1536
    assert embeddings[0].embedding_version == 1
    assert embeddings[0].qdrant_point_id == point_id

    # 3. Delete and Assert
    await embedding_repo.delete_for_version(version_id, 1)
    await db_session.flush()

    deleted_embeddings = await embedding_repo.list_for_version(version_id, 1)
    assert len(deleted_embeddings) == 0
