---
baseline_commit: dca536a3e4f796d98b7ad46e080e5225152aead0
---

# Story 1.5: Thinking/Reasoning via AG-UI

Status: done

## Story

As a frontend developer,
I want to optionally activate LLM thinking/reasoning via `forwardedProps.thinkingEffort` and receive the thinking output as AG-UI `REASONING_*` events,
so that my UI can display the model's chain-of-thought to the user.

## Context

- The CLI already supports thinking via `/thinking` command (`SetThinkingEffort`), and the `ConsoleUsageReporter` displays `messageEvent.Thinking` in the terminal.
- The ag-ui serve path creates a fresh `ConversationManager` per request but never calls `SetThinkingEffort` — thinking is always off.
- The AG-UI protocol defines `REASONING_*` event types. The Go Community SDK exposes constructors in `events/reasoning_events.go`: `NewReasoningStartEvent`, `NewReasoningMessageStartEvent`, `NewReasoningMessageContentEvent`, `NewReasoningMessageEndEvent`, `NewReasoningEndEvent`.
- Thinking content is already returned by Anthropic/OpenAI clients in `domain.Message.Thinking` (ephemeral, not persisted). It flows through `MessageEvent.Message.Thinking` to all `MessageEventHandler` instances in the pipeline.
- Post story 1.4.5: `AGUIEmitter` already handles `TEXT_MESSAGE_*` and `TOOL_CALL_*` events via `HandleMessageEvent` and `HandleToolCallStart/End`. The reasoning emission fits naturally inside the existing `AGUIEmitter.HandleMessageEvent` — no new handler needed.
- `ChatFunc` signature is `func(ctx, threadID, modelAlias, messages, ChatOptions) error`. `ChatOptions` currently contains only `SSEWriter`.
- `serve.go` constructs a pipeline `{aguiEmitter, messages}` in the same phase. The `AGUIEmitter` already receives all `MessageEvent`s with `Message.Thinking` populated.

## Acceptance Criteria

1. **Given** a `POST /agent` request with `forwardedProps.thinkingEffort` set to `"low"`, `"medium"`, or `"high"`, **when** the LLM supports thinking, **then** reasoning is activated for that request with the corresponding effort level, **and** the thinking output is emitted as AG-UI `REASONING_*` events before `TEXT_MESSAGE_*` events.

2. **Given** a `POST /agent` request without `forwardedProps.thinkingEffort` (or set to `"off"` or empty), **when** the request is processed, **then** thinking is not activated (backward compatible, same behavior as today).

3. **Given** a `POST /agent` request with an invalid `thinkingEffort` value (e.g. `"extreme"`), **when** the request is processed, **then** the value is ignored and thinking defaults to off (no error emitted).

4. **Given** thinking is activated and the LLM returns thinking content, **when** the SSE stream is built, **then** the event sequence is: `REASONING_START` → `REASONING_MESSAGE_START` (role=`"reasoning"`) → `REASONING_MESSAGE_CONTENT` (delta=thinking content) → `REASONING_MESSAGE_END` → `REASONING_END` → `TEXT_MESSAGE_START` → `TEXT_MESSAGE_CONTENT` → `TEXT_MESSAGE_END`.

5. **Given** thinking is activated and the LLM returns no thinking content (model didn't produce any), **when** the SSE stream is built, **then** no `REASONING_*` events are emitted.

6. **Given** the tool loop executes multiple LLM calls (tool_result iterations), **when** each intermediate LLM call returns thinking content, **then** reasoning events are emitted for each iteration (before the tool call events of the next iteration).

7. **Given** the client disconnects during reasoning event emission, **when** the context is cancelled, **then** no further events are emitted and the handler exits cleanly.

## Tasks / Subtasks

- [ ] Task 1: Add `ThinkingEffort` to `ChatOptions` and extract from `forwardedProps` (AC: #1, #2, #3)
  - [ ] In `talk/internal/agui/handler.go`, add `ThinkingEffort domain.ThinkingEffort` field to `ChatOptions` struct
  - [ ] Add `extractThinkingEffort(forwardedProps any) domain.ThinkingEffort` function
  - [ ] Valid values: `"low"`, `"medium"`, `"high"` → corresponding `domain.ThinkingEffort`; anything else → `""` (zero value = off)
  - [ ] In `ServeHTTP`, call `extractThinkingEffort(input.ForwardedProps)` and pass result in `ChatOptions`
  - [ ] Unit tests for all valid values, empty, missing, invalid, nil forwardedProps

- [ ] Task 2: Wire `thinkingEffort` into `ConversationManager` from serve.go (AC: #1, #2)
  - [ ] In `talk/cmd/cli/serve.go` `chatFn`, read `opts.ThinkingEffort` and call `manager.SetThinkingEffort(opts.ThinkingEffort)` before `manager.Chat()`
  - [ ] When `ThinkingEffort` is zero value (empty string), `SetThinkingEffort` is a no-op (thinking stays off)

- [ ] Task 3: Add reasoning event emission in `AGUIEmitter.HandleMessageEvent` (AC: #4, #5, #6, #7)
  - [ ] In `talk/internal/agui/emitter.go`, modify `HandleMessageEvent`:
    - Before the existing TEXT_MESSAGE logic, check `event.Message.Thinking != ""`
    - If thinking is present, emit the 5-event reasoning sequence via `e.writeEvent`:
      `NewReasoningStartEvent(reasoningID)` → `NewReasoningMessageStartEvent(reasoningID, "reasoning")` → `NewReasoningMessageContentEvent(reasoningID, thinking)` → `NewReasoningMessageEndEvent(reasoningID)` → `NewReasoningEndEvent(reasoningID)`
    - Generate a unique `reasoningID` (uuid) separate from the text message ID
    - If any write returns an error (client disconnect), return immediately (existing `writeEvent` best-effort policy applies)
  - [ ] Reasoning events are emitted for ALL assistant messages that have thinking content — including intermediate messages with tool calls (AC #6)
  - [ ] The existing TEXT_MESSAGE guard (`len(ToolCalls) == 0 && Content != ""`) still controls text emission — reasoning and text emission are independent filters

- [ ] Task 4: Unit tests for reasoning emission in `AGUIEmitter` (AC: #4, #5, #7)
  - [ ] Test `HandleMessageEvent` with assistant message + `Thinking` set + no tool calls → verify REASONING*\* then TEXT_MESSAGE*\* sequence
  - [ ] Test `HandleMessageEvent` with assistant message + `Thinking` set + tool calls present → verify REASONING*\* emitted, no TEXT_MESSAGE*\*
  - [ ] Test `HandleMessageEvent` with assistant message + empty `Thinking` → verify no REASONING\_\* events
  - [ ] Test `HandleMessageEvent` with user message + `Thinking` set → verify no events (Role filter)
  - [ ] Test cancelled context during reasoning emission → verify partial write stops, no error returned

- [ ] Task 5: Handler-level integration tests (AC: #1, #2, #3, #4, #5)
  - [ ] Test full SSE sequence with `forwardedProps.thinkingEffort: "high"` and thinking content present
  - [ ] Test no `REASONING_*` events when `thinkingEffort` is absent
  - [ ] Test no `REASONING_*` events when LLM returns empty thinking despite effort being set
  - [ ] Test invalid `thinkingEffort` value defaults to off

- [ ] Task 6: Integration test with tool calls + thinking (AC: #6)
  - [ ] Test reasoning events emitted for intermediate iterations when thinking is active
  - [ ] Verify ordering: `REASONING_*` → `TOOL_CALL_START/ARGS/END` → `REASONING_*` → `TEXT_MESSAGE_*`

### Review Findings

- [x] [Review][Patch] Replace hard-coded AG-UI event type strings in reasoning tests with SDK constants to reduce brittleness across protocol/SDK evolution [talk/internal/agui/emitter_test.go:254]

## Technical Notes

- **No new handler, no new file**: The reasoning logic is added directly to `AGUIEmitter.HandleMessageEvent`. This is the simplest approach because the `AGUIEmitter` already receives all `MessageEvent`s and already has the `SSEWriter` reference.
- **Independent filters**: Reasoning emission checks `event.Message.Thinking != ""` (any assistant message). Text emission checks `len(ToolCalls) == 0 && Content != ""` (final message only). Both can fire on the same event (final message with thinking + content).
- **Ordering within a single `HandleMessageEvent` call**: reasoning events are emitted BEFORE text events in the same method call. This guarantees AC #4 ordering.
- **Multi-iteration ordering**: `HandleMessageEvent` is called inside `Chat()` for each LLM response. For intermediate responses (with tool calls), reasoning fires → then tool execution dispatches `HandleToolCallStart/End`. This naturally produces: `REASONING_*` → `TOOL_CALL_*` per iteration.
- **`ChatOptions.ThinkingEffort`**: passed from handler to `chatFn`, then `chatFn` calls `manager.SetThinkingEffort()`. Same pattern as the CLI's `/thinking` command — no architectural change.
- **Best-effort SSE writes**: `AGUIEmitter.writeEvent` already handles context cancellation and returns errors. The reasoning emission follows the same pattern — if a write fails, stop emitting (don't crash the pipeline).

## Dependencies

- Story 1.4.5 (unified `MessageEventHandler`, `AGUIEmitter`, `ChatOptions`) — must be done
