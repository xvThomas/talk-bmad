---
baseline_commit: c4faae9ff6398328df24e345d3c765e2ef438758
---

# Story 4.4: Streaming message et auto-scroll

Status: review

## Story

As an end user,
I want to see the assistant's response appear progressively,
So that I know the assistant is actively responding.

## Acceptance Criteria (BDD)

1. **Given** the backend is streaming a response (TEXT_MESSAGE_CONTENT events) **When** content arrives **Then** the assistant's message bubble grows progressively (message-level streaming) **And** the assistant's message is left-aligned **And** auto-scroll keeps the latest content visible.
2. **Given** the user scrolls up during streaming **When** new content arrives **Then** auto-scroll is paused (user stays at their scroll position).
3. **Given** the user scrolls back to the bottom **When** new content arrives **Then** auto-scroll resumes.
4. **Given** all of the above **When** I run `pnpm build && pnpm lint && pnpm test` **Then** everything passes.

## Tasks / Subtasks

- [x] Task 1: Create `useAutoScroll` custom hook (AC: #1, #2, #3)
  - [x] Create `src/hooks/useAutoScroll.ts`
  - [x] Accept a `ref` to the scroll container and a dependency that changes on new content (e.g., messages array length or isRunning)
  - [x] Implement scroll-to-bottom behavior when new content arrives
  - [x] Detect user scroll-up to pause auto-scroll
  - [x] Resume auto-scroll when user scrolls back to bottom (within threshold)
- [x] Task 2: Integrate `useAutoScroll` into `ChatView` (AC: #1, #2, #3)
  - [x] Add a `ref` to the scrollable messages container (`div.overflow-y-auto`)
  - [x] Add a sentinel `div` at the bottom of the messages list for scroll-into-view
  - [x] Call `useAutoScroll` with the container ref and appropriate dependencies
  - [x] Ensure auto-scroll works during streaming AND when new messages appear
- [x] Task 3: Write tests for `useAutoScroll` (AC: #4)
  - [x] Test: scrolls to bottom when dependency changes and user is at bottom
  - [x] Test: does NOT scroll when user has scrolled up (paused)
  - [x] Test: resumes scrolling when user scrolls back to bottom
- [x] Task 4: Update `ChatView` tests (AC: #4)
  - [x] Test: scroll container has ref attached
  - [x] Test: sentinel div exists at bottom of message list
- [x] Task 5: Verify streaming works end-to-end (AC: #1)
  - [x] Verify no regressions with `pnpm build && pnpm lint && pnpm test`

### Review Findings

- No findings mapped to this story from the cross-story code review.

## Dev Notes

### Streaming Is Already Working

CopilotKit's `useAgent()` hook handles SSE parsing and progressively updates `agent.messages`. The assistant message's `content` field grows with each `TEXT_MESSAGE_CONTENT` delta. Since Story 4.5 already implemented `MarkdownContent` which re-renders when content changes, **streaming message display already works**. This story's focus is purely on **auto-scroll behavior**.

### Auto-Scroll Design

The auto-scroll behavior needs to:
1. **Scroll down** when new content arrives (both new messages AND streaming content growing)
2. **Pause** when the user manually scrolls up (they want to read earlier content)
3. **Resume** when the user scrolls back to the bottom

#### Implementation Strategy: Sentinel Element + `scrollIntoView`

Use a sentinel `<div ref={bottomRef} />` at the bottom of the messages list. When auto-scroll is active, call `bottomRef.current.scrollIntoView({ behavior: "smooth" })` to smoothly scroll to it.

#### Detecting User Scroll-Up (Pause)

Track whether the user is "at the bottom" by comparing `scrollTop + clientHeight` against `scrollHeight` in a `scroll` event listener on the container. If the user is NOT at the bottom (within a threshold, e.g., 50px), auto-scroll is paused.

```typescript
// src/hooks/useAutoScroll.ts
import { useCallback, useEffect, useRef } from "react";

const SCROLL_THRESHOLD = 50; // px from bottom to consider "at bottom"

export function useAutoScroll(deps: unknown[]) {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const isAtBottomRef = useRef(true);

  const checkIfAtBottom = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;
    const { scrollTop, scrollHeight, clientHeight } = container;
    isAtBottomRef.current =
      scrollHeight - scrollTop - clientHeight < SCROLL_THRESHOLD;
  }, []);

  // Listen for scroll events to detect user scroll-up
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    container.addEventListener("scroll", checkIfAtBottom, { passive: true });
    return () => container.removeEventListener("scroll", checkIfAtBottom);
  }, [checkIfAtBottom]);

  // Scroll to bottom when deps change and user is at bottom
  useEffect(() => {
    if (isAtBottomRef.current) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { containerRef, bottomRef };
}
```

**Key decisions:**
- `isAtBottomRef` uses a `ref` (not state) to avoid re-renders on every scroll event
- `SCROLL_THRESHOLD` of 50px gives tolerance for sub-pixel scroll positions
- `{ behavior: "smooth" }` for smooth scrolling during streaming
- `{ passive: true }` on scroll listener for performance
- `deps` array lets the consumer control when scroll happens (pass `[agent.messages, agent.isRunning]`)

### ChatView Integration

```typescript
// In ChatView, messages state branch:
const { containerRef, bottomRef } = useAutoScroll([
  visibleMessages.length,
  visibleMessages.at(-1)?.content,
  agent.isRunning,
]);

return (
  <main className="flex h-screen flex-col">
    <div ref={containerRef} className="flex-1 overflow-y-auto p-4">
      <div className="mx-auto flex max-w-2xl flex-col gap-3">
        {visibleMessages.map((msg) => (
          <MessageBubble key={msg.id} ... />
        ))}
        {agent.isRunning && <ActivityIndicator />}
        {error && (...)}
        <div ref={bottomRef} />
      </div>
    </div>
    ...
  </main>
);
```

**Dependencies explained:**
- `visibleMessages.length` — new messages added → scroll
- `visibleMessages.at(-1)?.content` — streaming content growing → scroll
- `agent.isRunning` — indicator appears/disappears → scroll

### Current State of Modified Files

**`src/components/ChatView.tsx` (current):**
- Uses `useEffect`, `useAgent`, `useCopilotKit` hooks
- Filters messages to user/assistant only
- Empty state: centered input
- Messages state: scrollable list + fixed input
- Shows `ActivityIndicator` when `agent.isRunning`
- Error display inline
- **No scroll logic exists** — need to add `useAutoScroll`

### File Structure (Changes from Story 4.5)

```
src/
├── hooks/
│   └── useAutoScroll.ts          # NEW — auto-scroll custom hook
├── components/
│   ├── ChatView.tsx              # UPDATE — add useAutoScroll + refs
│   ├── ChatInput.tsx             # unchanged
│   ├── MessageBubble.tsx         # unchanged
│   ├── MarkdownContent.tsx       # unchanged
│   └── ActivityIndicator.tsx     # unchanged
├── __tests__/
│   ├── use-auto-scroll.test.ts   # NEW — hook unit tests
│   ├── chat-view.test.tsx        # UPDATE — verify scroll elements
│   ├── markdown-content.test.tsx # unchanged
│   ├── message-bubble.test.tsx   # unchanged
│   ├── chat-input.test.tsx       # unchanged
│   ├── agent.test.ts             # unchanged
│   ├── app.test.tsx              # unchanged
│   └── env.test.ts               # unchanged
└── ...                           # everything else unchanged
```

### Testing Strategy

**`useAutoScroll` tests** (`src/__tests__/use-auto-scroll.test.ts`):

Testing a hook that interacts with DOM scroll properties requires careful setup:

- Use `renderHook` from `@testing-library/react` to test the hook
- Mock `scrollIntoView` on the sentinel element
- Simulate scroll state via `Object.defineProperty` on the container element for `scrollTop`, `scrollHeight`, `clientHeight`
- Fire `scroll` events to trigger pause/resume detection

**Test cases:**
1. Returns `containerRef` and `bottomRef` (both are ref objects)
2. Calls `scrollIntoView` on bottomRef when deps change and user is at bottom
3. Does NOT call `scrollIntoView` when user has scrolled up (simulated via scrollTop/scrollHeight mismatch)
4. Resumes scrolling after user scrolls back to bottom

**ChatView test updates:**
- Verify the scroll container div has the expected class (`overflow-y-auto`)
- Verify a sentinel div exists at the end of the messages list

### Previous Story Intelligence

From Story 4.5 (just completed):
- `rehype-highlight` is mocked in tests: `vi.mock("rehype-highlight", () => ({ default: () => () => {} }));`
- `mockCopilotKit` now includes `subscribe: vi.fn(() => ({ unsubscribe: vi.fn() }))`
- Components follow presentational pattern with Tailwind classes
- Tests use `@testing-library/react` with `vitest`
- New `src/hooks/` directory will be created — first hook in the project

### Potential Pitfalls

1. **`scrollIntoView` not available in jsdom**: jsdom doesn't implement `scrollIntoView`. Must mock it in tests: `Element.prototype.scrollIntoView = vi.fn()`.
2. **Scroll properties in jsdom**: `scrollTop`, `scrollHeight`, `clientHeight` all return 0 in jsdom. Must use `Object.defineProperty` to set them in tests.
3. **Passive event listener**: Use `{ passive: true }` on scroll listener to avoid blocking the main thread.
4. **`deps` ESLint warning**: The `useEffect` with spread `deps` will trigger `react-hooks/exhaustive-deps` warning. Suppress with `eslint-disable-next-line`.
5. **Initial render**: On initial render, `isAtBottomRef` should be `true` so the first message auto-scrolls.
6. **Empty state**: `useAutoScroll` refs are not used in the empty state branch of ChatView. The refs will be attached only in the messages state branch. This is fine — the hook handles null refs gracefully.

### Project Structure Notes

- New `src/hooks/` directory follows React convention for custom hooks
- Hook file named `useAutoScroll.ts` (not `.tsx` — no JSX in hooks)
- Test file matches existing pattern: `src/__tests__/use-auto-scroll.test.ts`

### References

- [Source: epics.md — Story 4.4 definition]
- [Source: PRD prd-talk-frontend-2026-06-28/prd.md — FR-1, FR-4]
- [Source: Story 4.5 — MarkdownContent handles streaming re-renders, mock patterns]
- [Source: Story 4.3 — ChatView component structure, test mock patterns]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
