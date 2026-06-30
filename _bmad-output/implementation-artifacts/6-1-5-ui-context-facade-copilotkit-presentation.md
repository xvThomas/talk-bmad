# Story 6.1.5: UI context facade (CopilotKit / presentation separation)

Status: ready-for-dev

## Story

As a developer,
I want a dedicated React UI context between CopilotKit hooks and presentation components,
so that the UI layer is decoupled, easier to test, and safer to evolve during Epic 6.

## Acceptance Criteria (BDD)

1. **Given** the chat UI reads conversation state
   **When** `ChatView` renders
   **Then** presentation components consume a dedicated UI context/view-model instead of directly reading CopilotKit internals
   **And** no functional behavior changes for end users

2. **Given** tool calls, reasoning, errors, and activity states
   **When** events flow through the app
   **Then** the UI context exposes normalized state for presentation components
   **And** Story 6.1, 6.2, 6.3, and 6.4 behaviors remain unchanged

3. **Given** tests for chat rendering
   **When** the refactor is complete
   **Then** existing tests continue to pass
   **And** new tests cover context provider behavior and view-model contract

4. **Given** future migration away from `HttpAgent`
   **When** the transport implementation changes in Epic 7
   **Then** presentation components require minimal or no changes thanks to the UI context boundary

## Tasks / Subtasks

- [ ] Task 1: Introduce a dedicated chat UI context provider (AC: #1, #2, #4)
  - [ ] 1.1 Create `src/context/ChatUIContext.tsx` with provider + hook (`useChatUIContext`)
  - [ ] 1.2 Move CopilotKit orchestration from `ChatView` into provider:
    - `useAgent`, `useCopilotKit`
    - `onError` subscription
    - `handleSend` logic with `forwardedProps`
  - [ ] 1.3 Expose a transport-agnostic view-model contract for presentation:
    - `visibleMessages` (from `normalizeMessages`)
    - `isRunning`
    - `error`
    - `setError` or clear-error action
    - `sendMessage(content)`
    - model/thinking state + setters
  - [ ] 1.4 Keep all user-visible behavior identical to current implementation

- [ ] Task 2: Refactor `ChatView` to presentation composition (AC: #1, #2)
  - [ ] 2.1 Replace direct `useAgent` / `useCopilotKit` calls in `ChatView` with `useChatUIContext`
  - [ ] 2.2 Preserve current rendering branches exactly:
    - `reasoning` -> `ReasoningBlock`
    - `tool-call` -> `ToolCallItem`
    - `user|assistant` -> `MessageBubble`
  - [ ] 2.3 Preserve existing auto-scroll trigger behavior (length/content/isRunning)
  - [ ] 2.4 Preserve current empty-state vs conversation-state layout behavior

- [ ] Task 3: Keep normalized message boundary in config layer (AC: #2, #4)
  - [ ] 3.1 Keep `normalizeMessages` as the transformation boundary used by provider
  - [ ] 3.2 Do not move AG-UI protocol parsing logic into presentation components
  - [ ] 3.3 Ensure provider contract does not expose raw CopilotKit internals to child components

- [ ] Task 4: Testing and regression safety (AC: #2, #3)
  - [ ] 4.1 Add provider tests in `src/__tests__/chat-ui-context.test.tsx`:
    - send flow
    - forwarded props model/thinking
    - error subscription handling
    - visibleMessages projection
  - [ ] 4.2 Update existing `ChatView` tests to mock provider contract instead of CopilotKit internals where relevant
  - [ ] 4.3 Ensure existing Story 6.1 tool-call tests remain green
  - [ ] 4.4 Run full `pnpm test`, `pnpm lint`, `pnpm format`

## Dev Notes

### Why this story exists now (Epic 6)

- Story 6.1 is done and introduced richer message roles (`reasoning`, `tool-call`) plus reconciliation logic in `normalizeMessages`.
- Upcoming 6.2/6.3/6.4 add more interaction complexity (interrupt, cancel, inline errors).
- A UI context facade now reduces coupling and lowers risk for the remaining Epic 6 stories.

### Current implementation snapshot (must preserve)

- `ChatView` currently mixes orchestration + presentation:
  - CopilotKit hooks (`useAgent`, `useCopilotKit`)
  - `onError` subscription
  - send/run logic
  - model/thinking state
  - rendering branches for `reasoning` / `tool-call` / bubbles
- `normalizeMessages` is already a strong boundary with protocol reconciliation logic.

### Architecture guardrails

1. **No behavior drift**
   - This is a refactor story. No UX changes expected.
   - Keep all labels, button behavior, tool expansion semantics, and error rendering unchanged.

2. **Single orchestration owner**
   - `ChatUIContext` becomes orchestration owner for conversation state consumption.
   - `ChatView` should be a composition/presentation container.

3. **Transport-agnostic contract**
   - Context must expose a stable UI contract independent from CopilotKit-specific objects.
   - Avoid leaking `agent` object directly into presentation components.

4. **Do not regress Story 6.1 fixes**
   - Keep `normalizeMessages` behavior for:
     - out-of-order tool results
     - empty-result completion handling
     - assistant content + toolCalls coexistence

5. **No new dependencies**
   - Use existing React + test stack.

### Suggested file plan

**NEW**

- `src/context/ChatUIContext.tsx`
- `src/__tests__/chat-ui-context.test.tsx`

**UPDATE**

- `src/components/ChatView.tsx`
- `src/__tests__/chat-view.test.tsx`

**UNCHANGED BUT CRITICAL**

- `src/config/normalize-messages.ts` (reuse as-is; only touch if required by contract typing)
- `src/components/ToolCallItem.tsx`
- `src/components/ReasoningBlock.tsx`
- `src/components/MessageBubble.tsx`

### Data contract proposal (provider -> presentation)

```ts
interface ChatUIViewModel {
  visibleMessages: ChatMessageViewModel[];
  isRunning: boolean;
  error: string | null;
  selectedModel: ModelAlias;
  thinkingEffort: ThinkingEffort;
  supportsThinkingForSelectedModel: boolean;
  sendMessage: (content: string) => void;
  setSelectedModel: (model: ModelAlias) => void;
  setThinkingEffort: (effort: ThinkingEffort) => void;
  clearError: () => void;
}
```

### Regression checklist (must pass)

- Tool call rows still appear/collapse/expand correctly (Story 6.1)
- In-progress tool indicator stops on final assistant output
- Empty tool result does not show misleading `RESULT` label
- Reasoning blocks still render in chronological order (Story 5.3)
- Model/thinking forwarded props remain identical
- Error subscription + inline error block behavior unchanged

### Testing strategy

1. **Provider unit/integration tests**
   - Mock CopilotKit hooks at provider level
   - Assert provider contract outputs expected values/actions

2. **ChatView tests**
   - Shift to contract-driven tests (context mock), not transport internals
   - Keep end-to-end rendering expectations unchanged

3. **Full suite + lint/format gate**
   - `pnpm test`
   - `pnpm lint`
   - `pnpm format`

### Git intelligence (recent patterns to follow)

Recent commits in `talk-ui` show the established patterns:

- `a509dba` — tool-call display + dedicated `ToolCallItem`
- `c3dc0c5` — error block handling + normalize tests reinforcement
- `436da65` — reasoning rendering through normalized message roles

Follow the same style:

- Strong test-first or test-with-change discipline
- Keep logic centralized in config/transformation layers
- Keep presentational components focused and simple

### References

- [Source: planning-artifacts/epics.md — Epic 6 Story 6.1.5]
- [Source: planning-artifacts/prds/prd-talk-frontend-2026-06-28/prd.md — FR-26, FR-27, FR-28]
- [Source: planning-artifacts/prds/prd-talk-frontend-2026-06-28/prd.md — NFR-17, NFR-18]
- [Source: implementation-artifacts/6-1-affichage-des-tool-calls.md]
- [Source: implementation-artifacts/5-3-affichage-du-raisonnement.md]
- [Source: src/components/ChatView.tsx]
- [Source: src/config/normalize-messages.ts]

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

### Completion Notes List

- Comprehensive context generated for Story 6.1.5 (Phase A) with explicit no-regression guardrails for stories 6.1/6.2/6.3/6.4.
- Provider contract and file-level plan included to accelerate `dev-story` execution.

### File List

- _bmad-output/implementation-artifacts/6-1-5-ui-context-facade-copilotkit-presentation.md
