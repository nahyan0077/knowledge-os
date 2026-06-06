from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from knowledge_os.domain.entities import Organization, Project, User


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
