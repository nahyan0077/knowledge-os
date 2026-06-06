# Architecture

## Architectural Style

The system is a modular monolith with separately deployable web, API, and Temporal worker processes. Domain boundaries are enforced inside the backend before any domain is considered for service extraction.

Core rules:

- Domain and application layers depend inward only.
- Infrastructure implements ports defined by application/domain layers.
- PostgreSQL is the transactional source of truth.
- External stores and workflow projections are rebuildable or reconcilable.
- Every tenant-owned operation is scoped by `organization_id`.

## System Architecture

```mermaid
flowchart LR
    User --> Web[Next.js Web]
    Web --> API[FastAPI API]
    API --> PG[(PostgreSQL)]
    API --> Temporal[Temporal]
    Temporal --> Workers[Workers]
    Workers --> PG
    Workers --> Blob[Azure Blob]
    Workers --> Qdrant[Qdrant - Planned]
    API --> AI[PydanticAI Gateway]
    Workers --> AI
    AI --> OpenAI
    AI --> Gemini
```

## Backend Component Diagram

```mermaid
flowchart TD
    Route[FastAPI Routes] --> App[Application Services]
    App --> Domain[Domain Entities and Policies]
    App --> Ports[Repository and Security Ports]
    Adapters[SQLAlchemy and Security Adapters] --> Ports
    Adapters --> PG[(PostgreSQL)]
    DI[Dependency Wiring] --> Route
    DI --> Adapters
```

## Folder Structure

```text
backend/src/knowledge_os/
  api/              FastAPI delivery and schemas
  application/      Use-case orchestration and ports
  domain/           Entities, errors, repository contracts
  infrastructure/   SQLAlchemy, security, and database adapters

frontend/src/
  app/              Next.js pages, routing layouts, and providers
  features/         Domain features (auth, projects, documents, conversations, chat)
  shared/           Re-usable layers (api, lib, types, hooks, ui)
```

## Runtime Architecture

| Runtime | Responsibility | Status |
|---|---|---|
| FastAPI API | Synchronous commands/queries, auth, streaming entry point | Implemented |
| Next.js web | User interface and browser state | Implemented |
| Temporal ingestion worker | Document validation, status updates, metadata extraction | Implemented |
| Temporal agent worker | Agent and report execution | Planned |
| PostgreSQL | Business truth and product-facing projections | Implemented |
| Qdrant | Derived vector index | Planned |
| Azure Blob | Immutable binaries and generated storage provider | Implemented |
| PydanticAI gateway | Provider-neutral model and agent execution | Implemented |

## Deployment Architecture

Planned Kubernetes deployments:

- `web`
- `api`
- `worker-ingestion`
- `worker-agent`
- `otel-collector`

Managed PostgreSQL, Blob Storage, Qdrant, and Temporal are preferred. API and workers are stateless and scale horizontally. Task queues isolate ingestion, embedding, agent, and report workloads.

## Request Data Flow

Implemented project command:

```text
HTTP request
  -> FastAPI/Pydantic validation
  -> bearer identity dependency
  -> application service
  -> unit of work
  -> tenant-scoped repository
  -> PostgreSQL transaction
  -> response schema
```

Implemented asynchronous command:

```text
HTTP command
  -> PostgreSQL state + outbox event
  -> workflow starter
  -> Temporal workflow
  -> idempotent activities
  -> PostgreSQL progress/result projection
```

## Related Decisions

- `docs/adr/ADR-001-modular-monolith.md`
- `docs/adr/ADR-002-temporal.md`
- `docs/adr/ADR-003-postgresql-source-of-truth.md`
- `docs/adr/ADR-004-qdrant-derived-store.md`
- `docs/adr/ADR-005-pydanticai.md`

