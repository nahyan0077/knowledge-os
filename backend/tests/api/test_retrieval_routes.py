from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from knowledge_os.api.dependencies import get_current_user_id, get_retrieval_service
from knowledge_os.application.retrieval import ScoredChunk
from knowledge_os.main import create_app


def test_retrieval_search_route_success() -> None:
    app = create_app()
    user_id = uuid4()
    project_id = uuid4()
    chunk_id = uuid4()
    version_id = uuid4()

    mock_service = MagicMock()
    mock_service.search = AsyncMock(
        return_value=[
            ScoredChunk(
                chunk_id=chunk_id,
                score=0.92,
                content="This is the retrieved chunk content.",
                document_version_id=version_id,
                chunk_number=4,
                token_count=5,
            )
        ]
    )

    app.dependency_overrides[get_current_user_id] = lambda: user_id
    app.dependency_overrides[get_retrieval_service] = lambda: mock_service

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/retrieval/search",
            json={
                "query": "find matching text",
                "project_id": str(project_id),
                "top_k": 3,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["chunk_id"] == str(chunk_id)
    assert data[0]["score"] == 0.92
    assert data[0]["content"] == "This is the retrieved chunk content."
    assert data[0]["document_version_id"] == str(version_id)
    assert data[0]["chunk_number"] == 4

    mock_service.search.assert_called_once_with(
        project_id=project_id,
        user_id=user_id,
        query="find matching text",
        top_k=3,
    )
