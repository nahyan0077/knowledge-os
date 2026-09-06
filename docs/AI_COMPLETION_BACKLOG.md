# AI Completion Backlog — Knowledge OS

Generated from repository analysis. Prioritized by blocking severity.

---

## P0 — Blocking

These prevent the application from functioning correctly or have security implications.

### TASK-001: Fix AuthorizationError HTTP Status Code

**Status:** TODO
**Why:** `AuthorizationError` currently maps to HTTP 404 in the global exception handler, which is semantically incorrect and hides authorization bugs from clients.

**Affected files:**
- `backend/src/knowledge_os/main.py:74`

**Acceptance criteria:**
- `AuthorizationError` returns HTTP 403
- `NotFoundError` remains HTTP 404
- Existing tests still pass

**Tests:** Existing route tests; add explicit 403 assertion for unauthorized access

---

### TASK-002: Frontend Auth Token Security Hardening

**Status:** TODO
**Why:** Access tokens are stored in `localStorage`, making them vulnerable to XSS attacks. The refresh token uses an HttpOnly cookie (correct), but the access token should also be moved to an HttpOnly cookie or the backend should be modified to use cookie-based auth exclusively.

**Affected files:**
- `frontend/src/shared/lib/store.ts`
- `frontend/src/shared/api/client.ts`
- `backend/src/knowledge_os/api/v1/auth.py`
- `backend/src/knowledge_os/config.py`

**Acceptance criteria:**
- Access tokens are not exposed to JavaScript (HttpOnly cookie)
- API client reads auth from cookies, not localStorage
- Refresh flow works with cookie-only auth
- Security headers configured correctly

**Tests:** Manual E2E auth flow; add security-focused tests

---

### TASK-003: Environment Variable Security Cleanup

**Status:** TODO
**Why:** `.env.example` contains a real file path for `GOOGLE_APPLICATION_CREDENTIALS`. Secrets and credentials must never appear in committed configuration.

**Affected files:**
- `backend/.env.example`

**Acceptance criteria:**
- All example values are placeholder-safe
- No real paths, keys, or credentials in `.env.example`
- `.gitignore` covers all credential files

---

## P1 — Core Product

Missing functionality required for the intended application.

### TASK-010: Implement Password Reset Flow

**Status:** TODO
**Why:** No way for users to recover access. The spec defines `POST /auth/password-reset/request` and `POST /auth/password-reset/confirm`. The `password_reset_tokens` table is referenced in the spec but not implemented.

**Affected files:**
- `backend/src/knowledge_os/domain/entities.py` (add `PasswordResetToken` entity)
- `backend/src/knowledge_os/domain/repositories.py` (add repository protocol)
- `backend/src/knowledge_os/application/auth.py` (add reset methods)
- `backend/src/knowledge_os/api/v1/auth.py` (add routes)
- `backend/src/knowledge_os/infrastructure/repositories/sqlalchemy.py` (implement)
- `backend/migrations/` (new migration)
- Frontend: forgot-password and reset-password pages

**Acceptance criteria:**
- User can request a password reset (returns 200 regardless of email existence)
- Secure token generated and stored hashed
- Token expires after 1 hour
- Password can be changed with valid token
- Invalid/expired tokens rejected with appropriate error
- Frontend flow complete

---

### TASK-011: Implement Organization Member Management

**Status:** TODO
**Why:** Multi-tenant team features require member invitation, role assignment, and removal. Currently only personal org bootstrap exists.

**Affected files:**
- `backend/src/knowledge_os/api/v1/` (new member routes)
- `backend/src/knowledge_os/application/` (member service)
- Frontend: settings/members page

**Acceptance criteria:**
- Owner can invite members by email
- Members can be assigned roles (owner, editor, viewer)
- Members can be removed
- Role changes are reflected in authorization

---

### TASK-012: Implement Agent Runs Domain

**Status:** TODO
**Why:** Core product feature for auditable AI agent execution. Spec defines agent catalog, bounded tools, model budgets, and runs.

**Affected files:**
- `backend/src/knowledge_os/domain/entities.py` (add `AgentRun`, `AgentRunStep`)
- `backend/src/knowledge_os/domain/repositories.py`
- `backend/src/knowledge_os/application/agents.py` (new)
- `backend/src/knowledge_os/api/v1/agents.py` (new)
- `backend/src/knowledge_os/infrastructure/`
- `backend/migrations/`
- Frontend: agents pages

**Acceptance criteria:**
- Agent catalog endpoint (list available agents)
- Start/list/cancel agent runs
- Agent run steps are persisted
- Runs have budgets (max duration, token spend, tool calls)
- Cancellation is cooperative

---

### TASK-013: Implement Reports Domain

**Status:** TODO
**Why:** Durable cited report generation is a key differentiator. Spec defines report requests, sections, artifacts, and lifecycle.

**Affected files:**
- `backend/src/knowledge_os/domain/entities.py` (add `Report`)
- `backend/src/knowledge_os/application/reports.py` (new)
- `backend/src/knowledge_os/api/v1/reports.py` (new)
- `backend/migrations/`
- Frontend: reports pages

**Acceptance criteria:**
- Request/list/read/download reports
- Reports have lifecycle status
- Report generation is resumable
- Artifacts stored in blob storage
- Citations are included

---

### TASK-014: Implement Search UI/API Page

**Status:** TODO
**Why:** Dedicated search interface beyond chat-based queries. Spec defines `POST /projects/{id}/search`.

**Affected files:**
- `frontend/src/app/projects/[projectId]/search/` (new page)
- `backend/src/knowledge_os/api/v1/search.py` (new or extend retrieval)
- `frontend/src/shared/types/index.ts`

**Acceptance criteria:**
- Search input with project scope
- Results displayed with relevance scores
- Citations link to source documents
- Search history is maintained

---

### TASK-015: Implement Hybrid Search (PostgreSQL Full-Text + Vector Fusion)

**Status:** TODO
**Why:** Vector-only search misses keyword-heavy queries. Spec defines Phase 2: hybrid search with reciprocal rank fusion.

**Affected files:**
- `backend/src/knowledge_os/infrastructure/search/`
- `backend/src/knowledge_os/application/retrieval.py`
- `backend/migrations/` (add full-text index on `document_chunks.content`)

**Acceptance criteria:**
- PostgreSQL full-text search candidates combined with Qdrant vector results
- Reciprocal rank fusion algorithm
- Toggle between vector-only and hybrid modes
- Evaluation metrics tracked

---

### TASK-016: Implement Reranking Provider

**Status:** TODO
**Why:** Retrieval quality improves significantly with reranking. Spec defines Phase 3: provider-independent reranker port.

**Affected files:**
- `backend/src/knowledge_os/application/ports.py` (add `RerankerPort`)
- `backend/src/knowledge_os/infrastructure/ai/reranker.py` (new)
- `backend/src/knowledge_os/application/retrieval.py`

**Acceptance criteria:**
- Reranker port protocol defined
- At least one reranker implementation (e.g., Cohere, Cross-encoder)
- Optional reranking in retrieval pipeline
- Evaluation gates before production enablement

---

### TASK-017: Implement Query Rewriting

**Status:** TODO
**Why:** Complex queries benefit from rewrite/multi-query strategies. Spec defines Phase 4: guarded rewrite preserving original query.

**Affected files:**
- `backend/src/knowledge_os/application/ports.py`
- `backend/src/knowledge_os/application/retrieval.py`
- `backend/src/knowledge_os/infrastructure/ai/`

**Acceptance criteria:**
- Query rewrite strategy port defined
- LLM-based rewrite implementation
- Original query preserved as fallback
- Multi-query expansion supported

---

### TASK-018: Implement Feedback Domain

**Status:** TODO
**Why:** Retrieval quality measurement requires user feedback. Spec defines ratings and qualitative feedback.

**Affected files:**
- `backend/src/knowledge_os/domain/entities.py` (add `Feedback`)
- `backend/src/knowledge_os/application/feedback.py` (new)
- `backend/src/knowledge_os/api/v1/feedback.py` (new)
- `backend/migrations/`

**Acceptance criteria:**
- Users can rate messages and agent runs
- Feedback linked to correct target (message OR agent run, not both)
- Feedback stored with category and comment
- Aggregated feedback available for evaluation

---

## P2 — Quality

Testing, validation, error handling, performance, maintainability.

### TASK-020: Add Frontend Tests

**Status:** TODO
**Why:** No frontend tests exist. Critical for preventing regressions in UI interactions.

**Affected files:**
- `frontend/src/**/*.test.tsx` (new)
- `frontend/package.json` (add test deps)

**Acceptance criteria:**
- Unit tests for API client
- Component tests for key pages (login, dashboard, documents, chat)
- Form validation tests
- Auth flow tests

---

### TASK-021: Add Backend Error Handling Improvements

**Status:** TODO
**Why:** Several error paths return generic messages. Domain errors should be more specific.

**Affected files:**
- `backend/src/knowledge_os/application/`
- `backend/src/knowledge_os/api/`

**Acceptance criteria:**
- All service methods raise typed domain errors
- Error responses include correlation IDs
- RFC 9457 Problem Details format fully implemented
- Field-level validation errors included

---

### TASK-022: Add Rate Limiting

**Status:** TODO
**Why:** No rate limiting on auth, upload, chat, or agent endpoints. Security risk.

**Affected files:**
- `backend/src/knowledge_os/api/` (middleware)
- `backend/src/knowledge_os/config.py`

**Acceptance criteria:**
- Rate limits on auth endpoints (e.g., 5 requests/minute)
- Rate limits on chat/agent endpoints (e.g., 30 requests/minute)
- Configurable per-endpoint
- 429 responses with Retry-After header

---

### TASK-023: Add Idempotency Key Enforcement

**Status:** TODO
**Why:** Spec requires `Idempotency-Key` header on retryable mutating requests but it's not enforced.

**Affected files:**
- `backend/src/knowledge_os/api/` (middleware or per-route)
- `backend/migrations/` (add `idempotency_keys` table)

**Acceptance criteria:**
- Idempotency key validated on POST endpoints
- Duplicate requests return cached response
- Keys expire after reasonable TTL

---

### TASK-024: Implement Soft-Delete Cleanup Workflow

**Status:** TODO
**Why:** Soft-deleting documents retains files in Blob Storage. No cleanup mechanism exists.

**Affected files:**
- `backend/src/knowledge_os/infrastructure/workflows/` (new workflow)
- `backend/src/knowledge_os/worker.py`
- `backend/migrations/`

**Acceptance criteria:**
- Scheduled or triggered cleanup of soft-deleted resources
- Blob files deleted after grace period
- Qdrant points removed
- Audit trail maintained

---

### TASK-025: Add CORS Production Configuration

**Status:** TODO
**Why:** CORS is configured from env but defaults are development-only. Production deployment needs proper origin restrictions.

**Affected files:**
- `backend/src/knowledge_os/config.py`
- `render.yaml`
- `frontend/.env`

**Acceptance criteria:**
- CORS origins configurable per environment
- Credentials properly handled
- No wildcard origins in production
- Frontend URL included in allowed origins

---

### TASK-026: Frontend Error Boundary Implementation

**Status:** TODO
**Why:** No React error boundaries exist. Unhandled component errors crash the entire app.

**Affected files:**
- `frontend/src/app/layout.tsx`
- `frontend/src/app/projects/[projectId]/layout.tsx`
- `frontend/src/shared/ui/ErrorBoundary.tsx` (new)

**Acceptance criteria:**
- Root error boundary catches unexpected errors
- Feature-level error boundaries at project layout
- Graceful fallback UI with retry option
- Error reporting to console/telemetry

---

### TASK-027: Frontend Loading and Empty State Improvements

**Status:** TODO
**Why:** Some pages lack proper loading, empty, or error states.

**Affected files:**
- `frontend/src/app/projects/[projectId]/`
- Various page components

**Acceptance criteria:**
- Every page has loading, empty, error, and success states
- Consistent skeleton loading patterns
- Empty states provide actionable guidance
- Error states offer retry options

---

### TASK-028: Add Frontend Accessibility Improvements

**Status:** TODO
**Why:** WCAG 2.2 AA is the target but ARIA labels, keyboard navigation, and focus management are incomplete.

**Affected files:**
- `frontend/src/app/**/*.tsx`
- `frontend/src/shared/ui/`

**Acceptance criteria:**
- All interactive elements are keyboard accessible
- ARIA labels on icon buttons
- Focus management in modals and drawers
- Screen reader tested

---

## P3 — Polish

Non-critical improvements.

### TASK-030: Implement UUIDv7 Primary Keys

**Status:** TODO
**Why:** Spec requires UUIDv7 for sortable distributed identifiers. Currently using uuid4.

**Affected files:**
- `backend/src/knowledge_os/domain/entities.py`
- `backend/src/knowledge_os/infrastructure/`
- `backend/migrations/`

**Acceptance criteria:**
- All new entities use UUIDv7
- IDs are time-sortable
- Existing uuid4 IDs remain functional

---

### TASK-031: Add Observability (OpenTelemetry)

**Status:** TODO
**Why:** No telemetry, tracing, or metrics. Critical for production monitoring.

**Affected files:**
- `backend/src/knowledge_os/` (middleware, instrumentations)
- `docker-compose.yml` (add OTel collector)
- `frontend/` (browser telemetry)

**Acceptance criteria:**
- Request tracing with correlation IDs
- LLM usage metrics (latency, tokens, cost)
- Workflow execution metrics
- Qdrant/PostgreSQL dependency health

---

### TASK-032: Add Kubernetes Deployment Manifests

**Status:** TODO
**Why:** No deployment manifests exist beyond Docker and Render.

**Affected files:**
- `deploy/kubernetes/` (new)
- `deploy/helm/` (new)

**Acceptance criteria:**
- Separate deployments for API, worker, frontend
- Horizontal Pod Autoscaling configured
- Pod disruption budgets
- Liveness/readiness probes

---

### TASK-033: Add CI/CD Pipeline

**Status:** TODO
**Why:** No automated testing or deployment pipeline.

**Affected files:**
- `.github/workflows/` (new)

**Acceptance criteria:**
- On PR: lint, typecheck, test, build
- On merge to main: deploy to staging
- On tag: deploy to production
- Dependency scanning

---

### TASK-034: Add Conversation Summarization

**Status:** TODO
**Why:** Long conversations hit context limits. Spec defines `summary` and `summary_through_sequence` columns on conversations.

**Affected files:**
- `backend/src/knowledge_os/application/conversations.py`
- `backend/src/knowledge_os/application/ports.py`
- Frontend: chat display

**Acceptance criteria:**
- Automatic summarization after N messages
- Summary used in context building
- Summary updated as conversation progresses
- Configurable threshold

---

### TASK-035: Add Document Knowledge Entries

**Status:** TODO
**Why:** Users should be able to curate project knowledge beyond uploaded documents.

**Affected files:**
- `backend/src/knowledge_os/domain/entities.py` (add `KnowledgeEntry`)
- `backend/src/knowledge_os/application/knowledge.py` (new)
- `backend/src/knowledge_os/api/v1/knowledge.py` (new)
- `backend/migrations/`

**Acceptance criteria:**
- CRUD for project knowledge entries
- Entries searchable alongside documents
- Entries have status (draft, published)
- Entries are project-scoped

---

### TASK-036: Add Audit Events

**Status:** TODO
**Why:** Security and compliance require audit trails for sensitive operations.

**Affected files:**
- `backend/src/knowledge_os/domain/entities.py` (add `AuditEvent`)
- `backend/src/knowledge_os/infrastructure/audit/` (new)
- `backend/migrations/`

**Acceptance criteria:**
- Audit events for auth, membership changes, project deletion, document access
- Events include actor, action, resource, timestamp
- Events are append-only
- Queryable audit log

---

### TASK-037: Add Response Caching

**Status:** TODO
**Why:** Repeated reads of the same data hit the database unnecessarily.

**Affected files:**
- `backend/src/knowledge_os/api/` (middleware or per-route)
- `backend/src/knowledge_os/config.py`

**Acceptance criteria:**
- Cache-Control headers on GET endpoints
- ETag support for conditional requests
- Invalidation on mutations
- Configurable TTL

---

### TASK-038: Add Database Seed Script

**Status:** TODO
**Why:** No way to populate development data for testing or demos.

**Affected files:**
- `backend/scripts/seed.py` (new)
- `Makefile` (add seed command)

**Acceptance criteria:**
- Creates sample organization, users, projects
- Optionally uploads sample documents
- Configurable via CLI arguments
- Idempotent (safe to run multiple times)

---

## Summary

| Priority | Count | Status |
|---|---|---|
| P0 (Blocking) | 3 | TODO |
| P1 (Core Product) | 9 | TODO |
| P2 (Quality) | 9 | TODO |
| P3 (Polish) | 9 | TODO |
| **Total** | **30** | |

---

## Recommended Execution Order

1. **P0-001** (AuthorizationError status fix) — 10 minutes
2. **P0-003** (env cleanup) — 10 minutes
3. **P2-021** (error handling improvements) — 1 hour
4. **P2-026** (error boundaries) — 30 minutes
5. **P0-002** (token security) — 2 hours
6. **P1-010** (password reset) — 3 hours
7. **P2-022** (rate limiting) — 2 hours
8. **P1-014** (search UI) — 3 hours
9. **P2-020** (frontend tests) — 4 hours
10. **P2-027** (loading/empty states) — 2 hours
11. **P2-028** (accessibility) — 3 hours
12. **P1-015** (hybrid search) — 4 hours
13. **P1-016** (reranking) — 3 hours
14. **P1-012** (agent runs) — 5 hours
15. **P1-013** (reports) — 5 hours
16. **P1-017** (query rewriting) — 3 hours
17. **P1-018** (feedback) — 2 hours
18. **P1-011** (org members) — 4 hours
19. **P2-023** (idempotency) — 2 hours
20. **P2-024** (soft-delete cleanup) — 3 hours
21. **P2-025** (CORS production) — 30 minutes
22. **P3-030** (UUIDv7) — 3 hours
23. **P3-031** (observability) — 4 hours
24. **P3-033** (CI/CD) — 3 hours
25. **P3-034** (conversation summarization) — 4 hours
26. **P3-035** (knowledge entries) — 3 hours
27. **P3-036** (audit events) — 3 hours
28. **P3-037** (response caching) — 2 hours
29. **P3-038** (seed script) — 1 hour
30. **P3-032** (Kubernetes manifests) — 4 hours
