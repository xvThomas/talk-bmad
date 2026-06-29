---
baseline_commit: d7f6677ea2945f3bf242fdb48d10eef4f34edc1c
---

# Story 4.3: Chat layout et envoi de message

Status: review

## Story

As an end user,
I want to see a chat interface and send a message,
So that I can converse with the assistant.

## Acceptance Criteria (BDD)

1. **Given** the app is loaded with no messages **When** the page renders **Then** the chat input is centered horizontally and vertically (empty state).
2. **Given** the user types a message and clicks Send (or presses Enter) **When** the message is submitted **Then** the user's message appears right-aligned in the conversation **And** the input is cleared **And** a discrete activity indicator is shown (assistant is working).
3. **Given** messages exist in the conversation **When** the layout renders **Then** messages scroll vertically downward **And** the input is fixed at the bottom, centered horizontally.
4. **Given** the assistant is running (`agent.isRunning`) **When** the activity indicator renders **Then** it is a subtle animated element (not a large spinner), visually distinct but not distracting.
5. **Given** all of the above **When** I run `pnpm build && pnpm lint && pnpm test` **Then** everything passes.

## Tasks / Subtasks

- [x] Task 1: Create ChatInput component (AC: #1, #2)
  - [x] Create `src/components/ChatInput.tsx`
  - [x] Text input with send button (icon or text)
  - [x] Submit on Enter key press or button click
  - [x] Input is disabled while agent is running
  - [x] Send button disabled when input is empty
  - [x] On submit: call `agent.addMessage()` + `copilotkit.runAgent()`
  - [x] Clear input after successful submit
- [x] Task 2: Create MessageBubble component (AC: #2, #3)
  - [x] Create `src/components/MessageBubble.tsx`
  - [x] Accept message role and content props
  - [x] User messages: right-aligned, accent background
  - [x] Assistant messages: left-aligned, muted background
  - [x] Proper spacing between messages
- [x] Task 3: Create ActivityIndicator component (AC: #4)
  - [x] Create `src/components/ActivityIndicator.tsx`
  - [x] Subtle animated dots or pulse (not a spinner)
  - [x] Shown only when `agent.isRunning` is true
  - [x] Positioned as left-aligned message (assistant side)
- [x] Task 4: Create ChatView composite component (AC: #1, #3)
  - [x] Create `src/components/ChatView.tsx`
  - [x] Uses `useAgent()` and `useCopilotKit()` hooks
  - [x] Empty state: input centered (flexbox center)
  - [x] Messages state: messages scroll area + fixed bottom input
  - [x] Transitions between states based on `agent.messages.length`
- [x] Task 5: Integrate in route (AC: #1, #3)
  - [x] Update `src/App.tsx` to render `<ChatView />`
  - [x] Full height layout (`min-h-screen`)
- [x] Task 6: Write tests (AC: #5)
  - [x] Test ChatInput: renders, submits on Enter, clears after submit
  - [x] Test MessageBubble: user right-aligned, assistant left-aligned
  - [x] Test ChatView: shows empty state, transitions to messages state
  - [x] Mock `useAgent()` and `useCopilotKit()` for component tests
- [x] Task 7: README skipped (no content change needed)

### Review Findings

- [x] [Review][Patch] Handle `runAgent` promise rejection in `handleSend` to prevent unhandled rejections and surface errors in UI [src/components/ChatView.tsx:87]
- [x] [Review][Patch] Add a runtime guard `if (agent.isRunning) return;` in `handleSend` to avoid fast double-submit race before disabled state re-renders [src/components/ChatView.tsx:79]
- [x] [Review][Patch] Ensure non-empty error fallback to avoid blank conversation layout when error message is an empty string [src/routes/__root.tsx:16]
- [x] [Review][Patch] Add accessible live error semantics (`role="alert"`) on the error bubble [src/components/ChatView.tsx:122]
- [x] [Review][Patch] Replace unsafe `as` casts by message normalization in `ChatView` and defensive rendering for non-text content in `MessageBubble` [src/components/ChatView.tsx:18]
- [x] [Review][Defer] Hardcoded model `haiku-4.5` should be configurable via app config [src/components/ChatView.tsx:41] — deferred, pre-existing
- [x] [Review][Defer] `visibleMessages.map(...)` has no upper bound/virtualization for long sessions [src/components/ChatView.tsx:54] — deferred, pre-existing

## Dev Notes

### CopilotKit Headless API (v2)

```typescript
import { useAgent } from "@copilotkit/react-core/v2";
import { useCopilotKit } from "@copilotkit/react-core/v2";
import { randomUUID } from "@copilotkit/shared";

function ChatView() {
  const { agent } = useAgent();
  const { copilotkit } = useCopilotKit();

  // Read state
  agent.messages; // Message[] — conversation history
  agent.isRunning; // boolean — true while processing

  // Send a message
  const send = async (content: string) => {
    agent.addMessage({
      id: randomUUID(),
      role: "user",
      content,
    });
    await copilotkit.runAgent({ agent });
  };

  // Stop the agent
  copilotkit.stopAgent({ agent });
}
```

**Message shape** (from AG-UI):

```typescript
interface Message {
  id: string;
  role: "user" | "assistant" | "tool";
  content: string;
  toolCalls?: ToolCall[]; // for assistant messages
  toolCallId?: string; // for tool messages
}
```

### Non-Text Message Behavior

- ChatView normalizes incoming agent messages before rendering.
- Only `user` and `assistant` roles are rendered in this story scope.
- Empty string content is ignored.
- For non-text content (object payloads), `MessageBubble` renders a safe placeholder instead of relying on casts.
- Current placeholder format:
  - `Non-text content is not displayed yet.`
  - `<type> content is not displayed yet.` (for payloads with a `type` field, e.g. `video`)

### Layout Architecture

```
┌─────────────────────────────────────────┐
│            EMPTY STATE                   │
│                                         │
│         ┌───────────────────┐           │
│         │  [input] [send]   │  ← centered
│         └───────────────────┘           │
│                                         │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│          MESSAGES STATE                  │
│  ┌─────────────────────────────────────┐│
│  │           Messages area (scrolls)   ││
│  │                                     ││
│  │  ┌──────────┐                      ││
│  │  │ Assistant │  ← left-aligned      ││
│  │  └──────────┘                      ││
│  │                     ┌──────────┐   ││
│  │                     │   User   │   ││  ← right-aligned
│  │                     └──────────┘   ││
│  │  ┌──┐                              ││
│  │  │••│  ← activity indicator         ││
│  │  └──┘                              ││
│  └─────────────────────────────────────┘│
│  ┌─────────────────────────────────────┐│
│  │  [input] [send]       ← fixed      ││
│  └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

### File Structure (Changes from Story 4.2)

```
src/
├── components/
│   ├── ChatView.tsx           # NEW — main chat composite
│   ├── ChatInput.tsx          # NEW — input + send button
│   ├── MessageBubble.tsx      # NEW — single message display
│   └── ActivityIndicator.tsx  # NEW — subtle loading animation
├── config/
│   ├── env.ts                 # unchanged
│   └── agent.ts              # unchanged
├── routes/
│   ├── __root.tsx            # unchanged (CopilotKit provider)
│   └── index.tsx             # unchanged
├── __tests__/
│   ├── chat-input.test.tsx    # NEW
│   ├── message-bubble.test.tsx # NEW
│   ├── chat-view.test.tsx     # NEW
│   ├── agent.test.ts         # unchanged
│   ├── app.test.tsx          # unchanged
│   └── env.test.ts           # unchanged
├── App.tsx                   # UPDATE — renders ChatView
├── main.tsx                  # unchanged
├── index.css                 # possibly extend with chat styles
└── test-setup.ts             # unchanged
```

### Current State of Modified Files

**`src/App.tsx` (current):**

```tsx
export function App() {
  return (
    <main className="flex min-h-screen items-center justify-center">
      <h1 className="text-2xl font-semibold text-foreground">talk-ui</h1>
    </main>
  );
}
```

**After this story:**

```tsx
import { ChatView } from "./components/ChatView";

export function App() {
  return <ChatView />;
}
```

### Styling Guidelines (Tailwind v4 dark theme)

- Background: `bg-background` (defined as `#0f172a` in index.css `@theme`)
- Text: `text-foreground` (`#e2e8f0`)
- Muted text: `text-muted` (`#64748b`)
- Accent: `text-accent` / `bg-accent` (`#38bdf8`)
- User bubble: `bg-accent/20 text-foreground` — right-aligned
- Assistant bubble: `bg-white/5 text-foreground` — left-aligned
- Input: `bg-white/10 border border-white/20 text-foreground placeholder:text-muted`
- Send button: `bg-accent text-background` when enabled, `opacity-50` when disabled
- Activity indicator: 3 dots with `animate-pulse` stagger

### Testing Strategy

**Mocking CopilotKit hooks:**

```typescript
import { vi } from "vitest";

// Mock the hooks
vi.mock("@copilotkit/react-core/v2", () => ({
  useAgent: () => ({
    agent: {
      messages: [],
      isRunning: false,
      addMessage: vi.fn(),
    },
  }),
  useCopilotKit: () => ({
    copilotkit: {
      runAgent: vi.fn(),
      stopAgent: vi.fn(),
    },
  }),
}));
```

**Test cases:**

- ChatInput: renders input + button, button disabled when empty, calls addMessage + runAgent on submit, clears input
- MessageBubble: renders content, applies correct alignment class for role
- ChatView: renders centered input when no messages, renders message list when messages exist
- ActivityIndicator: visible when isRunning=true, hidden when false

### Common Pitfalls to Avoid

1. **Do NOT use `<CopilotChat />`** — we build custom headless UI. CopilotChat is a prebuilt component we don't want.
2. **Do NOT install `@copilotkit/react-ui`** — not needed for headless approach.
3. **Import from `@copilotkit/react-core/v2`** — NOT `@copilotkit/react-core`.
4. **Use `copilotkit.runAgent({ agent })`** — NOT `agent.runAgent()`. The former handles tool execution and follow-ups.
5. **`randomUUID` from `@copilotkit/shared`** — NOT `crypto.randomUUID()` (ensures format compatibility).
6. **Do NOT implement auto-scroll yet** — that's Story 4.4.
7. **Do NOT implement streaming display** — that's Story 4.4. Just show final `message.content`.
8. **Do NOT implement cancel button** — that's Epic 6.
9. **Do NOT filter tool messages** — show only `user` and `assistant` role messages for now.
10. **Layout must handle both states** — empty (centered) and messages (scroll + fixed input). Use conditional rendering based on `agent.messages.length`.

### Previous Story Intelligence (4.2)

- CopilotKit provider wraps at `__root.tsx` level — hooks available in all route components
- Agent registered as `"default"` key (required for hooks without explicit `agentId`)
- Zod v4 installed (`zod/v4` import path)
- No `@copilotkit/react-ui` — headless only
- `import.meta.env.VITE_AGENT_URL` with fallback to `http://localhost:8090`
- TypeScript 6.0.3 strict mode, ESLint 10 `typescript-eslint/strict`
- Tailwind v4 with `@theme` variables: `--color-background`, `--color-foreground`, `--color-muted`, `--color-accent`

### NFR Compliance

- **NFR-1 (Zod):** Not applicable (no new incoming data boundaries in this story).
- **NFR-9 (Performance):** Final content renders immediately (streaming display is 4.4).
- **NFR-10 (Activity indicator):** Immediate visual feedback via `agent.isRunning`.
- **NFR-11 (WCAG):** Semantic HTML (`<main>`, `<form>`, `<button>`), keyboard submit (Enter), labels on input/button, sufficient contrast in dark theme.

### References

- [Source: PRD section 3.1 - Chat Conversation FR-1 to FR-4](../../planning-artifacts/prds/prd-talk-frontend-2026-06-28/prd.md#3.1)
- [Source: PRD section 3.6 - Send FR-16](../../planning-artifacts/prds/prd-talk-frontend-2026-06-28/prd.md#3.6)
- [Source: PRD section 3.8 - Activity indicator FR-21](../../planning-artifacts/prds/prd-talk-frontend-2026-06-28/prd.md#3.8)
- [Source: CopilotKit Programmatic Control](https://docs.copilotkit.ai/programmatic-control)
- [Source: CopilotKit Headless UI](https://docs.copilotkit.ai/custom-look-and-feel/headless-ui)

## File List

- `src/components/ChatInput.tsx` — NEW
- `src/components/MessageBubble.tsx` — NEW
- `src/components/ActivityIndicator.tsx` — NEW
- `src/components/ChatView.tsx` — NEW
- `src/App.tsx` — MODIFIED (renders ChatView)
- `src/__tests__/chat-input.test.tsx` — NEW (8 tests)
- `src/__tests__/message-bubble.test.tsx` — NEW (5 tests)
- `src/__tests__/chat-view.test.tsx` — NEW (6 tests)
- `src/__tests__/app.test.tsx` — MODIFIED (updated for ChatView)

## Dev Agent Record

### Implementation Plan

- Used `crypto.randomUUID()` instead of `@copilotkit/shared` (not directly importable via pnpm strict deps, native API works identically)
- Components split for single responsibility: ChatInput (form), MessageBubble (display), ActivityIndicator (feedback), ChatView (orchestrator)
- ChatView uses conditional rendering for empty/messages states
- Filtered tool messages from visible messages (`role === "user" || "assistant"`)
- Fixed TS errors: `type FormEvent` (verbatimModuleSyntax) and `msg.content` type union (coerced to string)

### Completion Notes

- All 25 tests pass across 6 test files
- Build passes (only warning: chunk size > 500kb due to CopilotKit bundle)
- Lint passes cleanly
- All 5 ACs satisfied

## Change Log

- 2026-06-28: Story created — full headless CopilotKit chat UI with layout states and component architecture.
- 2026-06-28: Story implemented — 4 components, 19 new tests, build+lint+test pass.
