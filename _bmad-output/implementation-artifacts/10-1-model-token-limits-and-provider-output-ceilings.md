---
baseline_commit: not-recorded
---

# Story 10.1: Model Token Limits and Provider Output Ceilings

Status: ready-for-dev

## Story

As a platform operator,
I want to configure token capacities and a request output ceiling for each model,
so that Talk can consistently apply its output policy and report documented provider limits.

## Acceptance Criteria (BDD)

1. **Given** the backend model registry **When** token-limit metadata is added **Then** every registered model can optionally define `ContextWindowTokens`, `ProviderMaxOutputTokens`, and `RequestMaxOutputTokens` **And** OpenAI-compatible models can optionally define `OutputLimitParameter` as `max_tokens` or `max_completion_tokens` **And** the Poolside `agent` model is removed **And** all other existing model aliases remain selectable.
2. **Given** `ProviderMaxOutputTokens > 0` **When** `RequestMaxOutputTokens` is absent, zero, or greater than the provider maximum **Then** the effective request output limit equals `ProviderMaxOutputTokens`.
3. **Given** both provider and request limits are configured **When** the request limit is positive and less than or equal to the provider maximum **Then** the effective request output limit equals `RequestMaxOutputTokens`.
4. **Given** no provider maximum is configured **When** `RequestMaxOutputTokens > 0` **Then** the effective request output limit equals `RequestMaxOutputTokens`.
5. **Given** neither limit produces a positive effective value **When** Talk creates a completion request **Then** no output-limit parameter is sent and the provider default is preserved.
6. **Given** an Anthropic model with an effective output limit **When** Talk creates a Messages API request **Then** the limit is sent as `max_tokens`.
7. **Given** an OpenAI-compatible model with an effective output limit and a configured supported parameter name **When** Talk creates a chat-completion request **Then** the limit is sent through the configured `max_tokens` or `max_completion_tokens` parameter.
8. **Given** the effective-limit resolver and provider mappings **When** the backend test suite runs **Then** tests cover every limit rule, both provider mappings, omission of an unset limit, removal of `agent`, and preservation of the remaining aliases.

## Tasks / Subtasks

- [ ] Task 1: Separate provider capabilities from Talk request policy (AC: #1-5)
  - [ ] Update `talk/internal/domain/model.go` to replace the ambiguous `MaxOutputTokens` field with optional/non-negative metadata for `ContextWindowTokens`, `ProviderMaxOutputTokens`, and `RequestMaxOutputTokens`.
  - [ ] Add a typed `OutputLimitParameter` value for OpenAI-compatible models, accepting only `max_tokens` and `max_completion_tokens`.
  - [ ] Preserve existing model aliases and provider/API model identifiers except for removing the Poolside `agent` entry.
  - [ ] Carry forward current configured request ceilings only where they represent Talk's existing request policy; do not present them as provider capabilities.

- [ ] Task 2: Implement effective output-limit resolution (AC: #2-5)
  - [ ] Add a small domain-level resolver with the rule: if provider maximum is positive, use `min(request, provider)` when request is positive and within the provider maximum; otherwise use the provider maximum; if provider maximum is absent, use a positive request maximum; otherwise return zero.
  - [ ] Ensure zero means omission, not an explicit zero sent to a provider.
  - [ ] Keep the resolver independent of SDK types so all boundary cases can be table-tested without network calls.

- [ ] Task 3: Apply the limit to Anthropic requests (AC: #6)
  - [ ] Update `talk/internal/llm/anthropic/client.go` to use the effective limit for `MessageNewParams.MaxTokens`.
  - [ ] Remove the current unconditional `4096` fallback; an unset effective limit must be handled according to the story's omission/default behavior.
  - [ ] Preserve existing system prompt, tools, thinking configuration, cancellation, response conversion, and usage extraction behavior.

- [ ] Task 4: Apply the configured parameter to OpenAI-compatible requests (AC: #7)
  - [ ] Update `talk/internal/llm/openai/client.go` to set only the configured supported output-limit field when the effective limit is positive.
  - [ ] Support both `max_tokens` and `max_completion_tokens` using the installed `github.com/openai/openai-go` v1.12.0 SDK or its supported request-field/extra-field mechanism; do not silently send an unsupported parameter.
  - [ ] Preserve reasoning effort, tools, custom base URLs, message conversion, response conversion, and usage extraction.

- [ ] Task 5: Add focused regression tests (AC: #8)
  - [ ] Extend `talk/internal/domain/model_test.go` for registry aliases, removal of `agent`, metadata validation/shape, and all effective-limit table cases.
  - [ ] Add client request-construction tests for Anthropic `max_tokens`, OpenAI `max_tokens`, OpenAI `max_completion_tokens`, and omitted output limits.
  - [ ] Prefer injectable/mockable transports or request inspection over live provider calls; tests must not require API keys or network access.
  - [ ] Keep existing model lookup, router, thinking, tool-call, and usage tests green.

- [ ] Task 6: Validate the backend module (AC: #8)
  - [ ] Run `gofmt` on changed Go files.
  - [ ] Run `go test ./...` from `talk-backend/talk`.
  - [ ] Run the repository's applicable lint/build checks if available and record any pre-existing unrelated failures.

## Dev Notes

### Scope and Boundaries

- This story implements model limit metadata, effective request-limit policy, and provider request mapping only.
- Story 10.2 owns confirmed token-usage `CUSTOM` AG-UI event emission; do not add stream events here.
- Story 10.3 owns last-completed-call indicators; do not add frontend state or UI here.
- This is not token estimation, context-window enforcement, history compaction, cost calculation, or a new HTTP endpoint.

### Current Code State

- `talk/internal/domain/model.go` currently has one `MaxOutputTokens int64` field. The registry contains `haiku-4.5`, `sonnet-4.6`, `opus-4.6`, `o4-mini`, `gpt-5.4`, `mistral-small`, and Poolside `agent`.
- `talk/internal/llm/anthropic/client.go` currently sends `MaxOutputTokens`, falling back to `4096` when it is zero. That behavior conflates a configured Talk ceiling with provider capability and must be replaced by the effective-limit rule.
- `talk/internal/llm/openai/client.go` currently sets model, messages, reasoning effort, and tools but sends no output-limit parameter.
- `talk/internal/llm/router/router.go` resolves a domain model and creates the provider client; retain this routing contract unless the new metadata requires a narrowly scoped change.
- Existing tests are primarily domain registry tests and converter tests. There are no current provider client request tests, so add them at the provider boundary without weakening existing assertions.

### Data Contract and Invariants

- `ContextWindowTokens` and `ProviderMaxOutputTokens` describe documented provider capabilities.
- `RequestMaxOutputTokens` is Talk's configured request policy and must not be treated as the provider maximum.
- Non-positive values mean unavailable/unconfigured. Do not invent provider limits and do not add safety margins in this story.
- `OutputLimitParameter` is relevant only to OpenAI-compatible models. Supported values are exactly `max_tokens` and `max_completion_tokens`; unsupported values must not result in a silently malformed request.
- An effective limit of zero means the request must omit the provider output-limit parameter.
- Keep model alias strings stable for `haiku-4.5`, `sonnet-4.6`, `opus-4.6`, `o4-mini`, `gpt-5.4`, and `mistral-small`; remove only `agent` as required by the PRD.

### Effective Limit Rule

Let `P` be `ProviderMaxOutputTokens` and `R` be `RequestMaxOutputTokens`:

```text
if P > 0:
    if R > 0 and R <= P: return R
    return P
if R > 0:
    return R
return 0
```

The resolver should be pure and reusable by both provider clients. The ratio/observability fields described in the addendum belong to later stories and must not be added here.

### Provider Mapping Guardrails

- Anthropic uses the Messages API `max_tokens` field. Preserve all unrelated request fields and existing thinking-budget behavior; if thinking-budget calculations depend on the selected output ceiling, keep them coherent with the effective value.
- OpenAI-compatible requests must distinguish `max_tokens` from `max_completion_tokens` based on model metadata. Verify the exact v1.12.0 SDK field names or supported extra JSON field mechanism before implementation.
- Provider requests should be inspectable in tests through a local round-trip/mock transport. Do not introduce live API calls, new dependencies, or a new provider abstraction solely for tests.

### Expected Files

- Update: `talk/internal/domain/model.go`
- Update: `talk/internal/domain/model_test.go`
- Update: `talk/internal/llm/anthropic/client.go`
- Add/update: `talk/internal/llm/anthropic/client_test.go` if request construction cannot be covered through an existing focused test
- Update: `talk/internal/llm/openai/client.go`
- Add/update: `talk/internal/llm/openai/client_test.go` for request parameter mapping
- Inspect/update only if required: `talk/internal/llm/router/router.go` and router tests

### Architecture and Library Requirements

- Follow the existing Go package boundaries: model policy in `internal/domain`, SDK translation in each provider client, routing in `internal/llm/router`.
- Use the already-installed Go 1.25 module and provider SDK versions from `talk/go.mod`; do not upgrade dependencies for this story.
- Keep public interfaces and `domain.LlmClient` behavior stable unless a compile-required change is narrowly scoped.
- Avoid `any`-based policy logic and avoid provider-specific assumptions in the domain resolver.
- No network, API key, database, or AG-UI transport dependency is allowed in unit tests.

### Regression Focus

- Existing model selection and forwarded aliases must continue to resolve after removing `agent`.
- Existing Anthropic thinking, tool calls, system prompts, cancellation, and usage conversion must remain unchanged.
- Existing OpenAI/Mistral custom base URL behavior, reasoning effort, tool calls, and usage conversion must remain unchanged.
- A request with no effective limit must not serialize a zero-valued output-limit field merely because the SDK has a default field value.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md`, Epic 10 and Story 10.1]
- [Source: `_bmad-output/planning-artifacts/prds/prd-token-observability-backend-2026-09-05/prd.md`, FR-1 to FR-10]
- [Source: `_bmad-output/planning-artifacts/prds/prd-token-observability-backend-2026-09-05/addendum.md`, Effective Limit Rule and Model Metadata Sources]
- [Source: `_bmad-output/planning-artifacts/prds/prd-token-observability-backend-2026-09-05/.decision-log.md`, Output Limits decision]
- [Source: `talk-backend/talk/internal/domain/model.go`]
- [Source: `talk-backend/talk/internal/llm/anthropic/client.go`]
- [Source: `talk-backend/talk/internal/llm/openai/client.go`]
- [Source: `talk-backend/talk/internal/domain/model_test.go`]
- [Source: `talk-backend/talk/go.mod`]

### Missing Optional Inputs

- No dedicated architecture or UX artifact was found for this backend story; context is derived from the Epic 10 planning section, the token observability PRD/addendum, and the current backend implementation.

## Dev Agent Record

### Agent Model Used

Not started.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story is ready for Amelia's implementation workflow.

### File List

- Story context file created; implementation files are unchanged.

## Change Log

- 2026-09-05: Created comprehensive implementation context for Story 10.1.
