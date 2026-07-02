# Story 2.5: Résilience des connexions MCP après perte de réseau

Status: ready-for-dev

## Story

As a platform operator,
I want the backend to recover MCP tool connections automatically after a transient network interruption or when the host wakes from sleep,
so that MCP tool calls continue to work without restarting `talk serve`.

## Acceptance Criteria

1. Given a previously connected MCP server session is lost after host sleep or transient network loss,
   when the next tool call is attempted,
   then the backend detects the invalid MCP session and attempts to reconnect it automatically.
2. Given reconnection succeeds,
   when the tool call is retried,
   then the user-facing conversation continues normally and the frontend receives the expected AG-UI tool and text events.
3. Given reconnection fails after retry,
   when the session cannot be restored,
   then the frontend receives an AG-UI error event explaining that MCP tool execution is unavailable for this server,
   and the backend logs the reconnect failure with server identity and error details.
4. Given other requests are in flight during MCP reconnect,
   when reconnect attempts are ongoing,
   then those other requests are not blocked by the reconnection logic.

## Tasks / Subtasks

- [ ] Task 1: Extend `talk/internal/mcp/manager.go` to support reconnecting MCP sessions.
  - [ ] Subtask 1.1: Add a manager method such as `EnsureConnected(ctx, cfg ServerConfig) (*mcp.ClientSession, error)` or `Reconnect(ctx, id string) error`.
  - [ ] Subtask 1.2: Protect session state with a mutex if manager methods will be called concurrently from request handlers.
  - [ ] Subtask 1.3: Ensure `ConnectAll()` remains the initial bootstrap path but does not become the only path to establish a session.

- [ ] Task 2: Update `talk/internal/mcp/tool_adapter.go` to recover from invalid session errors.
  - [ ] Subtask 2.1: Detect failures from `CallTool(ctx, ...)` that indicate a broken session or transport failure.
  - [ ] Subtask 2.2: On such a failure, ask the manager to reconnect the session and retry the tool call once.
  - [ ] Subtask 2.3: If reconnect succeeds, continue tool execution; if it fails, return a clear error for AG-UI error event emission.

- [ ] Task 3: Add tests for MCP session recovery.
  - [ ] Subtask 3.1: Add a unit test for `mcp.Manager` reconnect logic using a stubbed registry and fake session transport.
  - [ ] Subtask 3.2: Add a test for `mcpToolAdapter` that simulates a first tool call failure and a successful reconnect retry.
  - [ ] Subtask 3.3: Add a failure test where reconnect cannot restore the session and the error is surfaced.

- [ ] Task 4: Add observability and logging.
  - [ ] Subtask 4.1: Log reconnect attempts and outcomes at `INFO` or `ERROR` level with server name, URL, and error.
  - [ ] Subtask 4.2: Keep the error path user-facing: MCP reconnect failure should map to a friendly AG-UI error event.

## Dev Notes

- `talk/internal/mcp/manager.go` currently builds all MCP sessions once at startup with `ConnectAll()` and keeps them in `m.sessions`.
- The current design does not recreate a session after a dropped connection; a wake-from-sleep or network transient can leave `*mcp.ClientSession` invalid.
- `mcp.StreamableClientTransport` already supports SSE reconnects, but the higher-level MCP session object and manager state may still need explicit session recreation.
- This story is specifically about backend-side MCP resilience and reconnection, not about frontend retry policies.
- Be careful with concurrent access: `mcpManager.Tools()` is read by request handlers while reconnect may mutate `m.sessions` or rebuild tool adapters.
- The reconnect path should be limited to one retry per failed tool call to avoid long hangs.
- Prefer a manager-level reconnect method over embedding reconnect logic directly in the tool adapter to keep responsibility separated.

### Project structure to touch

- `talk/internal/mcp/manager.go`
- `talk/internal/mcp/tool_adapter.go`
- `talk/internal/mcp/manager_test.go`
- new or updated tests in `talk/internal/mcp/tool_adapter_test.go` or similar
- possibly `talk/cmd/cli/serve.go` if the error mapping to AG-UI events must be refined

### References

- `talk-backend/talk/internal/mcp/manager.go` — session bootstrap and current connection lifecycle
- `talk-backend/talk/internal/mcp/tool_adapter.go` — MCP tool call execution path
- `talk-backend/talk/cmd/cli/serve.go` — backend error handling and AG-UI event emission
- `talk-backend/talk/internal/mcp/manager_test.go` — existing manager tests
- MCP SDK: `StreamableClientTransport` reconnect support, but not full session recreation

## Dev Agent Record

### Agent Model Used

Raptor mini

### Completion Notes List

- Story covers Epic 2 backend resilience for MCP tools.
- The plan stresses manager-level reconnect and one retry per tool call.
- Concurrency safety and logs are explicit technical requirements.

### File List

- `talk-bmad/_bmad-output/implementation-artifacts/2-5-mcp-connection-resilience.md`
