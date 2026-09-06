# AI Project Context — Knowledge OS

## Product

**Knowledge OS** is an AI-first, project-centric knowledge platform. Users upload documents to projects, which are ingested, chunked, embedded, and indexed into a vector store. Users can then chat with an AI assistant that retrieves grounded, cited answers from the project's knowledge base. It aims to combine features of ChatGPT Projects, Claude Projects, Glean, Notion AI, and Perplexity Enterprise.

**Core user flows:**
1. Register/login (email + password or Google OAuth)
2. Create/manage projects within a personal organization
3. Upload documents (PDF) to projects → automatic ingestion pipeline (extract → chunk → embed → index)
4. Chat with AI assistant using RAG (retrieval-augmented generation) with inline citations
5. View citation sources in an embedded PDF viewer
6. Manage document versions and view processing status
7. Monitor workflow execution state

**Who it's for:** Individual knowledge workers initially; multi-tenant enterprise support is architecturally planned.

---

## Architecture

### Backend
- **Framework:** FastAPI (Python 3.13) — modular monolith
- **Pattern:** Clean Architecture — domain entities, application services, infrastructure adapters
- **Domain modules:** Auth, Projects, Documents, Conversations, Retrieval, Workflows
- **Dependencies injected via:** FastAPI `Depends()` into route handlers
- **Unit of Work pattern:** `UnitOfWork` protocol with SQLAlchemy async implementation
- **Domain errors:** Typed `DomainError` hierarchy (`AuthenticationError`, `NotFoundError`, etc.)

### Frontend
- **Framework:** Next.js 16 (React 19) with TypeScript
- **Styling:** Tailwind CSS 4
- **State management:** Zustand (auth + UI), TanStack Query (server state)
- **Forms:** React Hook Form + Zod validation
- **API layer:** Custom `apiClient` wrapper with JWT refresh-token rotation
- **Key pages:** Login/Register, Dashboard (project list), Documents (upload + versions), Chat (SSE streaming + citations), Settings

### Database
- **Primary store:** PostgreSQL via SQLAlchemy 2.0 async + Alembic migrations
- **Models:** Users, RefreshSessions, Organizations, OrganizationMembers, Projects, ProjectMembers, Documents, DocumentVersions, DocumentChunks, ChunkEmbeddings, Conversations, Messages, LlmUsage, WorkflowRuns, WorkflowEvents
- **12 Alembic migrations** applied

### External Services
- **Vector store:** Qdrant (multi-tenant with `organization_id` + `project_id` payload filters)
- **Object storage:** Azure Blob Storage or Google Cloud Storage (with local fallback)
- **AI providers:** OpenAI (GPT-4o/4o-mini, embeddings), Gemini (pro/flash, embeddings), Anthropic (Claude 3.5 Sonnet), TestModel
- **Workflows:** Temporal (document processing, chunking, embedding pipelines)

### API Structure
- Base path: `/api/v1`
- Auth: `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/google`
- Projects: `/projects` (CRUD)
- Documents: `/projects/{id}/documents` (CRUD + versioning)
- Conversations: `/projects/{id}/conversations` (CRUD), `/conversations/{id}/messages`
- Chat: `/conversations/{id}/chat` (non-streaming), `/conversations/{id}/chat/stream` (SSE)
- Retrieval: `/retrieval/search`, `/rag/ask`
- Config: `/config/models`
- Workflows: `/workflows/{run_id}`, `/projects/{id}/workflows`

---

## Repository Structure

```
/
├── .ai/                    # AI agent context files (PROJECT_CONTEXT, DOMAIN_MAP, etc.)
├── docs/
│   ├── technical-specification.md   # Full product/architecture spec
│   ├── adr/                          # Architecture Decision Records (7 ADRs)
│   └── retrieval/                    # Retrieval design docs
├── backend/
│   ├── src/knowledge_os/
│   │   ├── domain/           # Entities, repositories (Protocol), common errors
│   │   ├── application/      # Services, ports (Protocol), workflows
│   │   ├── infrastructure/   # DB, repos, AI adapters, storage, search, workflows
│   │   ├── api/              # FastAPI routes, schemas, dependencies
│   │   ├── config.py         # Pydantic Settings
│   │   ├── main.py           # FastAPI app factory
│   │   └── worker.py         # Temporal worker entry point
│   ├── tests/                # unit/, integration/, api/
│   ├── migrations/           # Alembic (12 versions)
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js App Router pages
│   │   └── shared/           # API client, types, stores, UI components
│   └── package.json
├── docker-compose.yml        # Qdrant + Temporal
├── Makefile                  # Dev commands
└── render.yaml               # Render.com deployment config
```

---

## Technology Stack

| Area | Technology | Version |
|---|---|---|
| Backend framework | FastAPI | 0.115+ |
| Python | CPython | 3.13 |
| ORM | SQLAlchemy (async) | 2.0.36+ |
| Migrations | Alembic | 1.14+ |
| Auth tokens | PyJWT (access), opaque refresh | 2.10+ |
| Password hashing | Argon2 (pwdlib) | 0.2+ |
| Frontend framework | Next.js | 16.2.7 |
| React | React | 19.2.4 |
| Styling | Tailwind CSS | 4 |
| State | Zustand 5 + TanStack Query 5 | latest |
| Vector DB | Qdrant | latest |
| Workflows | Temporal | 1.28+ |
| AI SDK | PydanticAI | 1.106+ |
| PDF parsing | pypdf | 5.0+ |
| Token counting | tiktoken | 0.8+ |
| Blob storage | Azure Blob / Google Cloud Storage | latest |
| Package manager (Python) | uv | latest |
| Package manager (Node) | npm | latest |
| Linter | Ruff | 0.9+ |
| Type checker | mypy (strict) | 1.14+ |
| Test framework | pytest + pytest-asyncio | 8.3+ / 0.25+ |
| Test DB | testcontainers (PostgreSQL) | 4.14+ |

---

## Development Workflow

```bash
# Backend
make setup          # Create env, install deps, migrate DB
make run            # Start FastAPI dev server (localhost:8000)
make test           # Run pytest
make lint           # Ruff lint
make format         # Ruff format
make typecheck      # mypy strict
make check          # All quality gates

# Frontend
cd frontend && npm install   # Install deps
cd frontend && npm run dev   # Start Next.js dev (localhost:3000)

# Infrastructure
make services-up    # Start Qdrant + Temporal in Docker
make services-down  # Stop them
make worker         # Start Temporal worker
```

---

## Current Implementation Status

### Implemented (Sprints 1-9)
- **Sprint 1-1.1:** Auth (register, login, refresh rotation, logout), personal org bootstrap, project CRUD
- **Sprint 2:** Document lifecycle (upload, versions, blob storage with local fallback)
- **Sprint 3:** Conversations and messages with sequence ordering
- **Sprint 4:** AI chat (PydanticAI, SSE streaming, model selection, usage tracking)
- **Sprint 4.5:** Full frontend (auth, dashboard, sidebar, documents, chat, settings)
- **Sprint 5:** Temporal workflows (document processing orchestration)
- **Sprint 6-6.1:** PDF extraction, token counting, chunk metadata
- **Sprint 7:** Embeddings (OpenAI + Gemini), Qdrant vector store
- **Sprint 8:** Retrieval service (vector search + PostgreSQL hydration)
- **Sprint 9:** Context builder, citation engine, RAG generation

### 84 tests passing across unit, integration, and API tests

### Not Implemented (Planned)
- **Agents domain:** Agent policies, runs, steps, tool calls, budgets
- **Reports domain:** Report generation, artifacts, download
- **Password reset flow**
- **Organization membership management** (invite/remove members)
- **Search UI** (dedicated search page beyond chat)
- **Hybrid search** (PostgreSQL full-text + Qdrant vector fusion)
- **Reranking** provider abstraction
- **Feedback** (ratings, qualitative)
- **Observability** (OpenTelemetry, Prometheus, Grafana)
- **Deployment manifests** (Kubernetes, Helm)
- **CI/CD pipeline** (GitHub Actions)
- **Frontend tests**

### Technical Debt
- Soft-deleting documents does not clean up Blob Storage files
- No blob cleanup workflow
- `AuthorizationError` maps to HTTP 404 (should be 403) in error handler
- Google OAuth client ID hardcoded path in `.env.example`
- Frontend stores access token in localStorage (not HttpOnly cookie)
- No idempotency key enforcement on mutating endpoints
- No rate limiting
- No input sanitization beyond Pydantic validation
- No CORS restrictions beyond origin list

---

## Important Constraints

1. Multi-tenant isolation via `organization_id` is mandatory on every tenant-owned resource
2. Domain code must not import FastAPI, SQLAlchemy, Temporal, Qdrant, or SDK types
3. Infrastructure adapters implement domain/application ports (dependency inversion)
4. ORM models are never returned from API routes — response schemas map explicitly
5. All external retried commands and Temporal activities are idempotent
6. Qdrant is derived/rebuildable — PostgreSQL is the system of record
7. Chat is request-scoped SSE; Temporal is for durable agent/report execution
8. UUIDv7 primary keys for sortable distributed identifiers (currently using uuid4)
