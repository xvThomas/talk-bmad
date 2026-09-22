# Investigation: OpenRouter Go SDK Integration

## Hand-off Brief

1. **What happened.** User wants to investigate adding a new LLM API via the native Go SDK of OpenRouter, not REST direct.
2. **Where the case stands.** Confirmed existence of community Go SDK `github.com/revrost/go-openrouter` (v1.8.0, July 2026). No official Go SDK from OpenRouter found. Existing LLM provider architecture uses `domain.LlmClient` with single `Complete()` method and separate provider clients (`internal/llm/openai/`, `internal/llm/anthropic/`).
3. **What's needed next.** Map exact interface signatures and request/response structures of existing providers, compare with OpenRouter SDK's API surface, then estimate integration effort and propose story.

## Case Info

| Field            | Value                                                                      |
| ---------------- | -------------------------------------------------------------------------- |
| Ticket           | N/A                                                                        |
| Date opened      | 2026-09-19                                                                 |
| Status           | Active                                                                     |
| System           | macOS, workspace root: talk-bmad                                           |
| Evidence sources | Project-context.md, implementation artifacts, pkg.go.dev, OpenRouter docs |

## Problem Statement

User wants to add OpenRouter as a new LLM provider in the `talk` project, using its native Go SDK (not REST direct). Must follow existing architecture patterns (`domain.LlmClient`, provider clients, router). Need to evaluate feasibility, identify required changes, and estimate effort.

## Evidence Inventory

| Source   | Status                          | Notes     |
| -------- | ------------------------------- | --------- |
| project-context.md | Available | Confirms LLM client interface (`domain.LlmClient` single `Complete()`), provider SDKs (OpenAI, Anthropic), testing patterns. |
| implementation artifacts referencing `talk/internal/llm/` | Partial | References to `openai/client.go`, `anthropic/client.go`, `router/router.go`. No direct access to talk-backend source due to root restriction. |
| OpenRouter documentation | Available | OpenRouter API is OpenAI-compatible; official client SDKs for TypeScript/Python, no official Go SDK. |
| OpenRouter official Go SDK `github.com/OpenRouterTeam/go-sdk` | Available | v0.8.1, Apache‑2.0, beta, full API coverage, custom HTTP client support. |
| Community Go SDK `github.com/revrost/go-openrouter` | Available | v1.8.0, unofficial, superseded by official SDK. |

## Investigation Backlog

| # | Path to Explore | Priority              | Status                                | Notes     |
| - | --------------- | --------------------- | ------------------------------------- | --------- |
| 1 | Examine existing LLM client signatures (OpenAI, Anthropic) | High | Open | Need to know exact method signature of `Complete()` and request/response types. |
| 2 | Compare with OpenRouter SDK's `CreateChatCompletion` signature | High | Open | Determine mapping between `domain.CompletionRequest` and OpenRouter's `ChatCompletionRequest`. |
| 3 | Identify required changes to `domain.Model` registry | Medium | Open | OpenRouter model slugs (e.g., `openrouter/deepseek/deepseek-chat`) need to be added. |
| 4 | Evaluate dependency addition (new go.mod entry) | Medium | Open | Check compatibility with existing dependencies, CGO constraints. |
| 5 | Test injection pattern (baseURL, *http.Client) | Medium | Open | Ensure OpenRouter client can be tested with `httptest`. |

## Timeline of Events

| Time        | Event               | Source                | Confidence            |
| ----------- | ------------------- | --------------------- | --------------------- |
| 2026-09-19 | User request: investigate OpenRouter Go SDK integration | User message | Confirmed |
| 2026-09-19 | Found community Go SDK on pkg.go.dev | pkg.go.dev | Confirmed |
| 2026-09-19 | Reviewed OpenRouter docs: no official Go SDK | openrouter.ai/docs | Confirmed |

## Confirmed Findings

### Finding 1: Community Go SDK exists and appears maintained

**Evidence:** pkg.go.dev/github.com/revrost/go-openrouter shows version v1.8.0 published July 27, 2026, Apache-2.0 license, 27 importers, stable tag.

**Detail:** SDK provides `Client` with `CreateChatCompletion`, `CreateChatCompletionStream`, embeddings, tool calling, reasoning, multimodal. Includes fallback, caching, audio, transcription. Likely covers full OpenRouter API surface.

### Finding 2: Official Go SDK exists (OpenRouterTeam/go-sdk v0.8.1)

**Evidence:** pkg.go.dev/github.com/OpenRouterTeam/go-sdk shows version v0.8.1 published September 19, 2026, Apache‑2.0 license, built by Speakeasy, beta status.

**Detail:** SDK provides full OpenRouter API coverage: chat completions (streaming/non‑streaming), embeddings, images, TTS, STT, responses API, platform APIs (API keys, models, providers, guardrails, analytics). Supports custom HTTP client, retries, typed errors.

### Finding 3: Community SDK also available but superseded

**Evidence:** `github.com/revrost/go-openrouter` v1.8.0 exists but is unofficial.

**Detail:** Official SDK is preferred for long‑term support; community SDK may have different API surface.

### Finding 4: Project uses `domain.LlmClient` interface with single `Complete()` method

**Evidence:** project-context.md lines: "Interfaces are tiny: 1-3 methods max. `LlmClient` is a single `Complete()` method."

**Detail:** Any new provider must implement this interface. Existing providers: OpenAI, Anthropic.

### Finding 4: Provider clients follow testable injection pattern

**Evidence:** project-context.md: "HTTP tools: production constructor uses `defaultBaseURL`, unexported test constructor accepts custom URL."

**Detail:** OpenRouter client must accept `baseURL` and `*http.Client` for testability.

## Deduced Conclusions

### Deduction 1: Integration is feasible with official SDK

**Based on:** Finding 2, Finding 4

**Reasoning:** The official SDK exposes `Chat.Send` and `Responses.Send`; can be wrapped to implement `domain.LlmClient.Complete()`. Must map request/response types. SDK supports custom HTTP client, allowing test injection.

**Conclusion:** Technical feasibility high; need to verify mapping details.

### Deduction 2: New provider will fit existing router pattern

**Based on:** Finding 3, references to `internal/llm/router/router.go`

**Reasoning:** Router selects provider based on model slug. OpenRouter models have prefix `openrouter/` or maybe `openrouter:`; router will need mapping.

**Conclusion:** Router extension required, but pattern exists.

## Hypothesized Paths

### Hypothesis 1: Official SDK's API matches existing provider signatures

**Status:** Open

**Theory:** OpenRouter's `ChatRequest` and `ChatResponse` are similar to OpenAI's, making mapping straightforward.

**Supporting indicators:** OpenRouter API is OpenAI‑compatible; SDK generated from OpenAPI spec.

**Would confirm:** Reading existing OpenAI client.go and comparing with OpenRouter SDK's types.

**Would refute:** Significant mismatches (e.g., different field names, nested structures).

### Hypothesis 2: Dependency addition will not conflict with existing constraints

**Status:** Open

**Theory:** `github.com/OpenRouterTeam/go-sdk` has no CGO dependencies, compatible with `CGO_ENABLED=0`.

**Supporting indicators:** SDK appears pure Go; imports standard library and common packages.

**Would confirm:** Inspect go.mod of SDK for problematic deps.

**Would refute:** Requires CGO or conflicts with pinned versions.

## Missing Evidence

| Gap              | Impact                               | How to Obtain   |
| ---------------- | ------------------------------------ | --------------- |
| Exact signature of `domain.LlmClient.Complete()` | Cannot implement adapter | Read `talk-backend/talk/internal/domain/llm.go` or similar |
| Structure of `domain.CompletionRequest` and `domain.CompletionResponse` | Cannot map to OpenRouter types | Read domain package source |
| Existing OpenAI client implementation | Pattern to follow | Read `talk/internal/llm/openai/client.go` |
| Router's model-to-provider mapping logic | Need to extend registry | Read `talk/internal/llm/router/router.go` |

## Source Code Trace

| Element       | Detail                                      |
| ------------- | ------------------------------------------- |
| Error origin  | N/A (exploration case)                      |
| Trigger       | User request to integrate OpenRouter        |
| Condition     | Existing LLM provider pattern established   |
| Related files | `talk/internal/llm/openai/client.go`, `talk/internal/llm/anthropic/client.go`, `talk/internal/llm/router/router.go`, `talk/internal/domain/llm.go` |

## Conclusion

**Confidence:** High

Official OpenRouter Go SDK exists (v0.8.1, beta). Integration likely requires:

1. New package `internal/llm/openrouter/` with client implementing `domain.LlmClient`.
2. Update router to recognize OpenRouter model slugs.
3. Add dependency `github.com/OpenRouterTeam/go-sdk@v0.8.1`.
4. Tests following existing provider test pattern (injectable baseURL).

Risk: SDK is beta (0.x), but published by OpenRouter team. Should pin version.

## Recommended Next Steps

### Fix direction

Implement OpenRouter provider as new Go module inside `talk`:

- Create `internal/llm/openrouter/client.go` with `type Client struct`, `func (c *Client) Complete(ctx context.Context, req domain.CompletionRequest) (domain.CompletionResponse, error)`.
- Map `domain.CompletionRequest` to OpenRouter's `ChatCompletionRequest`.
- Map response back, preserving token usage, finish reason, etc.
- Add `NewClient(baseURL string, httpClient *http.Client, apiKey string)` constructor.
- Register OpenRouter models in `domain` registry (or extend router's mapping).

### Diagnostic

Obtain missing evidence: either grant access to `talk-backend` source, or ask user to provide relevant snippets (interface definition, existing client examples).

## Reproduction Plan

N/A (exploration case).

## Side Findings

- OpenRouter provides BYOK (Bring Your Own Key) with 1M free requests/month.
- OpenRouter supports fallback between models automatically; SDK includes fallback logic.
- Project uses Go 1.25 with strict concurrency patterns (`sync.WaitGroup.Go`).

## Follow-up: 2026-09-19

### New Evidence

- Official SDK `github.com/OpenRouterTeam/go-sdk` v0.8.1 (beta, published 2026‑09‑19). Built by Speakeasy, covers full API.
- Community SDK `github.com/revrost/go-openrouter` v1.8.0 also exists but superseded.

### Additional Findings

- Project-context.md enforces `description` tags on MCP tool input fields; similar attention needed for OpenRouter request fields if they are exposed as tool parameters.

### Updated Hypotheses

- Hypothesis 1 (API match) remains Open until internal source inspected.
- Hypothesis 2 (dependency compatibility) likely confirmed — SDK appears pure Go.

### Backlog Changes

- Added items 1-5.

### Updated Conclusion

Official SDK available; integration feasible with pinning to v0.8.1. Need to examine existing provider signatures for mapping.