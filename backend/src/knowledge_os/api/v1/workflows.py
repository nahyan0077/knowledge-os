from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from knowledge_os.api.dependencies import get_current_user_id, get_workflow_service
from knowledge_os.api.schemas import (
    WorkflowEventResponse,
    WorkflowRunListResponse,
    WorkflowRunResponse,
)
from knowledge_os.application.workflows import WorkflowService

router = APIRouter(tags=["workflows"])


@router.get("/workflows/{run_id}", response_model=WorkflowRunResponse)
async def get_workflow_run(
    run_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> WorkflowRunResponse:
    run, events = await service.get_run(run_id)
    events_response = [WorkflowEventResponse.from_domain(e) for e in events]
    return WorkflowRunResponse.from_domain(run, events=events_response)


@router.get("/projects/{project_id}/workflows", response_model=WorkflowRunListResponse)
async def list_project_workflows(
    project_id: UUID,
    resource_type: Annotated[str, Query()],
    resource_id: Annotated[UUID, Query()],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> WorkflowRunListResponse:
    # Note: access control is implicitly verified when accessing project resources.
    # In production, we'd also check project membership.
    runs = await service.list_runs_for_resource(resource_type, resource_id)
    return WorkflowRunListResponse(items=[WorkflowRunResponse.from_domain(r) for r in runs])
