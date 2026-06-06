from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from knowledge_os.api.dependencies import get_current_user_id, get_workflow_service
from knowledge_os.domain.entities import WorkflowEvent, WorkflowRun, WorkflowRunStatus
from knowledge_os.main import create_app


class StubWorkflowService:
    def __init__(self, run_id, org_id, doc_id, event_id):
        self.run = WorkflowRun(
            id=run_id,
            organization_id=org_id,
            workflow_id="test-wf-id",
            workflow_type="DocumentProcessingWorkflow",
            resource_type="document",
            resource_id=doc_id,
            status=WorkflowRunStatus.COMPLETED,
            started_at=datetime(2026, 6, 7, 0, 0, 0, tzinfo=UTC),
            completed_at=datetime(2026, 6, 7, 0, 5, 0, tzinfo=UTC),
            error_message=None,
        )
        self.event = WorkflowEvent(
            id=event_id,
            workflow_run_id=run_id,
            event_type="document_validation_started",
            payload={"info": "started"},
            created_at=datetime(2026, 6, 7, 0, 0, 1, tzinfo=UTC),
        )

    async def get_run(self, run_id):
        return self.run, [self.event]

    async def list_runs_for_resource(self, resource_type: str, resource_id):
        return [self.run]


def test_get_workflow_run_route() -> None:
    app = create_app()
    user_id = uuid4()
    run_id = uuid4()
    org_id = uuid4()
    doc_id = uuid4()
    event_id = uuid4()

    service = StubWorkflowService(run_id, org_id, doc_id, event_id)
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    app.dependency_overrides[get_workflow_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(f"/api/v1/workflows/{run_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(run_id)
    assert data["organization_id"] == str(org_id)
    assert data["workflow_id"] == "test-wf-id"
    assert data["workflow_type"] == "DocumentProcessingWorkflow"
    assert data["resource_type"] == "document"
    assert data["resource_id"] == str(doc_id)
    assert data["status"] == "completed"
    assert len(data["events"]) == 1
    assert data["events"][0]["id"] == str(event_id)
    assert data["events"][0]["event_type"] == "document_validation_started"
    assert data["events"][0]["payload"] == {"info": "started"}


def test_list_project_workflows_route() -> None:
    app = create_app()
    user_id = uuid4()
    run_id = uuid4()
    org_id = uuid4()
    project_id = uuid4()
    doc_id = uuid4()
    event_id = uuid4()

    service = StubWorkflowService(run_id, org_id, doc_id, event_id)
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    app.dependency_overrides[get_workflow_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/projects/{project_id}/workflows?resource_type=document&resource_id={doc_id}"
        )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == str(run_id)
    assert data["items"][0]["resource_type"] == "document"
    assert data["items"][0]["resource_id"] == str(doc_id)


def test_workflow_routes_require_authentication() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get(f"/api/v1/workflows/{uuid4()}")
    assert response.status_code == 401
    assert response.json()["error_code"] == "authentication_required"
