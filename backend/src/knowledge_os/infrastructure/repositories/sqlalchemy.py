from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from knowledge_os.domain.common import ValidationError
from knowledge_os.domain.entities import (
    Organization,
    OrganizationMembership,
    Project,
    ProjectMembership,
    RefreshSession,
    User,
)
from knowledge_os.infrastructure.database.models import (
    OrganizationMemberModel,
    OrganizationModel,
    ProjectMemberModel,
    ProjectModel,
    RefreshSessionModel,
    UserModel,
)


def to_user(row: UserModel) -> User:
    return User(
        id=row.id,
        email=row.email,
        display_name=row.display_name,
        password_hash=row.password_hash,
        status=row.status,
        last_login_at=row.last_login_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def to_organization(row: OrganizationModel) -> Organization:
    return Organization(
        id=row.id,
        name=row.name,
        slug=row.slug,
        type=row.type,
        settings=row.settings,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def to_session(row: RefreshSessionModel) -> RefreshSession:
    return RefreshSession(
        id=row.id,
        user_id=row.user_id,
        token_hash=row.token_hash,
        family_id=row.family_id,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        replaced_by_session_id=row.replaced_by_session_id,
        created_at=row.created_at,
    )


def to_project(row: ProjectModel) -> Project:
    return Project(
        id=row.id,
        organization_id=row.organization_id,
        name=row.name,
        description=row.description,
        settings=row.settings,
        created_by=row.created_by,
        deleted_at=row.deleted_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        version=row.version,
    )


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, user: User) -> None:
        self.session.add(
            UserModel(
                id=user.id,
                email=user.email,
                display_name=user.display_name,
                password_hash=user.password_hash,
                status=user.status,
                last_login_at=user.last_login_at,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
        )

    async def save(self, user: User) -> None:
        await self.session.execute(
            update(UserModel)
            .where(UserModel.id == user.id)
            .values(
                display_name=user.display_name,
                status=user.status,
                last_login_at=user.last_login_at,
                updated_at=user.updated_at,
            )
        )

    async def get_by_id(self, user_id: UUID) -> User | None:
        row = await self.session.scalar(select(UserModel).where(UserModel.id == user_id))
        return to_user(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        row = await self.session.scalar(select(UserModel).where(UserModel.email == email))
        return to_user(row) if row else None


class SqlAlchemyOrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, organization: Organization) -> None:
        self.session.add(
            OrganizationModel(
                id=organization.id,
                name=organization.name,
                slug=organization.slug,
                type=organization.type,
                settings=organization.settings,
                created_at=organization.created_at,
                updated_at=organization.updated_at,
            )
        )

    async def add_membership(self, membership: OrganizationMembership) -> None:
        self.session.add(
            OrganizationMemberModel(
                id=membership.id,
                organization_id=membership.organization_id,
                user_id=membership.user_id,
                role=membership.role,
                created_at=membership.created_at,
            )
        )

    async def list_for_user(self, user_id: UUID) -> Sequence[Organization]:
        rows = (
            await self.session.scalars(
                select(OrganizationModel)
                .join(
                    OrganizationMemberModel,
                    OrganizationMemberModel.organization_id == OrganizationModel.id,
                )
                .where(
                    OrganizationMemberModel.user_id == user_id,
                    OrganizationModel.deleted_at.is_(None),
                )
                .order_by(OrganizationModel.created_at)
            )
        ).all()
        return [to_organization(row) for row in rows]

    async def user_role(self, organization_id: UUID, user_id: UUID) -> str | None:
        role = await self.session.scalar(
            select(OrganizationMemberModel.role).where(
                OrganizationMemberModel.organization_id == organization_id,
                OrganizationMemberModel.user_id == user_id,
            )
        )
        return role.value if role else None


class SqlAlchemyRefreshSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, session: RefreshSession) -> None:
        self.session.add(
            RefreshSessionModel(
                id=session.id,
                user_id=session.user_id,
                token_hash=session.token_hash,
                family_id=session.family_id,
                expires_at=session.expires_at,
                revoked_at=session.revoked_at,
                replaced_by_session_id=session.replaced_by_session_id,
                created_at=session.created_at,
            )
        )

    async def save(self, session: RefreshSession) -> None:
        await self.session.execute(
            update(RefreshSessionModel)
            .where(RefreshSessionModel.id == session.id)
            .values(
                revoked_at=session.revoked_at,
                replaced_by_session_id=session.replaced_by_session_id,
            )
        )

    async def get_by_id(self, session_id: UUID) -> RefreshSession | None:
        row = await self.session.scalar(
            select(RefreshSessionModel).where(RefreshSessionModel.id == session_id)
        )
        return to_session(row) if row else None

    async def revoke_family(self, family_id: UUID) -> None:
        await self.session.execute(
            update(RefreshSessionModel)
            .where(
                RefreshSessionModel.family_id == family_id,
                RefreshSessionModel.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )


class SqlAlchemyProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, project: Project) -> None:
        self.session.add(
            ProjectModel(
                id=project.id,
                organization_id=project.organization_id,
                name=project.name,
                description=project.description,
                settings=project.settings,
                created_by=project.created_by,
                deleted_at=project.deleted_at,
                version=project.version,
                created_at=project.created_at,
                updated_at=project.updated_at,
            )
        )

    async def save(self, project: Project) -> None:
        result = cast(
            CursorResult[Any],
            await self.session.execute(
                update(ProjectModel)
                .where(
                    ProjectModel.id == project.id,
                    ProjectModel.organization_id == project.organization_id,
                    ProjectModel.version == project.version - 1,
                )
                .values(
                    name=project.name,
                    description=project.description,
                    settings=project.settings,
                    deleted_at=project.deleted_at,
                    updated_at=project.updated_at,
                    version=project.version,
                )
            ),
        )
        if result.rowcount != 1:
            raise ValidationError("Project was modified by another request", "version_conflict")

    async def add_membership(self, membership: ProjectMembership) -> None:
        self.session.add(
            ProjectMemberModel(
                id=membership.id,
                organization_id=membership.organization_id,
                project_id=membership.project_id,
                user_id=membership.user_id,
                role=membership.role,
                created_at=membership.created_at,
            )
        )

    async def get_for_user(self, project_id: UUID, user_id: UUID) -> Project | None:
        row = await self.session.scalar(
            select(ProjectModel)
            .join(ProjectMemberModel, ProjectMemberModel.project_id == ProjectModel.id)
            .where(
                ProjectModel.id == project_id,
                ProjectMemberModel.user_id == user_id,
                ProjectMemberModel.organization_id == ProjectModel.organization_id,
                ProjectModel.deleted_at.is_(None),
            )
        )
        return to_project(row) if row else None

    async def list_for_user(
        self, organization_id: UUID, user_id: UUID, limit: int
    ) -> Sequence[Project]:
        rows = (
            await self.session.scalars(
                select(ProjectModel)
                .join(ProjectMemberModel, ProjectMemberModel.project_id == ProjectModel.id)
                .where(
                    ProjectModel.organization_id == organization_id,
                    ProjectMemberModel.user_id == user_id,
                    ProjectMemberModel.organization_id == ProjectModel.organization_id,
                    ProjectModel.deleted_at.is_(None),
                )
                .order_by(ProjectModel.updated_at.desc())
                .limit(limit)
            )
        ).all()
        return [to_project(row) for row in rows]

    async def user_role(self, project_id: UUID, user_id: UUID) -> str | None:
        role = await self.session.scalar(
            select(ProjectMemberModel.role).where(
                ProjectMemberModel.project_id == project_id,
                ProjectMemberModel.user_id == user_id,
            )
        )
        return role.value if role else None
