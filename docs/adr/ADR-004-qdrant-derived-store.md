# ADR-004: Qdrant as a Derived Vector Store

- Status: Accepted
- Date: 2026-06-06
- Implementation: Planned

## Context

Semantic retrieval requires efficient vector search, but vector indexes can drift, be corrupted, or require regeneration when embedding and chunking strategies change.

## Decision

Use Qdrant as a derived vector index. PostgreSQL chunks and index manifests are authoritative. Qdrant points use deterministic chunk IDs and mandatory `organization_id` and `project_id` payload filters.

Collection changes use versioned collections and alias swaps. Indexes must be rebuildable from PostgreSQL.

## Consequences

- Vector search scales independently without owning business truth.
- Indexing is eventually consistent and requires verification/reconciliation.
- Every Qdrant query must apply tenant scope.
- Reindex operations are expected platform capabilities.

## Rejected Alternatives

- Qdrant as source of truth: unacceptable provenance and recovery risk.
- PostgreSQL vector search only: remains an option for reassessment, but Qdrant is selected for dedicated vector-scale operations.

