from uuid import uuid4

import pytest
from temporalio.client import WorkflowFailureError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from knowledge_os.application.workflows.document import DocumentProcessingWorkflow
from knowledge_os.domain.entities import (
    Document,
    DocumentVersion,
    DocumentVersionStatus,
    MembershipRole,
    Organization,
    OrganizationType,
    Project,
    ProjectMembership,
    WorkflowRun,
    WorkflowRunStatus,
)
from knowledge_os.infrastructure.workflows.activities import (
    chunk_document,
    extract_document_metadata,
    extract_document_text,
    finalize_workflow_run,
    update_document_status,
    validate_document,
)
from tests.unit.fakes import FakeUnitOfWork, Store


@pytest.mark.asyncio
async def test_document_processing_workflow_success(monkeypatch: pytest.MonkeyPatch):
    store = Store()

    org_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    doc_id = uuid4()
    version_id = uuid4()
    run_id = uuid4()

    # Pre-populate fake store
    store.organizations[org_id] = Organization(
        id=org_id, name="Test Org", slug="test-org", type=OrganizationType.PERSONAL
    )
    store.projects[project_id] = Project(
        id=project_id,
        organization_id=org_id,
        name="Test Project",
        created_by=user_id,
    )
    store.project_memberships.append(
        ProjectMembership(
            organization_id=org_id,
            project_id=project_id,
            user_id=user_id,
            role=MembershipRole.OWNER,
        )
    )

    doc = Document(
        id=doc_id,
        organization_id=org_id,
        project_id=project_id,
        name="test.txt",
        created_by=user_id,
        current_version_id=version_id,
    )
    store.documents[doc_id] = doc

    version = DocumentVersion(
        id=version_id,
        organization_id=org_id,
        document_id=doc_id,
        version_number=1,
        blob_path="test_blob",
        source_filename="test.txt",
        mime_type="text/plain",
        size_bytes=100,
        sha256="fake_sha",
        etag="fake_etag",
        status=DocumentVersionStatus.UPLOADED,
    )
    store.versions[version_id] = version

    workflow_id = f"doc-processing-{version_id}"
    run = WorkflowRun(
        id=run_id,
        organization_id=org_id,
        workflow_id=workflow_id,
        workflow_type="DocumentProcessingWorkflow",
        resource_type="document",
        resource_id=doc_id,
        status=WorkflowRunStatus.PENDING,
    )
    store.workflow_runs[run_id] = run

    # Pre-upload mock document text to local storage fallback
    from knowledge_os.config import get_settings
    from knowledge_os.infrastructure.storage.azure import AzureBlobStorageAdapter

    storage = AzureBlobStorageAdapter(get_settings())
    await storage.upload(
        "test_blob",
        (
            b"Hello world! This is a test file for chunking. "
            b"It contains multiple sentences to check if the chunker works correctly."
        ),
        "text/plain",
    )

    # Monkeypatch SqlAlchemyUnitOfWork to use FakeUnitOfWork
    from knowledge_os.infrastructure.workflows import activities

    monkeypatch.setattr(
        activities,
        "SqlAlchemyUnitOfWork",
        lambda: FakeUnitOfWork(store),
    )

    # Start local in-memory temporal server
    async with await WorkflowEnvironment.start_time_skipping() as env:
        doc_worker = Worker(
            env.client,
            task_queue="test-task-queue",
            workflows=[DocumentProcessingWorkflow],
            activities=[
                validate_document,
                extract_document_metadata,
                extract_document_text,
                update_document_status,
                finalize_workflow_run,
            ],
        )

        chunk_worker = Worker(
            env.client,
            task_queue="chunk-processing",
            workflows=[],
            activities=[
                chunk_document,
            ],
        )

        async with doc_worker, chunk_worker:
            payload = {
                "organization_id": str(org_id),
                "project_id": str(project_id),
                "document_id": str(doc_id),
                "version_id": str(version_id),
                "user_id": str(user_id),
                "workflow_run_id": str(run_id),
            }

            result = await env.client.execute_workflow(
                DocumentProcessingWorkflow.run,
                payload,
                id=workflow_id,
                task_queue="test-task-queue",
            )

            assert result == {"status": "success"}

            # Assert document version status is updated to indexed and metadata is saved
            updated_version = store.versions[version_id]
            assert updated_version.status == DocumentVersionStatus.INDEXED
            assert updated_version.extracted_characters == 118
            assert updated_version.page_count is None

            # Assert workflow run status is updated to completed
            updated_run = store.workflow_runs[run_id]
            assert updated_run.status == WorkflowRunStatus.COMPLETED
            assert updated_run.completed_at is not None
            assert updated_run.error_message is None

            # Assert chunks were created and persisted correctly
            assert len(store.document_chunks) > 0
            assert any(c.content.startswith("Hello world!") for c in store.document_chunks)
            assert all(c.version_id == version_id for c in store.document_chunks)
            assert all(c.char_count == len(c.content) for c in store.document_chunks)
            assert all(c.token_count > 0 for c in store.document_chunks)

            # Assert events were recorded
            assert len(store.workflow_events) > 0
            event_types = [e.event_type for e in store.workflow_events]
            assert "document_validation_started" in event_types
            assert "document_validation_completed" in event_types
            assert "metadata_extraction_completed" in event_types
            assert "document_extraction_started" in event_types
            assert "document_text_extracted" in event_types
            assert "document_chunking_started" in event_types
            assert "document_chunking_completed" in event_types
            assert "workflow_finalized" in event_types


@pytest.mark.asyncio
async def test_document_processing_workflow_validation_failure(monkeypatch: pytest.MonkeyPatch):
    store = Store()

    org_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    doc_id = uuid4()
    version_id = uuid4()
    run_id = uuid4()
    # Pre-populate fake store
    store.organizations[org_id] = Organization(
        id=org_id, name="Test Org", slug="test-org", type=OrganizationType.PERSONAL
    )
    store.projects[project_id] = Project(
        id=project_id,
        organization_id=org_id,
        name="Test Project",
        created_by=user_id,
    )
    store.project_memberships.append(
        ProjectMembership(
            organization_id=org_id,
            project_id=project_id,
            user_id=user_id,
            role=MembershipRole.OWNER,
        )
    )

    # We do NOT add the document to the store, which will cause validation to fail!
    workflow_id = f"doc-processing-{version_id}"
    run = WorkflowRun(
        id=run_id,
        organization_id=org_id,
        workflow_id=workflow_id,
        workflow_type="DocumentProcessingWorkflow",
        resource_type="document",
        resource_id=doc_id,
        status=WorkflowRunStatus.PENDING,
    )
    store.workflow_runs[run_id] = run

    # Monkeypatch SqlAlchemyUnitOfWork to use FakeUnitOfWork
    from knowledge_os.infrastructure.workflows import activities

    monkeypatch.setattr(
        activities,
        "SqlAlchemyUnitOfWork",
        lambda: FakeUnitOfWork(store),
    )

    async with await WorkflowEnvironment.start_time_skipping() as env:
        doc_worker = Worker(
            env.client,
            task_queue="test-task-queue",
            workflows=[DocumentProcessingWorkflow],
            activities=[
                validate_document,
                extract_document_metadata,
                extract_document_text,
                update_document_status,
                finalize_workflow_run,
            ],
        )

        chunk_worker = Worker(
            env.client,
            task_queue="chunk-processing",
            workflows=[],
            activities=[
                chunk_document,
            ],
        )

        async with doc_worker, chunk_worker:
            payload = {
                "organization_id": str(org_id),
                "project_id": str(project_id),
                "document_id": str(doc_id),
                "version_id": str(version_id),
                "user_id": str(user_id),
                "workflow_run_id": str(run_id),
            }

            # Executing workflow should raise an exception since validation fails
            with pytest.raises(WorkflowFailureError):
                await env.client.execute_workflow(
                    DocumentProcessingWorkflow.run,
                    payload,
                    id=workflow_id,
                    task_queue="test-task-queue",
                )

            # Assert workflow run status is updated to failed in DB
            updated_run = store.workflow_runs[run_id]
            assert updated_run.status == WorkflowRunStatus.FAILED
            assert updated_run.completed_at is not None
            assert updated_run.error_message is not None
            assert "document not found" in updated_run.error_message.lower()
