---
baseline_commit: 70992c4d1f5e4a7aaedc052126e01b43a5f72e1e
---

# Story 2.3: Composition des handlers ToolCall et Message dans ConversationManager

Status: done

## Story

As a backend developer,
I want ConversationManager to use a unified `MessageEventHandler` contract for messages, turns, and tool lifecycle,
so that tool-call observability is preserved through a single deterministic handler pipeline.

## Acceptance Criteria

1. Given `EventHandlers` are provided in config and implement the unified `MessageEventHandler` interface, tool lifecycle events (`HandleToolCallStart`/`HandleToolCallEnd`) are dispatched through the same pipeline as message and turn events.
2. Given multiple handlers are composed through `MessageEventHandlers`, dispatch order and phase semantics remain deterministic and documented.
3. Given one handler fails during tool event dispatch, failure strategy is deterministic and tested (aggregate within phase, stop before next phase).
4. No regression on existing AG-UI tool-call event flow and message persistence flow.

## Tasks / Subtasks

- [x] Task 1: Adopt unified event contract in `ConversationManager` wiring (AC: #1)
  - [x] Route tool lifecycle dispatch through `MessageEventHandler` in `ConversationManager`/`ToolExecutor`
  - [x] Remove dependency on a separate `ToolCallHandler` config path

- [x] Task 2: Implement unified tool lifecycle dispatch (AC: #1, #2)
  - [x] Add `HandleToolCallStart` and `HandleToolCallEnd` to `MessageEventHandler`
  - [x] Dispatch both methods in phased `MessageEventHandlers` execution

- [x] Task 3: Define and implement error propagation semantics (AC: #3)
  - [x] Keep deterministic phased dispatch with aggregated errors within each phase
  - [x] Preserve phase boundary fail behavior before proceeding to subsequent phases

- [x] Task 4: Update wiring and compatibility paths (AC: #1, #4)
  - [x] Validate `talk/cmd/cli/serve.go` wiring still injects AG-UI and persistence handlers correctly
  - [x] Ensure no regression in message persistence flow

- [x] Task 5: Add/maintain tests for unified handler composition (AC: #1, #2, #3)
  - [x] Cover tool start/end dispatch in sequential and parallel execution paths
  - [x] Cover failure semantics for handler dispatch

- [x] Task 6: Add AG-UI non-regression integration tests (AC: #4)
  - [x] Verify tool-call SSE flow remains correct with unified handlers
  - [x] Verify persistence side effects remain intact

- [x] Task 7: Validation (AC: #1-#4)
  - [x] `go test ./internal/domain/ -count=1`
  - [x] `go test ./internal/agui/ -count=1`
  - [x] `go test ./... -short`

### Review Findings

- [x] [Review][Decision] Story 2.3 ACs assumed dual handler inputs, but implementation moved to a unified `MessageEventHandler` model [talk/internal/domain/conversation.go:35]

  Detail: Resolved by decision. Recent implementation is authoritative; the story has been updated to the unified `MessageEventHandler` contract and no dual-path API restoration is required.

## Definition of Done

1. All acceptance criteria are covered by automated tests.
2. Unified event contract (`MessageEventHandler`) is explicit and documented across domain and AG-UI wiring.
3. Error behavior for phased handler execution is explicit, deterministic, and documented.
4. No regression in AG-UI tool events or message persistence flows.

## Notes

This story is created from deferred review work linked to Story 2.2 and intentionally separates architecture-level handler composition from immediate tool-event reliability patches.
