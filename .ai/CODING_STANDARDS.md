# Coding Standards

## Architecture

- Follow Domain-Driven Design, Clean Architecture, SOLID, and dependency inversion.
- Keep domain entities free of FastAPI, SQLAlchemy, Temporal, Qdrant, Azure, and provider SDK imports.
- Application services coordinate use cases, authorization, repositories, and transactions.
- Repositories map between domain entities and ORM models.
- Delivery layers call application services; they do not contain business rules.

## Python Standards

- Python 3.13, async-first for I/O, SQLAlchemy 2.x typed async mappings.
- Strict explicit typing; `mypy` must pass.
- Pydantic models define HTTP input/output contracts.
- Dataclasses or domain-specific types define domain entities.
- Use UTC-aware datetimes and UUID identifiers.
- Catch specific exceptions; do not use blanket `except Exception` without re-raising at a boundary.
- Never log passwords, tokens, document content, prompts, or secrets.

## Size Limits

These are review thresholds, not excuses for mechanical splitting:

| Construct | Target maximum | Required action when exceeded |
|---|---:|---|
| Python source file | 400 lines | Split by cohesive responsibility or document why not |
| Class | 200 lines | Extract policies/collaborators |
| Function/method | 50 lines | Extract named operations |
| Function parameters | 6 | Introduce a typed command/query object |
| Cyclomatic complexity | 10 | Simplify or split branches |

Generated migrations and generated API clients are exempt from line limits but still require review.

## Import Rules

Allowed dependency direction:

```text
domain <- application <- api/temporal delivery
domain/application ports <- infrastructure adapters
```

Forbidden:

- `domain` importing `application`, `api`, or `infrastructure`.
- `application` importing FastAPI, SQLAlchemy models, or vendor SDKs.
- One domain importing another domain's infrastructure/repositories.
- Route modules importing SQLAlchemy sessions directly.
- Returning ORM models from APIs.

## Persistence and Transactions

- Repositories never commit.
- Application-level unit of work owns transactions.
- Tenant filters belong inside repository methods, not caller conventions.
- Mutations that can race use database-enforced optimistic locking.
- External dual writes require an outbox or idempotent reconciliation.

## Testing

- Domain/application rules: fast unit tests using ports/fakes.
- Routes/contracts: API tests with dependency overrides.
- Repository and migration behavior: PostgreSQL integration tests when introduced.
- Every security/tenant rule needs positive and negative tests.
- Run `make check` before completion.

## Documentation

- Update `.ai` files when boundaries, flows, or standards change.
- Add or supersede an ADR for durable architectural decisions.
- Mark planned capabilities explicitly; do not document them as current behavior.
- Keep comments focused on non-obvious intent, not line-by-line narration.

