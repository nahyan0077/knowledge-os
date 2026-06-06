# ADR-005: PydanticAI Behind Provider-Neutral Ports

- Status: Accepted
- Date: 2026-06-06
- Implementation: Planned

## Context

Agents need typed dependencies, structured outputs, streaming, tool invocation, and support for multiple model providers. Domain behavior must not become coupled to OpenAI, Gemini, or a single orchestration SDK.

## Decision

Use PydanticAI for agent modeling and structured output behind internal ports such as `ModelGateway`, `EmbeddingGateway`, `ToolRegistry`, and `ModelPolicyResolver`.

Application/domain code uses internal contracts. Provider and PydanticAI types remain in infrastructure adapters.

## Consequences

- Agent outputs and dependencies are strongly typed.
- Providers can be selected by capability, tenant policy, latency, and budget.
- PydanticAI upgrades or replacement remain localized.
- Fallback behavior must be policy-controlled and observable.

## Rejected Alternatives

- Direct provider SDK usage in application services: creates lock-in and scattered policy.
- Custom agent framework from scratch: unnecessary cost before requirements justify it.

