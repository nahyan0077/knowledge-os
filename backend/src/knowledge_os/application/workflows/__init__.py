from collections.abc import Callable, Sequence
from uuid import UUID

from knowledge_os.domain.common import NotFoundError
from knowledge_os.domain.entities import WorkflowEvent, WorkflowRun
from knowledge_os.domain.repositories import UnitOfWork


class WorkflowService:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def get_run(self, run_id: UUID) -> tuple[WorkflowRun, Sequence[WorkflowEvent]]:
        async with self._uow_factory() as uow:
            run = await uow.workflow_runs.get_by_id(run_id)
            if run is None:
                raise NotFoundError("Workflow run not found", "workflow_run_not_found")
            events = await uow.workflow_events.list_for_run(run_id)
            return run, events

    async def list_runs_for_resource(
        self, resource_type: str, resource_id: UUID
    ) -> Sequence[WorkflowRun]:
        async with self._uow_factory() as uow:
            return await uow.workflow_runs.list_for_resource(resource_type, resource_id)
