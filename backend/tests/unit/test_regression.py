import datetime
import inspect

import pytest
from pydantic import ValidationError as PydanticValidationError

from knowledge_os.api.schemas import LoginRequest, RegisterRequest
from knowledge_os.application.auth import AuthService
from knowledge_os.application.projects import ProjectService
from knowledge_os.domain.common import ConflictError
from knowledge_os.domain.entities import (
    MembershipRole,
    Organization,
    OrganizationMembership,
    OrganizationType,
    User,
)
from knowledge_os.infrastructure.database.models import RefreshSessionModel
from knowledge_os.infrastructure.security.services import Argon2PasswordService
from tests.unit.fakes import (
    FakeAccessTokenService,
    FakePasswordService,
    FakeRefreshTokenService,
    FakeUnitOfWork,
    Store,
)


def make_auth_service(store: Store) -> AuthService:
    return AuthService(
        lambda: FakeUnitOfWork(store),
        FakePasswordService(),
        FakeAccessTokenService(),
        FakeRefreshTokenService(),
        refresh_ttl_days=30,
    )


def make_project_service(store: Store) -> ProjectService:
    return ProjectService(lambda: FakeUnitOfWork(store))


def test_argon2_service_is_async() -> None:
    """Regression: Check that Argon2PasswordService uses coroutine methods (non-blocking)."""
    service = Argon2PasswordService()
    assert inspect.iscoroutinefunction(service.hash)
    assert inspect.iscoroutinefunction(service.verify)


@pytest.mark.asyncio
async def test_login_updates_updated_at() -> None:
    """Regression: Check that user.updated_at is updated when logging in."""
    store = Store()
    auth = make_auth_service(store)
    reg = await auth.register("person@example.com", "Person", "correct-horse-battery")
    # Set to a fixed past time to guarantee change detection
    reg.user.updated_at = datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC)

    login_result = await auth.login("person@example.com", "correct-horse-battery")
    assert login_result.user.updated_at > datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC)


def test_refresh_session_indexes_exist() -> None:
    """Regression: Check that RefreshSessionModel includes required indices on fields."""
    indexes = [index.name for index in RefreshSessionModel.__table__.indexes]
    assert "ix_refresh_sessions_user_id" in indexes
    assert "ix_refresh_sessions_expires_at" in indexes
    assert "ix_refresh_sessions_family_id" in indexes


def test_email_validation_on_request_schemas() -> None:
    """Regression: Check that schemas reject invalid email format using EmailStr."""
    with pytest.raises(PydanticValidationError):
        RegisterRequest(
            email="invalid-email",
            display_name="Person",
            password="correct-horse-battery",
        )

    with pytest.raises(PydanticValidationError):
        LoginRequest(email="invalid-email", password="password1234")


@pytest.mark.asyncio
async def test_fake_repo_concurrency_raises_conflict_error() -> None:
    """Regression: Check that concurrency conflict in fake repo raises ConflictError."""
    user = User("owner@example.com", "Owner", "hash")
    organization = Organization("Workspace", "workspace", OrganizationType.PERSONAL)
    store = Store(
        users={user.id: user},
        organizations={organization.id: organization},
        organization_memberships=[
            OrganizationMembership(organization.id, user.id, MembershipRole.OWNER)
        ],
    )
    service = make_project_service(store)
    project = await service.create(organization.id, user.id, "Research", None)

    # Simulate database version bump by another request
    store.projects[project.id].version = 2

    # Attempting to save with stale version should fail with ConflictError
    with pytest.raises(ConflictError) as exc:
        await service.update(
            project.id,
            user.id,
            expected_version=1,
            name="New Name",
            description=None,
        )
    assert exc.value.code == "version_conflict"
