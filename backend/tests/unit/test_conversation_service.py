from uuid import uuid4

import pytest

from knowledge_os.application.conversations import ConversationService
from knowledge_os.application.ports import LlmModelConfig
from knowledge_os.domain.common import AuthorizationError, NotFoundError, ValidationError
from knowledge_os.domain.entities import (
    LlmUsage,
    MembershipRole,
    Message,
    MessageRole,
    Organization,
    OrganizationMembership,
    OrganizationType,
    Project,
    ProjectMembership,
    User,
)
from tests.unit.fakes import FakeChatAgent, FakeUnitOfWork, Store


def setup_store() -> tuple[Store, User, Organization, Project]:
    user = User("owner@example.com", "Owner", "hash")
    organization = Organization("Workspace", "workspace", OrganizationType.PERSONAL)
    project = Project(organization.id, "Research", user.id)
    store = Store(
        users={user.id: user},
        organizations={organization.id: organization},
        organization_memberships=[
            OrganizationMembership(organization.id, user.id, MembershipRole.OWNER)
        ],
        projects={project.id: project},
        project_memberships=[
            ProjectMembership(organization.id, project.id, user.id, MembershipRole.OWNER)
        ],
    )
    return store, user, organization, project


def make_service(store: Store) -> ConversationService:
    return ConversationService(lambda: FakeUnitOfWork(store))


@pytest.mark.asyncio
async def test_create_conversation_success() -> None:
    store, user, org, project = setup_store()
    service = make_service(store)

    conv = await service.create(
        organization_id=org.id,
        project_id=project.id,
        user_id=user.id,
        title="My Conversation",
    )

    assert conv.title == "My Conversation"
    assert conv.project_id == project.id
    assert conv.organization_id == org.id
    assert conv.created_by == user.id
    assert conv.deleted_at is None
    assert store.conversations[conv.id].title == "My Conversation"


@pytest.mark.asyncio
async def test_create_conversation_unauthorized() -> None:
    store, _, org, project = setup_store()
    service = make_service(store)

    with pytest.raises(AuthorizationError):
        await service.create(
            organization_id=org.id,
            project_id=project.id,
            user_id=uuid4(),
            title="Unauthorized Conversation",
        )


@pytest.mark.asyncio
async def test_create_conversation_invalid_title() -> None:
    store, user, org, project = setup_store()
    service = make_service(store)

    with pytest.raises(ValidationError):
        await service.create(
            organization_id=org.id,
            project_id=project.id,
            user_id=user.id,
            title="   ",
        )


@pytest.mark.asyncio
async def test_list_conversations_success() -> None:
    store, user, org, project = setup_store()
    service = make_service(store)

    await service.create(org.id, project.id, user.id, "Conv 1")
    await service.create(org.id, project.id, user.id, "Conv 2")

    conversations = await service.list(org.id, project.id, user.id)
    assert len(conversations) == 2
    # Ordered by updated_at desc (newest first)
    assert conversations[0].title == "Conv 2"
    assert conversations[1].title == "Conv 1"


@pytest.mark.asyncio
async def test_get_conversation_success() -> None:
    store, user, org, project = setup_store()
    service = make_service(store)

    conv = await service.create(org.id, project.id, user.id, "My Conversation")
    retrieved = await service.get(conv.id, user.id)
    assert retrieved.id == conv.id
    assert retrieved.title == conv.title


@pytest.mark.asyncio
async def test_get_conversation_not_found() -> None:
    store, user, _, _ = setup_store()
    service = make_service(store)

    with pytest.raises(NotFoundError):
        await service.get(uuid4(), user.id)


@pytest.mark.asyncio
async def test_rename_conversation_success() -> None:
    store, user, org, project = setup_store()
    service = make_service(store)

    conv = await service.create(org.id, project.id, user.id, "Original Title")
    renamed = await service.rename(conv.id, user.id, "New Title")
    assert renamed.title == "New Title"
    assert store.conversations[conv.id].title == "New Title"


@pytest.mark.asyncio
async def test_soft_delete_conversation() -> None:
    store, user, org, project = setup_store()
    service = make_service(store)

    conv = await service.create(org.id, project.id, user.id, "To Delete")
    await service.delete(conv.id, user.id)

    assert store.conversations[conv.id].deleted_at is not None
    with pytest.raises(NotFoundError):
        await service.get(conv.id, user.id)


@pytest.mark.asyncio
async def test_add_message_success() -> None:
    store, user, org, project = setup_store()
    service = make_service(store)

    conv = await service.create(org.id, project.id, user.id, "Chat")
    msg1 = await service.add_message(
        conversation_id=conv.id,
        user_id=user.id,
        role="user",
        content="hello",
        metadata={"client": "web"},
    )

    assert msg1.role == MessageRole.USER
    assert msg1.content == "hello"
    assert msg1.metadata == {"client": "web"}
    assert msg1.conversation_id == conv.id

    msg2 = await service.add_message(
        conversation_id=conv.id,
        user_id=user.id,
        role="assistant",
        content="hi there",
    )
    assert msg2.role == MessageRole.ASSISTANT
    assert msg2.content == "hi there"


@pytest.mark.asyncio
async def test_add_message_invalid_role() -> None:
    store, user, org, project = setup_store()
    service = make_service(store)

    conv = await service.create(org.id, project.id, user.id, "Chat")
    with pytest.raises(ValidationError):
        await service.add_message(conv.id, user.id, "invalid_role", "hello")


@pytest.mark.asyncio
async def test_add_message_empty_content() -> None:
    store, user, org, project = setup_store()
    service = make_service(store)

    conv = await service.create(org.id, project.id, user.id, "Chat")
    with pytest.raises(ValidationError):
        await service.add_message(conv.id, user.id, "user", "   ")


@pytest.mark.asyncio
async def test_list_messages_success() -> None:
    store, user, org, project = setup_store()
    service = make_service(store)

    conv = await service.create(org.id, project.id, user.id, "Chat")
    await service.add_message(conv.id, user.id, "user", "message 1")
    await service.add_message(conv.id, user.id, "assistant", "message 2")

    messages = await service.list_messages(conv.id, user.id)
    assert len(messages) == 2
    assert messages[0].content == "message 1"
    assert messages[1].content == "message 2"


@pytest.mark.asyncio
async def test_send_message_success() -> None:
    store, user, org, project = setup_store()
    agent = FakeChatAgent(response_content="Hello human")
    service = ConversationService(lambda: FakeUnitOfWork(store), agent)

    conv = await service.create(org.id, project.id, user.id, "Chat")
    config = LlmModelConfig(provider="test", model_name="test-model")

    user_msg, assistant_msg, usage = await service.send_message(
        conversation_id=conv.id,
        user_id=user.id,
        content="Hello bot",
        config=config,
    )

    # Verify return values
    assert user_msg.content == "Hello bot"
    assert user_msg.role == MessageRole.USER
    assert assistant_msg.content == "Hello human"
    assert assistant_msg.role == MessageRole.ASSISTANT
    assert usage.cost == 0.0005
    assert usage.input_tokens == 10

    # Verify store persistence
    assert len(store.messages) == 2
    assert store.messages[0].content == "Hello bot"
    assert store.messages[1].content == "Hello human"
    assert usage.id in store.llm_usage

    # Verify agent was called with correct context (history)
    assert len(agent.calls) == 1
    sys_prompt, history, cfg = agent.calls[0]
    assert sys_prompt == "You are a helpful assistant."
    assert len(history) == 1
    assert history[0] == ("user", "Hello bot")
    assert cfg == config


@pytest.mark.asyncio
async def test_send_message_empty_content() -> None:
    store, user, org, project = setup_store()
    agent = FakeChatAgent()
    service = ConversationService(lambda: FakeUnitOfWork(store), agent)
    conv = await service.create(org.id, project.id, user.id, "Chat")
    config = LlmModelConfig(provider="test", model_name="test-model")

    with pytest.raises(ValidationError):
        await service.send_message(conv.id, user.id, "   ", config)


@pytest.mark.asyncio
async def test_send_message_stream_success() -> None:
    store, user, org, project = setup_store()
    agent = FakeChatAgent(response_content="Hello human world")
    service = ConversationService(lambda: FakeUnitOfWork(store), agent)

    conv = await service.create(org.id, project.id, user.id, "Chat")
    config = LlmModelConfig(provider="test", model_name="test-model")

    items = []
    async for item in service.send_message_stream(
        conversation_id=conv.id,
        user_id=user.id,
        content="Hello stream",
        config=config,
    ):
        items.append(item)

    # Expected sequence:
    # 1. Message (user)
    # 2. str ("Hello ")
    # 3. str ("human ")
    # 4. str ("world ")
    # 5. Message (assistant)
    # 6. LlmUsage (usage)
    assert len(items) == 6
    assert isinstance(items[0], Message)
    assert items[0].role == MessageRole.USER
    assert items[0].content == "Hello stream"

    assert items[1] == "Hello "
    assert items[2] == "human "
    assert items[3] == "world "

    assert isinstance(items[4], Message)
    assert items[4].role == MessageRole.ASSISTANT
    assert items[4].content == "Hello human world "

    assert isinstance(items[5], LlmUsage)
    assert items[5].cost == 0.0005

    # Verify store persistence
    assert len(store.messages) == 2
    assert store.messages[0].content == "Hello stream"
    assert store.messages[1].content == "Hello human world "
    assert items[5].id in store.llm_usage
