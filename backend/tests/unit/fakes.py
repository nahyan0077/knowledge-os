from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from uuid import UUID

from knowledge_os.application.ports import (
    LlmModelConfig,
    LlmResponse,
    LlmResponseChunk,
    LlmUsageMetrics,
)
from knowledge_os.domain.entities import (
    Conversation,
    Document,
    DocumentVersion,
    LlmUsage,
    Message,
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
    documents: dict[UUID, Document] = field(default_factory=dict)
    versions: dict[UUID, DocumentVersion] = field(default_factory=dict)
    conversations: dict[UUID, Conversation] = field(default_factory=dict)
    messages: list[Message] = field(default_factory=list)
    llm_usage: dict[UUID, LlmUsage] = field(default_factory=dict)


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
        current = self.store.projects.get(project.id)
        if current is not None:
            if current.version != project.version - 1:
                from knowledge_os.domain.common import ConflictError

                raise ConflictError("Project was modified by another request", "version_conflict")
        self.store.projects[project.id] = project

    async def add_membership(self, membership: ProjectMembership) -> None:
        self.store.project_memberships.append(membership)

    async def get_for_user(self, project_id: UUID, user_id: UUID) -> Project | None:
        import copy

        project = self.store.projects.get(project_id)
        if project is None or project.deleted_at is not None:
            return None
        allowed = any(
            item.project_id == project_id and item.user_id == user_id
            for item in self.store.project_memberships
        )
        return copy.deepcopy(project) if allowed else None

    async def list_for_user(
        self, organization_id: UUID, user_id: UUID, limit: int
    ) -> Sequence[Project]:
        import copy

        project_ids = {
            item.project_id for item in self.store.project_memberships if item.user_id == user_id
        }
        return [
            copy.deepcopy(item)
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


class DocumentRepo:
    def __init__(self, store: Store) -> None:
        self.store = store

    async def add(self, document: Document) -> None:
        self.store.documents[document.id] = document

    async def save(self, document: Document) -> None:
        self.store.documents[document.id] = document

    async def get_by_id(self, document_id: UUID, user_id: UUID) -> Document | None:
        import copy

        doc = self.store.documents.get(document_id)
        if doc is None or doc.deleted_at is not None:
            return None
        allowed = any(
            item.project_id == doc.project_id and item.user_id == user_id
            for item in self.store.project_memberships
        )
        return copy.deepcopy(doc) if allowed else None

    async def list_for_project(
        self, organization_id: UUID, project_id: UUID, user_id: UUID, limit: int
    ) -> Sequence[Document]:
        import copy

        allowed = any(
            item.project_id == project_id and item.user_id == user_id
            for item in self.store.project_memberships
        )
        if not allowed:
            return []
        return [
            copy.deepcopy(doc)
            for doc in self.store.documents.values()
            if doc.organization_id == organization_id
            and doc.project_id == project_id
            and doc.deleted_at is None
        ][:limit]

    async def add_version(self, version: DocumentVersion) -> None:
        self.store.versions[version.id] = version

    async def save_version(self, version: DocumentVersion) -> None:
        self.store.versions[version.id] = version

    async def get_version_by_id(self, version_id: UUID, user_id: UUID) -> DocumentVersion | None:
        import copy

        ver = self.store.versions.get(version_id)
        if ver is None:
            return None
        doc = self.store.documents.get(ver.document_id)
        if doc is None or doc.deleted_at is not None:
            return None
        allowed = any(
            item.project_id == doc.project_id and item.user_id == user_id
            for item in self.store.project_memberships
        )
        return copy.deepcopy(ver) if allowed else None

    async def get_version_by_number(
        self, document_id: UUID, version_number: int, user_id: UUID
    ) -> DocumentVersion | None:
        import copy

        doc = self.store.documents.get(document_id)
        if doc is None or doc.deleted_at is not None:
            return None
        allowed = any(
            item.project_id == doc.project_id and item.user_id == user_id
            for item in self.store.project_memberships
        )
        if not allowed:
            return None
        ver = next(
            (
                v
                for v in self.store.versions.values()
                if v.document_id == document_id and v.version_number == version_number
            ),
            None,
        )
        return copy.deepcopy(ver) if ver else None

    async def list_versions(self, document_id: UUID, user_id: UUID) -> Sequence[DocumentVersion]:
        import copy

        doc = self.store.documents.get(document_id)
        if doc is None or doc.deleted_at is not None:
            return []
        allowed = any(
            item.project_id == doc.project_id and item.user_id == user_id
            for item in self.store.project_memberships
        )
        if not allowed:
            return []
        return sorted(
            [
                copy.deepcopy(v)
                for v in self.store.versions.values()
                if v.document_id == document_id
            ],
            key=lambda x: x.version_number,
            reverse=True,
        )


class ConversationRepo:
    def __init__(self, store: Store) -> None:
        self.store = store

    async def add(self, conversation: Conversation) -> None:
        self.store.conversations[conversation.id] = conversation

    async def save(self, conversation: Conversation) -> None:
        self.store.conversations[conversation.id] = conversation

    async def get_by_id(self, conversation_id: UUID, user_id: UUID) -> Conversation | None:
        import copy

        conv = self.store.conversations.get(conversation_id)
        if conv is None or conv.deleted_at is not None:
            return None
        allowed = any(
            item.project_id == conv.project_id and item.user_id == user_id
            for item in self.store.project_memberships
        )
        return copy.deepcopy(conv) if allowed else None

    async def list_for_project(
        self, organization_id: UUID, project_id: UUID, user_id: UUID, limit: int
    ) -> Sequence[Conversation]:
        import copy

        allowed = any(
            item.project_id == project_id and item.user_id == user_id
            for item in self.store.project_memberships
        )
        if not allowed:
            return []
        return sorted(
            [
                copy.deepcopy(conv)
                for conv in self.store.conversations.values()
                if conv.organization_id == organization_id
                and conv.project_id == project_id
                and conv.deleted_at is None
            ],
            key=lambda x: x.updated_at,
            reverse=True,
        )[:limit]

    async def add_message(self, message: Message) -> None:
        if message.sequence_number <= 0:
            max_seq = max(
                [
                    msg.sequence_number
                    for msg in self.store.messages
                    if msg.conversation_id == message.conversation_id
                ],
                default=0,
            )
            message.sequence_number = max_seq + 1
        self.store.messages.append(message)

    async def save_message(self, message: Message) -> None:
        for idx, msg in enumerate(self.store.messages):
            if msg.id == message.id:
                self.store.messages[idx] = message
                break

    async def list_messages(self, conversation_id: UUID, user_id: UUID) -> Sequence[Message]:
        import copy

        conv = self.store.conversations.get(conversation_id)
        if conv is None or conv.deleted_at is not None:
            return []
        allowed = any(
            item.project_id == conv.project_id and item.user_id == user_id
            for item in self.store.project_memberships
        )
        if not allowed:
            return []
        return sorted(
            [
                copy.deepcopy(msg)
                for msg in self.store.messages
                if msg.conversation_id == conversation_id
            ],
            key=lambda x: x.sequence_number,
        )


class LlmUsageRepo:
    def __init__(self, store: Store) -> None:
        self.store = store

    async def add(self, usage: LlmUsage) -> None:
        self.store.llm_usage[usage.id] = usage

    async def get_by_id(self, usage_id: UUID) -> LlmUsage | None:
        import copy

        usage = self.store.llm_usage.get(usage_id)
        return copy.deepcopy(usage) if usage else None


class FakeUnitOfWork:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.users = UserRepo(store)
        self.organizations = OrganizationRepo(store)
        self.refresh_sessions = SessionRepo(store)
        self.projects = ProjectRepo(store)
        self.documents = DocumentRepo(store)
        self.conversations = ConversationRepo(store)
        self.llm_usage = LlmUsageRepo(store)
        self.commits = 0

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1


class FakePasswordService:
    async def hash(self, password: str) -> str:
        return f"hashed:{password}"

    async def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == await self.hash(password)


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


class FakeChatAgent:
    def __init__(
        self, response_content: str = "Fake response", metrics: LlmUsageMetrics | None = None
    ) -> None:
        self.response_content = response_content
        self.metrics = metrics or LlmUsageMetrics(
            provider="test",
            model="test-model",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            latency_ms=100,
            cost=0.0005,
        )
        self.calls: list[tuple[str, list[tuple[str, str]], LlmModelConfig]] = []

    async def generate(
        self,
        system_prompt: str,
        messages: list[tuple[str, str]],
        config: LlmModelConfig,
    ) -> LlmResponse:
        self.calls.append((system_prompt, messages, config))
        return LlmResponse(content=self.response_content, usage=self.metrics)

    async def generate_stream(
        self,
        system_prompt: str,
        messages: list[tuple[str, str]],
        config: LlmModelConfig,
    ) -> AsyncIterator[LlmResponseChunk | LlmUsageMetrics]:
        self.calls.append((system_prompt, messages, config))
        for chunk in self.response_content.split():
            yield LlmResponseChunk(content=chunk + " ")
        yield self.metrics
