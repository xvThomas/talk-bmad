---
baseline_commit: bc39bd4 (talk-backend, 10.1 merged)
---

# Story 10.2: Per-response token usage in the AG-UI stream

Status: in-progress

## Story

As a frontend developer,
I want a provider-neutral AG-UI event for every completed LLM response,
So that I can show the latest confirmed token consumption without polling another endpoint.

## Acceptance Criteria (BDD)

1. **Given** a successful LLM API response **When** its token usage is available **Then** the existing AG-UI SSE stream emits a custom `token_usage` event after that response is processed **And** the event identifies the model alias and the counts as confirmed usage for that completed call **And** it includes available input and output token counts, cache tokens (read/write), and reasoning tokens **And** it includes the selected model alias and its configured context-window and provider-output limits when available.
2. **Given** the response has confirmed input tokens and a positive context-window limit **When** the event is built **Then** the event includes the input-to-context ratio (confirmed input tokens ÷ context-window limit).
3. **Given** the response has confirmed output tokens and a positive provider-output limit **When** the event is built **Then** the event includes the output-to-provider-maximum ratio (confirmed output tokens ÷ provider max).
4. **Given** a count or its corresponding limit is unavailable **When** the event is built **Then** the affected ratio is omitted rather than estimated or represented as zero.
5. **Given** one user turn triggers multiple LLM responses through tool execution **When** each response completes **Then** each completed response produces its own dedicated token-usage event (payload = single call, NOT the turn's running total) **And** the event for a response is emitted before a subsequent error can end the turn.
6. **Given** the backend test suite runs **Then** tests cover event payloads, omitted ratios, and multiple completed responses in one turn **And** existing text, reasoning, tool, error, interrupt, and session events retain their current behavior.
7. **Given** a user turn has ended **When** the turn's authoritative total (`TurnEvent.TotalUsage`, summed server-side over every LLM call of the turn) is available **Then** the AG-UI SSE stream emits a custom `turn_usage` event carrying that total **And** it is emitted exactly once per turn **And** it is emitted for complete and interrupted (iteration-limit) turns alike **And** the per-call `token_usage` events of that turn remain unchanged.

## Tasks / Subtasks

- [ ] Task 1: Thread model token-limit metadata into the message pipeline (AC: #1)
  - [ ] Add the registered model limits (`ContextWindowTokens`, `ProviderMaxOutputTokens`) to the `domain.Model` carried on `MessageEvent.Model` — they are currently dropped (`conversation.go` builds a 2-field `Model{Name, OLTPProvider}`).
  - [ ] Pass the full `domain.Model` descriptor into `ConversationManager` instead of `ModelID string` + `Provider OLTPProvider`.
  - [ ] Update every `NewConversationManager` call site and `SetClient` so the full descriptor flows.
- [ ] Task 2: Add a pure domain payload builder for the token-usage event (AC: #1-4)
  - [ ] Define a JSON-serializable value type (model alias, counted tokens, cache read/write, reasoning tokens, configured limits, optional ratios).
  - [ ] Add ratio helpers: context ratio only when input tokens available AND context-window limit > 0; output ratio only when output tokens available AND provider-output limit > 0.
  - [ ] Omit unavailable counts/limits/ratios from the JSON payload (no zero substitutes).
  - [ ] Keep the builder free of AG-UI/SDK types so it is table-testable without SSE or network.
- [ ] Task 3: Emit the `token_usage` custom AG-UI event (AC: #1, #5)
  - [ ] In `AGUIEmitter.HandleMessageEvent`, after an assistant LLM response is processed, emit `events.NewCustomEvent("token_usage", events.WithValue(payload))` writing through the existing `writeEvent` path.
  - [ ] Emit exactly once per completed LLM response: for `CallKindInitial` assistant messages AND `CallKindToolResult` assistant messages; never for `RoleTool` tool-result messages.
  - [ ] Preserve existing REASONING_*/TEXT_MESSAGE_* ordering and all other handlers.
- [ ] Task 4: Focused regression tests (AC: #6)
  - [ ] Domain builder tests: full payload, each omitted ratio case, unavailable counts, negative/zero limits.
  - [ ] Emitter tests: one `token_usage` event per completed response, multi-response tool-loop turn, no event for tool-result messages.
  - [ ] Conversation/config wiring tests for the full model descriptor propagation.
- [ ] Task 5: Emit the `turn_usage` custom AG-UI event (AC: #7)
  - [ ] In `AGUIEmitter.HandleTurnEvent` (currently a no-op), after a turn finishes, emit `events.NewCustomEvent("turn_usage", events.WithValue(payload))` writing through the existing `writeEvent` path.
  - [ ] Payload = the turn's authoritative total (`TurnEvent.TotalUsage`, already accumulated server-side at `conversation.go:188/213`) with the same field-omission rules as `token_usage`; no ratios (ratios are per-call only).
  - [ ] Emit exactly once per completed turn for every status (`complete`, `incomplete`) without touching the per-call `token_usage` emission from Task 3.
- [ ] Task 6: Focused `turn_usage` regression tests (AC: #7)
  - [ ] Emitter tests: one `turn_usage` per turn with the summed totals, multi-call tool-loop turn sums every call, interrupted (iteration-limit) turn still emits its authoritative partial total.
  - [ ] Domain payload builder tests mirroring the `token_usage` omission cases.
- [ ] Task 7: Validate the backend module (AC: #6, #7)
  - [ ] `gofmt` + `goimports` on changed Go files.
  - [ ] `go test ./...` from `talk-backend/talk`.
  - [ ] Repository lint/build checks if available; record any pre-existing unrelated failures.

### Review Findings

- [x] [Review][Patch] Add an integration regression test proving a multi-call tool loop emits one authoritative summed `turn_usage`, and an iteration-limit turn emits its non-zero partial total [talk/internal/domain/conversation_test.go:318]
- [x] [Review][Patch] Complete the token-usage payload contract tests by asserting cache/reasoning/provider-limit fields and testing each ratio omission independently [talk/internal/domain/token_usage_test.go:9]
- [x] [Review][Defer] Correct model aliases that currently resolve to different provider model IDs [talk/internal/domain/model.go:92] — deferred, pre-existing
- [x] [Review][Defer] Align the mapping-agent prompt's required tool arguments with its workflow calls [docs/labs/FSM-discovery-mapping-agent.md:128] — deferred, pre-existing
- [x] [Review][Defer] Define handling for projected SRIDs, multiple geometry columns, and empty query results in the mapping workflow [docs/labs/FSM-discovery-mapping-agent.md:119] — deferred, pre-existing
- [x] [Review][Defer] Reconcile clustering and repeated-quartile requirements with the declared MapLibre style output contract [docs/labs/FSM-discovery-mapping-agent.md:151] — deferred, pre-existing
- [x] [Review][Defer] Reject unknown Anthropic thinking-effort values instead of silently mapping them to low [talk/internal/llm/anthropic/client.go:91] — deferred, pre-existing

## Dev Notes

### Scope and Boundaries

- This story emits confirmed token usage through the existing AG-UI stream: a per-call `token_usage` event (Task 3) and a per-turn authoritative `turn_usage` total for client reconciliation (Task 5). It does NOT estimate tokens, block/edit pre-send requests, add a new HTTP endpoint, persist usage, compact history, or compute costs.
- The frontend session cumulative is deliberately NOT fed by summing per-call events: it sums `turn_usage` totals, which is why the backend emits an authoritative per-turn aggregate (see Task 5). No usage is persisted anywhere in this story — the stream is the only carrier.
- Story 10.3 owns all frontend state/UI for these events — nothing frontend here.
- The payload describes ONE completed LLM call (not the turn total). `ConversationManager` already accumulates `totalUsage` for observability; the token-usage event must use the per-call `Usage`, never `totalUsage`.
- Model metadata (10.1) is already in the registry (`internal/domain/model.go:89-97`). This story only consumes `ContextWindowTokens` and `ProviderMaxOutputTokens` — it must not alter registry values or the effective-limit rule.

### Current Code State (line references = talk-backend/talk, HEAD bc39bd4)

- `internal/domain/conversation.go:120` builds the model for events as `Model{Name: m.modelID, OLTPProvider: m.oltpProvider}`. **The registered limits are dropped here.**
- `internal/domain/conversation.go` fields `modelID string` + `oltpProvider OLTPProvider` (config at `conversation.go:50-55`); `SetClient(client, modelID string)` at `:92`.
- `internal/domain/model.go` — `Model` now carries `ContextWindowTokens`, `ProviderMaxOutputTokens`, `RequestMaxOutputTokens`, `OutputLimitParameter`. `Lookup(alias)` returns the full descriptor.
- `cmd/cli/serve.go:203` already does `domain.Lookup(modelAlias)` and only forwards `modelDescriptor.OLTPProvider` + alias into `ConversationManagerConfig` (`serve.go:217-219`).
- `cmd/cli/main.go:70` (same pattern) and `cmd/cli/cmd_model.go:42` calls `a.Manager.SetClient(client, string(selected))`.
- `internal/domain/message_event_handlers.go:47-53` — `Usage{InputTokens, OutputTokens, CacheReadTokens, CacheWriteTokens, ReasoningTokens}` is already attached to `MessageEvent.Usage` at `conversation.go:251`.
- `internal/agui/emitter.go:33` — `HandleMessageEvent` currently emits reasoning + text events for assistant messages only; this is the emission point to extend.
- AG-UI SDK (`github.com/ag-ui-protocol/ag-ui/sdks/community/go@pinned`) provides `events.NewCustomEvent(name string, options ...CustomEventOption)` and `events.WithValue(value any)`. Custom events are app-defined, opt-in for clients, and have no fixed position in the event stream — fully backward compatible (NFR-1).

### Model Metadata Threading (Task 1 — the core architectural change)

The event payload needs `ContextWindowTokens` and `ProviderMaxOutputTokens`, but those values never reach `MessageEvent`. Fix at the source: make `ConversationManager` own the resolved `domain.Model`.

- Change `ConversationManagerConfig` to accept `Model domain.Model` (replacing `ModelID string` and `Provider OLTPProvider`).
- Change `ConversationManager` fields accordingly and build `model := m.model` directly at `conversation.go:120` (drop the lossy partial construction).
- Change `SetClient(client LlmClient, model domain.Model)` (`conversation.go:92`) and update the CLI call site `cmd_model.go:42` to `a.Manager.SetClient(client, selected)` where `selected` comes from `domain.Lookup`.
- Update constructors at `serve.go:215` and `main.go:102` to pass the already-resolved `modelDescriptor` (both files already look it up; do not call `Lookup` twice).
- Update affected `conversation_test.go` fixtures. This is an internal API change spanning 4 files + tests — keep it narrow; do NOT change `domain.MessageEventHandler` (interface unchanged) or `domain.LlmClient`.

If a sub-implementation prefers to keep `ModelID string` for backwards compat, the alternative is storing the full descriptor alongside it — but prefer the single `Model` field so there is exactly one source of truth.

### Event Payload Contract (Task 2)

Name the custom event exactly `token_usage` (matches PRD addendum and Story 10.3). Suggested JSON `value` (keys consumed by 10.3 — keep names stable):

```json
{
  "model": "sonnet-4.6",
  "input_tokens": 41230,
  "output_tokens": 854,
  "cache_read_tokens": 10000,
  "cache_write_tokens": 0,
  "reasoning_tokens": 200,
  "context_window_tokens": 200000,
  "provider_max_output_tokens": 64000,
  "context_ratio": 0.20615,
  "output_ratio": 0.01334375
}
```

- Use `omitempty`-style omission for every unavailable count/limit/ratio. `CacheWriteTokens` is Anthropic-only; other providers leave it unset (0) and it is omitted.
- Ratios must be `*float64` (pointer, omitted when nil): a legitimately computed 0.0 (`input>0`, huge limit) must serialize, while a missing ratio must not be confused with 0.
- Ratios are computed only when BOTH numerator and positive denominator are available. No safety margin; no estimation (per addendum).
- `model` = `Model.Name` (the friendly alias from the registry, e.g. `sonnet-4.6`), which is what the frontend model selector sends and what 10.3 keys against.
- Reality check on current registry: `mistral-small` (`model.go:96`) has `ContextWindowTokens: 0` and `ProviderMaxOutputTokens: 0` → its context/output ratios are correctly omitted. Do not invent limits.

### Emission Details (Task 3)

- Place emission inside `AGUIEmitter.HandleMessageEvent` for `Role == RoleAssistant` on Kinds `CallKindInitial` and `CallKindToolResult`, after the existing reasoning/text emission so existing event ordering is untouched.
- Do not emit for `HandleMessageEvent` invocations with `Role == RoleTool` (tool-result messages — they carry no per-response usage).
- Use the existing `e.writeEvent(ctx, event)` best-effort path (context-cancellation aware, logs unrelated write errors).
- Emission is synchronous within the Chat loop (`conversation.go` calls `storeAssistantResponse` → `HandleMessageEvent` before tool execution / before returning the iteration-limit error), which is what guarantees AC#5: each response's event precedes any subsequent terminal error.

### Emission du total de tour (Task 5 — `turn_usage`)

The per-call events power the frontend's "last completed call" indicator; they must NOT be summed client-side into the session cumulative (missed/duplicated events, tool-loop grouping, stream interruption). Instead the backend already accumulates `totalUsage` per turn (`conversation.go:133-213`) and carries it on `TurnEvent.TotalUsage` for every final turn event, including interrupted iteration-limit turns (`finishTurn`). Turn this into the authoritative reconciliation point:

- Emit a second custom AG-UI event `turn_usage` from `AGUIEmitter.HandleTurnEvent` (currently a no-op, `emitter.go:47`), exactly once per turn, for any `Status` (`complete`, `incomplete`).
- Payload = the turn's `TotalUsage` with the same omission rules as `token_usage` (no ratios — the context/output ratios only make sense per call, and the cumulative is counts-only):

```json
{
  "model": "sonnet-4.6",
  "input_tokens": 41230,
  "output_tokens": 1352,
  "cache_read_tokens": 10000,
  "cache_write_tokens": 0,
  "reasoning_tokens": 200
}
```

- Add `turn_id` (`TurnEvent.TurnID`) if frontend reconciliation ever needs dedup; by default the stream is strictly sequential so the frontend simply adds each `turn_usage` to its session cumulative and clears its per-turn scratch sum.
- Design constraints intentionally kept: **stream-only, zero persistence, no new HTTP endpoint** (NFR-4 stays intact). A `turn_usage` missed on a dropped stream is self-healing: the cumulative is per-session ("current consumption"), reset on conversation load / page reload. This is a deliberate UX decision — see decision-log entry 2026-09-14.

### Testing Guardrails

- Domain builder tests: full payload, each ratio omitted when numerator absent / limit ≤ 0, both-available case, zero-with-positive-input ratio serialization.
- Emitter tests via the existing `handlers := domain.NewMessageEventHandlers(...)` phase pattern or direct `AGUIEmitter` + a recording `SSEWriter`/`httptest` SSE reader; assert exactly one `CUSTOM`/`token_usage` per assistant response and none for `RoleTool`.
- Tool-loop scenario (initial + tool_result assistant messages in one `Chat`) → two `token_usage` events, second carries the tool_result call's usage only; `HandleTurnEvent` with those two calls → one `turn_usage` with the summed total.
- Interrupted-turn scenario: a `Chat` hitting `ErrMaxToolIterations` must still dispatch `HandleTurnEvent` with a partial `TotalUsage` → one `turn_usage` emitted with that authoritative partial total.
- No external mock framework (hand-written stubs with closure fields), table-driven tests, `t.Helper()`, `t.Cleanup()`, `t.Setenv()`. No API keys / network in tests.

### Previous Story Intelligence (10.1)

- 10.1 added model limit metadata, the effective-limit rule (`EffectiveOutputLimit`), and removed Poolside `agent`. The deferred review item "`ContextWindowTokens` non lu" was explicitly earmarked for 10.2/10.3 — this story closes it.
- 10.1 review noted the Anthropic `max_tokens` fallback 4096 and `gpt-5.4` → `max_tokens` mapping; neither affects this story.
- 10.1 follow-up (2026-09-06): `mistral-small` now maps to `mistral-small-4-0-26-03` (Mistral Small 4, hybrid reasoning) whose thinking content may be dropped on the OpenAI path (`msg.Thinking`). If the openai `fromSDKResponse` does not populate reasoning tokens, `reasoning_tokens` will simply be omitted — acceptable; do not fabricate.
- Establish the pattern (used again in 10.3's contract): confirmed counts only, omit what is unavailable.

### Architecture and Library Requirements

- Go 1.25 (`go.work`), CGO_ENABLED=0, stdlib only. No new dependencies — the AG-UI SDK `events.NewCustomEvent`/`WithValue` is already pinned in `talk/go.mod`.
- Follow package boundaries: pure payload/ratio logic in `internal/domain`, SDK translation in `internal/agui` (or the emitter), wiring in `cmd/cli`.
- Interfaces stay stable: `domain.LlmClient` and `domain.MessageEventHandler` unchanged.
- Project rules: `any` not `interface{}`, `wg.Go()` not `Add/Done`, wrap errors with operation names (`fmt.Errorf("building token usage event: %w", err)`), functions ≤ 50 lines, cognitive complexity ≤ 15, comments in English, `gofmt` + `goimports`.

### Files Expected

- Update: `talk/internal/domain/conversation.go` (Config + fields + `SetClient` + MessageEvent.Model source) — Task 1
- Update: `talk/internal/domain/conversation_test.go` — Task 1/4
- Add: `talk/internal/domain/token_usage.go` (payload types + pure ratio builder) — Task 2 (also hosts the `turn_usage` payload builder) — Task 5
- Add: `talk/internal/domain/token_usage_test.go` — Task 4 (extended in Task 6)
- Update: `talk/internal/agui/emitter.go` (emit `token_usage` custom event in `HandleMessageEvent` — Task 3; emit `turn_usage` custom event in `HandleTurnEvent` — Task 5)
- Update: `talk/internal/agui/emitter_test.go` — Task 4 (extended in Task 6)
- Update: `talk/cmd/cli/serve.go` (pass full `modelDescriptor` into config) — Task 1
- Update: `talk/cmd/cli/main.go` (same) — Task 1
- Update: `talk/cmd/cli/cmd_model.go` (`SetClient(client, selected)` with resolved descriptor) — Task 1
- No change expected: `internal/llm/*`, `internal/domain/model.go`, AG-UI SDK version, `go.mod`.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Epic 10, Story 10.2, FRs Token backend FR-11 to FR-18]
- [Source: `_bmad-output/planning-artifacts/prds/prd-token-observability-backend-2026-09-05/prd.md` §4.3, FR-11 to FR-18; NFR-1 to NFR-4]
- [Source: `_bmad-output/planning-artifacts/prds/prd-token-observability-backend-2026-09-05/addendum.md` — Observability Ratios, Suggested Event Payload]
- [Source: `_bmad-output/planning-artifacts/prds/prd-token-observability-backend-2026-09-05/.decision-log.md` — Transport decision]
- [Source: `_bmad-output/planning-artifacts/prds/prd-token-observability-frontend-2026-09-05/addendum.md` — payload = individual completed call]
- [Source: `_bmad-output/implementation-artifacts/10-1-model-token-limits-and-provider-output-ceilings.md` — review findings + follow-up]
- [Source: `talk-backend/talk/internal/domain/conversation.go`, `message_event_handlers.go`, `model.go`, `internal/agui/emitter.go`, `handler.go`, `sse.go`, `cmd/cli/serve.go`, `main.go`, `cmd_model.go`]
- [Source: AG-UI SDK `pkg/core/events/custom_events.go` — `NewCustomEvent`, `WithValue`]

### Missing Optional Inputs

- No dedicated architecture artifact for this backend story; the AG-UI `CUSTOM` event mechanism (SDK + protocol docs) and the Epic 10 planning section supply the contract. The map-related ADR (adr-001) does not apply.

## Dev Agent Record

### Agent Model Used

Amelia (GitHub Copilot)

### Debug Log References

### Completion Notes List

### File List