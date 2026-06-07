import asyncio
import logging
import sys

from temporalio.worker import Worker

from knowledge_os.application.workflows.document import DocumentProcessingWorkflow
from knowledge_os.infrastructure.workflows.activities import (
    chunk_document,
    extract_document_metadata,
    extract_document_text,
    finalize_workflow_run,
    generate_chunk_embeddings,
    update_document_status,
    validate_document,
)
from knowledge_os.infrastructure.workflows.client import get_temporal_client

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    logging.info("Starting Temporal Workers...")
    try:
        client = await get_temporal_client()
    except Exception as exc:
        logging.error(f"Failed to connect to Temporal: {exc}")
        sys.exit(1)

    document_worker = Worker(
        client,
        task_queue="document-processing",
        workflows=[DocumentProcessingWorkflow],
        activities=[
            validate_document,
            extract_document_metadata,
            extract_document_text,
            update_document_status,
            finalize_workflow_run,
        ],
    )

    chunk_worker = Worker(
        client,
        task_queue="chunk-processing",
        workflows=[],
        activities=[
            chunk_document,
        ],
    )

    embedding_worker = Worker(
        client,
        task_queue="embedding-processing",
        workflows=[],
        activities=[
            generate_chunk_embeddings,
        ],
    )

    logging.info(
        "Workers registered. Polling 'document-processing', "
        "'chunk-processing', and 'embedding-processing' queues..."
    )
    await asyncio.gather(
        document_worker.run(),
        chunk_worker.run(),
        embedding_worker.run(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Workers stopped by user.")
