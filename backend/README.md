# Knowledge OS Backend

The implemented backend currently contains authentication, personal-organization bootstrap, and tenant-scoped project CRUD only. For repository-wide architecture and AI-agent guidance, start at the root [README](../README.md) and [.ai context layer](../.ai/PROJECT_CONTEXT.md).

## Setup

From the repository root:

```bash
make setup
```

Equivalent backend-only commands:

```bash
uv sync --python 3.13
cp .env.example .env
uv run alembic upgrade head
```

Set a strong `KNOWLEDGE_OS_JWT_SECRET` and a PostgreSQL connection URL in `.env`.

## Run

```bash
make run
```

OpenAPI is available at `/docs`. API routes are under `/api/v1`.

## Quality Gates

```bash
make check
```

Run `make help` from the repository root for individual commands.
