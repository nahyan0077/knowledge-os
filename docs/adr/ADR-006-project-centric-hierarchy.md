# ADR-006: Project-Centric Hierarchy

- Status: Accepted
- Date: 2026-06-06
- Implementation: Partially implemented

## Context

Users need a coherent workspace in which documents, conversations, agent runs, reports, and knowledge share authorization and context. Enterprise tenancy must be possible without retrofitting isolation later.

## Decision

Use `Organization` as the mandatory tenant root and `Project` as the primary product workspace:

```text
Organization -> Project -> Documents, Conversations, Agent Runs, Reports, Knowledge, Workflows
```

Personal users receive a single-user organization. Project resources inherit organization/project scope. Access is resolved from server-side membership.

## Consequences

- Tenant and project filters are mandatory throughout storage, retrieval, workflows, telemetry, and tools.
- Project-level context and authorization are consistent across features.
- Cross-project sharing requires an explicit future design rather than implicit access.
- Cross-tenant inaccessible resources return `404`.

## Rejected Alternatives

- User-owned resources without organizations: makes enterprise collaboration and isolation costly to retrofit.
- Independent feature workspaces: fragments permissions and knowledge context.

