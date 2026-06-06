from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from knowledge_os.domain.entities import (
    Conversation,
    LlmUsage,
    MembershipRole,
    Message,
    MessageRole,
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
    SqlAlchemyConversationRepository,
    SqlAlchemyLlmUsageRepository,
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
async def test_sqlalchemy_llm_usage_lifecycle(db_session) -> None:
    user_id = uuid4()
    org_id = uuid4()
    project_id = uuid4()

    # Create user and organization
    db_session.add(
        UserModel(
            id=user_id,
            email="llm_integration@example.com",
            display_name="Integration User",
            password_hash="hash",
            status="active",
        )
    )
    db_session.add(
        OrganizationModel(
            id=org_id,
            name="Test Org",
            slug="test-org-llm",
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

    # Create conversation and message using SqlAlchemyConversationRepository
    conv_repo = SqlAlchemyConversationRepository(db_session)
    conv = Conversation(
        organization_id=org_id,
        project_id=project_id,
        title="RAG Chat",
        created_by=user_id,
    )
    await conv_repo.add(conv)
    await db_session.flush()

    msg = Message(
        conversation_id=conv.id,
        role=MessageRole.ASSISTANT,
        content="This is a response",
    )
    await conv_repo.add_message(msg)
    await db_session.flush()

    # Now create and insert LLM Usage
    usage_repo = SqlAlchemyLlmUsageRepository(db_session)
    usage = LlmUsage(
        organization_id=org_id,
        conversation_id=conv.id,
        message_id=msg.id,
        provider="openai",
        model="gpt-4o-mini",
        input_tokens=100,
        output_tokens=200,
        total_tokens=300,
        latency_ms=450,
        cost=0.000135,
    )

    # 1. Add
    await usage_repo.add(usage)
    await db_session.flush()

    # 2. Get and Assert
    retrieved = await usage_repo.get_by_id(usage.id)
    assert retrieved is not None
    assert retrieved.id == usage.id
    assert retrieved.organization_id == org_id
    assert retrieved.conversation_id == conv.id
    assert retrieved.message_id == msg.id
    assert retrieved.provider == "openai"
    assert retrieved.model == "gpt-4o-mini"
    assert retrieved.input_tokens == 100
    assert retrieved.output_tokens == 200
    assert retrieved.total_tokens == 300
    assert retrieved.latency_ms == 450
    assert abs(retrieved.cost - 0.000135) < 1e-9
    assert retrieved.created_at is not None

    # 3. Get non-existent
    assert await usage_repo.get_by_id(uuid4()) is None
