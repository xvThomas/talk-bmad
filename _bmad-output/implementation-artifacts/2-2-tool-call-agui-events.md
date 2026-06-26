---
baseline_commit: 70992c4d1f5e4a7aaedc052126e01b43a5f72e1e
---

# Story 2.2: Émission des événements tool call AG-UI

Status: done

## Story

As a frontend developer,
I want to receive AG-UI tool call events during execution,
so that my UI can show the user what tools are being used (loading indicators, tool names).

## Acceptance Criteria

1. Given the LLM requests a tool call, when the server begins tool execution, then a `TOOL_CALL_START` event is emitted with the tool name and call ID, a `TOOL_CALL_ARGS` event is emitted with the serialized tool input arguments, and after execution, a `TOOL_CALL_END` event is emitted with the tool result. All events are flushed immediately to the SSE stream (no buffering).
2. Given the LLM requests multiple tool calls in one iteration, when tools are executed, then each tool call produces its own START/ARGS/END event triplet.
3. Given the tool loop iterates multiple times (LLM calls tools, gets results, calls more tools), when intermediate tool calls are executed, then each iteration's tool calls also produce START/ARGS/END events.
4. Given the client disconnects during tool execution, when the context is cancelled, then no further tool call events are emitted and the handler exits cleanly (existing Story 1.4 behavior preserved).

## Tasks / Subtasks

- [x] Task 1: Extend `ToolCallEventHandler` interface with symmetric lifecycle (AC: #1)
  - [x] In `talk/internal/domain/usage.go`, rename `HandleToolCallEvent` → `HandleToolCallStart` on the `ToolCallEventHandler` interface
  - [x] Add `HandleToolCallEnd(ctx context.Context, event ToolCallEndEvent) error` to the interface
  - [x] Define `ToolCallEndEvent` struct: `TurnID string`, `ToolCall ToolCall`, `Result ToolResult`, `StartedAt time.Time`, `EndedAt time.Time`
  - [x] Update `MessageEventHandlers.HandleToolCallEvent` → rename to `HandleToolCallStart` and add `HandleToolCallEnd` dispatch (same type-assertion pattern)
  - [x] Update existing implementors: `ConsoleUsageReporter` (rename method + add no-op `HandleToolCallEnd`), test `recordingToolCallHandler` (rename + add recording for end events)
- [x] Task 2: Emit `HandleToolCallEnd` from ToolExecutor after each tool execution (AC: #1, #2, #3)
  - [x] In `talk/internal/domain/tool_executor.go`, rename `HandleToolCallEvent` calls → `HandleToolCallStart`
  - [x] After `ExecuteTool()` returns (both sequential and parallel paths), call `e.toolHandler.HandleToolCallEnd(ctx, ToolCallEndEvent{TurnID, ToolCall, Result, StartedAt, EndedAt})`
  - [x] Ensure parallel path handles errors from `HandleToolCallEnd` the same way as `HandleToolCallStart`
- [x] Task 3: Create AG-UI tool call event emitter (AC: #1)
  - [x] In `talk/internal/agui/`, create `tool_events.go` with `ToolCallEmitter` struct holding `*SSEWriter` and `*slog.Logger`
  - [x] `ToolCallEmitter` implements `domain.ToolCallEventHandler` only (not `MessageEventHandler`)
  - [x] `HandleToolCallStart` emits `TOOL_CALL_START` (toolCallID, toolCallName) then `TOOL_CALL_ARGS` (toolCallID, JSON-serialized Input)
  - [x] `HandleToolCallEnd` emits `TOOL_CALL_END` (toolCallID)
  - [x] Each SSE write checks `ctx.Err()` before emitting — if cancelled, return nil immediately
  - [x] Compile-time check: `var _ domain.ToolCallEventHandler = (*ToolCallEmitter)(nil)`
- [x] Task 4: Modify ChatFunc signature to accept an event emitter (AC: #1, #2, #3)
  - [x] In `talk/internal/agui/handler.go`, change `ChatFunc` signature to accept a `domain.ToolCallEventHandler` parameter: `func(ctx, threadID, modelAlias string, messages []types.Message, toolHandler domain.ToolCallEventHandler) (string, error)`
  - [x] In `ServeHTTP`, create a `ToolCallEmitter` with the SSE writer and pass it to `chatFn`
  - [x] Update all existing `chatFn` call sites (serve.go and tests) to match the new signature
- [x] Task 5: Wire emitter into ConversationManager via EventHandlers (AC: #1, #2, #3)
  - [x] In `talk/cmd/cli/serve.go`, update the `chatFn` closure to accept the `toolHandler` parameter
  - [x] Pass the `ToolCallEmitter` directly via a new `ToolCallEventHandler` field on `ConversationManagerConfig` (simpler wiring, avoids wrapper)
  - [x] Pass the assembled config to `ConversationManager`
- [x] Task 6: Unit tests for ToolCallEmitter (AC: #1, #2)
  - [x] In `talk/internal/agui/tool_events_test.go`, test that `HandleToolCallStart` emits TOOL_CALL_START + TOOL_CALL_ARGS events with correct fields
  - [x] Test that `HandleToolCallEnd` emits TOOL_CALL_END with the correct toolCallID
  - [x] Test with cancelled context — verify no events emitted and no error returned
  - [x] Test that `Input` map is correctly JSON-serialized in the TOOL_CALL_ARGS delta
- [x] Task 7: Update existing ToolExecutor tests (AC: #1, #2, #3)
  - [x] Rename `recordingToolCallHandler.HandleToolCallEvent` → `HandleToolCallStart`
  - [x] Add `HandleToolCallEnd` to `recordingToolCallHandler` that records end events
  - [x] Add test asserting both start AND end events are emitted for each tool call in sequential mode
  - [x] Add test asserting both start AND end events are emitted for each tool call in parallel mode
- [x] Task 8: Handler-level integration tests (AC: #1, #2, #3, #4)
  - [x] In `talk/internal/agui/handler_test.go`, add test where chatFn calls the `toolHandler` (HandleToolCallStart + HandleToolCallEnd) and verify the full SSE event sequence includes tool call events between RUN_STARTED and TEXT_MESSAGE events
  - [x] Test multiple tool calls — verify each produces its own START/ARGS/END triplet
  - [x] Test with cancelled context during tool event emission — verify handler exits cleanly

### Review Findings

- [x] [Review][Patch] Add mutex serialization in `SSEWriter.WriteEvent` to prevent concurrent SSE interleaving on a single stream [talk/internal/agui/sse.go:39]
- [x] [Review][Patch] On any tool execution failure, keep flow alive and emit `TOOL_CALL_END` + a tool error result (`TOOL_RESULT` in error state) with a single generic kind (no business/technical split yet) [talk/internal/domain/tool_executor.go:132]
- [x] [Review][Patch] Migrate parallel tool execution to `sync.WaitGroup.Go` (project Go 1.25 rule) in executor [talk/internal/domain/tool_executor.go:114]
- [x] [Review][Patch] Add handler-level integration tests for multi-tool and multi-iteration SSE tool-call sequences [talk/internal/agui/handler_test.go:357]
- [x] [Review][Patch] Add explicit assertions for tool end events (`HandleToolCallEnd`) in executor tests (count, toolCallID, timing/order) [talk/internal/domain/tool_executor_test.go:370]
- [x] [Review][Defer] ConversationManager explicit ToolCallHandler overrides EventHandlers ToolCallEventHandler instead of composing both [talk/internal/domain/conversation.go:59] — deferred, pre-existing

## Dev Notes

### Architecture Decision: Symmetric Tool Call Lifecycle in ToolExecutor

The core insight is that the `ToolExecutor` is the single place that knows the full lifecycle of each individual tool call (start → execute → end). Anchoring both START and END events here provides:

1. **Symmetry**: The same component that emits START also emits END — no split responsibility
2. **Precision**: END is emitted immediately after each tool finishes, not in a batch after all tools return
3. **Locality**: The handler receives `ToolCall`, `ToolResult`, and timing data directly — no need to parse composite `Message` structs to extract tool call IDs
4. **Future-proof**: If `Execute()` evolves to stream results (channel-based), the emit points stay the same

**Flow (per tool call, symmetric):**
```
ToolExecutor.executeSequential():
  for each call:
    ├── toolHandler.HandleToolCallStart(ToolCallEvent{ToolCall: call})     ← TOOL_CALL_START + TOOL_CALL_ARGS
    ├── ExecuteTool(ctx, call)                                             ← actual MCP call
    └── toolHandler.HandleToolCallEnd(ToolCallEndEvent{ToolCall, Result})  ← TOOL_CALL_END
```

**Why this approach (vs HandleMessageEvent-based TOOL_CALL_END):**
- ✅ Symmetric: same interface owns the full lifecycle (no split between ToolExecutor and ConversationManager)
- ✅ Granular: END is emitted per-tool immediately, not after all tools complete as a batch
- ✅ Clean data: `ToolCallEndEvent` carries `ToolCall.ID` directly — no parsing `Message.ToolCalls[0].ID`
- ✅ Separation of concerns: `HandleMessageEvent(CallKindToolResult)` in conversation.go remains purely for message store/observability
- ✅ Idiomatic Go: optional interface with type assertion — existing pattern in the codebase
- ❌ Requires modifying `ToolCallEventHandler` interface (breaking change on 2 implementors: `ConsoleUsageReporter` + test mock)
- ❌ Requires adding `HandleToolCallEnd` call in `tool_executor.go` (minor)

**Impact analysis on existing implementors:**
- `ConsoleUsageReporter`: rename `HandleToolCallEvent` → `HandleToolCallStart`, add no-op `HandleToolCallEnd`
- `recordingToolCallHandler` (test): rename + add recording for end events

### AG-UI SDK Event Constructors (EXACT signatures)

```go
// Source: github.com/ag-ui-protocol/ag-ui/sdks/community/go/pkg/core/events/tool_events.go

func NewToolCallStartEvent(toolCallID, toolCallName string, options ...ToolCallStartOption) *ToolCallStartEvent
// Fields: ToolCallID string, ToolCallName string, ParentMessageID *string (optional)

func NewToolCallArgsEvent(toolCallID, delta string) *ToolCallArgsEvent
// Fields: ToolCallID string, Delta string (JSON-serialized arguments)

func NewToolCallEndEvent(toolCallID string) *ToolCallEndEvent
// Fields: ToolCallID string
```

Event type constants:
```go
EventTypeToolCallStart  EventType = "TOOL_CALL_START"
EventTypeToolCallArgs   EventType = "TOOL_CALL_ARGS"
EventTypeToolCallEnd    EventType = "TOOL_CALL_END"
```

### Domain Types

```go
// Existing (Source: talk/internal/domain/message.go)
type ToolCall struct {
    ID    string         // Tool call ID (generated by LLM, e.g. "toolu_abc123")
    Name  string         // Tool name (matches registered MCP tool name)
    Input map[string]any // Arguments as map — must be json.Marshal'd for TOOL_CALL_ARGS delta
}

type ToolResult struct {
    ToolCallID string // Correlates with ToolCall.ID
    Content    string // JSON-serialized tool output
}

// Existing (to rename: HandleToolCallEvent → HandleToolCallStart)
type ToolCallEvent struct {
    TurnID    string
    ToolCall  ToolCall
    StartedAt time.Time
}

// NEW
type ToolCallEndEvent struct {
    TurnID    string
    ToolCall  ToolCall
    Result    ToolResult
    StartedAt time.Time
    EndedAt   time.Time
}
```

### Updated ToolCallEventHandler Interface

```go
// ToolCallEventHandler receives tool call lifecycle events.
// This interface is optional: only interested handlers need to implement it.
type ToolCallEventHandler interface {
    HandleToolCallStart(ctx context.Context, event ToolCallEvent) error
    HandleToolCallEnd(ctx context.Context, event ToolCallEndEvent) error
}
```

### ToolExecutor Changes (tool_executor.go)

Sequential path (lines ~65-90):
```go
for _, call := range calls {
    startedAt := time.Now()
    if e.toolHandler != nil {
        if err := e.toolHandler.HandleToolCallStart(ctx, ToolCallEvent{
            TurnID: turnID, ToolCall: call, StartedAt: startedAt,
        }); err != nil {
            return nil, fmt.Errorf("handling tool call start: %w", err)
        }
    }
    result, err := e.ExecuteTool(ctx, call)
    endedAt := time.Now()
    if err != nil {
        return nil, err
    }
    if e.toolHandler != nil {
        if err := e.toolHandler.HandleToolCallEnd(ctx, ToolCallEndEvent{
            TurnID: turnID, ToolCall: call, Result: result,
            StartedAt: startedAt, EndedAt: endedAt,
        }); err != nil {
            return nil, fmt.Errorf("handling tool call end: %w", err)
        }
    }
    // ... build ToolExecutionResult as before
}
```

Same pattern in the parallel path goroutines.

### ToolCallEmitter (AG-UI layer — implements only ToolCallEventHandler)

```go
type ToolCallEmitter struct {
    sse    *SSEWriter
    logger *slog.Logger
}

func (e *ToolCallEmitter) HandleToolCallStart(ctx context.Context, event domain.ToolCallEvent) error {
    if ctx.Err() != nil {
        return nil
    }
    if err := e.sse.WriteEvent(ctx, events.NewToolCallStartEvent(event.ToolCall.ID, event.ToolCall.Name)); err != nil {
        return err
    }
    argsJSON, _ := json.Marshal(event.ToolCall.Input)
    return e.sse.WriteEvent(ctx, events.NewToolCallArgsEvent(event.ToolCall.ID, string(argsJSON)))
}

func (e *ToolCallEmitter) HandleToolCallEnd(ctx context.Context, event domain.ToolCallEndEvent) error {
    if ctx.Err() != nil {
        return nil
    }
    return e.sse.WriteEvent(ctx, events.NewToolCallEndEvent(event.ToolCall.ID))
}
```

```go
type ToolCallEmitter struct {
    sse *SSEWriter
    log *slog.Logger
}

var _ domain.MessageEventHandler = (*ToolCallEmitter)(nil)
var _ domain.ToolCallEventHandler = (*ToolCallEmitter)(nil)

// HandleToolCallEvent — called BEFORE tool execution (from ToolExecutor)
func (e *ToolCallEmitter) HandleToolCallEvent(ctx context.Context, event domain.ToolCallEvent) error {
    if ctx.Err() != nil {
        return nil
    }
    // Emit TOOL_CALL_START
    if err := e.sse.WriteEvent(ctx, events.NewToolCallStartEvent(event.ToolCall.ID, event.ToolCall.Name)); err != nil {
        return nil  // Don't fail the tool execution if SSE write fails
    }
    // Emit TOOL_CALL_ARGS with JSON-serialized input
    argsJSON, _ := json.Marshal(event.ToolCall.Input)
    _ = e.sse.WriteEvent(ctx, events.NewToolCallArgsEvent(event.ToolCall.ID, string(argsJSON)))
    return nil
}

// HandleMessageEvent — called AFTER tool execution when Kind == CallKindToolResult
func (e *ToolCallEmitter) HandleMessageEvent(ctx context.Context, event domain.MessageEvent) error {
    if event.Kind != domain.CallKindToolResult || len(event.Message.ToolCalls) == 0 {
        return nil
    }
    if ctx.Err() != nil {
        return nil
    }
    _ = e.sse.WriteEvent(ctx, events.NewToolCallEndEvent(event.Message.ToolCalls[0].ID))
    return nil
}

// HandleTurnEvent — no-op for SSE emission
func (e *ToolCallEmitter) HandleTurnEvent(_ context.Context, _ domain.TurnEvent) error { return nil }
```

### Current serve.go EventHandlers Wiring (MUST UPDATE)

Currently in `serve.go:108`:
```go
EventHandlers: messages,  // Just the SQLite store (MessageEventHandler only)
```

Must change to:
```go
handlers := domain.NewMessageEventHandlers([][]domain.MessageEventHandler{
    {messages},          // Phase 1: persist messages
    {toolCallEmitter},   // Phase 2: emit SSE events
})
// ...
EventHandlers: handlers,
```

This mirrors the CLI pattern in `main.go:126-129`.

### Testing Patterns (Follow Existing Conventions)

**ToolCallEmitter unit test** — use httptest.ResponseRecorder with SSE:
```go
func TestToolCallEmitter_HandleToolCallEvent(t *testing.T) {
    rec := httptest.NewRecorder()
    sse, _ := NewSSEWriter(rec, nil)
    emitter := NewToolCallEmitter(sse, nil)

    err := emitter.HandleToolCallEvent(context.Background(), domain.ToolCallEvent{
        ToolCall: domain.ToolCall{ID: "call_1", Name: "weather", Input: map[string]any{"city": "Paris"}},
    })
    // Parse SSE events, verify TOOL_CALL_START + TOOL_CALL_ARGS
}
```

**Handler integration test** — chatFn that simulates tool events:
```go
chatFn := func(ctx context.Context, _ string, _ string, _ []types.Message, toolHandler domain.MessageEventHandler) (string, error) {
    // Simulate pre-execution event (from ToolExecutor)
    if h, ok := toolHandler.(domain.ToolCallEventHandler); ok {
        h.HandleToolCallEvent(ctx, domain.ToolCallEvent{
            ToolCall: domain.ToolCall{ID: "call_1", Name: "weather", Input: map[string]any{"city": "Paris"}},
        })
    }
    // Simulate post-execution event (from ConversationManager loop)
    toolHandler.HandleMessageEvent(ctx, domain.MessageEvent{
        Message: domain.Message{
            Role:        domain.RoleTool,
            ToolCalls:   []domain.ToolCall{{ID: "call_1", Name: "weather"}},
            ToolResults: []domain.ToolResult{{ToolCallID: "call_1", Content: `{"temp":22}`}},
        },
        Kind: domain.CallKindToolResult,
    })
    return "The weather in Paris is 22°C.", nil
}
```

### Project Structure Notes

- `talk/internal/agui/tool_events.go` — NEW file for `ToolCallEmitter`
- `talk/internal/agui/tool_events_test.go` — NEW file for emitter tests
- `talk/internal/agui/handler.go` — UPDATE `ChatFunc` signature
- `talk/internal/agui/handler_test.go` — UPDATE all existing tests for new ChatFunc signature + add new tests
- `talk/cmd/cli/serve.go` — UPDATE: change chatFn signature, wire `MessageEventHandlers` with emitter
- `talk/cmd/cli/serve_test.go` — UPDATE: adapt tests if chatFn signature changes

**No domain layer changes needed** — no modifications to `usage.go`, `tool_executor.go`, or `conversation.go`.

### Cross-Story Dependencies

- **Story 2.1** (done): Tool execution loop and sentinel error — completed, provides the foundation
- **Story 2.3** (next): MCP error handling — will use the same SSE event emission path for error events during tool execution
- **Story 1.4** (done): Client disconnection — cancellation behavior must be preserved through the tool event emission path

### Previous Story Intelligence (Story 2.1)

- `ErrMaxToolIterations` sentinel is defined and mapped in `userFacingError()`
- Tool loop exists in `conversation.go:134-225`, iterates up to 5 times
- `ToolCallEventHandler.HandleToolCallEvent()` already called before each tool execution in both sequential and parallel paths
- `HandleMessageEvent` with `Kind == CallKindToolResult` already called after each tool execution
- The `ConsoleUsageReporter` is the existing reference implementation of `ToolCallEventHandler`

### References

- [Source: talk/internal/domain/tool_executor.go#L64-80] — sequential execution with HandleToolCallEvent call
- [Source: talk/internal/domain/tool_executor.go#L100-120] — parallel execution with HandleToolCallEvent call
- [Source: talk/internal/domain/conversation.go#L210-219] — HandleMessageEvent with CallKindToolResult (TOOL_CALL_END trigger)
- [Source: talk/internal/domain/usage.go#L113-122] — ToolCallEvent struct and ToolCallEventHandler interface
- [Source: talk/internal/domain/usage.go#L156-165] — MessageEventHandlers.HandleToolCallEvent dispatch
- [Source: talk/internal/domain/conversation.go#L55-60] — ToolCallEventHandler extraction from EventHandlers
- [Source: talk/internal/usage/console.go#L51-58] — ConsoleUsageReporter as reference ToolCallEventHandler
- [Source: talk/cmd/cli/main.go#L126-129] — CLI EventHandlers wiring pattern (MessageEventHandlers with phases)
- [Source: talk/cmd/cli/serve.go#L108] — current serve.go EventHandlers wiring (bare messages store)
- [Source: AG-UI SDK events/tool_events.go] — NewToolCallStartEvent, NewToolCallArgsEvent, NewToolCallEndEvent constructors
- [Source: talk/internal/agui/handler.go#L26] — current ChatFunc signature
- [Source: talk/internal/agui/handler_test.go] — existing test patterns with parseSSEEvents and assertEventType helpers

## Verification

**Commands:**

- `cd talk && go test ./internal/agui/ -run TestToolCallEmitter -v` — expected: emitter unit tests pass
- `cd talk && go test ./internal/agui/ -run TestHandler -v` — expected: all handler tests pass including new tool call event tests
- `cd talk && go test ./cmd/cli/ -v` — expected: serve tests pass with updated chatFn signature
- `cd talk && go test ./... -count=1` — expected: full regression suite passes
- `cd talk && go build ./cmd/cli/` — expected: compiles cleanly

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
