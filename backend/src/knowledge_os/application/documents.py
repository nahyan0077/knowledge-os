import hashlib
from collections.abc import Callable, Sequence
from uuid import UUID, uuid4

from knowledge_os.application.ports import BlobStoragePort
from knowledge_os.domain.common import AuthorizationError, NotFoundError, ValidationError
from knowledge_os.domain.entities import (
    Document,
    DocumentVersion,
    DocumentVersionStatus,
    MembershipRole,
    utc_now,
)
from knowledge_os.domain.repositories import UnitOfWork


class DocumentService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        storage: BlobStoragePort,
    ) -> None:
        self._uow_factory = uow_factory
        self._storage = storage

    async def create(
        self,
        organization_id: UUID,
        project_id: UUID,
        user_id: UUID,
        name: str,
        filename: str,
        data: bytes,
        mime_type: str,
    ) -> tuple[Document, DocumentVersion]:
        clean_name = self._validate_name(name)
        clean_filename = filename.strip()
        if not clean_filename:
            raise ValidationError("Filename is required", "filename_required")

        async with self._uow_factory() as uow:
            project_role = await uow.projects.user_role(project_id, user_id)
            if project_role not in {MembershipRole.OWNER, MembershipRole.EDITOR}:
                raise AuthorizationError("Write access denied", "project_write_denied")

            project = await uow.projects.get_for_user(project_id, user_id)
            if project is None or project.organization_id != organization_id:
                raise NotFoundError("Project not found", "project_not_found")

            sha256 = hashlib.sha256(data).hexdigest()

            document = Document(
                organization_id=organization_id,
                project_id=project_id,
                name=clean_name,
                created_by=user_id,
            )

            version_id = uuid4()
            blob_path = (
                f"{organization_id}/{project_id}/{document.id}/{version_id}_{clean_filename}"
            )
            etag = await self._storage.upload(blob_path, data, mime_type)

            version = DocumentVersion(
                id=version_id,
                organization_id=organization_id,
                document_id=document.id,
                version_number=1,
                blob_path=blob_path,
                source_filename=clean_filename,
                mime_type=mime_type,
                size_bytes=len(data),
                sha256=sha256,
                etag=etag,
                status=DocumentVersionStatus.UPLOADED,
            )

            document.current_version_id = version.id

            await uow.documents.add(document)
            await uow.documents.add_version(version)
            await uow.commit()

            return document, version

    async def upload_version(
        self,
        document_id: UUID,
        user_id: UUID,
        filename: str,
        data: bytes,
        mime_type: str,
    ) -> DocumentVersion:
        clean_filename = filename.strip()
        if not clean_filename:
            raise ValidationError("Filename is required", "filename_required")

        async with self._uow_factory() as uow:
            document = await uow.documents.get_by_id(document_id, user_id)
            if document is None:
                raise NotFoundError("Document not found", "document_not_found")

            project_role = await uow.projects.user_role(document.project_id, user_id)
            if project_role not in {MembershipRole.OWNER, MembershipRole.EDITOR}:
                raise AuthorizationError("Write access denied", "project_write_denied")

            versions = await uow.documents.list_versions(document_id, user_id)
            next_version = 1
            if versions:
                next_version = max(v.version_number for v in versions) + 1

            sha256 = hashlib.sha256(data).hexdigest()
            version_id = uuid4()
            blob_path = (
                f"{document.organization_id}/{document.project_id}/"
                f"{document.id}/{version_id}_{clean_filename}"
            )
            etag = await self._storage.upload(blob_path, data, mime_type)

            version = DocumentVersion(
                id=version_id,
                organization_id=document.organization_id,
                document_id=document.id,
                version_number=next_version,
                blob_path=blob_path,
                source_filename=clean_filename,
                mime_type=mime_type,
                size_bytes=len(data),
                sha256=sha256,
                etag=etag,
                status=DocumentVersionStatus.UPLOADED,
            )

            document.current_version_id = version.id
            document.updated_at = utc_now()

            await uow.documents.add_version(version)
            await uow.documents.save(document)
            await uow.commit()

            return version

    async def list(
        self,
        organization_id: UUID,
        project_id: UUID,
        user_id: UUID,
        limit: int = 50,
    ) -> Sequence[Document]:
        async with self._uow_factory() as uow:
            project_role = await uow.projects.user_role(project_id, user_id)
            if project_role is None:
                raise AuthorizationError("Access denied", "project_access_denied")
            return await uow.documents.list_for_project(
                organization_id, project_id, user_id, min(limit, 100)
            )

    async def get(self, document_id: UUID, user_id: UUID) -> Document:
        async with self._uow_factory() as uow:
            document = await uow.documents.get_by_id(document_id, user_id)
            if document is None:
                raise NotFoundError("Document not found", "document_not_found")
            return document

    async def delete(self, document_id: UUID, user_id: UUID) -> None:
        async with self._uow_factory() as uow:
            document = await uow.documents.get_by_id(document_id, user_id)
            if document is None:
                raise NotFoundError("Document not found", "document_not_found")

            project_role = await uow.projects.user_role(document.project_id, user_id)
            if project_role not in {MembershipRole.OWNER, MembershipRole.EDITOR}:
                raise AuthorizationError("Write access denied", "project_write_denied")

            document.deleted_at = utc_now()
            document.updated_at = document.deleted_at
            await uow.documents.save(document)
            await uow.commit()

    @staticmethod
    def _validate_name(name: str) -> str:
        clean = name.strip()
        if not clean or len(clean) > 255:
            raise ValidationError("Document name must contain 1-255 characters", "invalid_name")
        return clean
