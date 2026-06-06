# API Guidelines

## REST Standards

- Base path: `/api/v1`.
- Use plural resource nouns and standard HTTP methods.
- JSON fields use `snake_case`.
- Pydantic request/response models are the external contract.
- Never expose ORM models, internal exceptions, secrets, or unsafe failure details.
- OpenAPI is the contract source of truth.

## Status Codes

| Situation | Status |
|---|---:|
| Create resource | `201` |
| Successful read/update | `200` |
| Successful delete/logout with no body | `204` |
| Missing/invalid authentication | `401` |
| Cross-tenant or inaccessible resource | `404` |
| Uniqueness/idempotency conflict | `409` |
| Valid JSON violating domain input rules | `422` |
| Rate limit | `429` |

Authorization failures intentionally return `404` when revealing resource existence would enable enumeration.

## Error Format

Use RFC 9457-style Problem Details:

```json
{
  "type": "https://knowledge-os.local/problems/project_not_found",
  "title": "Project Not Found",
  "status": 404,
  "detail": "Project not found",
  "error_code": "project_not_found",
  "instance": "/api/v1/projects/..."
}
```

Future production responses should also include `correlation_id`.

## Authentication

- Access tokens are short-lived JWT bearer tokens.
- JWT claims carry identity/session, not mutable authorization grants.
- Refresh tokens are opaque, stored only as hashes, rotated on use, and sent in `HttpOnly` cookies.
- Refresh-token reuse revokes the token family.

## Authorization

- Resolve organization/project roles server-side for each request.
- Scope every tenant-owned query by `organization_id`.
- Re-check authorization inside application services and tool/activity boundaries.
- Never trust tenant/project identifiers from a token or request without membership validation.

## Pagination

- Use cursor pagination for growing collections: `?cursor=&limit=`.
- Default limit is bounded; maximum is `100` unless justified.
- Return stable ordering and an opaque next cursor.
- Current project listing uses a bounded limit but has not yet implemented cursors.

## Mutations and Idempotency

- Retriable create/start endpoints require `Idempotency-Key` when the idempotency subsystem is implemented.
- Updates include an expected version when concurrent writes are possible.
- Deletes are soft first when asynchronous cleanup or retention applies.

## Streaming

- Use Server-Sent Events for one-way chat response streaming.
- Event names are typed and versionable.
- Persist message lifecycle separately from the client connection.
- Support cancellation and reconnection where retained events allow it.
- Do not use WebSockets until bidirectional real-time behavior is required.

## API Change Policy

- Additive changes are preferred within `/v1`.
- Breaking changes require a new API version or a documented compatibility migration.
- Update route tests, OpenAPI expectations, `.ai` guidance, and consumers together.

