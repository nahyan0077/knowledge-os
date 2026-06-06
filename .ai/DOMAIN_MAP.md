# Domain Map

## Boundary Rules

- Domains expose application services, command/query contracts, and events.
- A domain must not access another domain's repositories.
- Cross-domain synchronous calls use public application interfaces.
- Decoupled or durable integration uses versioned domain events.
- Infrastructure SDK types must not enter domain entities.

## Domain Catalog

### Auth

**Status:** Implemented with minimum tenancy bootstrap.

- Responsibilities: users, credentials, access tokens, refresh sessions, registration, login, logout.
- Public APIs: `POST /auth/register`, `/login`, `/refresh`, `/logout`; `AuthService`.
- Tables: `users`, `refresh_sessions`.
- Dependencies: tenancy bootstrap through organization repository; password and token ports.
- Must not access: projects, documents, conversations, retrieval, agents, reports, workflows.

### Projects

**Status:** Implemented.

- Responsibilities: project identity, metadata, memberships, tenant authorization, soft deletion.
- Public APIs: CRUD under `/projects`; `ProjectService`.
- Tables: `organizations`, `organization_members`, `projects`, `project_members`.
- Dependencies: authenticated user identity and organization membership.
- Must not access: document internals, chunks/Qdrant, messages, agent execution, workflow engine.

### Documents

**Status:** Planned.

- Responsibilities: upload metadata, logical documents, immutable versions, lifecycle status.
- Public APIs: initiate/finalize upload, list/read/delete/reprocess document versions.
- Tables: `documents`, `document_versions`.
- Dependencies: Projects, Blob port, Workflow public interface.
- Must not access: Qdrant directly, conversation repositories, agent internals.

### Conversations

**Status:** Planned.

- Responsibilities: persistent conversations, ordered messages, citations, context summaries.
- Public APIs: conversation CRUD, message history, submit message/stream response.
- Tables: `conversations`, `messages`, `message_citations`.
- Dependencies: Projects, Retrieval public interface, Chat Agent policy.
- Must not access: raw provider SDKs, document persistence internals, workflow storage.

### Retrieval

**Status:** Planned.

- Responsibilities: authorized candidate retrieval, fusion, reranking, context construction, diagnostics.
- Public APIs: project knowledge search and internal retrieval port.
- Tables: reads authoritative `chunks`; no aggregate tables initially.
- Dependencies: Projects authorization, Knowledge/chunk query port, Qdrant adapter, reranker port.
- Must not access: authentication credentials, mutate documents, invoke unrestricted agent tools.

### Agents

**Status:** Planned.

- Responsibilities: agent policies, bounded tools, model budgets, runs, steps, structured outputs.
- Public APIs: agent catalog, start/read/cancel runs.
- Tables: `agent_runs`, `agent_run_steps`.
- Dependencies: Projects, Retrieval, Workflows, provider-neutral AI ports.
- Must not access: provider SDKs from domain/application code, unrestricted cross-project data.

### Reports

**Status:** Planned.

- Responsibilities: report requests, cited content, generated artifacts, report lifecycle.
- Public APIs: request/list/read/download reports.
- Tables: `reports`.
- Dependencies: Projects, Agents, Workflows, Blob artifact port.
- Must not access: auth credentials, Qdrant directly, Temporal persistence directly.

### Workflows

**Status:** Planned.

- Responsibilities: durable orchestration, progress projection, retry/cancellation semantics.
- Public APIs: start/query/cancel workflow operations; workflow monitor API.
- Tables: `workflow_runs`; Temporal owns execution history.
- Dependencies: domain application interfaces and infrastructure activities.
- Must not access: domain repositories from deterministic workflow code; large document bodies in workflow history.

## Dependency Direction

```text
API / Temporal delivery
  -> Application services
     -> Domain entities and ports
Infrastructure adapters
  -> Domain/application ports
```

No dependency may point from domain code to delivery or infrastructure code.

