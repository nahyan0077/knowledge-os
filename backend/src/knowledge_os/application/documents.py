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
                storage_provider=self._storage.provider_name,
                status=DocumentVersionStatus.UPLOADED,
            )

            document.current_version_id = version.id

            await uow.documents.add(document)
            await uow.flush()
            await uow.documents.add_version(version)
            await uow.commit()

        await self._start_processing_workflow(
            organization_id=organization_id,
            project_id=project_id,
            document_id=document.id,
            version_id=version.id,
            user_id=user_id,
        )

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
                storage_provider=self._storage.provider_name,
                status=DocumentVersionStatus.UPLOADED,
            )

            document.current_version_id = version.id
            document.updated_at = utc_now()

            await uow.documents.add_version(version)
            await uow.documents.save(document)
            await uow.commit()

        await self._start_processing_workflow(
            organization_id=document.organization_id,
            project_id=document.project_id,
            document_id=document.id,
            version_id=version.id,
            user_id=user_id,
        )

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

    async def list_versions(self, document_id: UUID, user_id: UUID) -> Sequence[DocumentVersion]:
        async with self._uow_factory() as uow:
            document = await uow.documents.get_by_id(document_id, user_id)
            if document is None:
                raise NotFoundError("Document not found", "document_not_found")
            return await uow.documents.list_versions(document_id, user_id)

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

    async def _start_processing_workflow(
        self,
        organization_id: UUID,
        project_id: UUID,
        document_id: UUID,
        version_id: UUID,
        user_id: UUID,
    ) -> None:
        import logging

        from knowledge_os.domain.entities import WorkflowRun, WorkflowRunStatus
        from knowledge_os.infrastructure.workflows.client import get_temporal_client

        logger = logging.getLogger(__name__)
        workflow_id = f"doc-processing-{version_id}"
        run_id = uuid4()

        async with self._uow_factory() as uow:
            run = WorkflowRun(
                id=run_id,
                organization_id=organization_id,
                workflow_id=workflow_id,
                workflow_type="DocumentProcessingWorkflow",
                resource_type="document",
                resource_id=document_id,
                status=WorkflowRunStatus.PENDING,
            )
            await uow.workflow_runs.add(run)
            await uow.commit()

        try:
            client = await get_temporal_client()
            payload = {
                "organization_id": str(organization_id),
                "project_id": str(project_id),
                "document_id": str(document_id),
                "version_id": str(version_id),
                "user_id": str(user_id),
                "workflow_run_id": str(run_id),
            }
            await client.start_workflow(
                "DocumentProcessingWorkflow",
                payload,
                id=workflow_id,
                task_queue="document-processing",
            )
        except Exception as exc:
            logger.error(f"Failed to start Temporal workflow for document {document_id}: {exc}")
            async with self._uow_factory() as uow:
                existing_run = await uow.workflow_runs.get_by_id(run_id)
                if existing_run:
                    existing_run.status = WorkflowRunStatus.FAILED
                    existing_run.completed_at = utc_now()
                    existing_run.error_message = f"Temporal start failure: {exc}"
                    await uow.workflow_runs.save(existing_run)
                await uow.commit()
