from typing import Any
from uuid import UUID

from temporalio import activity

from knowledge_os.domain.common import NotFoundError
from knowledge_os.domain.entities import (
    DocumentVersionStatus,
    WorkflowEvent,
    WorkflowRunStatus,
    utc_now,
)
from knowledge_os.infrastructure.database.uow import SqlAlchemyUnitOfWork


@activity.defn
async def validate_document(payload: dict[str, Any]) -> dict[str, Any]:
    document_id = UUID(payload["document_id"])
    version_id = UUID(payload["version_id"])
    workflow_run_id = UUID(payload["workflow_run_id"])
    user_id = UUID(payload["user_id"])

    activity.logger.info(f"Validating document {document_id}")

    async with SqlAlchemyUnitOfWork() as uow:
        # Update workflow run status to RUNNING
        run = await uow.workflow_runs.get_by_id(workflow_run_id)
        if run:
            run.status = WorkflowRunStatus.RUNNING
            await uow.workflow_runs.save(run)

        event = WorkflowEvent(
            workflow_run_id=workflow_run_id,
            event_type="document_validation_started",
            payload={"document_id": str(document_id)},
        )
        await uow.workflow_events.add(event)
        await uow.commit()

    async with SqlAlchemyUnitOfWork() as uow:
        doc = await uow.documents.get_by_id(document_id, user_id)
        if not doc:
            raise NotFoundError("Document not found", "document_not_found")

        version = await uow.documents.get_version_by_id(version_id, user_id)
        if not version:
            raise NotFoundError("Document version not found", "version_not_found")

        if not version.blob_path:
            raise ValueError("Invalid blob path")

        event = WorkflowEvent(
            workflow_run_id=workflow_run_id,
            event_type="document_validation_completed",
            payload={"status": "valid"},
        )
        await uow.workflow_events.add(event)
        await uow.commit()

    return {"valid": True}


@activity.defn
async def extract_document_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    document_id = UUID(payload["document_id"])
    version_id = UUID(payload["version_id"])
    workflow_run_id = UUID(payload["workflow_run_id"])
    user_id = UUID(payload["user_id"])

    activity.logger.info(f"Extracting metadata for document {document_id}")

    async with SqlAlchemyUnitOfWork() as uow:
        event = WorkflowEvent(
            workflow_run_id=workflow_run_id,
            event_type="metadata_extraction_started",
            payload={"version_id": str(version_id)},
        )
        await uow.workflow_events.add(event)
        await uow.commit()

    async with SqlAlchemyUnitOfWork() as uow:
        version = await uow.documents.get_version_by_id(version_id, user_id)
        if not version:
            raise NotFoundError("Version not found", "version_not_found")

        metadata = {
            "filename": version.source_filename,
            "size_bytes": version.size_bytes,
            "mime_type": version.mime_type,
            "sha256": version.sha256,
        }

        event = WorkflowEvent(
            workflow_run_id=workflow_run_id,
            event_type="metadata_extraction_completed",
            payload=metadata,
        )
        await uow.workflow_events.add(event)
        await uow.commit()

    return metadata


@activity.defn
async def update_document_status(payload: dict[str, Any]) -> dict[str, Any]:
    document_id = UUID(payload["document_id"])
    version_id = UUID(payload["version_id"])
    workflow_run_id = UUID(payload["workflow_run_id"])
    user_id = UUID(payload["user_id"])
    new_status_str = payload["status"]

    activity.logger.info(f"Updating document {document_id} status to {new_status_str}")

    try:
        new_status = DocumentVersionStatus(new_status_str)
    except ValueError as err:
        raise ValueError(f"Invalid status: {new_status_str}") from err

    async with SqlAlchemyUnitOfWork() as uow:
        event = WorkflowEvent(
            workflow_run_id=workflow_run_id,
            event_type="document_status_update_started",
            payload={"target_status": new_status_str},
        )
        await uow.workflow_events.add(event)
        await uow.commit()

    async with SqlAlchemyUnitOfWork() as uow:
        version = await uow.documents.get_version_by_id(version_id, user_id)
        if not version:
            raise NotFoundError("Version not found", "version_not_found")

        version.status = new_status
        await uow.documents.save_version(version)

        event = WorkflowEvent(
            workflow_run_id=workflow_run_id,
            event_type="document_status_update_completed",
            payload={"status": new_status_str},
        )
        await uow.workflow_events.add(event)
        await uow.commit()

    return {"updated": True}


@activity.defn
async def finalize_workflow_run(payload: dict[str, Any]) -> dict[str, Any]:
    workflow_run_id = UUID(payload["workflow_run_id"])
    status_str = payload["status"]
    error_message = payload.get("error_message")

    activity.logger.info(f"Finalizing workflow run {workflow_run_id} to status {status_str}")

    try:
        status = WorkflowRunStatus(status_str)
    except ValueError as err:
        raise ValueError(f"Invalid status: {status_str}") from err

    async with SqlAlchemyUnitOfWork() as uow:
        run = await uow.workflow_runs.get_by_id(workflow_run_id)
        if run:
            run.status = status
            run.completed_at = utc_now()
            run.error_message = error_message
            await uow.workflow_runs.save(run)

            event = WorkflowEvent(
                workflow_run_id=workflow_run_id,
                event_type="workflow_finalized",
                payload={"status": status_str, "error_message": error_message},
            )
            await uow.workflow_events.add(event)
            await uow.commit()

    return {"finalized": True}
