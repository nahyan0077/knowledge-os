from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, Query, Response, UploadFile, status

from knowledge_os.api.dependencies import get_current_user_id, get_document_service
from knowledge_os.api.schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentVersionResponse,
)
from knowledge_os.application.documents import DocumentService

router = APIRouter(tags=["documents"])


@router.post(
    "/projects/{project_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    project_id: UUID,
    name: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    organization_id: Annotated[UUID, Form()],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentResponse:
    file_bytes = await file.read()
    document, _ = await service.create(
        organization_id=organization_id,
        project_id=project_id,
        user_id=user_id,
        name=name,
        filename=file.filename or "file",
        data=file_bytes,
        mime_type=file.content_type or "application/octet-stream",
    )
    return DocumentResponse.from_domain(document)


@router.post(
    "/projects/{project_id}/documents/{document_id}/versions",
    response_model=DocumentVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_version(
    document_id: UUID,
    file: Annotated[UploadFile, File()],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentVersionResponse:
    file_bytes = await file.read()
    version = await service.upload_version(
        document_id=document_id,
        user_id=user_id,
        filename=file.filename or "file",
        data=file_bytes,
        mime_type=file.content_type or "application/octet-stream",
    )
    return DocumentVersionResponse.from_domain(version)


@router.get("/projects/{project_id}/documents", response_model=DocumentListResponse)
async def list_documents(
    project_id: UUID,
    organization_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[DocumentService, Depends(get_document_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> DocumentListResponse:
    documents = await service.list(
        organization_id=organization_id,
        project_id=project_id,
        user_id=user_id,
        limit=limit,
    )
    return DocumentListResponse(items=[DocumentResponse.from_domain(doc) for doc in documents])


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentResponse:
    document = await service.get(document_id, user_id)
    return DocumentResponse.from_domain(document)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> Response:
    await service.delete(document_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/documents/{document_id}/versions", response_model=list[DocumentVersionResponse])
async def list_document_versions(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> list[DocumentVersionResponse]:
    versions = await service.list_versions(document_id, user_id)
    return [DocumentVersionResponse.from_domain(v) for v in versions]


def _parse_range_header(value: str | None, size: int) -> tuple[int, int] | None:
    if value is None or not value.startswith("bytes=") or "," in value:
        return None
    start_text, separator, end_text = value.removeprefix("bytes=").partition("-")
    if not separator or not start_text.isdigit():
        return None
    start = int(start_text)
    end = int(end_text) if end_text.isdigit() else size - 1
    if start >= size or end < start:
        return None
    return start, min(end, size - 1)


@router.get("/document-versions/{version_id}/content")
async def get_document_version_content(
    version_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[DocumentService, Depends(get_document_service)],
    range_header: Annotated[str | None, Header(alias="Range")] = None,
) -> Response:
    version = await service.get_version(version_id, user_id)
    selected_range = _parse_range_header(range_header, version.size_bytes)
    if range_header is not None and selected_range is None:
        return Response(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            headers={"Content-Range": f"bytes */{version.size_bytes}"},
        )
    version, content = await service.get_version_content(version_id, user_id, selected_range)

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f"inline; filename*=UTF-8''{quote(version.source_filename)}",
        "ETag": version.etag,
        "Cache-Control": "private, max-age=0, must-revalidate",
    }
    response_status = status.HTTP_200_OK
    if selected_range is not None:
        start, end = selected_range
        headers["Content-Range"] = f"bytes {start}-{end}/{version.size_bytes}"
        response_status = status.HTTP_206_PARTIAL_CONTENT
    return Response(
        content=content,
        status_code=response_status,
        media_type=version.mime_type,
        headers=headers,
    )
