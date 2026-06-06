from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from knowledge_os.api.dependencies import get_conversation_service, get_current_user_id
from knowledge_os.api.schemas import (
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationRenameRequest,
    ConversationResponse,
    MessageAddRequest,
    MessageListResponse,
    MessageResponse,
)
from knowledge_os.application.conversations import ConversationService

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
