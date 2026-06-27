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
- The `MessageEventHandler` mechanism already propagates thinking content to all registered handlers (store, reporter). A `ReasoningEmitter` can be wired the same way as the existing `ToolCallEmitter` pattern — no change to `ChatFunc` or `Chat()` signatures needed.

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

- [ ] Task 2: Wire `thinkingEffort` into `ConversationManager` from serve.go (AC: #1, #2)
  - [ ] In `talk/cmd/cli/serve.go` `chatFn`, extract `thinkingEffort` from `forwardedProps` and call `manager.SetThinkingEffort(thinkingEffort)` before `manager.Chat()`
  - [ ] No change to `ChatFunc` signature — `thinkingEffort` is set on the manager directly (same pattern as the CLI `/thinking` command)

- [ ] Task 3: Create `ReasoningEmitter` as a `MessageEventHandler` (AC: #4, #5, #6, #7)
  - [ ] In `talk/internal/agui/`, create `reasoning_emitter.go` with `ReasoningEmitter` struct
  - [ ] `ReasoningEmitter` implements `domain.MessageEventHandler`
  - [ ] Constructor: `NewReasoningEmitter(sse *SSEWriter, log *slog.Logger) *ReasoningEmitter`
  - [ ] In `HandleMessageEvent`: if `event.Message.Thinking != ""`, emit the 5-event reasoning sequence via `SSEWriter`
  - [ ] Event sequence: `NewReasoningStartEvent(messageID)` → `NewReasoningMessageStartEvent(messageID, "reasoning")` → `NewReasoningMessageContentEvent(messageID, thinking)` → `NewReasoningMessageEndEvent(messageID)` → `NewReasoningEndEvent(messageID)`
  - [ ] Generate a unique `messageID` per reasoning emission (separate from the text message ID)
  - [ ] Check `ctx.Err()` before each write — if cancelled, return nil immediately
  - [ ] If `event.Message.Thinking` is empty, no-op (return nil)
  - [ ] `HandleTurnEvent`: no-op (return nil)

- [ ] Task 4: Register `ReasoningEmitter` in the event handler pipeline (AC: #4, #5, #6)
  - [ ] In `talk/cmd/cli/serve.go`, instantiate `ReasoningEmitter` per request (needs the `SSEWriter`)
  - [ ] Add it to the `MessageEventHandlers` phases when building the `ConversationManager`
  - [ ] Place it in a phase that executes before the store handler (reasoning events must be emitted to SSE before the response is finalized)
  - [ ] This follows the same pattern as `ToolCallEmitter` which is already passed into the manager's pipeline

- [ ] Task 5: Ensure correct event ordering in the SSE stream (AC: #4, #6)
  - [ ] The `ReasoningEmitter` fires during `HandleMessageEvent` — this happens *inside* the `Chat()` loop, so reasoning events are emitted live per LLM iteration
  - [ ] For intermediate iterations (with tool calls): reasoning events are emitted before tool call events (ToolCallEmitter fires separately)
  - [ ] For the final iteration (text response): reasoning events are emitted before the handler writes `TEXT_MESSAGE_*` events
  - [ ] Verify no change needed to the handler's post-`chatFn` code — `TEXT_MESSAGE_*` events are emitted after `Chat()` returns, which is after all `HandleMessageEvent` calls have completed

- [ ] Task 6: Unit tests for `ReasoningEmitter` (AC: #4, #5, #7)
  - [ ] Test `HandleMessageEvent` with non-empty `Message.Thinking` — verify 5-event sequence written to SSEWriter
  - [ ] Test `HandleMessageEvent` with empty `Message.Thinking` — verify no events
  - [ ] Test `HandleMessageEvent` with cancelled context — verify no events and no error
  - [ ] Test `HandleTurnEvent` — verify no-op

- [ ] Task 7: Handler-level integration tests (AC: #1, #2, #3, #4, #5)
  - [ ] Test full SSE sequence with `forwardedProps.thinkingEffort: "high"` and thinking content present
  - [ ] Test no `REASONING_*` events when `thinkingEffort` is absent
  - [ ] Test no `REASONING_*` events when LLM returns empty thinking despite effort being set
  - [ ] Test invalid `thinkingEffort` value defaults to off

- [ ] Task 8: Integration test with tool calls + thinking (AC: #6)
  - [ ] Test reasoning events emitted between tool iterations when thinking is active
  - [ ] Verify ordering: `REASONING_*` → `TOOL_CALL_*` → `REASONING_*` → `TEXT_MESSAGE_*`

## Technical Notes

- **No signature changes required**: `ChatFunc` remains `(string, error)` and `Chat()` remains `(string, error)`. The thinking content is already propagated through `MessageEvent.Message.Thinking` to all registered `MessageEventHandler` instances — the `ReasoningEmitter` receives it via the existing pipeline.
- The `REASONING_MESSAGE_CHUNK` convenience event could simplify emission (auto start/end), but the explicit Start/Content/End pattern is clearer and matches the tool call event pattern already used.
- For multi-iteration tool loops, thinking is emitted per-iteration naturally because `HandleMessageEvent` is called at each loop iteration inside `Chat()`. The `ReasoningEmitter` fires live — no batching needed.
- This approach mirrors `ToolCallEmitter` which also emits SSE events from within the `Chat()` execution loop without changing its return type.
- The `ReasoningEmitter` must be instantiated per-request (it holds a reference to the request's `SSEWriter`), same as `ToolCallEmitter`.

## Dependencies

- Story 1.2 (handler, SSE writer) — must be done
- Story 2.2 (ToolCallEmitter pattern to follow) — must be done
- Story 1.4 (context cancellation) — must be done
