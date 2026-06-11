import json
from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sse_starlette import EventSourceResponse

from knowledge_os.api.dependencies import get_conversation_service, get_current_user_id
from knowledge_os.api.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationRenameRequest,
    ConversationResponse,
    LlmUsageResponse,
    MessageAddRequest,
    MessageListResponse,
    MessageResponse,
)
from knowledge_os.application.conversations import ConversationService
from knowledge_os.application.ports import LlmModelConfig
from knowledge_os.domain.entities import LlmUsage, Message, MessageRole

router = APIRouter(tags=["conversations"])


@router.post(
    "/projects/{project_id}/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    project_id: UUID,
    req: ConversationCreateRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationResponse:
    conversation = await service.create(
        organization_id=req.organization_id,
        project_id=project_id,
        user_id=user_id,
        title=req.title,
    )
    return ConversationResponse.from_domain(conversation)


@router.get("/projects/{project_id}/conversations", response_model=ConversationListResponse)
async def list_conversations(
    project_id: UUID,
    organization_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ConversationListResponse:
    conversations = await service.list(
        organization_id=organization_id,
        project_id=project_id,
        user_id=user_id,
        limit=limit,
    )
    return ConversationListResponse(
        items=[ConversationResponse.from_domain(c) for c in conversations]
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationResponse:
    conversation = await service.get(conversation_id, user_id)
    return ConversationResponse.from_domain(conversation)


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def rename_conversation(
    conversation_id: UUID,
    req: ConversationRenameRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationResponse:
    conversation = await service.rename(conversation_id, user_id, req.title)
    return ConversationResponse.from_domain(conversation)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> Response:
    await service.delete(conversation_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_message(
    conversation_id: UUID,
    req: MessageAddRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> MessageResponse:
    message = await service.add_message(
        conversation_id=conversation_id,
        user_id=user_id,
        role=req.role,
        content=req.content,
        metadata=req.metadata,
    )
    return MessageResponse.from_domain(message)


@router.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse)
async def list_messages(
    conversation_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> MessageListResponse:
    messages = await service.list_messages(conversation_id, user_id)
    return MessageListResponse(items=[MessageResponse.from_domain(m) for m in messages])


@router.post(
    "/conversations/{conversation_id}/chat",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_200_OK,
)
async def chat(
    conversation_id: UUID,
    req: ChatMessageRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ChatMessageResponse:
    config = LlmModelConfig(
        provider=req.provider,
        model_name=req.model,
        temperature=req.temperature,
    )
    user_msg, assistant_msg, usage = await service.send_message(
        conversation_id=conversation_id,
        user_id=user_id,
        content=req.content,
        config=config,
        selected_document_ids=req.selected_document_ids,
    )
    return ChatMessageResponse(
        user_message=MessageResponse.from_domain(user_msg),
        assistant_message=MessageResponse.from_domain(assistant_msg),
        usage=LlmUsageResponse.from_domain(usage),
    )


@router.post("/conversations/{conversation_id}/chat/stream")
async def chat_stream(
    conversation_id: UUID,
    req: ChatMessageRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> EventSourceResponse:
    async def sse_generator() -> AsyncIterator[dict[str, Any]]:
        config = LlmModelConfig(
            provider=req.provider,
            model_name=req.model,
            temperature=req.temperature,
        )
        try:
            async for item in service.send_message_stream(
                conversation_id=conversation_id,
                user_id=user_id,
                content=req.content,
                config=config,
                selected_document_ids=req.selected_document_ids,
            ):
                if isinstance(item, Message):
                    if item.role == MessageRole.USER:
                        yield {
                            "event": "user_message",
                            "data": MessageResponse.from_domain(item).model_dump_json(),
                        }
                    else:
                        yield {
                            "event": "assistant_message",
                            "data": MessageResponse.from_domain(item).model_dump_json(),
                        }
                elif isinstance(item, LlmUsage):
                    yield {
                        "event": "usage",
                        "data": LlmUsageResponse.from_domain(item).model_dump_json(),
                    }
                elif isinstance(item, str):
                    yield {
                        "event": "chunk",
                        "data": json.dumps({"content": item}),
                    }
        except Exception as err:
            yield {
                "event": "error",
                "data": str(err),
            }

    return EventSourceResponse(sse_generator())
