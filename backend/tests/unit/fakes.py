from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID

from knowledge_os.domain.entities import (
    Organization,
    OrganizationMembership,
    Project,
    ProjectMembership,
    RefreshSession,
    User,
    utc_now,
)


@dataclass
class Store:
    users: dict[UUID, User] = field(default_factory=dict)
    organizations: dict[UUID, Organization] = field(default_factory=dict)
    organization_memberships: list[OrganizationMembership] = field(default_factory=list)
    sessions: dict[UUID, RefreshSession] = field(default_factory=dict)
    projects: dict[UUID, Project] = field(default_factory=dict)
    project_memberships: list[ProjectMembership] = field(default_factory=list)


class UserRepo:
    def __init__(self, store: Store) -> None:
        self.store = store

    async def add(self, user: User) -> None:
        self.store.users[user.id] = user

    async def save(self, user: User) -> None:
        self.store.users[user.id] = user

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self.store.users.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((user for user in self.store.users.values() if user.email == email), None)


class OrganizationRepo:
    def __init__(self, store: Store) -> None:
        self.store = store

    async def add(self, organization: Organization) -> None:
        self.store.organizations[organization.id] = organization

    async def add_membership(self, membership: OrganizationMembership) -> None:
        self.store.organization_memberships.append(membership)

    async def list_for_user(self, user_id: UUID) -> Sequence[Organization]:
        organization_ids = {
            item.organization_id
            for item in self.store.organization_memberships
            if item.user_id == user_id
        }
        return [self.store.organizations[item] for item in organization_ids]

    async def user_role(self, organization_id: UUID, user_id: UUID) -> str | None:
        membership = next(
            (
                item
                for item in self.store.organization_memberships
                if item.organization_id == organization_id and item.user_id == user_id
            ),
            None,
        )
        return membership.role.value if membership else None


class SessionRepo:
    def __init__(self, store: Store) -> None:
        self.store = store

    async def add(self, session: RefreshSession) -> None:
        self.store.sessions[session.id] = session

    async def save(self, session: RefreshSession) -> None:
        self.store.sessions[session.id] = session

    async def get_by_id(self, session_id: UUID) -> RefreshSession | None:
        return self.store.sessions.get(session_id)

    async def revoke_family(self, family_id: UUID) -> None:
        for session in self.store.sessions.values():
            if session.family_id == family_id and session.revoked_at is None:
                session.revoked_at = utc_now()


class ProjectRepo:
    def __init__(self, store: Store) -> None:
        self.store = store

    async def add(self, project: Project) -> None:
        self.store.projects[project.id] = project

    async def save(self, project: Project) -> None:
        self.store.projects[project.id] = project

    async def add_membership(self, membership: ProjectMembership) -> None:
        self.store.project_memberships.append(membership)

    async def get_for_user(self, project_id: UUID, user_id: UUID) -> Project | None:
        project = self.store.projects.get(project_id)
        if project is None or project.deleted_at is not None:
            return None
        allowed = any(
            item.project_id == project_id and item.user_id == user_id
            for item in self.store.project_memberships
        )
        return project if allowed else None

    async def list_for_user(
        self, organization_id: UUID, user_id: UUID, limit: int
    ) -> Sequence[Project]:
        project_ids = {
            item.project_id for item in self.store.project_memberships if item.user_id == user_id
        }
        return [
            item
            for item in self.store.projects.values()
            if item.organization_id == organization_id
            and item.id in project_ids
            and item.deleted_at is None
        ][:limit]

    async def user_role(self, project_id: UUID, user_id: UUID) -> str | None:
        membership = next(
            (
                item
                for item in self.store.project_memberships
                if item.project_id == project_id and item.user_id == user_id
            ),
            None,
        )
        return membership.role.value if membership else None


class FakeUnitOfWork:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.users = UserRepo(store)
        self.organizations = OrganizationRepo(store)
        self.refresh_sessions = SessionRepo(store)
        self.projects = ProjectRepo(store)
        self.commits = 0

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1


class FakePasswordService:
    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == self.hash(password)


class FakeAccessTokenService:
    def issue(self, user_id: UUID, session_id: UUID):
        from knowledge_os.application.ports import IssuedAccessToken

        return IssuedAccessToken(f"access:{user_id}:{session_id}", 900)

    def decode(self, token: str) -> tuple[UUID, UUID]:
        _, user_id, session_id = token.split(":")
        return UUID(user_id), UUID(session_id)


class FakeRefreshTokenService:
    def issue(self, session_id: UUID) -> tuple[str, str]:
        secret = f"secret-{session_id}"
        return f"{session_id}.{secret}", f"hash:{secret}"

    def parse(self, token: str) -> tuple[UUID, str]:
        session_id, secret = token.split(".", maxsplit=1)
        return UUID(session_id), secret

    def matches(self, secret: str, token_hash: str) -> bool:
        return token_hash == f"hash:{secret}"
