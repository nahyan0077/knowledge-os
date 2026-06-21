from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from knowledge_os.api.dependencies import get_current_user_id, get_rag_service
from knowledge_os.api.schemas import CitationResponse, RagAskRequest, RagAskResponse
from knowledge_os.application.rag import RagService

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/ask", response_model=RagAskResponse)
async def ask_rag(
    payload: RagAskRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[RagService, Depends(get_rag_service)],
) -> RagAskResponse:
    answer, citations = await service.ask(
        project_id=payload.project_id,
        user_id=user_id,
        question=payload.question,
    )
    return RagAskResponse(
        answer=answer,
        citations=[
            CitationResponse(
                chunk_id=cit.chunk_id,
                document_version_id=cit.document_version_id,
                chunk_number=cit.chunk_number,
                score=cit.score,
                page_start=cit.page_start,
                page_end=cit.page_end,
                quote=cit.quote,
                citation_number=cit.citation_number,
                document_id=cit.document_id,
                document_name=cit.document_name,
                source_filename=cit.source_filename,
            )
            for cit in citations
        ],
    )
