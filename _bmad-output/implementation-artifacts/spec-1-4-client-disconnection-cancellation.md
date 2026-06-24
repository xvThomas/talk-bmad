---
title: "Story 1.4: Client disconnection cancellation"
type: "feature"
created: "2026-06-24"
status: "done"
baseline_commit: "a20e4cb"
context:
  - "{project-root}/talk/internal/agui/handler.go"
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** When a client closes the SSE connection mid-request, the server continues processing the LLM call and may emit events into a dead stream, wasting resources. The handler must detect disconnection, cancel in-flight work, and exit cleanly without leaking goroutines.

**Approach:** After `chatFn` returns, check `ctx.Err()` before emitting response events. If cancelled, skip all further writes and return immediately. Context propagation to LLM SDKs already exists — the SDK call will return an error when ctx is cancelled. Add a test proving no goroutine leak on disconnection.

## Boundaries & Constraints

**Always:** Use `r.Context().Done()` for disconnection detection — never poll or use timers. The handler must not write any event after detecting cancellation (no partial TEXT_MESSAGE_CONTENT). Existing context propagation to chatFn/LLM must remain unchanged.

**Ask First:** Adding a dedicated cancellation log line (info vs debug level).

**Never:** Spawn background goroutines in the handler that outlive the request. Do not add recovery/retry logic for cancelled requests. Do not persist any state for cancelled requests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Normal request | Client stays connected | Full event sequence emitted | N/A |
| Disconnect before chatFn returns | Client closes mid-LLM-call | chatFn returns ctx error, no events emitted after RUN_STARTED | Handler returns silently |
| Disconnect after chatFn returns | Client closes between response ready and write | No TEXT_MESSAGE events written | Handler returns silently |
| chatFn error (not cancellation) | LLM returns non-ctx error | AG-UI error event emitted as today | Existing error path unchanged |

</frozen-after-approval>

## Code Map

- `talk/internal/agui/handler.go` -- Add ctx.Err() check after chatFn returns, before emitting response events
- `talk/internal/agui/handler_test.go` -- Add cancellation tests: mid-call disconnect, post-call disconnect, goroutine leak verification

## Tasks & Acceptance

**Execution:**

- [x] `talk/internal/agui/handler.go` -- After chatFn returns, if ctx.Err() != nil, log and return without emitting response events. Also check ctx before each SSE write block.
- [x] `talk/internal/agui/handler_test.go` -- Add TestHandler_ClientDisconnectDuringChat (cancelled context, verify no response events), TestHandler_NoGoroutineLeak (runtime.NumGoroutine before/after with cancelled context)

**Acceptance Criteria:**

- Given a POST /agent in flight, when the client closes the connection, then chatFn's context is cancelled and the LLM SDK call aborts
- Given chatFn returned a context.Canceled error, when handler processes the result, then no TEXT_MESSAGE or RUN_FINISHED events are emitted
- Given multiple cancelled requests in sequence, when measuring goroutines, then count returns to baseline (no leak)

## Verification

**Commands:**

- `cd talk && go test ./internal/agui/ -run TestHandler -v` -- expected: all handler tests pass including new cancellation tests
- `cd talk && go build ./cmd/cli/` -- expected: compiles cleanly

## Suggested Review Order

- Early return on cancelled context — single guard after chatFn prevents partial event emission
  [`handler.go:103`](../../../talk-backend/talk/internal/agui/handler.go#L103)

- Integration test proving no text/run events reach the wire after disconnect
  [`handler_test.go:292`](../../../talk-backend/talk/internal/agui/handler_test.go#L292)

- Goroutine-leak regression test — 10 cancelled requests, baseline+2 tolerance
  [`handler_test.go:325`](../../../talk-backend/talk/internal/agui/handler_test.go#L325)
