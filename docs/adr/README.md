# Architecture Decision Records

ADRs record durable decisions that constrain future implementation.

Statuses:

- **Accepted:** The decision governs new work.
- **Superseded:** A newer ADR replaces it.
- **Proposed:** Not yet binding.

Implementation status is tracked separately because an accepted future-state decision may not yet exist in code.

| ADR | Decision |
|---|---|
| [ADR-001](ADR-001-modular-monolith.md) | Modular monolith |
| [ADR-002](ADR-002-temporal.md) | Temporal for durable workflows |
| [ADR-003](ADR-003-postgresql-source-of-truth.md) | PostgreSQL as source of truth |
| [ADR-004](ADR-004-qdrant-derived-store.md) | Qdrant as derived store |
| [ADR-005](ADR-005-pydanticai.md) | PydanticAI behind provider-neutral ports |
| [ADR-006](ADR-006-project-centric-hierarchy.md) | Project-centric hierarchy |

When changing an accepted decision, create a new ADR that supersedes the old one. Do not silently rewrite architectural history.

