# ADR-003: PostgreSQL as Source of Truth

- Status: Accepted
- Date: 2026-06-06
- Implementation: Partially implemented

## Context

The system needs authoritative tenant ownership, document metadata, chunk provenance, conversations, agent runs, reports, workflow projections, and transactional invariants.

## Decision

PostgreSQL is the authoritative transactional system of record. Domain state changes commit through application-level units of work. Cross-system publication uses an outbox or idempotent reconciliation.

Document chunk text and provenance remain in PostgreSQL so derived search indexes can be rebuilt.

## Consequences

- Strong relational constraints and transactions protect business invariants.
- Schema migration quality and query/index discipline are critical.
- Derived systems must reconcile against PostgreSQL, not become parallel authorities.
- Large binary content belongs in object storage, not PostgreSQL.

## Rejected Alternatives

- Qdrant as the only chunk store: weakens provenance and rebuild capability.
- Multiple authoritative databases per domain from inception: creates consistency complexity.

