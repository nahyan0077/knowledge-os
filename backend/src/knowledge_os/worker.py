import asyncio
import logging
import sys

from temporalio.worker import Worker

from knowledge_os.application.workflows.document import DocumentProcessingWorkflow
from knowledge_os.infrastructure.workflows.activities import (
    extract_document_metadata,
    finalize_workflow_run,
    update_document_status,
    validate_document,
)
from knowledge_os.infrastructure.workflows.client import get_temporal_client

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    logging.info("Starting Temporal Worker...")
    try:
        client = await get_temporal_client()
    except Exception as exc:
        logging.error(f"Failed to connect to Temporal: {exc}")
        sys.exit(1)

    worker = Worker(
        client,
        task_queue="document-processing",
        workflows=[DocumentProcessingWorkflow],
        activities=[
            validate_document,
            extract_document_metadata,
            update_document_status,
            finalize_workflow_run,
        ],
    )

    logging.info("Worker successfully registered. Polling task queue 'document-processing'...")
    await worker.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Worker stopped by user.")
