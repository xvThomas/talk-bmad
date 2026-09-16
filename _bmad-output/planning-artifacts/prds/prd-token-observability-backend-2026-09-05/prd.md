---
title: "talk-backend - Token Limit Observability"
status: draft
created: 2026-09-05
updated: 2026-09-16
---

## 1. Purpose

This PRD defines the backend contract for exposing confirmed per-call LLM token consumption and model token limits to the `talk-ui` application. It is limited to observability: it does not estimate tokens before a call, prevent an over-limit request, or compact conversation history.

## 2. Problem

Talk already receives input and output token usage from LLM providers, but does not expose it through the AG-UI stream. Users therefore cannot see how close the most recent LLM call was to the context or output limits of the selected model.

## 3. Target Users and Jobs

- **Chat user:** after every LLM response, understand the confirmed input context and generated output relative to the selected model's documented limits.
- **Operator or developer:** configure known model limits and a requested output ceiling without confusing a provider capability with Talk's application policy.
- **Frontend developer:** receive a stable, self-contained AG-UI event without polling or a new HTTP endpoint.

## 4. Functional Requirements

### 4.1 Model Limit Metadata

- **FR-1:** The backend model definition supports optional `ContextWindowTokens`, `ProviderMaxOutputTokens`, and `RequestMaxOutputTokens` values for every registered model.
- **FR-2:** The backend model definition supports an optional `OutputLimitParameter` for OpenAI-compatible models, identifying whether the provider accepts `max_tokens` or `max_completion_tokens`.
- **FR-3:** Existing model aliases remain selectable unless explicitly retired. The decommissioned Poolside `agent` model is removed from the backend model registry.
- **FR-4:** `ContextWindowTokens` and `ProviderMaxOutputTokens` represent documented provider capabilities. `RequestMaxOutputTokens` represents Talk's configured request ceiling and must not be presented as a provider capability.

### 4.2 Effective Request Output Limit

- **FR-5:** When `ProviderMaxOutputTokens` is set and `RequestMaxOutputTokens` is absent, zero, or greater than the provider maximum, the effective request output limit equals `ProviderMaxOutputTokens`.
- **FR-6:** When both limits are set and the requested value is less than or equal to the provider maximum, the effective request output limit equals `RequestMaxOutputTokens`.
- **FR-7:** When `ProviderMaxOutputTokens` is absent and `RequestMaxOutputTokens` is positive, the effective request output limit equals `RequestMaxOutputTokens`.
- **FR-8:** When neither limit is available, Talk does not send an output-limit parameter and lets the provider apply its default.
- **FR-9:** Anthropic requests apply the effective request output limit through the provider's `max_tokens` parameter.
- **FR-10:** OpenAI-compatible requests apply the effective request output limit only when both a positive effective limit and a supported `OutputLimitParameter` are configured.

### 4.3 Confirmed Token Usage Events

- **FR-11:** After each successful LLM API response, including responses following a tool result in the same user turn, the backend emits a token-usage event through the existing AG-UI SSE stream.
- **FR-12:** The event includes confirmed input and output token counts from the provider response whenever available.
- **FR-13:** The event includes the selected model alias and its configured context and provider-output limits when available.
- **FR-14:** When `ContextWindowTokens` is positive, the event includes the context ratio calculated from the response's confirmed input tokens divided by that limit.
- **FR-15:** When `ProviderMaxOutputTokens` is positive, the event includes the output ratio calculated from the response's confirmed output tokens divided by that limit.
- **FR-16:** When a count or its corresponding limit is unavailable, the backend omits the affected ratio rather than fabricating an estimate.
- **FR-17:** The event identifies its data as confirmed provider usage for the completed LLM call, not an estimate of the next request.
- **FR-18:** Existing AG-UI text, reasoning, tool-call, error, and interrupt behavior remains unchanged.

### 4.4 Provider-Normalized Total Consumption

- **FR-19:** Every LLM client calculates a confirmed `total_tokens` value at the provider conversion boundary so downstream domain and AG-UI code remain provider-neutral.
- **FR-20:** For OpenAI-compatible responses, normalized total is `input_tokens + output_tokens`; cached tokens remain a subset of input and reasoning tokens remain a subset of output, so neither is added again.
- **FR-21:** For Anthropic responses, normalized total is `input_tokens + cache_read_tokens + cache_write_tokens + output_tokens`, because cached and cache-created inputs are reported separately from uncached input.
- **FR-22:** `domain.Usage.Add` aggregates normalized totals across every call of a complete or interrupted turn.
- **FR-23:** Both `token_usage` and `turn_usage` expose optional `total_tokens`; `turn_usage.total_tokens` is the authoritative normalized total for session accumulation.
- **FR-24:** Normalized total represents processed token volume, not price, context occupancy, quota, or persistent historical analytics.

### 4.5 Optional Reasoning Breakdown

- **FR-25:** `reasoning_tokens` remains optional and is propagated when the provider supplies a confirmed breakdown.
- **FR-26:** OpenAI reasoning tokens remain a breakdown already included in `output_tokens` and normalized total.
- **FR-27:** Anthropic reasoning tokens are omitted until a documented API/SDK field can be captured; they are never inferred from thinking content or configured budgets.
- **FR-28:** When Anthropic reasoning-token support is introduced, it must not alter `output_tokens` or normalized `total_tokens`, because thinking is already part of provider output accounting.

## 5. Non-Functional Requirements

- **NFR-1:** The AG-UI event contract is provider-neutral and remains backward compatible for clients that ignore new optional fields.
- **NFR-2:** Unit tests cover effective-limit resolution and request parameter selection for Anthropic and OpenAI-compatible clients.
- **NFR-3:** Unit tests cover token ratios, provider-specific normalized totals, unavailable values, per-call emission, and complete/interrupted turn aggregation.
- **NFR-4:** The implementation does not introduce a new HTTP endpoint or additional provider API call.
- **NFR-5:** Provider-specific accounting formulas remain localized to LLM client/converter boundaries.

## 6. Out of Scope

- Estimating tokens before sending a request.
- Rejecting or modifying calls that might exceed a context limit.
- Automatic conversation summarization, truncation, or compaction.
- Cost calculation, rate-limit tracking, persistence, and cross-conversation usage analytics.
- Streaming partial token-usage updates while a provider response is still generating.

## 7. Related Artifacts

- Frontend PRD: `prds/prd-token-observability-frontend-2026-09-05/prd.md`
- Technical decisions: `addendum.md`
