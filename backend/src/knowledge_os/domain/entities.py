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
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
