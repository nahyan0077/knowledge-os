# Project Context

## Purpose

The AI Knowledge Operating System gives users a durable project workspace for uploading knowledge, asking grounded questions, running specialized AI agents, and producing cited reports.

It should feel like a combination of ChatGPT Projects, Claude Projects, Glean, Notion AI, and Perplexity Enterprise while preserving explicit project ownership, provenance, workflow progress, and conversation history.

## Status Vocabulary

- **Implemented:** Present in the repository and covered by tests.
- **Planned:** Approved future architecture, not available in code.
- **Decision:** A durable constraint documented by an ADR.

Never describe a planned capability as implemented.

## Current Implementation

Implemented:

- Register, login, refresh-token rotation/reuse detection, and logout.
- Personal organization creation during registration.
- Tenant-scoped project create, list, read, update, and soft delete.
- PostgreSQL SQLAlchemy models and Alembic migration for identity, tenancy, and projects.
- FastAPI routes, unit tests, and route tests.

Planned:

- Documents, conversations, retrieval, agents, reports, Temporal workflows, frontend, Qdrant, Azure Blob Storage, and deployment manifests.

## Product Goals

1. Make project knowledge searchable and conversational.
2. Preserve citations, source versions, conversation state, and workflow history.
3. Run bounded and auditable AI agents.
4. Support durable, retryable document and report workflows.
5. Scale horizontally without compromising tenant isolation.
6. Remain understandable and extensible by humans and coding agents.

## Tech Stack

| Area | Technology | Status |
|---|---|---|
| Backend | FastAPI, Python 3.13, Pydantic | Implemented |
| Persistence | PostgreSQL, SQLAlchemy Async, Alembic | Implemented |
| Security | Argon2id, JWT access tokens, opaque refresh tokens | Implemented |
| Frontend | Next.js 15, TypeScript, Tailwind, shadcn/ui, TanStack Query, Zustand | Planned |
| Workflows | Temporal | Planned |
| Vector store | Qdrant | Planned |
| Object storage | Azure Blob Storage | Planned |
| AI | PydanticAI, OpenAI, Gemini | Planned |
| Observability | OpenTelemetry, Prometheus, Grafana | Planned |
| Deployment | Docker, Kubernetes | Planned |

## Core Concepts

- **Organization:** Mandatory tenant boundary. Personal users receive a single-user organization.
- **User:** Authenticated identity that belongs to organizations and projects.
- **Project:** Primary workspace and authorization boundary for knowledge operations.
- **Document:** Stable logical file identity with immutable versions.
- **Conversation:** Persistent project-scoped message history.
- **Agent Run:** Auditable execution of an AI policy with bounded tools and budgets.
- **Report:** Durable, cited artifact generated from project knowledge.
- **Workflow Run:** Product-facing progress projection for durable execution.

## Project Hierarchy

```text
Organization
  -> Users and memberships
  -> Projects
       -> Documents and versions
       -> Conversations and messages
       -> Agent Runs and steps
       -> Reports
       -> Knowledge entries and chunks
       -> Workflow Runs
```

A user accesses a project through tenant and project membership. All project-owned resources inherit the project's `organization_id`; cross-tenant access returns `404`.

## Authoritative Sources

1. Current code and migrations define implemented behavior.
2. ADRs define accepted durable decisions.
3. `.ai/*` summarizes architecture and working rules.
4. `docs/technical-specification.md` defines the detailed future-state design.

When sources conflict, do not guess. Update stale documentation as part of the change.

