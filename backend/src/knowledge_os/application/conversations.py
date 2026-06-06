from collections.abc import Callable, Sequence
from typing import Any
from uuid import UUID

from knowledge_os.domain.common import (
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from knowledge_os.domain.entities import (
    Conversation,
    MembershipRole,
    Message,
    MessageRole,
    utc_now,
)
from knowledge_os.domain.repositories import UnitOfWork


class ConversationService:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def create(
        self,
        organization_id: UUID,
        project_id: UUID,
        user_id: UUID,
        title: str,
    ) -> Conversation:
        clean_title = self._validate_title(title)

        async with self._uow_factory() as uow:
            project_role = await uow.projects.user_role(project_id, user_id)
            if project_role not in {MembershipRole.OWNER, MembershipRole.EDITOR}:
                raise AuthorizationError("Write access denied", "project_write_denied")

            project = await uow.projects.get_for_user(project_id, user_id)
            if project is None or project.organization_id != organization_id:
                raise NotFoundError("Project not found", "project_not_found")

            conversation = Conversation(
                organization_id=organization_id,
                project_id=project_id,
                title=clean_title,
                created_by=user_id,
            )

            await uow.conversations.add(conversation)
            await uow.commit()

            return conversation

    async def list(
        self,
        organization_id: UUID,
        project_id: UUID,
        user_id: UUID,
        limit: int = 50,
    ) -> Sequence[Conversation]:
        async with self._uow_factory() as uow:
            project_role = await uow.projects.user_role(project_id, user_id)
            if project_role is None:
                raise AuthorizationError("Access denied", "project_access_denied")

            project = await uow.projects.get_for_user(project_id, user_id)
            if project is None or project.organization_id != organization_id:
                raise NotFoundError("Project not found", "project_not_found")

            return await uow.conversations.list_for_project(
                organization_id, project_id, user_id, min(limit, 100)
            )

    async def get(self, conversation_id: UUID, user_id: UUID) -> Conversation:
        async with self._uow_factory() as uow:
            conversation = await uow.conversations.get_by_id(conversation_id, user_id)
            if conversation is None:
                raise NotFoundError("Conversation not found", "conversation_not_found")
            return conversation

    async def rename(self, conversation_id: UUID, user_id: UUID, title: str) -> Conversation:
        clean_title = self._validate_title(title)

        async with self._uow_factory() as uow:
            conversation = await uow.conversations.get_by_id(conversation_id, user_id)
            if conversation is None:
                raise NotFoundError("Conversation not found", "conversation_not_found")

            project_role = await uow.projects.user_role(conversation.project_id, user_id)
            if project_role not in {MembershipRole.OWNER, MembershipRole.EDITOR}:
                raise AuthorizationError("Write access denied", "project_write_denied")

            conversation.title = clean_title
            conversation.updated_at = utc_now()

            await uow.conversations.save(conversation)
            await uow.commit()

            return conversation

    async def delete(self, conversation_id: UUID, user_id: UUID) -> None:
        async with self._uow_factory() as uow:
            conversation = await uow.conversations.get_by_id(conversation_id, user_id)
            if conversation is None:
                raise NotFoundError("Conversation not found", "conversation_not_found")

            project_role = await uow.projects.user_role(conversation.project_id, user_id)
            if project_role not in {MembershipRole.OWNER, MembershipRole.EDITOR}:
                raise AuthorizationError("Write access denied", "project_write_denied")

            conversation.deleted_at = utc_now()
            conversation.updated_at = conversation.deleted_at

            await uow.conversations.save(conversation)
            await uow.commit()

    async def add_message(
        self,
        conversation_id: UUID,
        user_id: UUID,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        if not content.strip():
            raise ValidationError("Message content cannot be empty", "empty_content")

        try:
            msg_role = MessageRole(role)
        except ValueError as err:
            raise ValidationError(f"Invalid message role: {role}", "invalid_role") from err

        async with self._uow_factory() as uow:
            conversation = await uow.conversations.get_by_id(conversation_id, user_id)
            if conversation is None:
                raise NotFoundError("Conversation not found", "conversation_not_found")

            project_role = await uow.projects.user_role(conversation.project_id, user_id)
            if project_role not in {MembershipRole.OWNER, MembershipRole.EDITOR}:
                raise AuthorizationError("Write access denied", "project_write_denied")

            message = Message(
                conversation_id=conversation_id,
                role=msg_role,
                content=content.strip(),
                metadata=metadata or {},
            )

            conversation.updated_at = utc_now()

            await uow.conversations.add_message(message)
            await uow.conversations.save(conversation)
            await uow.commit()

            return message

    async def list_messages(self, conversation_id: UUID, user_id: UUID) -> Sequence[Message]:
        async with self._uow_factory() as uow:
            conversation = await uow.conversations.get_by_id(conversation_id, user_id)
            if conversation is None:
                raise NotFoundError("Conversation not found", "conversation_not_found")

            return await uow.conversations.list_messages(conversation_id, user_id)

    @staticmethod
    def _validate_title(title: str) -> str:
        clean = title.strip()
        if not clean or len(clean) > 255:
            raise ValidationError(
                "Conversation title must contain 1-255 characters", "invalid_title"
            )
        return clean
