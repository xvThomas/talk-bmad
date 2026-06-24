# Story 2.1: Boucle d'exécution d'outils MCP

Status: ready-for-dev

## Story

As an end client,
I want the assistant to call external tools (route calculation, weather) during a conversation,
so that I get answers that require real-time data or computation.

## Acceptance Criteria

1. Given the server is configured with one or more MCP servers, when the LLM response contains tool call requests, then the server executes tool calls against the configured MCP server(s) and tool results are fed back to the LLM as context for the next completion.
2. Given the LLM produces tool calls, when the loop iterates, then it continues until the LLM produces a final text response (max 5 iterations) and the final text is emitted as `TEXT_MESSAGE_START` → `TEXT_MESSAGE_CONTENT` → `TEXT_MESSAGE_END`.
3. Given the tool loop reaches 5 iterations without a final text response, when the limit is hit, then an AG-UI error event is emitted with the message: "Le traitement nécessite plus d'étapes. Dites « continue » pour poursuivre."
4. Given the tool loop has been exhausted, when intermediate messages have been produced, then all intermediate messages (tool calls + results) are persisted in the session store.
5. Given a previous request hit the 5-iteration limit, when a subsequent "continue" message from the user arrives with the same `threadId`, then it resumes with full context (prior tool calls and results loaded from store).

## Tasks / Subtasks

- [ ] Task 1: Create sentinel error for max iterations (AC: #3, #4)
  - [ ] In `talk/internal/domain/conversation.go`, replace the raw `fmt.Errorf("exceeded maximum tool call iterations (%d)")` with a typed sentinel `ErrMaxToolIterations` that can be detected with `errors.Is()`
  - [ ] Ensure the error is returned AFTER persisting all intermediate messages (current behavior already correct — messages are stored in the loop before the error return)
- [ ] Task 2: Map sentinel to user-friendly AG-UI message (AC: #3)
  - [ ] In `talk/cmd/cli/serve.go` `userFacingError()`, add a case for `domain.ErrMaxToolIterations` returning: `"Le traitement nécessite plus d'étapes. Dites « continue » pour poursuivre."`
- [ ] Task 3: Verify session resume after max iterations (AC: #5)
  - [ ] Write integration test: first request triggers tool calls → hits max iterations → second request with same threadId and "continue" message → verify LLM receives the full prior context
- [ ] Task 4: End-to-end test for tool execution through AG-UI (AC: #1, #2)
  - [ ] Write handler-level test: mock chatFn that simulates a tool-loop turn → returns final text → verify correct SSE event sequence (RUN_STARTED → TEXT_MESSAGE_* → RUN_FINISHED)
  - [ ] Write handler-level test: mock chatFn that returns the sentinel error → verify RUN_ERROR event contains the user-friendly message

## Dev Notes

### Critical Architecture Context

**The tool execution loop already exists and is fully functional.** The `ConversationManager.Chat()` in `talk/internal/domain/conversation.go` already implements:
- A loop iterating up to `maxToolCalls = 5` times
- LLM completion → tool call detection → `ToolExecutor.Execute()` → results fed back to LLM
- All messages (assistant tool calls, tool results) persisted via `messageHandler.HandleMessageEvent()`
- Turn event emission with full observability (timing, usage, tracing IDs)

**The chatFn wiring in `serve.go` already connects MCP tools:**
```go
manager := domain.NewConversationManager(domain.ConversationManagerConfig{
    Tools:              mcpManager.Tools,  // Already wired!
    MaxConcurrentTools: cfg.ToolsMaxConcurrent,
    // ...
})
```

**What is NOT yet correct:** The "exceeded max iterations" error is caught by the generic `default` case in `userFacingError()` → maps to "an unexpected error occurred" instead of the specified user-friendly message.

### Implementation Approach

This story is primarily about **error path refinement and verification**, not building new infrastructure:

1. **Minimal code change:** Add `ErrMaxToolIterations` sentinel, detect it in `userFacingError()`
2. **Verification tests:** Prove the existing tool loop works end-to-end through the HTTP handler layer
3. **Resume test:** Prove that after hitting the limit, re-posting with the same threadId provides full history context to the LLM

### Key Files to Modify

| File | Action | Purpose |
|------|--------|---------|
| `talk/internal/domain/conversation.go` | UPDATE | Replace raw error with sentinel `ErrMaxToolIterations` |
| `talk/internal/domain/conversation.go` | ADD sentinel | Define `ErrMaxToolIterations` next to existing `ErrSystemPrompt` (line 13) |
| `talk/cmd/cli/serve.go` | UPDATE | Add `ErrMaxToolIterations` case in `userFacingError()` |
| `talk/internal/agui/handler_test.go` | UPDATE | Add tests for tool loop success and max-iteration error |
| `talk/cmd/cli/serve_test.go` | UPDATE or CREATE | Test `userFacingError` mapping |

### Existing Code Behavior (MUST PRESERVE)

**`conversation.go` loop (lines ~170-221):**
- Messages stored INSIDE the loop before the error return → AC #4 is already satisfied
- `toolExecutor.Execute(ctx, turnID, response.ToolCalls)` handles both sequential and parallel tool execution
- Context propagation from `r.Context()` through to MCP tool calls already works (Story 1.4 verified this)

**`serve.go` chatFn:**
- Creates a NEW ConversationManager per request (per-request model resolution)
- BUT uses shared `messages` store (SQLite) and `browser` → session history is accessible across requests with the same threadId
- `extractUserInput()` gets the last user message content from AG-UI messages array

**Session resume mechanism:**
- `contextBuilder.BuildContextMessages(ctx, turnID)` loads prior messages from the store for the given session scope
- Session scope is `domain.NewSessionScope(threadID, "anonymous")` — keyed by threadId
- So a second request with the same threadId automatically gets the full history

### Testing Patterns (Follow Existing Conventions)

```go
// Existing pattern from handler_test.go:
chatFn := func(ctx context.Context, _ string, _ string, _ []types.Message) (string, error) {
    return "response", nil  // or return "", domain.ErrMaxToolIterations
}
handler := NewHandler(nil, chatFn, []string{"sonnet-4.6"})
```

For `userFacingError` testing, test the function directly:
```go
func Test_userFacingError_maxToolIterations(t *testing.T) {
    err := userFacingError(domain.ErrMaxToolIterations)
    want := "Le traitement nécessite plus d'étapes. Dites « continue » pour poursuivre."
    if err.Error() != want {
        t.Errorf("got %q, want %q", err.Error(), want)
    }
}
```

### Project Structure Notes

- `domain/errors.go` or inline in `conversation.go` — check if `errors.go` already exists. If not, a sentinel can be defined at top of `conversation.go` (keep to existing patterns).
- No new packages or modules needed.
- No new dependencies.

### Previous Story Intelligence (Story 1.4)

- `ctx.Err()` check after `chatFn` returns → any error from max iterations passes through cleanly (chatFn returns non-nil error, ctx.Err() is nil → error path executes)
- SSE write after RUN_STARTED will emit RUN_ERROR event for the max-iterations case
- Test patterns: cancelled context tests, `parseSSEEvents()` helper, model in forwardedProps format

### Cross-Story Dependencies

- **Story 2.2** (next) will add TOOL_CALL_START/ARGS/END events to the SSE stream — this story does NOT emit those events yet. Story 2.1 only ensures the tool loop works and the final response (or error) reaches the client.
- **Story 2.3** will add MCP server error handling — this story assumes MCP servers are reachable.

### References

- [Source: talk/internal/domain/conversation.go#L170-221] — existing tool loop
- [Source: talk/cmd/cli/serve.go#L89-131] — chatFn wiring with mcpManager.Tools
- [Source: talk/cmd/cli/serve.go#L216-240] — userFacingError switch
- [Source: AG-UI SDK events/run_events.go] — NewRunErrorEvent constructor
- [Source: talk/internal/agui/handler.go#L103-108] — error event emission
- [Source: _bmad-output/implementation-artifacts/spec-1-4-client-disconnection-cancellation.md] — previous story context

## Verification

**Commands:**

- `cd talk && go test ./internal/domain/ -run TestConversation -v` — expected: all conversation tests pass
- `cd talk && go test ./internal/agui/ -run TestHandler -v` — expected: all handler tests pass including new tool-loop tests
- `cd talk && go test ./cmd/cli/ -run TestUserFacingError -v` — expected: error mapping test passes
- `cd talk && go build ./cmd/cli/` — expected: compiles cleanly

## Dev Agent Record

### Agent Model Used

(to be filled by dev agent)

### Completion Notes List

(to be filled after implementation)

### File List

(to be filled after implementation)
