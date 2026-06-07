from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from knowledge_os.application.auth import AuthService
from knowledge_os.application.conversations import ConversationService
from knowledge_os.application.documents import DocumentService
from knowledge_os.application.projects import ProjectService
from knowledge_os.application.rag import RagService
from knowledge_os.application.retrieval import RetrievalService
from knowledge_os.application.workflows import WorkflowService
from knowledge_os.config import Settings, get_settings
from knowledge_os.domain.common import AuthenticationError
from knowledge_os.domain.repositories import UnitOfWork
from knowledge_os.infrastructure.database.uow import SqlAlchemyUnitOfWork
from knowledge_os.infrastructure.security.services import (
    Argon2PasswordService,
    JwtAccessTokenService,
    OpaqueRefreshTokenService,
)
from knowledge_os.infrastructure.storage.azure import AzureBlobStorageAdapter

bearer = HTTPBearer(auto_error=False)


def get_uow() -> UnitOfWork:
    return SqlAlchemyUnitOfWork()


def get_auth_service(settings: Annotated[Settings, Depends(get_settings)]) -> AuthService:
    return AuthService(
        uow_factory=get_uow,
        passwords=Argon2PasswordService(),
        access_tokens=JwtAccessTokenService(settings),
        refresh_tokens=OpaqueRefreshTokenService(),
        refresh_ttl_days=settings.refresh_token_ttl_days,
    )


def get_project_service() -> ProjectService:
    return ProjectService(uow_factory=get_uow)


def get_blob_storage_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AzureBlobStorageAdapter:
    return AzureBlobStorageAdapter(settings)


def get_document_service(
    storage: Annotated[AzureBlobStorageAdapter, Depends(get_blob_storage_service)],
) -> DocumentService:
    return DocumentService(uow_factory=get_uow, storage=storage)


def get_retrieval_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> RetrievalService:
    from knowledge_os.application.retrieval import RetrievalService
    from knowledge_os.infrastructure.ai.embeddings import OpenAIEmbeddingProvider
    from knowledge_os.infrastructure.search.qdrant import QdrantVectorStore

    provider = OpenAIEmbeddingProvider(settings)
    vector_store = QdrantVectorStore(settings)
    return RetrievalService(
        uow_factory=get_uow,
        embedding_provider=provider,
        vector_store=vector_store,
    )


def get_conversation_service(
    settings: Annotated[Settings, Depends(get_settings)],
    retrieval_service: Annotated[RetrievalService, Depends(get_retrieval_service)],
) -> ConversationService:
    from knowledge_os.application.context_builder import ContextBuilder
    from knowledge_os.infrastructure.ai.pydantic_ai_adapter import PydanticAiAdapter
    from knowledge_os.infrastructure.services.pricing import ConfigPricingService

    pricing_service = ConfigPricingService(pricing_dict=settings.model_pricing)
    context_builder = ContextBuilder()
    return ConversationService(
        uow_factory=get_uow,
        chat_agent=PydanticAiAdapter(pricing_service),
        retrieval_service=retrieval_service,
        context_builder=context_builder,
    )


def get_access_token_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> JwtAccessTokenService:
    return JwtAccessTokenService(settings)


def get_workflow_service() -> WorkflowService:
    from knowledge_os.application.workflows import WorkflowService

    return WorkflowService(uow_factory=get_uow)


def get_rag_service(
    settings: Annotated[Settings, Depends(get_settings)],
    retrieval_service: Annotated[RetrievalService, Depends(get_retrieval_service)],
) -> RagService:
    from knowledge_os.application.context_builder import ContextBuilder
    from knowledge_os.application.rag import RagService
    from knowledge_os.infrastructure.ai.pydantic_ai_adapter import PydanticAiAdapter
    from knowledge_os.infrastructure.services.pricing import ConfigPricingService

    pricing_service = ConfigPricingService(pricing_dict=settings.model_pricing)
    chat_agent = PydanticAiAdapter(pricing_service)
    context_builder = ContextBuilder()
    return RagService(
        retrieval_service=retrieval_service,
        context_builder=context_builder,
        chat_agent=chat_agent,
    )


def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    tokens: Annotated[JwtAccessTokenService, Depends(get_access_token_service)],
) -> UUID:
    if credentials is None:
        raise AuthenticationError("Authentication required", "authentication_required")
    try:
        user_id, _ = tokens.decode(credentials.credentials)
        return user_id
    except (jwt.InvalidTokenError, ValueError, KeyError) as exc:
        raise AuthenticationError("Invalid access token", "invalid_access_token") from exc
