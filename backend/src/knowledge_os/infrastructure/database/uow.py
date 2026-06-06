from sqlalchemy.ext.asyncio import AsyncSession

from knowledge_os.domain.repositories import (
    ConversationRepository,
    DocumentRepository,
    LlmUsageRepository,
    OrganizationRepository,
    ProjectRepository,
    RefreshSessionRepository,
    UserRepository,
)
from knowledge_os.infrastructure.database.session import session_factory
from knowledge_os.infrastructure.repositories.sqlalchemy import (
    SqlAlchemyConversationRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyLlmUsageRepository,
    SqlAlchemyOrganizationRepository,
    SqlAlchemyProjectRepository,
    SqlAlchemyRefreshSessionRepository,
    SqlAlchemyUserRepository,
)


class SqlAlchemyUnitOfWork:
    users: UserRepository
    organizations: OrganizationRepository
    refresh_sessions: RefreshSessionRepository
    projects: ProjectRepository
    documents: DocumentRepository
    conversations: ConversationRepository
    llm_usage: LlmUsageRepository

    def __init__(self) -> None:
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        self.session = session_factory()
        self.users = SqlAlchemyUserRepository(self.session)
        self.organizations = SqlAlchemyOrganizationRepository(self.session)
        self.refresh_sessions = SqlAlchemyRefreshSessionRepository(self.session)
        self.projects = SqlAlchemyProjectRepository(self.session)
        self.documents = SqlAlchemyDocumentRepository(self.session)
        self.conversations = SqlAlchemyConversationRepository(self.session)
        self.llm_usage = SqlAlchemyLlmUsageRepository(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        tb: object,
    ) -> None:
        assert self.session is not None
        if exc_type is not None:
            await self.session.rollback()
        await self.session.close()

    async def commit(self) -> None:
        assert self.session is not None
        await self.session.commit()
