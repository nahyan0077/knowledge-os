from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from knowledge_os.domain.entities import (
    Conversation,
    MembershipRole,
    Message,
    MessageRole,
    MessageStatus,
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
from knowledge_os.infrastructure.repositories.sqlalchemy import SqlAlchemyConversationRepository


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
async def test_sqlalchemy_conversation_lifecycle(db_session) -> None:
    user_id = uuid4()
    org_id = uuid4()
    project_id = uuid4()

    db_session.add(
        UserModel(
            id=user_id,
            email="conv_integration@example.com",
            display_name="Integration",
            password_hash="hash",
            status="active",
        )
    )
    db_session.add(
        OrganizationModel(
            id=org_id,
            name="Test Org",
            slug="test-org-conv",
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

    repo = SqlAlchemyConversationRepository(db_session)

    # 1. Add Conversation
    conv = Conversation(
        organization_id=org_id,
        project_id=project_id,
        title="AI Q&A",
        created_by=user_id,
    )
    await repo.add(conv)
    await db_session.flush()

    # 2. Get and Assert Conversation
    retrieved_conv = await repo.get_by_id(conv.id, user_id)
    assert retrieved_conv is not None
    assert retrieved_conv.title == "AI Q&A"
    assert retrieved_conv.created_by == user_id
    assert retrieved_conv.deleted_at is None

    # 3. Add Messages
    msg1 = Message(
        conversation_id=conv.id,
        role=MessageRole.USER,
        content="What is RAG?",
        metadata={"client": "cli"},
    )
    msg2 = Message(
        conversation_id=conv.id,
        role=MessageRole.ASSISTANT,
        content="Retrieval-Augmented Generation.",
    )
    await repo.add_message(msg1)
    await repo.add_message(msg2)
    await db_session.flush()

    # 4. List Messages
    messages = await repo.list_messages(conv.id, user_id)
    assert len(messages) == 2
    assert messages[0].role == MessageRole.USER
    assert messages[0].content == "What is RAG?"
    assert messages[0].metadata == {"client": "cli"}
    assert messages[0].sequence_number == 1
    assert messages[0].status == MessageStatus.COMPLETE
    assert messages[1].role == MessageRole.ASSISTANT
    assert messages[1].content == "Retrieval-Augmented Generation."
    assert messages[1].sequence_number == 2
    assert messages[1].status == MessageStatus.COMPLETE

    # 5. Rename Conversation
    conv.title = "Renamed Chat"
    await repo.save(conv)
    await db_session.flush()

    updated_conv = await repo.get_by_id(conv.id, user_id)
    assert updated_conv is not None
    assert updated_conv.title == "Renamed Chat"

    # 6. List Conversations for Project
    conv_list = await repo.list_for_project(org_id, project_id, user_id, 10)
    assert len(conv_list) == 1
    assert conv_list[0].title == "Renamed Chat"
