# AI Knowledge Operating System

An AI-first, project-centric knowledge platform for documents, conversations, retrieval, agents, reports, and durable workflows.

## Repository Status

Only the first backend slice is implemented:

- Authentication and refresh-token rotation
- Personal organization bootstrap
- Tenant-scoped project CRUD
- PostgreSQL models and Alembic migration
- FastAPI routes and tests

Documents, conversations, retrieval, agents, reports, workflows, frontend, and deployment infrastructure are planned architecture, not implemented features.

## Start Here

| Reader | Entry point |
|---|---|
| New engineer | [.ai/PROJECT_CONTEXT.md](.ai/PROJECT_CONTEXT.md) |
| AI coding agent | [AGENTS.md](AGENTS.md) |
| Claude Code / Gemini CLI / Cursor | Tool-specific root/rule files pointing to `AGENTS.md` and `.ai/` |
| System architecture | [.ai/ARCHITECTURE.md](.ai/ARCHITECTURE.md) |
| Domain boundaries | [.ai/DOMAIN_MAP.md](.ai/DOMAIN_MAP.md) |
| Full technical specification | [docs/technical-specification.md](docs/technical-specification.md) |
| Architecture decisions | [docs/adr](docs/adr) |

## Quick Setup

Prerequisites: `uv`, Python 3.13, and a reachable PostgreSQL database matching `backend/.env`.

```bash
make setup
make run
```

OpenAPI is available at `http://localhost:8000/docs`.

Common commands:

```bash
make help
make test
make check
make migrate
make migration-sql
```

## Repository Layout

```text
.ai/        Focused context and working rules for humans and AI agents
backend/    Implemented FastAPI modular-monolith backend
docs/       Full specification and architecture decision records
Makefile    Stable local-development command interface
```
