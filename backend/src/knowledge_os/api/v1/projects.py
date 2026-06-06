from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from knowledge_os.api.dependencies import get_current_user_id, get_project_service
from knowledge_os.api.schemas import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)
from knowledge_os.application.projects import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreateRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectResponse:
    project = await service.create(
        payload.organization_id,
        user_id,
        payload.name,
        payload.description,
    )
    return ProjectResponse.from_domain(project)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    organization_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[ProjectService, Depends(get_project_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ProjectListResponse:
    projects = await service.list(organization_id, user_id, limit)
    return ProjectListResponse(items=[ProjectResponse.from_domain(item) for item in projects])


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectResponse:
    return ProjectResponse.from_domain(await service.get(project_id, user_id))


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdateRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectResponse:
    project = await service.update(
        project_id,
        user_id,
        payload.version,
        payload.name,
        payload.description,
    )
    return ProjectResponse.from_domain(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> Response:
    await service.delete(project_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
