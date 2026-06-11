import asyncio
from collections.abc import AsyncIterator, Callable, Sequence
from typing import Any
from uuid import UUID

from knowledge_os.application.context_builder import ContextBuilder
from knowledge_os.application.ports import (
    ChatAgentPort,
    LlmModelConfig,
    LlmResponseChunk,
    LlmUsageMetrics,
)
from knowledge_os.application.retrieval import RetrievalService
from knowledge_os.domain.common import (
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from knowledge_os.domain.entities import (
    Citation,
    Conversation,
    LlmUsage,
    MembershipRole,
    Message,
    MessageRole,
    MessageStatus,
    utc_now,
)
from knowledge_os.domain.repositories import UnitOfWork


class ConversationService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        chat_agent: ChatAgentPort | None = None,
        retrieval_service: RetrievalService | None = None,
        context_builder: ContextBuilder | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._chat_agent = chat_agent
        self._retrieval_service = retrieval_service
        self._context_builder = context_builder

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

    async def send_message(
        self,
        conversation_id: UUID,
        user_id: UUID,
        content: str,
        config: LlmModelConfig,
        selected_document_ids: Sequence[UUID] | None = None,
    ) -> tuple[Message, Message, LlmUsage]:
        if not content.strip():
            raise ValidationError("Message content cannot be empty", "empty_content")

        async with self._uow_factory() as uow:
            conversation = await uow.conversations.get_by_id(conversation_id, user_id)
            if conversation is None:
                raise NotFoundError("Conversation not found", "conversation_not_found")

            project_role = await uow.projects.user_role(conversation.project_id, user_id)
            if project_role not in {MembershipRole.OWNER, MembershipRole.EDITOR}:
                raise AuthorizationError("Write access denied", "project_write_denied")

            user_msg = Message(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=content.strip(),
                status=MessageStatus.COMPLETE,
            )
            await uow.conversations.add_message(user_msg)

            # Start assistant message in STREAMING status initially
            assistant_msg = Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content="",
                status=MessageStatus.STREAMING,
            )
            await uow.conversations.add_message(assistant_msg)

            conversation.updated_at = utc_now()
            await uow.conversations.save(conversation)
            await uow.commit()

        async with self._uow_factory() as uow:
            history = await uow.conversations.list_messages(conversation_id, user_id)

        # Exclude empty streaming assistant message from history
        messages_tuples = [
            (msg.role.value, msg.content) for msg in history if msg.id != assistant_msg.id
        ]

        # RAG Context retrieval
        context_text = ""
        citations: list[Citation] = []
        if self._retrieval_service and self._context_builder:
            retrieved = await self._retrieval_service.search(
                project_id=conversation.project_id,
                user_id=user_id,
                query=content.strip(),
                top_k=20,
                document_ids=selected_document_ids,
            )
            context_text, citations = self._context_builder.build_context(retrieved)

        if context_text:
            system_prompt = (
                "You are a helpful assistant. You must answer the user's question "
                "using only the provided source context.\n"
                "If the context does not contain the information needed to answer "
                "the question, state that you do not know.\n\n"
                f"Context:\n{context_text}"
            )
        else:
            system_prompt = "You are a helpful assistant."

        assert self._chat_agent is not None

        try:
            response = await self._chat_agent.generate(system_prompt, messages_tuples, config)
            status = MessageStatus.COMPLETE
            content_out = response.content
            metrics = response.usage
        except Exception:
            async with self._uow_factory() as uow:
                assistant_msg.content = ""
                assistant_msg.status = MessageStatus.FAILED
                await uow.conversations.save_message(assistant_msg)
                await uow.commit()
            raise

        async with self._uow_factory() as uow:
            assistant_msg.content = content_out
            assistant_msg.status = status

            # Persist Citations in Message Metadata
            if citations:
                assistant_msg.metadata = {
                    "citations": [
                        {
                            "chunk_id": str(cit.chunk_id),
                            "document_version_id": str(cit.document_version_id),
                            "chunk_number": cit.chunk_number,
                            "score": cit.score,
                        }
                        for cit in citations
                    ]
                }

            usage = LlmUsage(
                organization_id=conversation.organization_id,
                conversation_id=conversation_id,
                message_id=assistant_msg.id,
                provider=metrics.provider,
                model=metrics.model,
                input_tokens=metrics.input_tokens,
                output_tokens=metrics.output_tokens,
                total_tokens=metrics.total_tokens,
                latency_ms=metrics.latency_ms,
                cost=metrics.cost,
            )

            conversation = await uow.conversations.get_by_id(conversation_id, user_id)
            if conversation:
                conversation.updated_at = utc_now()
                await uow.conversations.save(conversation)

            await uow.conversations.save_message(assistant_msg)
            await uow.llm_usage.add(usage)
            await uow.commit()

        return user_msg, assistant_msg, usage

    async def send_message_stream(
        self,
        conversation_id: UUID,
        user_id: UUID,
        content: str,
        config: LlmModelConfig,
        selected_document_ids: Sequence[UUID] | None = None,
    ) -> AsyncIterator[Message | LlmUsage | str]:
        if not content.strip():
            raise ValidationError("Message content cannot be empty", "empty_content")

        async with self._uow_factory() as uow:
            conversation = await uow.conversations.get_by_id(conversation_id, user_id)
            if conversation is None:
                raise NotFoundError("Conversation not found", "conversation_not_found")

            project_role = await uow.projects.user_role(conversation.project_id, user_id)
            if project_role not in {MembershipRole.OWNER, MembershipRole.EDITOR}:
                raise AuthorizationError("Write access denied", "project_write_denied")

            user_msg = Message(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=content.strip(),
                status=MessageStatus.COMPLETE,
            )
            await uow.conversations.add_message(user_msg)

            # Start assistant message in STREAMING status initially
            assistant_msg = Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content="",
                status=MessageStatus.STREAMING,
            )
            await uow.conversations.add_message(assistant_msg)

            conversation.updated_at = utc_now()
            await uow.conversations.save(conversation)
            await uow.commit()

        yield user_msg
        yield assistant_msg

        async with self._uow_factory() as uow:
            history = await uow.conversations.list_messages(conversation_id, user_id)

        # Exclude empty streaming assistant message from history
        messages_tuples = [
            (msg.role.value, msg.content) for msg in history if msg.id != assistant_msg.id
        ]

        # RAG Context retrieval
        context_text = ""
        citations: list[Citation] = []
        if self._retrieval_service and self._context_builder:
            retrieved = await self._retrieval_service.search(
                project_id=conversation.project_id,
                user_id=user_id,
                query=content.strip(),
                top_k=20,
                document_ids=selected_document_ids,
            )
            context_text, citations = self._context_builder.build_context(retrieved)

        if context_text:
            system_prompt = (
                "You are a helpful assistant. You must answer the user's question "
                "using only the provided source context.\n"
                "If the context does not contain the information needed to answer "
                "the question, state that you do not know.\n\n"
                f"Context:\n{context_text}"
            )
        else:
            system_prompt = "You are a helpful assistant."

        assert self._chat_agent is not None

        full_content = ""
        metrics = None
        status = MessageStatus.COMPLETE

        try:
            async for item in self._chat_agent.generate_stream(
                system_prompt, messages_tuples, config
            ):
                if isinstance(item, LlmResponseChunk):
                    full_content += item.content
                    yield item.content
                elif isinstance(item, LlmUsageMetrics):
                    metrics = item
        except asyncio.CancelledError:
            status = MessageStatus.INTERRUPTED
            raise
        except Exception:
            status = MessageStatus.FAILED
            raise
        finally:

            async def persist_final_state() -> LlmUsage:
                nonlocal metrics
                if metrics is None:
                    metrics = LlmUsageMetrics(
                        provider=config.provider,
                        model=config.model_name,
                        input_tokens=0,
                        output_tokens=0,
                        total_tokens=0,
                        latency_ms=0,
                        cost=0.0,
                    )

                async with self._uow_factory() as uow:
                    assistant_msg.content = full_content
                    assistant_msg.status = status
                    if citations:
                        assistant_msg.metadata = {
                            "citations": [
                                {
                                    "chunk_id": str(cit.chunk_id),
                                    "document_version_id": str(cit.document_version_id),
                                    "chunk_number": cit.chunk_number,
                                    "score": cit.score,
                                }
                                for cit in citations
                            ]
                        }
                    await uow.conversations.save_message(assistant_msg)

                    usage = LlmUsage(
                        organization_id=conversation.organization_id,
                        conversation_id=conversation_id,
                        message_id=assistant_msg.id,
                        provider=metrics.provider,
                        model=metrics.model,
                        input_tokens=metrics.input_tokens,
                        output_tokens=metrics.output_tokens,
                        total_tokens=metrics.total_tokens,
                        latency_ms=metrics.latency_ms,
                        cost=metrics.cost,
                    )
                    await uow.llm_usage.add(usage)

                    conv = await uow.conversations.get_by_id(conversation_id, user_id)
                    if conv:
                        conv.updated_at = utc_now()
                        await uow.conversations.save(conv)

                    await uow.commit()
                    return usage

            usage_record = await asyncio.shield(persist_final_state())
            if status == MessageStatus.COMPLETE:
                yield assistant_msg
                yield usage_record

    @staticmethod
    def _validate_title(title: str) -> str:
        clean = title.strip()
        if not clean or len(clean) > 255:
            raise ValidationError(
                "Conversation title must contain 1-255 characters", "invalid_title"
            )
        return clean
