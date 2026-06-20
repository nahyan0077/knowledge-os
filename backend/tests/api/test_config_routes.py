from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from knowledge_os.api.dependencies import get_current_user_id
from knowledge_os.config import Settings
from knowledge_os.main import create_app


def test_config_models_route_requires_auth() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/config/models")
    assert response.status_code == 401


def test_config_models_gemini_only() -> None:
    app = create_app()
    app.dependency_overrides[get_current_user_id] = lambda: uuid4()

    mock_settings = Settings(
        gemini_api_key="fake-gemini-key",
        openai_api_key=None,
    )

    with patch("knowledge_os.api.v1.config.get_settings", return_value=mock_settings):
        with TestClient(app) as client:
            response = client.get("/api/v1/config/models")

    assert response.status_code == 200
    data = response.json()
    assert len(data["models"]) == 2
    assert data["models"][0]["provider"] == "google"
    assert data["models"][0]["name"] == "gemini-1.5-flash"
    assert data["default_model"]["name"] == "gemini-1.5-flash"


def test_config_models_openai_only() -> None:
    app = create_app()
    app.dependency_overrides[get_current_user_id] = lambda: uuid4()

    mock_settings = Settings(
        gemini_api_key=None,
        openai_api_key="fake-openai-key",
    )

    with patch("knowledge_os.api.v1.config.get_settings", return_value=mock_settings):
        with TestClient(app) as client:
            response = client.get("/api/v1/config/models")

    assert response.status_code == 200
    data = response.json()
    assert len(data["models"]) == 2
    assert data["models"][0]["provider"] == "openai"
    assert data["models"][0]["name"] == "gpt-4o-mini"
    assert data["default_model"]["name"] == "gpt-4o-mini"


def test_config_models_fallback_to_test() -> None:
    app = create_app()
    app.dependency_overrides[get_current_user_id] = lambda: uuid4()

    mock_settings = Settings(
        gemini_api_key=None,
        openai_api_key=None,
    )

    with patch("knowledge_os.api.v1.config.get_settings", return_value=mock_settings):
        with TestClient(app) as client:
            response = client.get("/api/v1/config/models")

    assert response.status_code == 200
    data = response.json()
    assert len(data["models"]) == 1
    assert data["models"][0]["provider"] == "test"
    assert data["models"][0]["name"] == "test"
    assert data["default_model"]["name"] == "test"
