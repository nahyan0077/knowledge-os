# AI Engineering Task Template

Copy this template into an issue or working document before substantial implementation.

## Feature Request

Short user-facing description.

## Problem

What problem exists, who experiences it, and why it matters.

## Scope

### In Scope

- Explicit deliverables.

### Out of Scope

- Related work that must not be implemented.

## Current State

- Relevant implemented behavior and code paths.
- Relevant planned architecture.

## Requirements

- Functional requirements.
- Security, tenant-isolation, performance, and observability requirements.

## Affected Domains

| Domain | Change | Owned data/contracts affected |
|---|---|---|
| Example | Add/modify/read only | Details |

## Architecture Impact

- Boundary changes:
- New ports/adapters:
- New or superseded ADR required:
- Alternatives considered:

## Database Changes

- Tables/columns/constraints/indexes:
- Migration and backfill plan:
- Roll-forward/compatibility plan:

## API Changes

- Endpoints/contracts/errors:
- Authentication/authorization:
- Pagination/streaming/idempotency:

## Workflow Changes

- Trigger:
- Inputs/outputs:
- Activities/checkpoints:
- Retry/cancellation/failure semantics:

## Test Plan

- Unit:
- API/contract:
- Integration:
- Tenant/security negative cases:
- Failure/retry cases:

## Acceptance Criteria

- Verifiable behavior statements.
- `make check` passes.
- Context docs and ADRs are updated where required.

## Risks and Tradeoffs

- Known risks, rejected alternatives, and mitigations.

## Completion Notes

- Files changed:
- Commands run:
- Residual risk or deferred work:

