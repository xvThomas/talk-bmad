---
baseline_commit: null
---

# Story 1.5: Thinking/Reasoning via AG-UI

Status: not-started

## Story

As a frontend developer,
I want to optionally activate LLM thinking/reasoning via `forwardedProps.thinkingEffort` and receive the thinking output as AG-UI `REASONING_*` events,
so that my UI can display the model's chain-of-thought to the user.

## Context

- The CLI already supports thinking via `/thinking` command (`SetThinkingEffort`), and the `ConsoleUsageReporter` displays `messageEvent.Thinking` in the terminal.
- The ag-ui serve path creates a fresh `ConversationManager` per request but never calls `SetThinkingEffort` — thinking is always off.
- The AG-UI protocol defines `REASONING_*` event types. The Go Community SDK exposes constructors in `events/reasoning_events.go`: `NewReasoningStartEvent`, `NewReasoningMessageStartEvent`, `NewReasoningMessageContentEvent`, `NewReasoningMessageEndEvent`, `NewReasoningEndEvent`.
- Thinking content is already returned by Anthropic/OpenAI clients in `domain.Message.Thinking` (ephemeral, not persisted). It flows through `MessageEvent.Message.Thinking` to event handlers.
- The `ChatFunc` currently returns only `(string, error)` — the thinking content is lost before the handler can emit reasoning events.

## Acceptance Criteria

1. **Given** a `POST /agent` request with `forwardedProps.thinkingEffort` set to `"low"`, `"medium"`, or `"high"`, **when** the LLM supports thinking, **then** reasoning is activated for that request with the corresponding effort level, **and** the thinking output is emitted as AG-UI `REASONING_*` events before `TEXT_MESSAGE_*` events.

2. **Given** a `POST /agent` request without `forwardedProps.thinkingEffort` (or set to `"off"` or empty), **when** the request is processed, **then** thinking is not activated (backward compatible, same behavior as today).

3. **Given** a `POST /agent` request with an invalid `thinkingEffort` value (e.g. `"extreme"`), **when** the request is processed, **then** the value is ignored and thinking defaults to off (no error emitted).

4. **Given** thinking is activated and the LLM returns thinking content, **when** the SSE stream is built, **then** the event sequence is: `REASONING_START` → `REASONING_MESSAGE_START` (role=`"reasoning"`) → `REASONING_MESSAGE_CONTENT` (delta=thinking content) → `REASONING_MESSAGE_END` → `REASONING_END` → `TEXT_MESSAGE_START` → `TEXT_MESSAGE_CONTENT` → `TEXT_MESSAGE_END`.

5. **Given** thinking is activated and the LLM returns no thinking content (model didn't produce any), **when** the SSE stream is built, **then** no `REASONING_*` events are emitted.

6. **Given** the tool loop executes multiple LLM calls (tool_result iterations), **when** each intermediate LLM call returns thinking content, **then** reasoning events are emitted for each iteration (before the tool call events of the next iteration).

7. **Given** the client disconnects during reasoning event emission, **when** the context is cancelled, **then** no further events are emitted and the handler exits cleanly.

## Tasks / Subtasks

- [ ] Task 1: Extract `thinkingEffort` from `forwardedProps` in handler (AC: #1, #2, #3)
  - [ ] In `talk/internal/agui/handler.go`, add `extractThinkingEffort(forwardedProps any) domain.ThinkingEffort` function
  - [ ] Valid values: `"low"`, `"medium"`, `"high"` → corresponding `domain.ThinkingEffort`; anything else → `""` (zero value = off)
  - [ ] Unit tests for all valid values, empty, missing, invalid, nil forwardedProps

- [ ] Task 2: Extend `ChatFunc` to pass `thinkingEffort` and return thinking content (AC: #1, #4, #5)
  - [ ] Define `ChatResult struct { Response string; Thinking string }` in `talk/internal/agui/handler.go`
  - [ ] Change `ChatFunc` signature from `func(...) (string, error)` to `func(ctx context.Context, threadID string, modelAlias string, messages []types.Message, toolHandler domain.ToolCallEventHandler, thinkingEffort domain.ThinkingEffort) (ChatResult, error)`
  - [ ] Update all `chatFn` call sites in handler, serve.go, and tests

- [ ] Task 3: Wire `thinkingEffort` into `ConversationManager` from serve.go (AC: #1, #2)
  - [ ] In `talk/cmd/cli/serve.go` `chatFn`, call `manager.SetThinkingEffort(thinkingEffort)` before `manager.Chat()`
  - [ ] Return thinking from `manager.Chat()` — requires Task 4

- [ ] Task 4: Propagate thinking content from `ConversationManager.Chat()` (AC: #4, #5, #6)
  - [ ] Change `Chat()` return from `(string, error)` to `(ChatResponse, error)` where `ChatResponse struct { Content string; Thinking string }`
  - [ ] In the conversation loop, capture `response.Thinking` from each LLM call
  - [ ] For the final iteration (produces text), return thinking in `ChatResponse.Thinking`
  - [ ] For intermediate iterations with thinking, emit thinking via the `MessageEventHandler` (already flows through `HandleMessageEvent` via `MessageEvent.Message.Thinking`)
  - [ ] Update all callers of `Chat()` (CLI and serve)

- [ ] Task 5: Create AG-UI reasoning event emitter (AC: #4, #5, #6, #7)
  - [ ] In `talk/internal/agui/`, create `reasoning_events.go` with `emitReasoningEvents(ctx context.Context, w *SSEWriter, messageID string, thinking string) error`
  - [ ] Emit the 5-event sequence: `NewReasoningStartEvent(messageID)` → `NewReasoningMessageStartEvent(messageID, "reasoning")` → `NewReasoningMessageContentEvent(messageID, thinking)` → `NewReasoningMessageEndEvent(messageID)` → `NewReasoningEndEvent(messageID)`
  - [ ] Check `ctx.Err()` before each write — if cancelled, return nil immediately
  - [ ] If thinking is empty, return nil without emitting anything

- [ ] Task 6: Emit reasoning events from handler before TEXT_MESSAGE events (AC: #4, #5, #7)
  - [ ] In `handler.go` `ServeHTTP`, after `chatFn` returns, if `result.Thinking != ""`, call `emitReasoningEvents` before `TEXT_MESSAGE_START`
  - [ ] Generate a unique messageID for the reasoning events (separate from the text message ID)

- [ ] Task 7: Handle reasoning in tool loop iterations (AC: #6)
  - [ ] Implement a `ReasoningEmitter` that implements `domain.MessageEventHandler` to capture intermediate thinking
  - [ ] In `HandleMessageEvent`, if `event.Message.Thinking != ""` and tool calls follow, emit reasoning events immediately via SSEWriter
  - [ ] Alternative: accumulate intermediate thinking and emit all at once — choose based on AG-UI protocol semantics (live is preferred)

- [ ] Task 8: Unit tests for reasoning event emission (AC: #4, #5, #7)
  - [ ] Test `emitReasoningEvents` with non-empty thinking — verify 5-event sequence
  - [ ] Test `emitReasoningEvents` with empty thinking — verify no events
  - [ ] Test cancelled context — verify no events and no error

- [ ] Task 9: Handler-level integration tests (AC: #1, #2, #3, #4, #5)
  - [ ] Test full SSE sequence with `forwardedProps.thinkingEffort: "high"` and thinking content present
  - [ ] Test no `REASONING_*` events when `thinkingEffort` is absent
  - [ ] Test no `REASONING_*` events when LLM returns empty thinking despite effort being set
  - [ ] Test invalid `thinkingEffort` value defaults to off

- [ ] Task 10: Integration test with tool calls + thinking (AC: #6)
  - [ ] Test reasoning events emitted between tool iterations when thinking is active
  - [ ] Verify ordering: `REASONING_*` → `TOOL_CALL_*` → `REASONING_*` → `TEXT_MESSAGE_*`

## Technical Notes

- The `REASONING_MESSAGE_CHUNK` convenience event could simplify emission (auto start/end), but the explicit Start/Content/End pattern is clearer and matches the tool call event pattern already used.
- For multi-iteration tool loops, thinking needs to be emitted per-iteration (not just at the end). This requires a `MessageEventHandler`-based approach similar to `ToolCallEmitter`.
- Consider whether intermediate thinking (during tool iterations) should be emitted live or batched. Live emission is more aligned with the ag-ui event model.
- Changing `Chat()` return type is a breaking change for existing callers (CLI `chatLoop`). The CLI caller can simply ignore the `Thinking` field (it already prints thinking via `ConsoleUsageReporter`).

## Dependencies

- Story 1.2 (handler, SSE writer) — must be done
- Story 2.2 (ToolCallEmitter pattern to follow) — must be done
- Story 1.4 (context cancellation) — must be done
