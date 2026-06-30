---
baseline_commit: c3dc0c5decead39d4264f385754f558f97817cc1
---

# Story 6.1: Affichage des tool calls (collapse/expand)

Status: done

## Story

As an end user,
I want to see which tools the assistant uses during a conversation,
So that I understand what external actions are being performed on my behalf.

## Acceptance Criteria (BDD)

1. **Given** the backend emits `TOOL_CALL_START` / `TOOL_CALL_ARGS` / `TOOL_CALL_END` events **When** a tool call is in progress **Then** a tool item appears in the message flow with an in-progress indicator

2. **Given** a tool call completes (`TOOL_CALL_END`) **When** it renders **Then** the item shows the tool name + a chevron, collapsed by default

3. **Given** the user clicks on a collapsed tool item **When** it expands **Then** the arguments and result are displayed **And** clicking again collapses it

4. **Given** multiple tool calls occur in one turn **When** they render **Then** each tool call is a separate collapsible item in sequence

## Tasks / Subtasks

- [x] Task 1: Extend normalizeMessages to surface tool call data (AC: #1, #2, #4)
  - [x] 1.1 Add `"tool-call"` to `ChatRole` union type
  - [x] 1.2 Extend `ChatMessageViewModel` with optional fields: `toolName?: string`, `toolArgs?: string`, `toolResult?: string`, `toolCallId?: string`
  - [x] 1.3 Match `AssistantMessage` records that have `toolCalls` array (no content) — emit one `ChatMessageViewModel` per tool call with `role: "tool-call"`, `toolName`, `toolArgs` extracted from `function.name` and `function.arguments`
  - [x] 1.4 Match `ToolMessage` records (`role: "tool"`) — find the preceding tool-call view model with matching `toolCallId` and attach the `toolResult` content to it
  - [x] 1.5 If no matching tool-call VM exists for a ToolMessage, skip it (defensive)
  - [x] 1.6 Unit tests: single tool call emits tool-call VM with name+args; tool result attaches to matching VM; multiple tool calls produce separate VMs; unmatched tool messages are skipped; existing user/assistant/reasoning filtering unchanged

- [x] Task 2: Create ToolCallItem component (AC: #1, #2, #3)
  - [x] 2.1 Create `src/components/ToolCallItem.tsx`
  - [x] 2.2 Props: `toolName: string`, `toolArgs?: string`, `toolResult?: string`
  - [x] 2.3 Collapsed state (default): single row with tool icon, tool name, chevron pointing right
  - [x] 2.4 Expanded state: chevron rotates down, shows arguments (JSON formatted) and result below the header
  - [x] 2.5 In-progress state: when `toolResult` is undefined/null, show a pulsing dot or spinner instead of the chevron; the item is not expandable in this state
  - [x] 2.6 Toggle via click on the entire collapsed header row (not just chevron)
  - [x] 2.7 Accessibility: `button` role on the header, `aria-expanded` attribute, keyboard-accessible (Enter/Space)
  - [x] 2.8 Unit tests: renders tool name; collapsed by default when result exists; expands on click showing args+result; collapses on second click; shows in-progress indicator when no result; not expandable when in-progress

- [x] Task 3: Integrate ToolCallItem in ChatView message rendering loop (AC: #1, #2, #3, #4)
  - [x] 3.1 In ChatView, add a branch for `msg.role === "tool-call"` rendering `<ToolCallItem>`
  - [x] 3.2 Pass `toolName`, `toolArgs`, `toolResult` from the view model
  - [x] 3.3 Integration tests: tool-call items render in sequence between reasoning/assistant messages; in-progress indicator shown during active tool call; multiple tool calls render as separate items

- [x] Task 4: Styling and visual polish (AC: #1, #2, #3)
  - [x] 4.1 Tool call item styled distinct from message bubbles: compact height, subtle background (`bg-white/5`), rounded, left-aligned
  - [x] 4.2 Tool name in monospace or semi-bold
  - [x] 4.3 Chevron uses CSS transition for rotation (`transition-transform duration-200`)
  - [x] 4.4 In-progress indicator: small pulsing dot (`animate-pulse`) matching project's ActivityIndicator style
  - [x] 4.5 Expanded content area: slightly indented, code-style formatting for JSON args/result, muted text color

### Review Findings

- [x] [Review][Patch] Preserve assistant content when `toolCalls` and textual `content` coexist [src/config/normalize-messages.ts:40]
- [x] [Review][Patch] Ensure unique fallback IDs for multiple tool calls without valid IDs in one assistant message [src/config/normalize-messages.ts:49]
- [x] [Review][Patch] Buffer or reconcile out-of-order tool results arriving before their matching tool-call VM [src/config/normalize-messages.ts:67]
- [x] [Review][Patch] Handle non-string tool result payloads without forcing perpetual in-progress state [src/config/normalize-messages.ts:75]
- [x] [Review][Patch] Render result section even when `toolResult` is an empty string to avoid silent completed-empty outputs [src/components/ToolCallItem.tsx:66]

## Dev Notes

### Architecture Compliance

- **Message flow pattern**: `agent.messages` from CopilotKit's `useAgent()` hook already contains `AssistantMessage` (with `toolCalls`) and `ToolMessage` objects interleaved in the correct order. No new API calls or subscriptions needed.
- **State ownership**: ChatView remains the single orchestrator. `normalizeMessages` handles all data transformation. Expand/collapse state is local to `ToolCallItem` via `useState` — no lifting state needed.
- **No `any` types** anywhere (NFR-1). Use AG-UI's typed `Message` union.
- **Zod v4**: Not needed for this story — AG-UI messages are already validated by CopilotKit internally.

### AG-UI Protocol: Message Types for Tool Calls

From `@ag-ui/core` v0.0.57:

```typescript
// AssistantMessage with tool calls (no content field)
{
  id: string;
  role: "assistant";
  content?: string;        // absent when message is a tool-call container
  toolCalls?: ToolCall[];  // present when LLM invokes tools
}

// ToolCall shape
{
  id: string;              // correlates with ToolMessage.toolCallId
  type: "function";
  function: {
    name: string;          // e.g. "get_weather", "search_routes"
    arguments: string;     // JSON-serialized arguments
  };
}

// ToolMessage (result)
{
  id: string;
  role: "tool";
  content: string;         // JSON-serialized tool output
  toolCallId: string;      // correlates with ToolCall.id
  error?: string;          // present if tool execution failed
}
```

### Backend Event Sequence (from Story 2.2)

For each tool call in a turn:
```
TOOL_CALL_START  { toolCallId, toolCallName }
TOOL_CALL_ARGS   { toolCallId, delta: JSON args }
TOOL_CALL_END    { toolCallId }
```

CopilotKit's AG-UI client translates these into the `agent.messages` array entries described above. The `AssistantMessage` with `toolCalls` appears when `TOOL_CALL_START` is received; the `ToolMessage` appears after `TOOL_CALL_END`.

### Message Array Examples

**Single tool call in progress (TOOL_CALL_START received, no END yet):**
```typescript
[
  { id: "u1", role: "user", content: "What's the weather?" },
  { id: "tc1", role: "assistant", toolCalls: [{ id: "call_1", type: "function", function: { name: "get_weather", arguments: '{"city":"Paris"}' } }] },
  // no ToolMessage yet → in-progress state
]
```

**Single tool call completed:**
```typescript
[
  { id: "u1", role: "user", content: "What's the weather?" },
  { id: "tc1", role: "assistant", toolCalls: [{ id: "call_1", type: "function", function: { name: "get_weather", arguments: '{"city":"Paris"}' } }] },
  { id: "t1", role: "tool", content: '{"temperature":22,"unit":"celsius"}', toolCallId: "call_1" },
  { id: "a1", role: "assistant", content: "It's 22°C in Paris." },
]
```

**Multiple tool calls in one turn:**
```typescript
[
  { id: "u1", role: "user", content: "Compare weather" },
  { id: "tc1", role: "assistant", toolCalls: [
    { id: "call_1", type: "function", function: { name: "get_weather", arguments: '{"city":"Paris"}' } },
    { id: "call_2", type: "function", function: { name: "get_weather", arguments: '{"city":"London"}' } },
  ] },
  { id: "t1", role: "tool", content: '{"temperature":22}', toolCallId: "call_1" },
  { id: "t2", role: "tool", content: '{"temperature":18}', toolCallId: "call_2" },
  { id: "a1", role: "assistant", content: "Paris is warmer." },
]
```

### normalizeMessages Strategy

**Current behavior:** Filters to `role === "user" | "assistant" | "reasoning"` only. Assistant messages without `content` (tool-call containers) are explicitly skipped.

**New behavior:**
1. Iterate messages in order
2. When encountering an `AssistantMessage` with `toolCalls` array:
   - For EACH tool call in the array, emit a `ChatMessageViewModel` with `role: "tool-call"`, `toolName: tc.function.name`, `toolArgs: tc.function.arguments`, `toolCallId: tc.id`, `toolResult: undefined`
3. When encountering a `ToolMessage` (`role: "tool"`):
   - Find the already-emitted tool-call VM with matching `toolCallId` and set `toolResult = message.content`
   - If no match found, skip (defensive)
4. User, assistant (with content), reasoning: unchanged behavior

**In-progress detection:** A tool-call VM with `toolResult === undefined` means the tool is still executing (no `TOOL_CALL_END` received yet). This is the signal for the in-progress indicator in `ToolCallItem`.

### Component Design

```
ChatView
  └─ map(msg =>
       msg.role === "reasoning" → <ReasoningBlock />
       msg.role === "tool-call" → <ToolCallItem />     ← NEW
       msg.role === "user"|"assistant" → <MessageBubble />
     )
```

**ToolCallItem internal structure:**
```
┌─────────────────────────────────────────────────────┐
│ 🔧 get_weather                              ▸       │  ← collapsed (default)
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ 🔧 get_weather                              ▾       │  ← expanded header
├─────────────────────────────────────────────────────┤
│   Arguments:                                        │
│   { "city": "Paris" }                               │
│                                                     │
│   Result:                                           │
│   { "temperature": 22, "unit": "celsius" }          │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ 🔧 get_weather                           ●          │  ← in-progress (pulsing dot)
└─────────────────────────────────────────────────────┘
```

### Styling Specifications

- **Container**: `bg-white/5 rounded-lg px-3 py-2` — lighter than message bubbles, compact
- **Header row**: `flex items-center gap-2 cursor-pointer` — clickable
- **Tool icon**: `🔧` emoji or a wrench SVG (keep it simple, emoji is fine)
- **Tool name**: `font-mono text-sm text-white/80`
- **Chevron**: `text-white/40 transition-transform duration-200` — rotates 90° on expand
- **In-progress dot**: `w-2 h-2 rounded-full bg-white/60 animate-pulse`
- **Expanded body**: `mt-2 pl-4 text-xs text-white/60 font-mono whitespace-pre-wrap`
- **Section labels** ("Arguments:", "Result:"): `text-white/40 text-xs uppercase tracking-wider mb-1`

### Previous Story (5.3) Lessons

- **normalizeMessages is the single transformation point** — keep components data-driven and stateless (except local UI state like expand/collapse).
- **Testing pattern**: Mock `agent.messages` with expected shape, verify rendered output via Testing Library queries.
- **Component rendering loop**: Branch by `msg.role` in ChatView's map function — established pattern.
- **MarkdownContent is reusable** — tool results that are plain text can use it, but JSON is better shown as `<pre>` with monospace styling.
- **Keep MessageBubble focused** — only handles `user`/`assistant` roles. New roles get dedicated components.

### Testing Standards

- **Framework**: Vitest 4.1.9 + @testing-library/react 16 + @testing-library/user-event 14
- **Location**: `src/__tests__/` for test files
- **Naming**: `tool-call-item.test.tsx`, extend `normalize-messages.test.ts` and `chat-view.test.tsx`
- **Pattern**: Each test controls `agent.messages` mock, verifies DOM output
- **Accessibility**: Test `aria-expanded` attribute toggling, keyboard interaction

### File Structure

- **NEW**: `src/components/ToolCallItem.tsx` — collapsible tool call display
- **NEW**: `src/__tests__/tool-call-item.test.tsx` — unit tests for ToolCallItem
- **UPDATE**: `src/config/normalize-messages.ts` — add tool-call role handling
- **UPDATE**: `src/__tests__/normalize-messages.test.ts` — add tool-call test cases
- **UPDATE**: `src/components/ChatView.tsx` — add tool-call branch in rendering loop
- **UPDATE**: `src/__tests__/chat-view.test.tsx` — add integration tests for tool calls

### Anti-Patterns to Avoid

- **Do NOT add a separate state store for tool calls** — derive everything from `agent.messages` via `normalizeMessages`.
- **Do NOT mutate the original messages array** — `normalizeMessages` returns a new array.
- **Do NOT use `useEffect` to track tool call completion** — the view model's `toolResult` field is the single source of truth.
- **Do NOT add external animation libraries** — use Tailwind's built-in `animate-pulse` and `transition-transform`.
- **Do NOT parse `function.arguments` JSON in normalizeMessages** — pass the raw string to the component; let `ToolCallItem` handle display formatting (try/catch JSON.parse for pretty-printing).

### References

- [Source: epics.md, Epic 6 Story 6.1] — acceptance criteria
- [Source: prd-talk-frontend-2026-06-28/prd.md, FR-10, FR-11, FR-12, FR-22] — functional requirements
- [Source: story 2-2-tool-call-agui-events.md] — backend event emission (TOOL_CALL_START/ARGS/END)
- [Source: story 5-3-affichage-du-raisonnement.md] — normalizeMessages patterns, component architecture
- [Source: @ag-ui/core v0.0.57 index.d.ts] — AssistantMessage, ToolMessage, ToolCall type definitions
- [Source: project-context.md] — testing standards, no `any`, Tailwind styling

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (copilot)

### Completion Notes List

- Task 1: Extended `normalizeMessages` to emit `tool-call` view models from AG-UI `AssistantMessage` (with `toolCalls`) and attach results from `ToolMessage`. Updated existing tests that expected tool calls to be filtered out. Added 7 new test cases covering single/multiple tool calls, in-progress state, orphaned tool messages, and positional ordering.
- Task 2: Created `ToolCallItem` component with collapsed/expanded/in-progress states. Uses `useState` for local expand/collapse. JSON pretty-printing with try/catch fallback. Accessible via `button` with `aria-expanded`. 8 unit tests.
- Task 3: Integrated `ToolCallItem` in ChatView's rendering loop via `msg.role === "tool-call"` branch. 3 integration tests covering rendering, in-progress state, and multiple tool calls.
- Task 4: All styling applied inline via Tailwind classes matching spec (bg-white/5, font-mono, animate-pulse, transition-transform).
- Review patches applied: preserve assistant content when toolCalls coexist with content, unique fallback IDs for missing tool-call ids, buffering/reconciliation for out-of-order tool results, non-string tool result normalization, and empty-string result rendering.
- Validation after review patches: `pnpm test` (108/108 passing), `pnpm lint` (pass), `pnpm format` (pass).

### File List

- NEW: src/components/ToolCallItem.tsx
- NEW: src/__tests__/tool-call-item.test.tsx
- UPDATE: src/config/normalize-messages.ts
- UPDATE: src/__tests__/normalize-messages.test.ts
- UPDATE: src/components/ChatView.tsx
- UPDATE: src/__tests__/chat-view.test.tsx
