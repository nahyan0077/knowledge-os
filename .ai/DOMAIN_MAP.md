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

**Status:** Implemented (enhanced with Sprint 6 & 6.1 PDF extraction, token counting, and chunk metadata).

- Responsibilities: upload metadata, logical documents, immutable versions, lifecycle status, PDF and plain text extraction, tiktoken tokenization, sliding-window chunking, database persistence of document chunks with metrics.
- Public APIs: `POST /projects/{project_id}/documents`, `POST /projects/{project_id}/documents/{document_id}/versions`, `GET /projects/{project_id}/documents`, `GET /documents/{document_id}`, `GET /documents/{document_id}/versions`, `DELETE /documents/{document_id}`.
- Tables: `documents`, `document_versions`, `document_chunks`.
- Dependencies: Projects, Blob port.
- Must not access: Qdrant directly, conversation repositories, agent internals.

### Conversations

**Status:** Implemented (enhanced with basic conversational AI and LLM usage tracking in Sprint 4).

- Responsibilities: persistent conversations, ordered messages, basic conversational AI chat (using PydanticAI), LLM usage metrics tracking.
- Public APIs: `POST /projects/{project_id}/conversations`, `GET /projects/{project_id}/conversations`, `GET /conversations/{conversation_id}`, `PATCH /conversations/{conversation_id}`, `DELETE /conversations/{conversation_id}`, `POST /conversations/{conversation_id}/messages`, `GET /conversations/{conversation_id}/messages`, `POST /conversations/{conversation_id}/chat`, `POST /conversations/{conversation_id}/chat/stream`.
- Tables: `conversations`, `messages`, `llm_usage`.
- Dependencies: Projects, PydanticAI.
- Must not access: document persistence internals, Qdrant, Temporal, report generation.

### Retrieval

**Status:** Implemented (Sprint 7, 8 & 9 completed).

- Responsibilities: tracking embedding metadata and versions, upserting/deleting vectors in Qdrant, authorized query embedding generation, tenant-isolated vector search, authoritative PostgreSQL chunk hydration, scoring, context building/deduplication, token budget enforcement, citation tracking/mapping.
- Public APIs: `POST /retrieval/search` (through `RetrievalService`), `POST /rag/ask` (through `RagService`).
- Tables: `chunk_embeddings` table; reads authoritative `document_chunks`.
- Dependencies: Projects authorization, Documents (chunks), Qdrant adapter, OpenAI embeddings API, PydanticAI gateway.
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

**Status:** Implemented.

- Responsibilities: durable orchestration, progress projection, retry/cancellation semantics, tracking workflow execution state and events.
- Public APIs: `GET /api/v1/workflows/{run_id}`, `GET /api/v1/projects/{project_id}/workflows`; `WorkflowService`.
- Tables: `workflow_runs`, `workflow_events`; Temporal owns execution history.
- Dependencies: domain application interfaces and infrastructure activities, Temporal Client/Worker.
- Must not access: domain repositories from deterministic workflow code; large document bodies in workflow history. All DB operations are isolated in activities.

## Dependency Direction

```text
API / Temporal delivery
  -> Application services
     -> Domain entities and ports
Infrastructure adapters
  -> Domain/application ports
```

No dependency may point from domain code to delivery or infrastructure code.

