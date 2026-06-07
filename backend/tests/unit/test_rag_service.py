from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from knowledge_os.application.context_builder import ContextBuilder
from knowledge_os.application.rag import RagService
from knowledge_os.application.retrieval import RetrievalService, ScoredChunk
from knowledge_os.domain.entities import Citation


@pytest.mark.asyncio
async def test_rag_service_ask() -> None:
    project_id = uuid4()
    user_id = uuid4()
    question = "What is the meaning of life?"

    # Mock retrieval service
    mock_retrieval = MagicMock(spec=RetrievalService)
    scored_chunks = [
        ScoredChunk(
            chunk_id=uuid4(),
            score=0.9,
            content="Context chunk content",
            document_version_id=uuid4(),
            chunk_number=1,
            token_count=10,
        )
    ]
    mock_retrieval.search = AsyncMock(return_value=scored_chunks)

    # Mock context builder
    mock_builder = MagicMock(spec=ContextBuilder)
    citations = [
        Citation(
            chunk_id=scored_chunks[0].chunk_id,
            document_version_id=scored_chunks[0].document_version_id,
            chunk_number=1,
            score=0.9,
        )
    ]
    mock_builder.build_context = MagicMock(return_value=("Context chunk content", citations))

    # Mock chat agent
    mock_chat_agent = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "The meaning of life is 42."
    mock_chat_agent.generate = AsyncMock(return_value=mock_response)

    service = RagService(
        retrieval_service=mock_retrieval,
        context_builder=mock_builder,
        chat_agent=mock_chat_agent,
    )

    answer, result_citations = await service.ask(
        project_id=project_id,
        user_id=user_id,
        question=question,
        token_budget=100,
    )

    assert answer == "The meaning of life is 42."
    assert len(result_citations) == 1
    assert result_citations[0].chunk_id == scored_chunks[0].chunk_id

    # Verify calls
    mock_retrieval.search.assert_called_once_with(
        project_id=project_id,
        user_id=user_id,
        query=question,
        top_k=20,
    )
    mock_builder.build_context.assert_called_once_with(
        retrieved_chunks=scored_chunks,
        token_budget=100,
    )

    # Verify generate is called with proper prompt
    _, kwargs = mock_chat_agent.generate.call_args
    assert "Context:\nContext chunk content" in kwargs["system_prompt"]
    assert kwargs["messages"] == [("user", question)]
    assert kwargs["config"].provider == "openai"
    assert kwargs["config"].model_name == "gpt-4o-mini"
    assert kwargs["config"].temperature == 0.0
