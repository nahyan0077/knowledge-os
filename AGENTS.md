# AI Agent Operating Guide

Read these files before changing code:

1. `.ai/PROJECT_CONTEXT.md`
2. `.ai/DOMAIN_MAP.md`
3. `.ai/CODING_STANDARDS.md`
4. `.ai/API_GUIDELINES.md` when changing HTTP contracts
5. `.ai/WORKFLOW_MAP.md` when changing long-running behavior
6. Relevant ADRs under `docs/adr/`

## Non-Negotiable Rules

- Distinguish implemented behavior from planned architecture.
- Do not implement future domains unless the task explicitly requests them.
- Preserve tenant isolation through `organization_id`.
- Keep domain and application code independent of FastAPI, SQLAlchemy, Temporal, Qdrant, Azure, and model SDKs.
- Use application ports and infrastructure adapters at external boundaries.
- Never return ORM models from API routes.
- Add tests proportional to the change and run `make check`.
- Update `.ai` context and ADRs when changing boundaries or durable decisions.
- Do not modify business logic during documentation-only tasks.

Use `.ai/TASK_TEMPLATE.md` to frame substantial work before implementation.

