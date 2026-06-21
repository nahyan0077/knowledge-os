from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(UTC)


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class OrganizationType(StrEnum):
    PERSONAL = "personal"
    TEAM = "team"


class MembershipRole(StrEnum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


@dataclass(slots=True)
class User:
    email: str
    display_name: str
    password_hash: str
    id: UUID = field(default_factory=uuid4)
    status: UserStatus = UserStatus.ACTIVE
    last_login_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class Organization:
    name: str
    slug: str
    type: OrganizationType
    id: UUID = field(default_factory=uuid4)
    settings: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class OrganizationMembership:
    organization_id: UUID
    user_id: UUID
    role: MembershipRole
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class RefreshSession:
    user_id: UUID
    token_hash: str
    family_id: UUID
    expires_at: datetime
    id: UUID = field(default_factory=uuid4)
    revoked_at: datetime | None = None
    replaced_by_session_id: UUID | None = None
    created_at: datetime = field(default_factory=utc_now)

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.expires_at > utc_now()


@dataclass(slots=True)
class Project:
    organization_id: UUID
    name: str
    created_by: UUID
    description: str | None = None
    id: UUID = field(default_factory=uuid4)
    settings: dict[str, Any] = field(default_factory=dict)
    deleted_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    version: int = 1


@dataclass(slots=True)
class ProjectMembership:
    organization_id: UUID
    project_id: UUID
    user_id: UUID
    role: MembershipRole
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)


class DocumentVersionStatus(StrEnum):
    PENDING_UPLOAD = "pending_upload"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    DELETED = "deleted"


@dataclass(slots=True)
class Document:
    organization_id: UUID
    project_id: UUID
    name: str
    created_by: UUID
    current_version_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    deleted_at: datetime | None = None


@dataclass(slots=True)
class DocumentVersion:
    organization_id: UUID
    document_id: UUID
    version_number: int
    blob_path: str
    source_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    etag: str
    storage_provider: str = "azure_blob"
    status: DocumentVersionStatus = DocumentVersionStatus.PENDING_UPLOAD
    failure_code: str | None = None
    failure_detail: str | None = None
    extracted_characters: int | None = None
    page_count: int | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageStatus(StrEnum):
    STREAMING = "streaming"
    COMPLETE = "complete"
    INTERRUPTED = "interrupted"
    FAILED = "failed"


@dataclass(slots=True)
class Conversation:
    organization_id: UUID
    project_id: UUID
    title: str
    created_by: UUID
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    deleted_at: datetime | None = None


@dataclass(slots=True)
class Message:
    conversation_id: UUID
    role: MessageRole
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    status: MessageStatus = MessageStatus.COMPLETE
    sequence_number: int = 0
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class LlmUsage:
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
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)


class WorkflowRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class WorkflowRun:
    organization_id: UUID
    workflow_id: str
    workflow_type: str
    resource_type: str
    resource_id: UUID
    status: WorkflowRunStatus = WorkflowRunStatus.PENDING
    started_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None
    error_message: str | None = None
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class WorkflowEvent:
    workflow_run_id: UUID
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class DocumentChunk:
    organization_id: UUID
    document_id: UUID
    version_id: UUID
    chunk_index: int
    content: str
    char_offset: int
    token_count: int
    char_count: int
    page_start: int | None = None
    page_end: int | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class ChunkEmbedding:
    organization_id: UUID
    document_chunk_id: UUID
    provider: str
    model: str
    embedding_dimension: int
    embedding_version: int
    qdrant_point_id: UUID
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class Citation:
    chunk_id: UUID
    document_version_id: UUID
    chunk_number: int
    score: float
    page_start: int | None = None
    page_end: int | None = None
    quote: str | None = None
    citation_number: int | None = None
    document_id: UUID | None = None
    document_name: str | None = None
    source_filename: str | None = None
