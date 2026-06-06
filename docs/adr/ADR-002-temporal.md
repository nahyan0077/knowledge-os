# ADR-002: Temporal for Durable Workflows

- Status: Accepted
- Date: 2026-06-06
- Implementation: Planned

## Context

Document ingestion, agent execution, report generation, and project purge are long-running, multi-step operations that require retries, recovery, cancellation, progress, and auditability.

## Decision

Use Temporal for durable workflows longer than a normal request or requiring resume/retry semantics. Workflow code orchestrates deterministically; I/O occurs in idempotent activities. Product-visible progress is projected to PostgreSQL.

Ordinary low-latency chat remains request-scoped SSE initially unless durable chat requirements justify Temporal.

## Consequences

- Worker restarts do not lose execution state.
- Activities require explicit idempotency, timeout, retry, and cancellation behavior.
- Temporal history is not the product database and must not contain large or sensitive payloads.
- Workflow versioning becomes part of release discipline.

## Rejected Alternatives

- Background tasks inside API processes: not durable or observable enough.
- Generic queue-only orchestration: requires rebuilding workflow state, retries, and cancellation.

