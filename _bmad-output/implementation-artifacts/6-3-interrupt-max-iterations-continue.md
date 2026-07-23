# Story 6.3: Interrupt max-iterations et bouton Continue

Status: ready-for-dev

## Story

As an end user,
I want to see a "Continue" option when the assistant hits its tool call limit,
So that I can let it resume working without starting over.

## Acceptance Criteria (BDD)

**AC#1** — Interrupt detection and inline message
**Given** the backend emits a `RUN_FINISHED` event with `outcome.type === "interrupt"` and `interrupts[*].reason === "talk:max_iterations"`
**When** the event is received by the AG-UI layer
**Then** an inline message is displayed in the conversation explaining the limit was reached
**And** a "Continue" button is shown below the message

**AC#2** — Continue action
**Given** the user clicks "Continue"
**When** the resume request is sent
**Then** it is sent with `resume: [{ interruptId: <id>, status: "resolved" }]` and the `agent.threadId` is preserved in the request (auto-handled by `runAgent`)
**And** the assistant continues processing (new streaming response begins)
**And** the InterruptBlock disappears once `agent.pendingInterrupts` is cleared

**AC#3** — New message doesn't resume
**Given** the user types and sends a new message instead of clicking "Continue"
**When** the message is submitted
**Then** it is sent as a standard run (no `resume` entries)
**And** the "Continue" button becomes inactive (disabled) while `isRunning` is true
**And** once the run completes normally, the `pendingInterrupts` are cleared by the library and the InterruptBlock disappears

**AC#4** — CI gates
**Given** the implementation is complete
**When** `pnpm lint && pnpm test && pnpm build` are executed
**Then** all pass with no regressions

## Tasks / Subtasks

- [ ] Task 1: Extend context types and provider (AC: #1, #2, #3)
  - [ ] 1.1 Import `Interrupt` type from `@ag-ui/client` in `chat-ui-context-types.ts`
  - [ ] 1.2 Add `pendingInterrupt: Interrupt | null` to `ChatUIContextValue`
  - [ ] 1.3 Add `continueFromInterrupt: () => void` to `ChatUIContextValue`
  - [ ] 1.4 In `ChatUIContext.tsx`, add local state `pendingInterrupt` (initially `null`)
  - [ ] 1.5 Add `useEffect` that watches `agent.pendingInterrupts`: when non-empty and contains an interrupt with `reason === "talk:max_iterations"`, set `pendingInterrupt` to that interrupt; when empty, clear it to `null`
  - [ ] 1.6 Implement `continueFromInterrupt`: call `copilotkit.runAgent({ agent, forwardedProps, resume: [{ interruptId: pendingInterrupt.id, status: "resolved" }] })` wrapped in `void` with `.catch` error handler identical to `sendMessage`
  - [ ] 1.7 Expose `pendingInterrupt` and `continueFromInterrupt` in context value

- [ ] Task 2: Create InterruptBlock component (AC: #1, #2, #3)
  - [ ] 2.1 Create `src/components/InterruptBlock.tsx`
  - [ ] 2.2 Props: `{ onContinue: () => void; disabled: boolean }`
  - [ ] 2.3 Render: info-accent container + message text "The assistant reached its tool call limit." + "Continue" button (disabled when `disabled` is true)
  - [ ] 2.4 Style consistent with `ErrorBlock` (amber/info accent instead of red)

- [ ] Task 3: Wire into ChatView (AC: #1, #2, #3)
  - [ ] 3.1 Destructure `pendingInterrupt` and `continueFromInterrupt` from `useChatUIContext()` in `ChatView`
  - [ ] 3.2 Render `<InterruptBlock>` after the message list and before `ActivityIndicator` when `pendingInterrupt !== null`
  - [ ] 3.3 Pass `disabled={isRunning}` to `InterruptBlock`

- [ ] Task 4: Tests (AC: #1, #2, #3, #4)
  - [ ] 4.1 Extend `mockAgent` in existing test files to include `pendingInterrupts: []`
  - [ ] 4.2 In `chat-ui-context.test.tsx`: add tests for interrupt detection (pendingInterrupts populated → `pendingInterrupt` exposed), `continueFromInterrupt` calls `mockCopilotKit.runAgent` with correct `resume` array
  - [ ] 4.3 Create `src/__tests__/interrupt-block.test.tsx`: render tests (shows message + button), button disabled when `disabled=true`, `onContinue` called on click
  - [ ] 4.4 In `chat-view.test.tsx`: add test that `InterruptBlock` renders when `agent.pendingInterrupts` contains a `talk:max_iterations` interrupt, and disappears when `pendingInterrupts` is empty
  - [ ] 4.5 Run full gates: lint, tests, build

## Dev Notes

### AG-UI interrupt types (from `@ag-ui/client` v0.0.57)

```typescript
// Interrupt shape (from @ag-ui/core)
interface Interrupt {
  id: string;
  reason: string; // "talk:max_iterations" is the value we filter for
  message?: string; // optional human-readable message from backend
  toolCallId?: string;
  metadata?: Record<string, unknown>;
  responseSchema?: Record<string, unknown>;
  expiresAt?: string;
}

// ResumeEntry shape — what to send back
interface ResumeEntry {
  interruptId: string;
  status: "resolved" | "cancelled";
  payload?: unknown;
}
```

**Import path:** `import type { Interrupt } from "@ag-ui/client";`

### AbstractAgent properties relevant to this story

```typescript
// On the agent object returned by useAgent()
agent.pendingInterrupts: Interrupt[]  // auto-populated by library after RUN_FINISHED with outcome.type === "interrupt"
agent.threadId: string                // auto-included in every runAgent() call — no manual handling needed
```

`pendingInterrupts` is:

- **Populated** when `RUN_FINISHED` arrives with `outcome.type === "interrupt"` (library updates it automatically)
- **Cleared** when a subsequent `runAgent()` completes successfully (or with a new interrupt)

### Resume call pattern

```typescript
// In continueFromInterrupt implementation:
void copilotkit
  .runAgent({
    agent,
    forwardedProps,
    resume: [{ interruptId: pendingInterrupt.id, status: "resolved" }],
  })
  .catch((caught: unknown) => {
    const fallback = "An unexpected error occurred";
    if (caught instanceof Error && caught.message.trim() !== "") {
      setError(caught.message);
      return;
    }
    setError(fallback);
  });
```

The `forwardedProps` state is already available in `ChatUIContext` (same closure as `sendMessage`). The `agent.threadId` is automatically included in `prepareRunAgentInput` by the `AbstractAgent` base class — no manual `threadId` passing needed.

### useEffect watch pattern for pendingInterrupts

```typescript
useEffect(() => {
  const maxIterInterrupt = agent.pendingInterrupts.find(
    (i) => i.reason === "talk:max_iterations",
  );
  setPendingInterrupt(maxIterInterrupt ?? null);
}, [agent.pendingInterrupts]);
```

**Caution:** `agent.pendingInterrupts` is an array reference. The `useEffect` dependency should be `agent.pendingInterrupts` directly (React will compare by reference, which is correct since the library replaces the array on each update).

### continueFromInterrupt guard

```typescript
const continueFromInterrupt = useCallback(() => {
  if (!pendingInterrupt) return;
  if (agent.isRunning) return;
  // ... resume call
}, [agent, copilotkit, pendingInterrupt, forwardedProps, setError]);
```

Wait — `forwardedProps` is computed inline in `sendMessage`. For `continueFromInterrupt`, build it the same way:

```typescript
const continueFromInterrupt = useCallback(() => {
  if (!pendingInterrupt || agent.isRunning) return;
  setError(null);
  const fp: Record<string, string> = { model: selectedModel };
  if (thinkingEffort !== "off" && supportsThinking(selectedModel)) {
    fp.thinkingEffort = thinkingEffort;
  }
  void (
    copilotkit
      .runAgent({
        agent,
        forwardedProps: fp,
        resume: [{ interruptId: pendingInterrupt.id, status: "resolved" }],
      })
      .catch(/* same handler as sendMessage */)
  );
}, [
  agent,
  copilotkit,
  pendingInterrupt,
  selectedModel,
  thinkingEffort,
  setError,
]);
```

### InterruptBlock styling reference

Copy `ErrorBlock` structure and swap color classes: red → amber:

- `ErrorBlock` uses `border-red-500/30 bg-red-500/10 text-red-400`
- `InterruptBlock` should use `border-amber-500/30 bg-amber-500/10 text-amber-300` (or blue/info)

Props pattern to follow:

```typescript
interface InterruptBlockProps {
  onContinue: () => void;
  disabled: boolean;
}
```

No `content` or `message` prop needed — the text is static: "The assistant reached its tool call limit."

### ChatView render location

Insert `InterruptBlock` between the message list and `ActivityIndicator`:

```tsx
{visibleMessages.map(...)}
{pendingInterrupt !== null && (
  <InterruptBlock
    onContinue={continueFromInterrupt}
    disabled={isRunning}
  />
)}
{isRunning && <ActivityIndicator />}
{error && <ErrorBlock message={error} />}
```

### Test mock update (REQUIRED)

All existing test files that define `mockAgent` must add `pendingInterrupts`:

```typescript
const mockAgent = {
  // ...existing fields...
  pendingInterrupts: [] as Interrupt[],
};
```

Without this, TypeScript strict checks will fail once `pendingInterrupts` is accessed in `ChatUIContext`.

**Affected files:** `src/__tests__/chat-ui-context.test.tsx`, `src/__tests__/chat-view.test.tsx`

### Test pattern for interrupt scenario

```typescript
it("exposes pendingInterrupt when agent has talk:max_iterations interrupt", () => {
  mockAgent.pendingInterrupts = [
    { id: "intr-1", reason: "talk:max_iterations" },
  ];
  // re-render or trigger re-render
  // assert pendingInterrupt in context is non-null
  // assert continueFromInterrupt calls runAgent with resume
});
```

### Files targeted

| File                                     | Status | Note                                            |
| ---------------------------------------- | ------ | ----------------------------------------------- |
| `src/context/chat-ui-context-types.ts`   | UPDATE | Add `pendingInterrupt`, `continueFromInterrupt` |
| `src/context/ChatUIContext.tsx`          | UPDATE | Add state, useEffect, continueFromInterrupt     |
| `src/components/InterruptBlock.tsx`      | NEW    | Inline interrupt UI                             |
| `src/components/ChatView.tsx`            | UPDATE | Render InterruptBlock                           |
| `src/__tests__/interrupt-block.test.tsx` | NEW    | Component tests                                 |
| `src/__tests__/chat-ui-context.test.tsx` | UPDATE | Add interrupt tests, update mockAgent           |
| `src/__tests__/chat-view.test.tsx`       | UPDATE | Add interrupt rendering test, update mockAgent  |

### Architecture guardrails (from project-context.md)

- **No `as` assertions** — strictTypeChecked ESLint is active. Use type guards and proper narrowing.
- **No `any`** — `Interrupt` is fully typed; import and use the type.
- **No-confusing-void-expression** — event handlers must use braces: `onClick={() => { onContinue(); }}`
- **No-floating-promises** — wrap `copilotkit.runAgent(...)` calls with `void` and `.catch`.
- **No-misused-promises** — `continueFromInterrupt` must be `() => void` (not async), matching event handler expectations.
- **useCallback deps** — include all referenced state/props in `useCallback` dep array.

### Preserved behaviors (must not regress)

- `sendMessage` flow unchanged — no `resume` entries passed for normal sends
- Tool call display (`showTools` toggle) unaffected
- Model selector, thinking effort selector unaffected
- Error display via `ErrorBlock` unaffected
- Auto-scroll behavior unaffected (InterruptBlock renders in the scroll container)

## Dev Agent Record

### Completion Notes

_To be filled by dev agent after implementation._

## Change Log

- 2026-07-17: Story created — AG-UI interrupt types researched, AbstractAgent API documented, resume call pattern established, test patterns specified.
