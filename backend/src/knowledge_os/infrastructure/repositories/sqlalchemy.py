from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from knowledge_os.domain.common import ConflictError
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
)
from knowledge_os.infrastructure.database.models import (
    ConversationModel,
    DocumentModel,
    DocumentVersionModel,
    LlmUsageModel,
    MessageModel,
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
            raise ConflictError("Project was modified by another request", "version_conflict")

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


def to_document(row: DocumentModel) -> Document:
    return Document(
        id=row.id,
        organization_id=row.organization_id,
        project_id=row.project_id,
        name=row.name,
        current_version_id=row.current_version_id,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


def to_document_version(row: DocumentVersionModel) -> DocumentVersion:
    return DocumentVersion(
        id=row.id,
        organization_id=row.organization_id,
        document_id=row.document_id,
        version_number=row.version_number,
        storage_provider=row.storage_provider,
        blob_path=row.blob_path,
        source_filename=row.source_filename,
        mime_type=row.mime_type,
        size_bytes=row.size_bytes,
        sha256=row.sha256,
        etag=row.etag,
        status=row.status,
        failure_code=row.failure_code,
        failure_detail=row.failure_detail,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, document: Document) -> None:
        self.session.add(
            DocumentModel(
                id=document.id,
                organization_id=document.organization_id,
                project_id=document.project_id,
                name=document.name,
                current_version_id=document.current_version_id,
                created_by=document.created_by,
                deleted_at=document.deleted_at,
                created_at=document.created_at,
                updated_at=document.updated_at,
            )
        )

    async def save(self, document: Document) -> None:
        await self.session.execute(
            update(DocumentModel)
            .where(
                DocumentModel.id == document.id,
                DocumentModel.organization_id == document.organization_id,
            )
            .values(
                name=document.name,
                current_version_id=document.current_version_id,
                deleted_at=document.deleted_at,
                updated_at=document.updated_at,
            )
        )

    async def get_by_id(self, document_id: UUID, user_id: UUID) -> Document | None:
        row = await self.session.scalar(
            select(DocumentModel)
            .join(ProjectMemberModel, ProjectMemberModel.project_id == DocumentModel.project_id)
            .where(
                DocumentModel.id == document_id,
                ProjectMemberModel.user_id == user_id,
                DocumentModel.deleted_at.is_(None),
            )
        )
        return to_document(row) if row else None

    async def list_for_project(
        self, organization_id: UUID, project_id: UUID, user_id: UUID, limit: int
    ) -> Sequence[Document]:
        rows = (
            await self.session.scalars(
                select(DocumentModel)
                .join(ProjectMemberModel, ProjectMemberModel.project_id == DocumentModel.project_id)
                .where(
                    DocumentModel.organization_id == organization_id,
                    DocumentModel.project_id == project_id,
                    ProjectMemberModel.user_id == user_id,
                    DocumentModel.deleted_at.is_(None),
                )
                .order_by(DocumentModel.updated_at.desc())
                .limit(limit)
            )
        ).all()
        return [to_document(row) for row in rows]

    async def add_version(self, version: DocumentVersion) -> None:
        self.session.add(
            DocumentVersionModel(
                id=version.id,
                organization_id=version.organization_id,
                document_id=version.document_id,
                version_number=version.version_number,
                storage_provider=version.storage_provider,
                blob_path=version.blob_path,
                source_filename=version.source_filename,
                mime_type=version.mime_type,
                size_bytes=version.size_bytes,
                sha256=version.sha256,
                etag=version.etag,
                status=version.status,
                failure_code=version.failure_code,
                failure_detail=version.failure_detail,
                created_at=version.created_at,
                updated_at=version.updated_at,
            )
        )

    async def save_version(self, version: DocumentVersion) -> None:
        await self.session.execute(
            update(DocumentVersionModel)
            .where(
                DocumentVersionModel.id == version.id,
                DocumentVersionModel.organization_id == version.organization_id,
            )
            .values(
                status=version.status,
                failure_code=version.failure_code,
                failure_detail=version.failure_detail,
                updated_at=version.updated_at,
            )
        )

    async def get_version_by_id(self, version_id: UUID, user_id: UUID) -> DocumentVersion | None:
        row = await self.session.scalar(
            select(DocumentVersionModel)
            .join(DocumentModel, DocumentModel.id == DocumentVersionModel.document_id)
            .join(ProjectMemberModel, ProjectMemberModel.project_id == DocumentModel.project_id)
            .where(
                DocumentVersionModel.id == version_id,
                ProjectMemberModel.user_id == user_id,
                DocumentModel.deleted_at.is_(None),
            )
        )
        return to_document_version(row) if row else None

    async def get_version_by_number(
        self, document_id: UUID, version_number: int, user_id: UUID
    ) -> DocumentVersion | None:
        row = await self.session.scalar(
            select(DocumentVersionModel)
            .join(DocumentModel, DocumentModel.id == DocumentVersionModel.document_id)
            .join(ProjectMemberModel, ProjectMemberModel.project_id == DocumentModel.project_id)
            .where(
                DocumentVersionModel.document_id == document_id,
                DocumentVersionModel.version_number == version_number,
                ProjectMemberModel.user_id == user_id,
                DocumentModel.deleted_at.is_(None),
            )
        )
        return to_document_version(row) if row else None

    async def list_versions(self, document_id: UUID, user_id: UUID) -> Sequence[DocumentVersion]:
        rows = (
            await self.session.scalars(
                select(DocumentVersionModel)
                .join(DocumentModel, DocumentModel.id == DocumentVersionModel.document_id)
                .join(ProjectMemberModel, ProjectMemberModel.project_id == DocumentModel.project_id)
                .where(
                    DocumentVersionModel.document_id == document_id,
                    ProjectMemberModel.user_id == user_id,
                    DocumentModel.deleted_at.is_(None),
                )
                .order_by(DocumentVersionModel.version_number.desc())
            )
        ).all()
        return [to_document_version(row) for row in rows]


def to_conversation(row: ConversationModel) -> Conversation:
    return Conversation(
        id=row.id,
        organization_id=row.organization_id,
        project_id=row.project_id,
        title=row.title,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


def to_message(row: MessageModel) -> Message:
    return Message(
        id=row.id,
        conversation_id=row.conversation_id,
        role=row.role,
        content=row.content,
        metadata=row.meta,
        created_at=row.created_at,
    )


class SqlAlchemyConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, conversation: Conversation) -> None:
        self.session.add(
            ConversationModel(
                id=conversation.id,
                organization_id=conversation.organization_id,
                project_id=conversation.project_id,
                title=conversation.title,
                created_by=conversation.created_by,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
                deleted_at=conversation.deleted_at,
            )
        )

    async def save(self, conversation: Conversation) -> None:
        await self.session.execute(
            update(ConversationModel)
            .where(
                ConversationModel.id == conversation.id,
                ConversationModel.organization_id == conversation.organization_id,
            )
            .values(
                title=conversation.title,
                deleted_at=conversation.deleted_at,
                updated_at=conversation.updated_at,
            )
        )

    async def get_by_id(self, conversation_id: UUID, user_id: UUID) -> Conversation | None:
        row = await self.session.scalar(
            select(ConversationModel)
            .join(ProjectMemberModel, ProjectMemberModel.project_id == ConversationModel.project_id)
            .where(
                ConversationModel.id == conversation_id,
                ProjectMemberModel.user_id == user_id,
                ConversationModel.deleted_at.is_(None),
            )
        )
        return to_conversation(row) if row else None

    async def list_for_project(
        self, organization_id: UUID, project_id: UUID, user_id: UUID, limit: int
    ) -> Sequence[Conversation]:
        rows = (
            await self.session.scalars(
                select(ConversationModel)
                .join(
                    ProjectMemberModel,
                    ProjectMemberModel.project_id == ConversationModel.project_id,
                )
                .where(
                    ConversationModel.organization_id == organization_id,
                    ConversationModel.project_id == project_id,
                    ProjectMemberModel.user_id == user_id,
                    ConversationModel.deleted_at.is_(None),
                )
                .order_by(ConversationModel.updated_at.desc())
                .limit(limit)
            )
        ).all()
        return [to_conversation(row) for row in rows]

    async def add_message(self, message: Message) -> None:
        self.session.add(
            MessageModel(
                id=message.id,
                conversation_id=message.conversation_id,
                role=message.role,
                content=message.content,
                meta=message.metadata,
                created_at=message.created_at,
            )
        )

    async def list_messages(self, conversation_id: UUID, user_id: UUID) -> Sequence[Message]:
        rows = (
            await self.session.scalars(
                select(MessageModel)
                .join(ConversationModel, ConversationModel.id == MessageModel.conversation_id)
                .join(
                    ProjectMemberModel,
                    ProjectMemberModel.project_id == ConversationModel.project_id,
                )
                .where(
                    MessageModel.conversation_id == conversation_id,
                    ProjectMemberModel.user_id == user_id,
                    ConversationModel.deleted_at.is_(None),
                )
                .order_by(MessageModel.created_at.asc())
            )
        ).all()
        return [to_message(row) for row in rows]


def to_llm_usage(row: LlmUsageModel) -> LlmUsage:
    return LlmUsage(
        id=row.id,
        organization_id=row.organization_id,
        conversation_id=row.conversation_id,
        message_id=row.message_id,
        provider=row.provider,
        model=row.model,
        input_tokens=row.input_tokens,
        output_tokens=row.output_tokens,
        total_tokens=row.total_tokens,
        latency_ms=row.latency_ms,
        cost=float(row.cost),
        created_at=row.created_at,
    )


class SqlAlchemyLlmUsageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, usage: LlmUsage) -> None:
        self.session.add(
            LlmUsageModel(
                id=usage.id,
                organization_id=usage.organization_id,
                conversation_id=usage.conversation_id,
                message_id=usage.message_id,
                provider=usage.provider,
                model=usage.model,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
                latency_ms=usage.latency_ms,
                cost=usage.cost,
                created_at=usage.created_at,
            )
        )

    async def get_by_id(self, usage_id: UUID) -> LlmUsage | None:
        row = await self.session.scalar(select(LlmUsageModel).where(LlmUsageModel.id == usage_id))
        return to_llm_usage(row) if row else None
