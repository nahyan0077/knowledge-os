from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy


@workflow.defn
class DocumentProcessingWorkflow:
    @workflow.run
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        workflow_run_id = payload["workflow_run_id"]

        # Define standard retry policy for activities
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=3,
        )

        try:
            # 1. Validate Document
            await workflow.execute_activity(
                "validate_document",
                payload,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=retry_policy,
            )

            # 2. Update status to "processing"
            processing_payload = {**payload, "status": "processing"}
            await workflow.execute_activity(
                "update_document_status",
                processing_payload,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=retry_policy,
            )

            # 3. Extract Document Metadata
            await workflow.execute_activity(
                "extract_document_metadata",
                payload,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=retry_policy,
            )

            # 4. Extract Document Text
            extraction_result = await workflow.execute_activity(
                "extract_document_text",
                payload,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=retry_policy,
            )

            # 5. Chunk Document (Runs on the chunk-processing task queue)
            chunking_payload = {
                **payload,
                "extracted_text_path": extraction_result["extracted_text_path"],
            }
            await workflow.execute_activity(
                "chunk_document",
                chunking_payload,
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=retry_policy,
                task_queue="chunk-processing",
            )

            # 6. Embed & Index Chunks (Runs on the embedding-processing task queue)
            await workflow.execute_activity(
                "generate_chunk_embeddings",
                payload,
                start_to_close_timeout=timedelta(minutes=15),
                retry_policy=retry_policy,
                task_queue="embedding-processing",
            )

            # 7. Update status to "indexed" representing successful pipeline processing completion
            indexed_payload = {**payload, "status": "indexed"}
            await workflow.execute_activity(
                "update_document_status",
                indexed_payload,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=retry_policy,
            )

            # 7. Finalize workflow run as completed
            finalize_payload = {
                "workflow_run_id": workflow_run_id,
                "status": "completed",
            }
            await workflow.execute_activity(
                "finalize_workflow_run",
                finalize_payload,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=retry_policy,
            )

            return {"status": "success"}

        except Exception as err:
            error_message = str(err)
            from temporalio.exceptions import ActivityError

            if isinstance(err, ActivityError) and err.cause:
                error_message = getattr(err.cause, "message", str(err.cause))
            workflow.logger.error(f"Workflow execution failed: {error_message}")

            # Update document status to failed
            try:
                failed_payload = {**payload, "status": "failed"}
                await workflow.execute_activity(
                    "update_document_status",
                    failed_payload,
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=retry_policy,
                )
            except Exception as nested_err:
                workflow.logger.error(f"Failed to update document status to failed: {nested_err}")

            # Finalize workflow run as failed
            try:
                finalize_payload = {
                    "workflow_run_id": workflow_run_id,
                    "status": "failed",
                    "error_message": error_message,
                }
                await workflow.execute_activity(
                    "finalize_workflow_run",
                    finalize_payload,
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=retry_policy,
                )
            except Exception as nested_err:
                workflow.logger.error(f"Failed to finalize workflow run as failed: {nested_err}")

            raise err
