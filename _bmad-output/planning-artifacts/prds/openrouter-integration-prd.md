# Product Requirements Document: OpenRouter LLM Provider Integration

**Document ID**: PRD-OPENROUTER-001  
**Date**: 2026-09-19  
**Author**: John (Product Manager)  
**Status**: Draft

## 1. Overview

Add OpenRouter as a new LLM provider to the `talk` project, using its official Go SDK (`github.com/OpenRouterTeam/go-sdk`). This enables access to hundreds of AI models through a single API key, with automatic routing, fallback, and unified billing.

## 2. Problem Statement

Currently, the project supports OpenAI and Anthropic providers directly. Adding new providers requires implementing custom SDK integrations. OpenRouter offers:

- **Model diversity**: 400+ models across providers (DeepSeek, Google, Anthropic, OpenAI, etc.)
- **Cost optimization**: automatic routing to the most cost‑effective provider per request
- **BYOK (Bring Your Own Key)**: 1M free requests/month with own provider keys
- **Unified billing & monitoring**: single API key, usage analytics, guardrails
- **Advanced features**: reasoning tokens, prompt/response caching, server tools (web search, image generation)

Users want to leverage these benefits without managing multiple provider integrations.

## 3. Goals

### Primary Goals

1. **Seamless provider addition** – integrate OpenRouter as a new `LlmClient` following existing architectural patterns.
2. **Full feature parity** – support chat completion (streaming/non‑streaming), embeddings, token usage reporting.
3. **Testability** – maintain injectable `baseURL` + `*http.Client` pattern for unit tests.
4. **Backward compatibility** – no breaking changes to `domain.LlmClient` interface or router contract.
5. **Production readiness** – error handling, rate limiting, observability aligned with existing providers.

### Success Metrics

- OpenRouter provider passes existing provider test suite.
- Router correctly routes model slugs prefixed `openrouter/` to OpenRouter client.
- Token usage (including `reasoning_tokens` if present) correctly emitted as AG‑UI events.
- Dependency addition does not conflict with existing pinned SDKs (CGO_ENABLED=0 preserved).

## 4. User Stories (High‑Level)

1. As a developer, I want to configure an OpenRouter API key in the environment and have the system use it for model requests.
2. As a user, I want to select a model like `openrouter/deepseek/deepseek-chat` and receive completions via OpenRouter’s routing.
3. As a DevOps engineer, I want to see token usage breakdowns (`prompt_tokens`, `completion_tokens`, `reasoning_tokens`) per request in logs/AG‑UI events.
4. As a product owner, I want to reduce costs by leveraging OpenRouter’s automatic fallback and BYOK free tier.

## 5. Technical Scope

### In Scope

- New Go package `internal/llm/openrouter/` with:
  - `Client` struct implementing `domain.LlmClient` (single `Complete()` method).
  - Mapping between `domain.CompletionRequest` ↔ OpenRouter `ChatRequest`.
  - Mapping between OpenRouter `ChatResult` ↔ `domain.CompletionResponse`.
  - Support for streaming responses (SSE).
  - Token usage extraction (`usage` field) with optional `reasoning_tokens`.
- Router extension (`internal/llm/router/router.go`) to recognize model slugs starting with `openrouter/`.
- Dependency addition: `github.com/OpenRouterTeam/go-sdk@v0.8.1` pinned in `talk/go.mod`.
- Unit tests following existing provider pattern (injectable `httptest.Server`).
- Environment variable `OPENROUTER_API_KEY` loaded via config.
- AG‑UI events: emit `turn_usage` with token counts (including reasoning tokens if available).

### Out of Scope

- OpenRouter‑specific features not required for basic chat completions (images, TTS, STT, video generation, interns, vault, etc.).
- Changes to `domain.LlmClient` interface or existing provider implementations.
- Support for OpenRouter’s “Responses API” (unless later needed).
- Dynamic model listing from OpenRouter’s `/models` endpoint (static registry suffices).

## 6. Architecture & Design

### Existing Pattern

```
domain.LlmClient
    └── Complete(ctx, req domain.CompletionRequest) (domain.CompletionResponse, error)

Provider clients:
    openai.Client   (uses github.com/openai/openai-go)
    anthropic.Client (uses github.com/anthropics/anthropic-sdk-go)

Router:
    router.Resolve(model string) → LlmClient
```

### New Component

```
openrouter.Client
    ├── embeds *openrouter.OpenRouter (official SDK)
    ├── NewClient(baseURL string, httpClient *http.Client, apiKey string)
    └── Complete(ctx, req domain.CompletionRequest) (domain.CompletionResponse, error)
```

**Mapping notes**:

- `domain.CompletionRequest` contains `Model` (string), `Messages` ([]domain.Message), `MaxTokens`, `Temperature`, etc.
- OpenRouter `ChatRequest` expects `Model`, `Messages` (converted), `MaxCompletionTokens`, `Temperature`, etc.
- `reasoning_effort` maps if present; `reasoning_tokens` returned in `usage` (new field in `domain.CompletionResponse`?).

### Token Usage Mapping

OpenRouter’s `usage` field may contain:

```json
{
  "prompt_tokens": 100,
  "completion_tokens": how,
  "reasoning_tokens": how
}
```

If `domain.CompletionResponse` lacks a `ReasoningTokens` field, we can aggregate into `PromptTokens` (lossy) or extend the domain struct (requires analysis).

### Risk: Domain Model Extension

If the domain struct doesn’t support `reasoning_tokens`, we have three options:

1. **Add field** (breaking change) – requires updates to all providers and callers.
2. **Add optional field** (`*int`) – backward compatible but still changes struct.
3. **Ignore reasoning tokens** – lose granularity but keep compatibility.

**Recommendation**: First examine `domain.CompletionResponse` definition; if missing, propose minimal optional addition.

## 7. Dependencies & Constraints

### Dependencies

- `github.com/OpenRouterTeam/go-sdk` v0.8.1 (beta, Apache‑2.0).
- No CGO dependencies (pure Go).
- Compatible with Go 1.25 (project minimum).

### Constraints

- **CGO_ENABLED=0** mandatory – verified SDK meets this.
- **Pinned versions** – must not conflict with existing `openai-go` or `anthropic-sdk-go`.
- **Rate limiting** – OpenRouter’s own limits; client must respect 429 responses.
- **API key** – must be configurable via env var (`OPENROUTER_API_KEY`).

## 8. Non‑Functional Requirements

- **Performance**: latency comparable to existing providers (routing adds negligible overhead).
- **Reliability**: handle OpenRouter‑specific errors (402 payment required, 524 infrastructure timeout) with appropriate retry/fallback.
- **Security**: API key never logged; use `httptest` for tests.
- **Maintainability**: follow existing code style, documentation, and test patterns.

## 9. Open Questions / Risks

| Risk | Mitigation |
|------|------------|
| SDK is beta (0.x) | Pin exact version (`@v0.8.1`); monitor releases for breaking changes. |
| Reasoning tokens not in domain model | Analyze domain struct; propose minimal optional extension. |
| Mapping complexity (cache, plugins) | Ignore advanced features initially; support basic chat completion. |
| Dependency conflict | Audit SDK’s transitive dependencies for version clashes. |
| OpenRouter API changes | Follow their changelog; integration tests catch regressions. |

## 10. Validation & Acceptance Criteria

### Technical Acceptance

- [ ] `go test ./internal/llm/openrouter` passes with 80%+ coverage.
- [ ] `go test ./internal/llm/router` passes with OpenRouter model slugs.
- [ ] `make lint` and `make vet` pass.
- [ ] `CGO_ENABLED=0 go build ./...` succeeds.
- [ ] AG‑UI emits `turn_usage` events with correct token counts.
- [ ] Environment variable `OPENROUTER_API_KEY` loads correctly.

### Functional Acceptance

- [ ] Selecting model `openrouter/deepseek/deepseek-chat` routes to OpenRouter.
- [ ] Chat completions (streaming and non‑streaming) work end‑to‑end.
- [ ] Token usage appears in logs/AG‑UI (prompt, completion, total).
- [ ] Error handling: invalid API key, insufficient credits, rate limits surface clearly.

## 11. Out‑of‑Band Considerations

- **BYOK setup** – users can bring their own provider keys via OpenRouter dashboard; no code changes needed.
- **Model discovery** – future enhancement: periodically fetch `/models` to update registry.
- **Guardrails & workspaces** – advanced OpenRouter features can be added later as separate stories.

## 12. Next Steps

1. **Finalize PRD** – stakeholder review.
2. **Create implementation story** with detailed tasks.
3. **Examine domain.CompletionResponse** to decide reasoning‑token handling.
4. **Implement provider client** (spike) to validate mapping.
5. **Integrate into router** and test end‑to‑end.

---

*PRD approved by:*  
[ ] Product Owner  
[ ] Architect  
[ ] Lead Developer

*Revision history*  
- 2026‑09‑19 – Draft created (John)