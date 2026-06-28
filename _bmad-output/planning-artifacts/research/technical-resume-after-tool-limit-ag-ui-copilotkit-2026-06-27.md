---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - _bmad-output/planning-artifacts/epics.md
  - _bmad-output/implementation-artifacts/2-1-mcp-tool-execution-loop.md
  - _bmad-output/project-context.md
workflowType: "research"
research_type: "technical"
research_topic: "Resume after tool iteration limit — AG-UI Interrupts & CopilotKit patterns"
research_goals: "Determine the correct mechanism for story 2.4 (conversation resume after max tool iterations) that is coherent with AG-UI protocol and CopilotKit frontend capabilities"
user_name: "Xavierthomas"
date: "2026-06-27"
web_research_enabled: true
source_verification: true
---

# Research Report: Resume After Tool Iteration Limit

**Date:** 2026-06-27
**Author:** Xavierthomas
**Research Type:** Technical
**Related Story:** 2.4 — Reprise de conversation après limite d'itérations

---

## Research Overview

Technical research to determine the correct implementation approach for resuming a conversation after the tool call iteration limit (5) is reached. The goal is to ensure coherence with AG-UI protocol capabilities and CopilotKit frontend patterns.

---

## 1. AG-UI Protocol — Native Interrupt Mechanism

AG-UI provides a **native interrupt-and-resume lifecycle** designed for exactly this type of scenario.

### Interrupt Lifecycle

```
Run 1: RunStarted → ToolCall* → RunFinished { outcome: { type: "interrupt", interrupts: [...] } }
         ↓ (agent needs human input or reached a limit)
Client: RunAgentInput { threadId, resume: [{interruptId, status, payload?}] }
         ↓
Run 2: RunStarted → ...continue → RunFinished { outcome: { type: "success" } }
```

### Key Protocol Rules

1. `RunFinished` can carry `outcome: { type: "interrupt", interrupts: [...] }` instead of `{ type: "success" }`
2. The client resumes with a new `RunAgentInput` containing a `resume[]` field addressing each interrupt
3. **Critical rule**: Before emitting `RunFinished` with interrupt, the server MUST emit `StateSnapshot` + `MessagesSnapshot` to provide full context for resume
4. Interrupts support standard `reason` values: `tool_call`, `input_required`, `confirmation`
5. Custom reasons are valid with namespace pattern: `<framework>:<name>` (e.g., `talk:max_iterations`)
6. A `responseSchema` JSON Schema can guide the expected response
7. All open interrupts must be addressed in a single resume (no partial resumes)

### The Interrupt Type

```typescript
type Interrupt = {
  id: string; // Correlation key
  reason: string; // Categorical routing hint
  message?: string; // Human-readable prompt (universal fallback UI)
  toolCallId?: string; // Binds to a prior ToolCall* sequence
  responseSchema?: JsonSchema; // JSON Schema for resume.payload
  expiresAt?: string; // Optional ISO-8601 TTL
  metadata?: Record<string, any>; // Free-form framework-specific data
};
```

### Resume Mechanism

```typescript
type RunAgentInput = {
  // ... existing fields
  resume?: Array<{
    interruptId: string;
    status: "resolved" | "cancelled";
    payload?: any;
  }>;
};
```

- `resolved` — user responded; `payload` carries the response
- `cancelled` — user abandoned without providing input

### State at Interrupt Boundary

The protocol mandates that the agent must emit any state required for resume via `StateSnapshot` and `MessagesSnapshot` events BEFORE the `RunFinished` event carrying the interrupt. This makes the protocol resume-mode-agnostic.

_Source: https://docs.ag-ui.com/concepts/interrupts_
_Source: https://docs.ag-ui.com/concepts/events_

---

## 2. CopilotKit Frontend Capabilities

### Thread Management

- CopilotKit manages **persistent threads** via `useAgent` hook
- The `AgentRunner` handles `run`, `connect` (reconnection), and `stop`
- Threads are resumed via `threadId` — client sends a new `RunAgentInput` on the same thread
- History is maintained server-side (Enterprise Intelligence Platform) or in-memory

### AG-UI Event Handling

CopilotKit exposes all AG-UI events via `agent.subscribe()`:

| Category      | Events                                                                                       |
| ------------- | -------------------------------------------------------------------------------------------- |
| Run lifecycle | `onRunStartedEvent`, `onRunFinishedEvent`, `onRunErrorEvent`                                 |
| Tool calls    | `onToolCallStartEvent`, `onToolCallArgsEvent`, `onToolCallEndEvent`, `onToolCallResultEvent` |
| State         | `onStateSnapshotEvent`, `onStateDeltaEvent`                                                  |
| Messages      | `onMessagesSnapshotEvent`                                                                    |

### Interrupt Support

- CopilotKit handles AG-UI interrupts natively through `onRunFinishedEvent`
- When `outcome.type === "interrupt"`, the framework can prompt the user
- Resume is sent as a new `RunAgentInput` with `resume[]` array
- **No specific "continue after tool limit" mechanism** — it's the server's responsibility to signal via the interrupt protocol

_Source: https://docs.copilotkit.ai/backend/ag-ui_
_Source: https://docs.copilotkit.ai/backend/agent-runner_
_Source: https://docs.copilotkit.ai/threads_

---

## 3. Current talk-backend State Analysis

### Context Builder (`talk/internal/domain/context_builder.go`)

Three modes controlled by `CONTEXT_FULL_TURNS` config:

| Mode   | Value         | Behavior                                              |
| ------ | ------------- | ----------------------------------------------------- |
| Full   | `-1`          | All messages returned as-is                           |
| Lean   | `0` (default) | Only current turn detailed; older turns = Q/A summary |
| Hybrid | `N > 0`       | Last N turns detailed; older = summary                |

### Max Iterations Handling (`talk/internal/domain/conversation.go`)

```go
const maxToolCalls = 5

for range maxToolCalls {
    // LLM call → store assistant message → check tool calls
    if len(response.ToolCalls) == 0 {
        // ✅ Normal exit: HandleTurnEvent called, turn recorded
        return response.Content, nil
    }
    // Execute tools → store tool results → continue loop
}
// ❌ Loop exhausted: ErrMaxToolIterations returned
return "", ErrMaxToolIterations
```

### Critical Gap: When max iterations is reached

| Aspect                 | Current Behavior                                               | Problem                                  |
| ---------------------- | -------------------------------------------------------------- | ---------------------------------------- |
| `HandleTurnEvent`      | **NOT called**                                                 | Turn not recorded in `history_turns`     |
| Intermediate messages  | Assistant + tool results **ARE persisted** in `messages` table | ✅ Data is available                     |
| `HistoryTurn` struct   | No `Status` or `Incomplete` field                              | No way to distinguish an incomplete turn |
| Context builder (lean) | Only current turn is detailed                                  | A "continue" loses tool call context     |
| `history_turns` schema | No status column                                               | No persistence of incomplete state       |

### Data Structures

```go
// TurnEvent — no status field
type TurnEvent struct {
    TurnID, TurnSpanID string
    StartedAt, EndedAt time.Time
    SessionScope       SessionScope
    Model              Model
    TotalUsage         Usage
    CallCount          int
    Input, Output      string
    ToolCalls          []ToolCall
}

// HistoryTurn — no status field
type HistoryTurn struct {
    Question, Answer string
    At               time.Time
    Model            string
    CallCount        int
    TurnID           string
}
```

```sql
-- history_turns table — no status column
CREATE TABLE history_turns (
    session_id  TEXT,
    turn_id     TEXT,
    question    TEXT,
    answer      TEXT,
    question_at DATETIME,
    answer_at   DATETIME,
    PRIMARY KEY (session_id, turn_id)
);
```

---

## 4. Implementation Options

### Option A: AG-UI Interrupts (Protocol-Native)

```
When max iterations reached:
1. Emit MessagesSnapshot (full history including tool calls)
2. Emit RunFinished { outcome: { type: "interrupt", interrupts: [{
     id: "int-xxx",
     reason: "talk:max_iterations",
     message: "Tool call limit reached. Would you like me to continue?"
   }] } }

On client "continue":
3. Receive RunAgentInput { threadId, resume: [{interruptId, status: "resolved"}] }
4. Load FULL context of interrupted turn (force-include detailed messages)
5. Re-invoke LLM with complete context
```

**Pros:** Standard AG-UI, CopilotKit handles natively, no custom hack, forward-compatible.
**Cons:** Requires implementing `resume` support in AG-UI handler (new infrastructure).

### Option B: Simple Message Resume (Implicit)

```
When max iterations reached:
1. Emit RUN_ERROR with user-facing message
2. User sends "continue" as a normal message
3. Context builder force-includes the incomplete turn in detail
```

**Pros:** Simpler, no new transport mechanism.
**Cons:** Context builder modification needed; LLM doesn't explicitly know it's "resuming"; not standard; error event terminates run lifecycle.

### Option C: Hybrid (Pragmatic)

Implement Option B **now** (context builder modification + incomplete turn flag), while structuring the code so that Option A can be added later when interrupt support is implemented globally.

**Changes required for Option C:**

1. Add `Status string` field to `TurnEvent` / `HistoryTurn` (values: `"complete"`, `"incomplete"`)
2. Add `status TEXT DEFAULT 'complete'` column to `history_turns` table
3. Call `HandleTurnEvent` even when max iterations is hit (with `Status: "incomplete"`, `Output: ""`)
4. Modify `BuildContextMessages` to force-include turns with `Status == "incomplete"` in detail regardless of context mode
5. On next message in the same thread, LLM receives full tool call context automatically

---

## 5. Recommendation

**Option C (Hybrid)** is recommended for Story 2.4:

### Rationale

1. The AG-UI interrupt infrastructure (`resume` field in `RunAgentInput`, `outcome` in `RunFinished`) is still marked as **DRAFT** in the AG-UI spec
2. The "continue as normal message" pattern works naturally with the existing flow
3. The only real problem is that the **context builder** loses tool call details in lean mode
4. The changes required are minimal, backward-compatible, and don't break existing behavior
5. The `Status` field on turns prepares for future interrupt support without coupling to it

### Future Path to Option A

When AG-UI interrupts are stabilized and the frontend supports the interrupt UI:

1. Replace `RUN_ERROR` emission with `RunFinished { outcome: interrupt }`
2. Add `resume` field parsing to the AG-UI handler
3. The context builder changes from Option C still apply (force-include incomplete turns)

---

## 6. Impact on Story 2.4 Acceptance Criteria

The original story AC states:

> **Given** a previous request hit the 5-iteration limit on a session
> **When** the user sends a follow-up message with the same `threadId`
> **Then** the LLM receives the full detailed context of prior tool calls and results

This maps exactly to Option C:

- ✅ Turn marked as incomplete → context builder includes it in detail
- ✅ Works regardless of `CONTEXT_FULL_TURNS` mode (lean, hybrid, full)
- ✅ No frontend changes required — user just sends another message

The design note in the epic about "needs-continuation flag" or "automatic context mode elevation" maps to the `Status: "incomplete"` field proposed above.

---

## Sources

- AG-UI Events: https://docs.ag-ui.com/concepts/events
- AG-UI Interrupts: https://docs.ag-ui.com/concepts/interrupts
- AG-UI Architecture: https://docs.ag-ui.com/concepts/architecture
- CopilotKit AG-UI integration: https://docs.copilotkit.ai/backend/ag-ui
- CopilotKit AgentRunner: https://docs.copilotkit.ai/backend/agent-runner
- CopilotKit Threads: https://docs.copilotkit.ai/threads
- talk-backend context builder: `talk/internal/domain/context_builder.go`
- talk-backend conversation manager: `talk/internal/domain/conversation.go`
- talk-backend story 2.1: `_bmad-output/implementation-artifacts/2-1-mcp-tool-execution-loop.md`
