from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from knowledge_os.domain.entities import (
    Conversation,
    Document,
    DocumentVersion,
    LlmUsage,
    Message,
    Organization,
    Project,
    User,
)


class RegisterRequest(BaseModel):
    email: EmailStr = Field(max_length=320)
    display_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=12, max_length=256)


class LoginRequest(BaseModel):
    email: EmailStr = Field(max_length=320)
    password: str = Field(max_length=256)


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str

    @classmethod
    def from_domain(cls, user: User) -> "UserResponse":
        return cls(id=user.id, email=user.email, display_name=user.display_name)


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    type: str

    @classmethod
    def from_domain(cls, organization: Organization) -> "OrganizationResponse":
        return cls(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            type=organization.type.value,
        )


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    organization: OrganizationResponse | None


class ProjectCreateRequest(BaseModel):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)


class ProjectUpdateRequest(BaseModel):
    version: int = Field(gt=0)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    created_by: UUID
    version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, project: Project) -> "ProjectResponse":
        return cls.model_validate(project)


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]


class ProblemDetail(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    error_code: str


class DocumentResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: UUID
    name: str
    current_version_id: UUID | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, doc: Document) -> "DocumentResponse":
        return cls(
            id=doc.id,
            organization_id=doc.organization_id,
            project_id=doc.project_id,
            name=doc.name,
            current_version_id=doc.current_version_id,
            created_by=doc.created_by,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]


class DocumentVersionResponse(BaseModel):
    id: UUID
    organization_id: UUID
    document_id: UUID
    version_number: int
    blob_path: str
    source_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    etag: str
    storage_provider: str
    status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, ver: DocumentVersion) -> "DocumentVersionResponse":
        return cls(
            id=ver.id,
            organization_id=ver.organization_id,
            document_id=ver.document_id,
            version_number=ver.version_number,
            blob_path=ver.blob_path,
            source_filename=ver.source_filename,
            mime_type=ver.mime_type,
            size_bytes=ver.size_bytes,
            sha256=ver.sha256,
            etag=ver.etag,
            storage_provider=ver.storage_provider,
            status=ver.status.value,
            created_at=ver.created_at,
            updated_at=ver.updated_at,
        )


class ConversationCreateRequest(BaseModel):
    organization_id: UUID
    title: str = Field(min_length=1, max_length=255)


class ConversationRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ConversationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: UUID
    title: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, conv: Conversation) -> "ConversationResponse":
        return cls(
            id=conv.id,
            organization_id=conv.organization_id,
            project_id=conv.project_id,
            title=conv.title,
            created_by=conv.created_by,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]


class MessageAddRequest(BaseModel):
    role: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    metadata: dict[str, Any]
    created_at: datetime

    @classmethod
    def from_domain(cls, msg: Message) -> "MessageResponse":
        return cls(
            id=msg.id,
            conversation_id=msg.conversation_id,
            role=msg.role.value,
            content=msg.content,
            metadata=msg.metadata,
            created_at=msg.created_at,
        )


class MessageListResponse(BaseModel):
    items: list[MessageResponse]


class ChatMessageRequest(BaseModel):
    content: str = Field(min_length=1)
    provider: str = Field(default="openai", max_length=100)
    model: str = Field(default="gpt-4o-mini", max_length=100)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)


class LlmUsageResponse(BaseModel):
    id: UUID
    organization_id: UUID
    conversation_id: UUID
    message_id: UUID
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: int
    cost: float
    created_at: datetime

    @classmethod
    def from_domain(cls, usage: LlmUsage) -> "LlmUsageResponse":
        return cls(
            id=usage.id,
            organization_id=usage.organization_id,
            conversation_id=usage.conversation_id,
            message_id=usage.message_id,
            provider=usage.provider,
            model=usage.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            latency_ms=usage.latency_ms,
            cost=usage.cost,
            created_at=usage.created_at,
        )


class ChatMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
    usage: LlmUsageResponse
