---
baseline_commit: b48c005e818ba93f43c47a104789abcc52c51198
---

# Story 5.3: Affichage du raisonnement

Status: done

## Story

As an end user,
I want to see the model's reasoning/thinking when it is produced,
So that I understand how the assistant arrived at its answer.

## Acceptance Criteria (BDD)

1. **Given** the backend emits `REASONING_*` events during a response **When** reasoning content is received **Then** it is displayed above the assistant's text response **And** it is always visible (not collapsed) **And** it is visually distinct from the final response (muted color, italic, bordered block)

2. **Given** a response has no reasoning events **When** the assistant responds **Then** no reasoning block is shown (only the text response)

3. **Given** multiple LLM iterations (tool loop) each produce reasoning **When** reasoning arrives for each iteration **Then** each reasoning block is displayed in order above the final text

## Tasks / Subtasks

- [x] Task 1: Update normalizeMessages to preserve reasoning messages (AC: #1, #2, #3)
  - [x] 1.1 Extend `ChatMessageViewModel` type: add `reasoningContent?: string` field
  - [x] 1.2 Modify `normalizeMessages` to pair `role: "reasoning"` messages with the next `role: "assistant"` message
  - [x] 1.3 When a reasoning message precedes an assistant message, attach its content to the assistant's `reasoningContent` field
  - [x] 1.4 When multiple reasoning messages precede an assistant message (tool loop iterations), concatenate them (newline-separated) into a single `reasoningContent`
  - [x] 1.5 Reasoning messages that don't precede an assistant message are still attached to the nearest following assistant message
  - [x] 1.6 Unit tests for normalizeMessages: reasoning paired, multiple reasoning paired, no reasoning, reasoning without following assistant message

- [x] Task 2: Create ReasoningBlock component (AC: #1)
  - [x] 2.1 Create `src/components/ReasoningBlock.tsx` — displays reasoning text above assistant content
  - [x] 2.2 Props: `content: string`
  - [x] 2.3 Visual: muted color (`text-white/50`), italic, left border (`border-l-2 border-white/20 pl-3`), smaller font (`text-sm`)
  - [x] 2.4 Render with `<MarkdownContent>` (reasoning may contain markdown formatting)
  - [x] 2.5 Always visible (no collapse/expand toggle)
  - [x] 2.6 Unit test: renders content, applies visual styling

- [x] Task 3: Integrate ReasoningBlock into MessageBubble (AC: #1, #2, #3)
  - [x] 3.1 Extend `MessageBubbleProps` to accept `reasoningContent?: string`
  - [x] 3.2 When `role === "assistant"` and `reasoningContent` is provided, render `<ReasoningBlock>` above the text content inside the bubble
  - [x] 3.3 When `reasoningContent` is absent or empty, don't render any reasoning block (AC: #2)
  - [x] 3.4 Unit tests: assistant with reasoning shows block above text, assistant without reasoning shows text only, user messages ignore reasoningContent

- [x] Task 4: Pass reasoningContent through ChatView (AC: #1, #2, #3)
  - [x] 4.1 Update `ChatView` message rendering loop: pass `reasoningContent` from `ChatMessageViewModel` to `MessageBubble`
  - [x] 4.2 Integration test: full flow with mocked agent.messages containing reasoning + assistant messages verifies reasoning display

## Dev Notes

### Architecture Compliance

- **Message flow**: AG-UI protocol emits `ReasoningMessage` objects with `role: "reasoning"` in `agent.messages`. These arrive interleaved between assistant messages in the same messages array.
- **State ownership pattern**: ChatView remains the single owner — `normalizeMessages` is responsible for pairing reasoning with assistant messages. No new state needed.
- **No new state**: Reasoning content is derived from message data, not user input. No `useState` required.
- **Zod v4**: Import from `"zod/v4"` if schema validation needed (likely not needed for this story).
- **No `any` types** anywhere in implementation (NFR-1).

### AG-UI Protocol: ReasoningMessage Type

From `@ag-ui/core` (v0.0.57), the `Message` discriminated union includes:

```typescript
// ReasoningMessage schema from @ag-ui/core
{
  id: string;
  role: "reasoning";     // discriminant
  content: string;       // the reasoning text
  encryptedValue?: string;
}
```

This is part of the `Message` union type: `UserMessage | AssistantMessage | ToolMessage | ActivityMessage | ReasoningMessage | DeveloperMessage | SystemMessage`

### CopilotKit v2 Integration

- CopilotKit v2 already provides a `CopilotChatReasoningMessage` component, but we are NOT using CopilotKit's built-in chat UI (we have custom `ChatView`/`MessageBubble`).
- The `agent.messages` array from `useAgent()` includes `ReasoningMessage` objects when the backend emits `REASONING_*` events.
- The AG-UI client has a `ThinkingToReasoningMiddleware` that maps deprecated `THINKING_*` events to `REASONING_*` — our backend already emits `REASONING_*` directly, so no middleware concern.

### Backend Event Sequence (from Story 1.5)

When thinking is activated, the backend emits per LLM call:

```
REASONING_START → REASONING_MESSAGE_START (role="reasoning")
  → REASONING_MESSAGE_CONTENT (delta=thinking text)
  → REASONING_MESSAGE_END → REASONING_END
→ TEXT_MESSAGE_START → TEXT_MESSAGE_CONTENT → TEXT_MESSAGE_END
```

In tool-loop scenarios (multiple iterations):

```
[Iteration 1] REASONING_* → TEXT_MESSAGE_* (or TOOL_CALL_*)
[Iteration 2] REASONING_* → TEXT_MESSAGE_* (or TOOL_CALL_*)
...
[Final]       REASONING_* → TEXT_MESSAGE_*
```

Each reasoning block is a separate `ReasoningMessage` in `agent.messages`.

### Message Array Structure in agent.messages

After a thinking-enabled response, `agent.messages` will look like:

```typescript
[
  { id: "u1", role: "user", content: "explain X" },
  { id: "r1", role: "reasoning", content: "Let me think about this..." },
  { id: "a1", role: "assistant", content: "Here's my answer..." },
];
```

With tool loop (multiple reasoning blocks):

```typescript
[
  { id: "u1", role: "user", content: "do Y" },
  { id: "r1", role: "reasoning", content: "I need to call tool A..." },
  // tool messages may be present here (filtered by normalizeMessages)
  { id: "r2", role: "reasoning", content: "Now with tool result, I can..." },
  { id: "a1", role: "assistant", content: "Done! Here's the result..." },
];
```

### normalizeMessages Strategy

Current behavior: filters to `role === "user" || "assistant"` only, discarding reasoning.

New behavior:

1. Iterate through messages in order
2. Collect consecutive `role: "reasoning"` messages into a buffer
3. When an `role: "assistant"` message is encountered, attach buffered reasoning content to it
4. Other roles (tool, system, developer, activity) are skipped as before
5. Return `ChatMessageViewModel[]` where each assistant message MAY have `reasoningContent`

This approach keeps the view model flat and simple — no nested arrays or complex state.

### Visual Design

```
┌─ Assistant message bubble ────────────────────────────┐
│ ┌─ Reasoning block (if present) ────────────────────┐ │
│ │ │ Let me think about this step by step...         │ │  ← muted, italic, left-bordered
│ │ │ First, I'll consider...                         │ │
│ └───────────────────────────────────────────────────┘ │
│                                                       │
│ Here's my answer: the result is 42.                   │  ← normal assistant text
└───────────────────────────────────────────────────────┘
```

Styling for reasoning block:

- `text-white/50` — muted text color
- `italic` — visual distinction
- `border-l-2 border-white/20 pl-3` — left border accent
- `text-sm` — slightly smaller than assistant text
- `mb-3` — spacing between reasoning and answer
- Uses `<MarkdownContent>` for rendering (reasoning may contain formatted text)

### Component Hierarchy

```
ChatView
  └─ MessageBubble (role="assistant", content="...", reasoningContent="...")
       ├─ ReasoningBlock (content="reasoning text")  ← NEW, conditionally rendered
       └─ MarkdownContent (content="assistant text") ← existing
```

### Project Structure Notes

- All source in `talk-ui/src/`
- Components: `src/components/ReasoningBlock.tsx` (NEW file)
- Modify: `src/components/MessageBubble.tsx`, `src/components/ChatView.tsx`
- Tests: `src/__tests__/message-bubble.test.tsx` (extend), `src/__tests__/chat-view.test.tsx` (extend)
- Labels/aria in French where applicable
- No i18n library — hardcoded French strings

### Previous Story (5.2) Lessons

- **normalizeMessages is the right place** to handle message transformation — keep components simple and data-driven.
- **Testing pattern**: Mock `agent.messages` with the expected message array shape, verify rendered output.
- **Lint trap**: Don't set state inside `useEffect` that depends on that state.
- **Integration tests**: Use `screen.getByText()` / `screen.queryByText()` to verify content presence/absence.
- **Controlled components**: MessageBubble is a pure presentational component — all data comes through props, no internal state.

### Testing Standards

- Vitest 4.1.9 + @testing-library/react 16 + @testing-library/user-event 14
- Test file location: `src/__tests__/`
- Assertions: `expect(...)` with vitest matchers
- Mock pattern for CopilotKit: already established in `chat-view.test.tsx` (vi.mock + vi.fn())
- New test: `src/__tests__/reasoning-block.test.tsx` for ReasoningBlock unit tests
- Extend: `src/__tests__/message-bubble.test.tsx` for reasoning integration
- Extend: `src/__tests__/chat-view.test.tsx` for full flow integration

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 5, Story 5.3]
- [Source: PRD FR-5, FR-6, FR-7, FR-12, FR-14 — Thinking, reasoning display]
- [Source: PRD D-3, D-4, D-8 — AG-UI events, message structure]
- [Source: _bmad-output/implementation-artifacts/1-5-thinking-reasoning-agui-events.md — Backend reasoning emission]
- [Source: _bmad-output/implementation-artifacts/5-2-selection-du-thinking-effort.md — Previous story patterns]
- [Source: @ag-ui/core v0.0.57 — ReasoningMessage schema, Message union type]
- [Source: @copilotkit/react-core v2 — CopilotChatReasoningMessage (not used, custom implementation)]
- [Source: src/components/ChatView.tsx — normalizeMessages, message rendering loop]
- [Source: src/components/MessageBubble.tsx — Presentation component to extend]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (GitHub Copilot)

### Completion Notes List

- Task 1: Extracted `normalizeMessages` into `src/config/normalize-messages.ts` as a standalone utility with `ChatMessageViewModel` type including `reasoningContent?: string`. Logic buffers `role: "reasoning"` messages and attaches them to the next assistant message. 9 unit tests.
- Task 2: Created `src/components/ReasoningBlock.tsx` — renders reasoning text with `<MarkdownContent>`, styled with muted color, italic, left border, smaller font. 5 unit tests.
- Task 3: Extended `MessageBubble` with `reasoningContent` prop — renders `<ReasoningBlock>` above assistant text when present. 4 new unit tests.
- Task 4: Updated `ChatView` to pass `reasoningContent` from the view model to `MessageBubble`. 3 integration tests covering single reasoning, no reasoning, and multi-iteration scenarios.

### Change Log

| Date       | Change                                    | Reason                        |
| ---------- | ----------------------------------------- | ----------------------------- |
| 2026-06-29 | Implemented reasoning display (Tasks 1-4) | Story 5.3 full implementation |

### File List

**NEW:**

- `src/config/normalize-messages.ts` — Extracted normalizeMessages utility with reasoning buffer logic
- `src/components/ReasoningBlock.tsx` — Reasoning display component (muted, italic, bordered)
- `src/__tests__/normalize-messages.test.ts` — 9 unit tests for normalizeMessages
- `src/__tests__/reasoning-block.test.tsx` — 5 unit tests for ReasoningBlock

**UPDATE:**

- `src/components/ChatView.tsx` — Imports normalizeMessages from utility, passes reasoningContent to MessageBubble
- `src/components/MessageBubble.tsx` — Accepts reasoningContent prop, renders ReasoningBlock above assistant text
- `src/__tests__/message-bubble.test.tsx` — 4 new tests for reasoning integration
- `src/__tests__/chat-view.test.tsx` — 3 new integration tests for reasoning display flow
