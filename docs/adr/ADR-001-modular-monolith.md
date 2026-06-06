# ADR-001: Modular Monolith

- Status: Accepted
- Date: 2026-06-06
- Implementation: Partially implemented

## Context

The product has multiple business domains but is early-stage. Starting with independent microservices would introduce network contracts, distributed transactions, deployments, and operational overhead before domain boundaries and scaling needs are proven.

## Decision

Build a modular monolith with explicit domain/application/infrastructure boundaries. Deploy the API, web application, and Temporal worker processes separately where runtime scaling differs.

Domains communicate through public application interfaces or versioned events, never another domain's repository.

## Consequences

- Faster iteration and simpler transactional behavior.
- Domain boundaries must be enforced through structure, tests, and review rather than network boundaries.
- A domain may be extracted later only when measured scaling, ownership, or deployment requirements justify it.

## Rejected Alternatives

- Microservices from inception: excessive operational and consistency complexity.
- Unstructured monolith: insufficient boundary enforcement and difficult future extraction.

