---
baseline_commit: 70992c4d1f5e4a7aaedc052126e01b43a5f72e1e
---

# Story 2.3: Composition des handlers ToolCall et Message dans ConversationManager

Status: draft

## Story

As a backend developer,
I want ConversationManager to compose ToolCallHandler and EventHandlers when both are provided,
so that tool-call observability is not lost and all configured handlers receive expected events.

## Acceptance Criteria

1. Given both `ToolCallHandler` and `EventHandlers` are provided in config, when tool calls are executed, then both handler paths receive tool lifecycle events.
2. Given only `EventHandlers` is provided and it implements `ToolCallEventHandler`, behavior remains unchanged (backward compatibility).
3. Given only `ToolCallHandler` is provided, tool lifecycle events are still emitted correctly.
4. Given one handler fails during tool event dispatch, failure strategy is deterministic and tested (either fail-fast or aggregate, but documented).
5. No regression on existing AG-UI tool-call event flow and message persistence flow.

## Tasks / Subtasks

- [ ] Task 1: Define composition strategy in `ConversationManager` config resolution (AC: #1, #2, #3)
  - [ ] In `talk/internal/domain/conversation.go`, replace current precedence logic with explicit composition when both handlers are available
  - [ ] Preserve current behavior when only one handler path exists

- [ ] Task 2: Implement a composite `ToolCallEventHandler` fan-out (AC: #1, #4)
  - [ ] Add composite handler in `talk/internal/domain/usage.go` (or dedicated file) that dispatches to multiple `ToolCallEventHandler` implementations
  - [ ] Keep dispatch order deterministic and documented

- [ ] Task 3: Define and implement error propagation semantics (AC: #4)
  - [ ] Decide fail-fast vs aggregated errors for fan-out dispatch
  - [ ] Document behavior in code comments and ensure consistency for start/end events

- [ ] Task 4: Update wiring and compatibility paths (AC: #1, #2, #3, #5)
  - [ ] Validate `talk/cmd/cli/serve.go` wiring still injects AG-UI tool handler and message store handlers correctly
  - [ ] Ensure no regression in existing message event persistence flow

- [ ] Task 5: Add domain-level tests for handler composition (AC: #1, #2, #3, #4)
  - [ ] Add tests covering both handlers active (both receive start/end)
  - [ ] Add tests covering only message handler path
  - [ ] Add tests covering only explicit tool handler path
  - [ ] Add tests for handler failure semantics and propagation

- [ ] Task 6: Add AG-UI non-regression integration tests (AC: #5)
  - [ ] In `talk/internal/agui/handler_test.go`, verify tool-call SSE flow remains correct when composed handlers are active
  - [ ] Verify message persistence side effects remain intact

- [ ] Task 7: Validation (AC: #1-#5)
  - [ ] `go test ./internal/domain/ -count=1`
  - [ ] `go test ./internal/agui/ -count=1`
  - [ ] `go test ./... -short`

## Definition of Done

1. All acceptance criteria are covered by automated tests.
2. Backward compatibility is preserved for existing single-handler configurations.
3. Error behavior for composed tool handlers is explicit, deterministic, and documented.
4. No regression in AG-UI tool events or message persistence flows.

## Notes

This story is created from deferred review work linked to Story 2.2 and intentionally separates architecture-level handler composition from immediate tool-event reliability patches.
