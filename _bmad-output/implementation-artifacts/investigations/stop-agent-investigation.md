# Investigation: Stop Agent Feature Coverage

## Hand-off Brief

1. **What happened.** The investigation covers two distinct "stop" mechanisms specified in the PRDs: (A) user-initiated mid-stream cancellation (FR-17/FR-18) and (B) backend max-iterations interrupt with Continue button (FR-13/FR-14). The backend implements both correctly; the frontend implements neither.
2. **Where the case stands.** Concluded — root cause is Confirmed for both gaps. Frontend `ChatUIContext` exposes no `stopAgent` action and `ChatInput`/`ChatView` have no cancel button UI. The PRD (Epic 6) explicitly covers both features but they are not yet implemented.
3. **What's needed next.** Create two stories under Epic 6: one for the cancel button (FR-17/FR-18), one for the Continue button on interrupt (FR-13/FR-14).

## Case Info

| Field            | Value                                                                         |
| ---------------- | ----------------------------------------------------------------------------- |
| Ticket           | N/A                                                                           |
| Date opened      | 2026-07-24                                                                    |
| Status           | Concluded                                                                     |
| System           | talk-ui (React/CopilotKit), talk-backend (Go/AG-UI)                          |
| Evidence sources | PRD prd-talk-frontend-2026-06-28, epics.md, ChatInput.tsx, ChatView.tsx, ChatUIContext.tsx, handler.go, emitter.go |

## Problem Statement

Determine whether the feature to stop the agent while it is in its agentic loop (answering a question) is:
1. Specified in the PRD
2. Implemented in the frontend (talk-ui)
3. Implemented in the backend (talk-backend)

## Evidence Inventory

| Source                                                               | Status    | Notes                                            |
| -------------------------------------------------------------------- | --------- | ------------------------------------------------ |
| `_bmad-output/planning-artifacts/prds/prd-talk-frontend-2026-06-28/prd.md` | Available | FR-13, FR-14, FR-17, FR-18 found                |
| `_bmad-output/planning-artifacts/epics.md`                          | Available | Epic 6 covers cancel + interrupt; stories written |
| `talk-ui/src/components/ChatInput.tsx`                               | Available | No cancel button, only send button                |
| `talk-ui/src/components/ChatView.tsx`                                | Available | No cancel/stop UI element                        |
| `talk-ui/src/context/ChatUIContext.tsx`                              | Available | No `stopAgent` call exposed                      |
| `talk-ui/src/context/chat-ui-context-types.ts`                      | Available | Interface has no `stopAgent` or `cancelRun`       |
| `talk-backend/talk/internal/agui/handler.go`                        | Available | Client disconnect + max-iterations interrupt done |
| `talk-backend/talk/internal/agui/emitter.go`                        | Available | Context cancellation propagated correctly        |

## Investigation Backlog

| # | Path to Explore             | Priority | Status | Notes                                        |
| - | --------------------------- | -------- | ------ | -------------------------------------------- |
| 1 | FR-17/FR-18 frontend impl   | High     | Done   | Not implemented — confirmed gap              |
| 2 | FR-13/FR-14 frontend impl   | High     | Done   | Not implemented — confirmed gap              |
| 3 | Backend cancel propagation  | Medium   | Done   | Implemented via `ctx` from `r.Context()`     |
| 4 | `copilotkit.stopAgent()` API| Medium   | Done   | API exists in mock but never called in prod  |

## Timeline of Events

| Time       | Event                                                              | Source               | Confidence |
| ---------- | ------------------------------------------------------------------ | -------------------- | ---------- |
| 2026-06-21 | PRD backend created — FR-3 (client disconnect cancel) specified    | prd.md               | Confirmed  |
| 2026-06-28 | PRD frontend created — FR-17/FR-18 (cancel button) specified       | prd-talk-frontend/prd.md | Confirmed  |
| 2026-06-28 | PRD frontend created — FR-13/FR-14 (interrupt Continue) specified  | prd-talk-frontend/prd.md | Confirmed  |
| 2026-06-28 | Decision log: Continue button inline in flow                       | .decision-log.md     | Confirmed  |
| 2026-07-24 | Frontend implementation missing both features                      | ChatInput/ChatView   | Confirmed  |
| 2026-07-24 | Backend implementation complete for both mechanisms                | handler.go           | Confirmed  |

---

## Confirmed Findings

### Finding 1: PRD specifies both stop mechanisms — FR-17/FR-18 and FR-13/FR-14

**Evidence:** `_bmad-output/planning-artifacts/prds/prd-talk-frontend-2026-06-28/prd.md:73-83`

**Detail:**
- **§3.5 Interrupt Handling (Max Iterations)**: FR-13 — display a "Continue" button when backend emits `RUN_FINISHED` with `outcome.type = interrupt` and `reason = talk:max_iterations`. FR-14 — clicking Continue sends a resume request.
- **§3.6 Send & Cancel**: FR-17 — send button transforms into cancel button during streaming. FR-18 — after cancellation, partial response disappears; user question stays with a "Retry" button.
- Both are part of **Epic 6** (`epics.md:483`), with user stories written at `epics.md:814-877`.

---

### Finding 2: Backend correctly implements client-disconnect cancellation

**Evidence:** `talk-backend/talk/internal/agui/handler.go:168,194`

**Detail:** The handler passes `r.Context()` through to `chatFn`. When the HTTP client disconnects, Go's `net/http` automatically cancels `r.Context()`. The handler checks `ctx.Err() != nil` in two places:
1. After `chatFn` returns — silent return (no `RUN_FINISHED` emitted).
2. Before emitting `RUN_FINISHED` — same silent return.

The emitter (`emitter.go:114`) also detects the broken connection on each `WriteEvent`. No goroutine leak — the context propagates cancellation down to the LLM call chain.

---

### Finding 3: Backend correctly implements max-iterations interrupt

**Evidence:** `talk-backend/talk/internal/agui/handler.go:178-191`

**Detail:** When `chatFn` returns `domain.ErrMaxToolIterations`, the handler emits a `RUN_FINISHED` event with `outcome.type = interrupt`, `reason = talk:max_iterations`, and a human-readable `message`. A resume request with `status = cancelled` is also handled (emits empty `RUN_STARTED`/`RUN_FINISHED`). The interrupt fields are persisted to SQLite (`store.go:58-60`).

---

### Finding 4: Frontend has NO cancel button — FR-17/FR-18 not implemented

**Evidence:** `talk-ui/src/components/ChatInput.tsx:1-80` (full file) and `talk-ui/src/context/chat-ui-context-types.ts:1-16`

**Detail:**
- `ChatInput` renders a single submit button; no conditional render for a cancel/stop button.
- `ChatUIContextValue` interface has no `stopAgent`, `cancelRun`, or equivalent action.
- `ChatUIContext.tsx` never calls `copilotkit.stopAgent()` (the method exists in the mock at `chat-view.test.tsx:22` but is never wired in production).
- During streaming (`isRunning = true`), the send button is simply `disabled` — not replaced by a cancel button.

---

### Finding 5: Frontend has NO Continue button — FR-13/FR-14 not implemented

**Evidence:** `talk-ui/src/components/ChatView.tsx:1-120` (full file), `talk-ui/src/config/normalize-messages.ts`

**Detail:**
- `ChatView` renders messages, `ActivityIndicator`, and `ErrorBlock`. No component checks for an interrupt outcome or renders a "Continue" button.
- `normalize-messages.ts` was scanned — no handling of `RUN_FINISHED` with `outcome.type = interrupt`.
- The `sendMessage` in `ChatUIContext.tsx` does not include resume logic (`input.resume` / `ResumeEntry`).

---

## Deduced Conclusions

### Conclusion 1: Epic 6 is partially implemented (backend only)

**Deduced from:** Findings 2, 3 (backend complete) + Findings 4, 5 (frontend missing).

The backend was implemented first (or independently) and is production-ready for both stop mechanisms. The frontend work for Epic 6 (cancel + interrupt handling) remains to be done.

### Conclusion 2: `copilotkit.stopAgent()` is the correct API for FR-17

**Deduced from:** The method is mocked in all three test files (`app.test.tsx:15`, `chat-ui-context.test.tsx:28`, `chat-view.test.tsx:22`). It was anticipated during test setup, confirming the team knows the API exists. CopilotKit's `stopAgent()` closes the SSE connection client-side, which triggers `r.Context()` cancellation on the backend — aligning with Finding 2.

---

## Hypothesized Paths

### Hypothesis 1: `normalize-messages.ts` would need to surface interrupt state for the Continue button

**Status:** Open  
**Confirm:** Read `normalize-messages.ts` fully and check if `RunFinishedEvent` with interrupt outcome produces any view model.  
**Refute:** Finding a `MessageBubble` or dedicated component that already handles interrupt outcome.

---

## Source Code Trace

| Aspect             | Location                                                    |
| ------------------ | ----------------------------------------------------------- |
| Cancel API (front) | `copilotkit.stopAgent()` — available, not wired             |
| Cancel UI (front)  | `ChatInput.tsx` — button missing                            |
| Cancel type (front)| `chat-ui-context-types.ts` — `stopAgent` action missing     |
| Interrupt UI       | `ChatView.tsx` — no Continue button                         |
| Interrupt context  | `ChatUIContext.tsx` — no resume logic                       |
| Cancel (backend)   | `handler.go:168,194` — via `r.Context()` propagation       |
| Interrupt (backend)| `handler.go:178-191` — `ErrMaxToolIterations` → SSE event  |

---

## Final Conclusion

**Confidence: High**

Both stop mechanisms are **specified in the PRD** (FR-13, FR-14, FR-17, FR-18 — Epic 6).  
Both are **fully implemented in the backend** (`handler.go`).  
Neither is **implemented in the frontend** (`talk-ui`).

**Fix direction:**
1. **FR-17/FR-18 (Cancel button):** Wire `copilotkit.stopAgent()` into `ChatUIContextValue`; replace the send button with a cancel button when `isRunning`; on cancel, clear partial streamed content and show a Retry affordance.
2. **FR-13/FR-14 (Continue button):** Handle `RUN_FINISHED` interrupt outcome in `normalize-messages.ts` or a dedicated hook; render an inline "Continue" button in `ChatView`; wire it to a `sendResume()` action that calls `copilotkit.runAgent()` with `resume: [{ interruptId, status: "resolved" }]`.

**Recommended next action:** `bmad-create-story` — create two stories under Epic 6 for these two frontend gaps.
