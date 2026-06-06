# Workflow Map

## Status

No Temporal workflow is implemented yet. The workflows below are approved future-state contracts. Do not create a workflow unless the task explicitly includes it.

## Workflow Rules

- Workflow code orchestrates only and must remain deterministic.
- I/O occurs in idempotent activities.
- Inputs contain IDs and immutable parameters, not large content.
- Transient errors retry with bounded exponential backoff and jitter.
- Validation, authorization, unsupported format, and quota errors do not retry.
- Product-visible progress is projected to PostgreSQL `workflow_runs`.

## Document Ingestion

- Trigger: `document.upload_finalized.v1`.
- Inputs: organization, project, document version, pipeline version IDs.
- Steps: validate blob; extract text; persist extraction artifact; chunk; persist chunks; embed batches; upsert Qdrant; verify index manifest; mark indexed.
- Outputs: indexed version, chunks, index manifest, progress projection.
- Failure handling: retain completed checkpoints; mark terminal failure with safe code.
- Retry behavior: retry transient activity failures; deterministic chunk IDs make Qdrant upserts idempotent.

## Chat Workflow

- Trigger: user submits a conversation message.
- Inputs: tenant/project/conversation/message IDs and model policy.
- Steps: load bounded conversation context; retrieve; rerank; build context; execute chat agent; stream; persist assistant message and citations.
- Outputs: completed or failed assistant message with citations.
- Failure handling: preserve user message and assistant lifecycle state; allow client reconnection.
- Retry behavior: ordinary chat is initially request-scoped SSE; use Temporal only when durable chat requirements justify it.

## Agent Workflow

- Trigger: `agent.run_requested.v1`.
- Inputs: agent run ID and immutable execution policy.
- Steps: validate scope; build context; resolve policy/tools; execute; persist steps; validate structured output; finalize.
- Outputs: auditable agent result, usage, steps, status.
- Failure handling: record safe error and partial steps; enforce budget and cancellation.
- Retry behavior: retry idempotent tool/model activities where policy permits; never repeat unsafe side effects without idempotency.

## Report Workflow

- Trigger: `report.generation_requested.v1`.
- Inputs: report ID, source scope, report policy.
- Steps: validate; research/retrieve; generate checkpointed sections; validate citations/schema; assemble; render; persist artifact; finalize.
- Outputs: report content, artifact URI, citations, status.
- Failure handling: preserve completed sections; expose safe failure and retry state.
- Retry behavior: resume from completed checkpoints; rendering and artifact writes are idempotent.

## Project Purge Workflow

- Trigger: `project.deleted.v1`.
- Inputs: organization ID and project ID.
- Steps: revoke access; purge derived indexes/artifacts; apply retention rules; finalize deletion projection.
- Outputs: verified purge result.
- Failure handling: project remains inaccessible while cleanup retries.
- Retry behavior: all deletion activities must be idempotent and verifiable.

