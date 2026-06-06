from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from knowledge_os.domain.entities import (
    Document,
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
from knowledge_os.infrastructure.repositories.sqlalchemy import SqlAlchemyDocumentRepository


@pytest.fixture(scope="session")
def postgres_container():
    # Spin up Postgres container using Testcontainers
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
async def test_sqlalchemy_repository_lifecycle(db_session) -> None:
    user_id = uuid4()
    org_id = uuid4()
    project_id = uuid4()

    db_session.add(
        UserModel(
            id=user_id,
            email="integration@example.com",
            display_name="Integration",
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

    repo = SqlAlchemyDocumentRepository(db_session)

    # 1. Add Document
    doc = Document(
        organization_id=org_id,
        project_id=project_id,
        name="Reports",
        created_by=user_id,
    )
    await repo.add(doc)
    await db_session.flush()

    # 2. Add Version
    ver = DocumentVersion(
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
    await repo.add_version(ver)
    await db_session.flush()

    # Update document link
    doc.current_version_id = ver.id
    await repo.save(doc)
    await db_session.flush()

    # 3. Retrieve and Assert
    retrieved_doc = await repo.get_by_id(doc.id, user_id)
    assert retrieved_doc is not None
    assert retrieved_doc.name == "Reports"
    assert retrieved_doc.current_version_id == ver.id

    retrieved_ver = await repo.get_version_by_id(ver.id, user_id)
    assert retrieved_ver is not None
    assert retrieved_ver.source_filename == "report.pdf"
    assert retrieved_ver.size_bytes == 1024

    # 4. List versions
    versions = await repo.list_versions(doc.id, user_id)
    assert len(versions) == 1
    assert versions[0].version_number == 1
