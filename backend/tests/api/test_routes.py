from uuid import uuid4

from fastapi.testclient import TestClient

from knowledge_os.api.dependencies import (
    get_auth_service,
    get_current_user_id,
    get_project_service,
)
from knowledge_os.application.auth import AuthResult
from knowledge_os.application.ports import IssuedAccessToken
from knowledge_os.domain.entities import Organization, OrganizationType, Project, User
from knowledge_os.main import create_app


class StubAuthService:
    def __init__(self) -> None:
        self.user = User("person@example.com", "Person", "hash")
        self.organization = Organization(
            "Person's Workspace", "personal", OrganizationType.PERSONAL
        )

    async def register(self, email: str, display_name: str, password: str) -> AuthResult:
        return AuthResult(
            user=self.user,
            organization=self.organization,
            access_token=IssuedAccessToken("access-token", 900),
            refresh_token="session.secret",
        )


class StubProjectService:
    def __init__(self, user_id, organization_id) -> None:
        self.project = Project(organization_id, "Research", user_id)

    async def list(self, organization_id, user_id, limit=50):
        return [self.project]


def test_register_route_sets_http_only_refresh_cookie() -> None:
    app = create_app()
    app.dependency_overrides[get_auth_service] = StubAuthService

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "person@example.com",
                "display_name": "Person",
                "password": "correct-horse-battery",
            },
        )

    assert response.status_code == 201
    assert response.json()["access_token"] == "access-token"
    assert "HttpOnly" in response.headers["set-cookie"]


def test_project_list_route_uses_authenticated_user_dependency() -> None:
    app = create_app()
    user_id = uuid4()
    organization_id = uuid4()
    service = StubProjectService(user_id, organization_id)
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    app.dependency_overrides[get_project_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(f"/api/v1/projects?organization_id={organization_id}")

    assert response.status_code == 200
    assert response.json()["items"][0]["name"] == "Research"


def test_project_routes_require_authentication() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get(f"/api/v1/projects?organization_id={uuid4()}")

    assert response.status_code == 401
    assert response.json()["error_code"] == "authentication_required"
