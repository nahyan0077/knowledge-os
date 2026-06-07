from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from knowledge_os.api.dependencies import get_current_user_id, get_retrieval_service
from knowledge_os.api.schemas import RetrievalSearchRequest, ScoredChunkResponse
from knowledge_os.application.retrieval import RetrievalService

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/search", response_model=list[ScoredChunkResponse])
async def search_retrieval(
    payload: RetrievalSearchRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[RetrievalService, Depends(get_retrieval_service)],
) -> list[ScoredChunkResponse]:
    results = await service.search(
        project_id=payload.project_id,
        user_id=user_id,
        query=payload.query,
        top_k=payload.top_k,
    )
    return [
        ScoredChunkResponse(
            chunk_id=item.chunk_id,
            score=item.score,
            content=item.content,
            document_version_id=item.document_version_id,
            chunk_number=item.chunk_number,
        )
        for item in results
    ]
