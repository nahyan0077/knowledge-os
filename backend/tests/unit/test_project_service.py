from uuid import uuid4

import pytest

from knowledge_os.application.projects import ProjectService
from knowledge_os.domain.common import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
)
from knowledge_os.domain.entities import (
    MembershipRole,
    Organization,
    OrganizationMembership,
    OrganizationType,
    User,
)
from tests.unit.fakes import FakeUnitOfWork, Store


def setup_store() -> tuple[Store, User, Organization]:
    user = User("owner@example.com", "Owner", "hash")
    organization = Organization("Workspace", "workspace", OrganizationType.PERSONAL)
    store = Store(
        users={user.id: user},
        organizations={organization.id: organization},
        organization_memberships=[
            OrganizationMembership(organization.id, user.id, MembershipRole.OWNER)
        ],
    )
    return store, user, organization


def make_service(store: Store) -> ProjectService:
    return ProjectService(lambda: FakeUnitOfWork(store))


@pytest.mark.asyncio
async def test_create_project_assigns_creator_as_owner() -> None:
    store, user, organization = setup_store()

    project = await make_service(store).create(organization.id, user.id, "Research", "Notes")

    assert project.organization_id == organization.id
    assert store.project_memberships[0].role is MembershipRole.OWNER


@pytest.mark.asyncio
async def test_create_project_rejects_cross_tenant_user() -> None:
    store, _, organization = setup_store()

    with pytest.raises(AuthorizationError):
        await make_service(store).create(organization.id, uuid4(), "Unauthorized", None)


@pytest.mark.asyncio
async def test_update_rejects_stale_version() -> None:
    store, user, organization = setup_store()
    service = make_service(store)
    project = await service.create(organization.id, user.id, "Research", None)

    with pytest.raises(ConflictError) as error:
        await service.update(
            project.id, user.id, expected_version=2, name="Changed", description=None
        )

    assert error.value.code == "version_conflict"


@pytest.mark.asyncio
async def test_delete_is_owner_only_and_soft_deletes() -> None:
    store, owner, organization = setup_store()
    service = make_service(store)
    project = await service.create(organization.id, owner.id, "Research", None)

    await service.delete(project.id, owner.id)

    assert store.projects[project.id].deleted_at is not None
    with pytest.raises(NotFoundError):
        await service.get(project.id, owner.id)
