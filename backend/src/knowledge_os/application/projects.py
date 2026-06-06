from collections.abc import Callable, Sequence
from uuid import UUID

from knowledge_os.domain.common import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from knowledge_os.domain.entities import MembershipRole, Project, ProjectMembership, utc_now
from knowledge_os.domain.repositories import UnitOfWork


class ProjectService:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def create(
        self,
        organization_id: UUID,
        user_id: UUID,
        name: str,
        description: str | None,
    ) -> Project:
        clean_name = self._validate_name(name)
        async with self._uow_factory() as uow:
            organization_role = await uow.organizations.user_role(organization_id, user_id)
            if organization_role not in {MembershipRole.OWNER, MembershipRole.EDITOR}:
                raise AuthorizationError("Organization access denied", "organization_access_denied")
            project = Project(
                organization_id=organization_id,
                name=clean_name,
                description=self._clean_description(description),
                created_by=user_id,
            )
            await uow.projects.add(project)
            await uow.flush()
            await uow.projects.add_membership(
                ProjectMembership(
                    organization_id=organization_id,
                    project_id=project.id,
                    user_id=user_id,
                    role=MembershipRole.OWNER,
                )
            )
            await uow.commit()
            return project

    async def list(
        self, organization_id: UUID, user_id: UUID, limit: int = 50
    ) -> Sequence[Project]:
        async with self._uow_factory() as uow:
            if await uow.organizations.user_role(organization_id, user_id) is None:
                raise AuthorizationError("Organization access denied", "organization_access_denied")
            return await uow.projects.list_for_user(organization_id, user_id, min(limit, 100))

    async def get(self, project_id: UUID, user_id: UUID) -> Project:
        async with self._uow_factory() as uow:
            project = await uow.projects.get_for_user(project_id, user_id)
            if project is None:
                raise NotFoundError("Project not found", "project_not_found")
            return project

    async def update(
        self,
        project_id: UUID,
        user_id: UUID,
        expected_version: int,
        name: str | None,
        description: str | None,
    ) -> Project:
        async with self._uow_factory() as uow:
            project = await uow.projects.get_for_user(project_id, user_id)
            if project is None:
                raise NotFoundError("Project not found", "project_not_found")
            role = await uow.projects.user_role(project_id, user_id)
            if role not in {MembershipRole.OWNER, MembershipRole.EDITOR}:
                raise AuthorizationError("Project write access denied", "project_write_denied")
            if project.version != expected_version:
                raise ConflictError("Project was modified by another request", "version_conflict")
            if name is not None:
                project.name = self._validate_name(name)
            if description is not None:
                project.description = self._clean_description(description)
            project.updated_at = utc_now()
            project.version += 1
            await uow.projects.save(project)
            await uow.commit()
            return project

    async def delete(self, project_id: UUID, user_id: UUID) -> None:
        async with self._uow_factory() as uow:
            project = await uow.projects.get_for_user(project_id, user_id)
            if project is None:
                raise NotFoundError("Project not found", "project_not_found")
            if await uow.projects.user_role(project_id, user_id) != MembershipRole.OWNER:
                raise AuthorizationError(
                    "Only project owners may delete projects", "owner_required"
                )
            project.deleted_at = utc_now()
            project.updated_at = project.deleted_at
            project.version += 1
            await uow.projects.save(project)
            await uow.commit()

    @staticmethod
    def _validate_name(name: str) -> str:
        clean = name.strip()
        if not clean or len(clean) > 160:
            raise ValidationError("Project name must contain 1-160 characters", "invalid_name")
        return clean

    @staticmethod
    def _clean_description(description: str | None) -> str | None:
        if description is None:
            return None
        clean = description.strip()
        if len(clean) > 4000:
            raise ValidationError("Project description is too long", "invalid_description")
        return clean or None
