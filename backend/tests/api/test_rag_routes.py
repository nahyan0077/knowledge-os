from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from knowledge_os.api.dependencies import get_current_user_id, get_rag_service
from knowledge_os.domain.entities import Citation
from knowledge_os.main import create_app


def test_rag_ask_route_success() -> None:
    app = create_app()
    user_id = uuid4()
    project_id = uuid4()
    chunk_id = uuid4()
    version_id = uuid4()

    mock_service = MagicMock()
    mock_service.ask = AsyncMock(
        return_value=(
            "Answer content",
            [
                Citation(
                    chunk_id=chunk_id,
                    document_version_id=version_id,
                    chunk_number=2,
                    score=0.88,
                )
            ],
        )
    )

    app.dependency_overrides[get_current_user_id] = lambda: user_id
    app.dependency_overrides[get_rag_service] = lambda: mock_service

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rag/ask",
            json={
                "question": "What is the answer?",
                "project_id": str(project_id),
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Answer content"
    assert len(data["citations"]) == 1
    assert data["citations"][0]["chunk_id"] == str(chunk_id)
    assert data["citations"][0]["document_version_id"] == str(version_id)
    assert data["citations"][0]["chunk_number"] == 2
    assert data["citations"][0]["score"] == 0.88

    mock_service.ask.assert_called_once_with(
        project_id=project_id,
        user_id=user_id,
        question="What is the answer?",
    )
