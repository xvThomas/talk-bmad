# Story 6.1.5: UI context facade (CopilotKit / presentation separation)

Status: done

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
   **And** Story 6.1, 6.3, 6.4, and 6.5 behaviors remain unchanged

3. **Given** tests for chat rendering
   **When** the refactor is complete
   **Then** existing tests continue to pass
   **And** new tests cover context provider behavior and view-model contract

4. **Given** future migration away from `HttpAgent`
   **When** the transport implementation changes in Epic 7
   **Then** presentation components require minimal or no changes thanks to the UI context boundary

5. **Given** a tool call has started and no final assistant message has been emitted yet
   **When** the UI receives tool-call events
   **Then** the corresponding tool item is rendered immediately in the conversation
   **And** the item is expandable/clickable while still in progress
   **And** partial args/result content is visible as soon as available

6. **Given** tool-call events arrive before the final assistant completion event
   **When** state is reconciled in the UI context
   **Then** rendering does not wait for final assistant completion to expose tool details
   **And** final assistant completion only transitions run status, without gating tool item interactivity

7. **Given** a user wants to reduce visual noise in the conversation flow
   **When** they toggle the Tools selector from `Show` to `Hide`
   **Then** `tool-call` rows are hidden from the message list
   **And** non-tool messages (`user`, `assistant`, `reasoning`, `error/activity`) remain visible and unchanged

8. **Given** tool rows are hidden via the Tools selector
   **When** the user toggles back to `Show`
   **Then** tool rows are rendered again immediately using current normalized state
   **And** no new backend request is triggered by this display toggle

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
  - [ ] 1.5 Add per-tool incremental state projection in the provider (`pending|running|done|error`) so presentation can render tool rows before assistant final completion (AC: #5, #6)

- [ ] Task 2: Refactor `ChatView` to presentation composition (AC: #1, #2)
  - [ ] 2.1 Replace direct `useAgent` / `useCopilotKit` calls in `ChatView` with `useChatUIContext`
  - [ ] 2.2 Preserve current rendering branches exactly:
    - `reasoning` -> `ReasoningBlock`
    - `tool-call` -> `ToolCallItem`
    - `user|assistant` -> `MessageBubble`
  - [ ] 2.3 Preserve existing auto-scroll trigger behavior (length/content/isRunning)
  - [ ] 2.4 Preserve current empty-state vs conversation-state layout behavior
  - [ ] 2.5 Ensure tool rows remain interactive while run is active (expand/collapse enabled before assistant final output) (AC: #5)
  - [ ] 2.6 Add a compact Tools display selector (`Tools: Show/Hide`) near model/thinking selectors, reusing the existing tool icon style (AC: #7, #8)
  - [ ] 2.7 Apply tool-row filtering at presentation level from provider state (`showTools`) without mutating normalized message data (AC: #7, #8)

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
  - [ ] 4.4 Add a sequence test where tool-call events arrive before assistant final output and assert immediate render + expandability
  - [ ] 4.5 Add a sequence test validating live update of expanded tool content as tool args/result deltas arrive
  - [ ] 4.6 Add tests for Tools selector toggle:
    - hide tool rows when set to `Hide`
    - restore tool rows when toggled back to `Show`
    - ensure non-tool rows remain visible in both states
  - [ ] 4.7 Run full `pnpm test`, `pnpm lint`, `pnpm format`

## Dev Notes

### Why this story exists now (Epic 6)

- Story 6.1 is done and introduced richer message roles (`reasoning`, `tool-call`) plus reconciliation logic in `normalizeMessages`.
- Upcoming 6.3/6.4/6.5 add more interaction complexity (interrupt, cancel, inline errors).
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
   - This is a refactor-first story with one explicit UX correction: tool rows become interactable immediately when tool events arrive.
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
- Tool call rows are expandable before the final assistant message is emitted
- Tools selector (`Show/Hide`) hides only tool rows and does not affect user/assistant/reasoning visibility
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

3. **Event-order and streaming tests**
   - Validate ordering where tool events precede assistant final completion
   - Validate expanded tool row remains open and receives incremental payload updates

4. **Full suite + lint/format gate**
   - `pnpm test`
   - `pnpm lint`
   - `pnpm format`

### Implementation sequence (ready-to-execute)

1. **Extract orchestration to provider**
   - Create `src/context/ChatUIContext.tsx` with `ChatUIProvider` + `useChatUIContext`.
   - Move from `ChatView` to provider:
     - `useAgent`, `useCopilotKit`
     - error subscription (`copilotkit.subscribe({ onError })`)
     - `handleSend` with `forwardedProps` (`model`, conditional `thinkingEffort`)
   - Expose a stable VM contract: `visibleMessages`, `isRunning`, `error`, selectors state, actions.

2. **Guarantee real-time tool item interactivity**
   - Keep `normalizeMessages` as message transformation boundary.
   - In provider, project tool-call items directly from normalized stream updates.
   - Ensure no gating by assistant final completion event for tool row render/expandability.

3. **Refactor ChatView to pure composition**
   - Replace direct CopilotKit hooks with `useChatUIContext`.
   - Keep existing render branches unchanged (`reasoning` / `tool-call` / bubble).
   - Keep existing auto-scroll dependency signals (length/last-content/isRunning).

4. **Adjust ToolCallItem behavior for in-progress expansion**
   - Allow expand/collapse while in-progress.
   - Keep in-progress indicator visible when `toolResult` is not finalized.
   - Preserve current rule: no `Result` section for empty-string completion.

5. **Tests and gates**
   - Add `src/__tests__/chat-ui-context.test.tsx` for provider contract.
   - Update `src/__tests__/chat-view.test.tsx` to consume context contract.
   - Update `src/__tests__/tool-call-item.test.tsx` to assert in-progress expandability.
   - Add sequence test for event order: tool events before assistant final message.
   - Run `pnpm test`, `pnpm lint`, `pnpm format`.

### Definition of Done (Story 6.1.5)

- `ChatView` no longer imports CopilotKit hooks directly.
- Provider exposes a transport-agnostic UI VM contract consumed by presentation.
- Tool rows are visible and expandable before assistant final completion.
- Existing Story 6.1 behavior is preserved (no regression in labels/layout/order).
- All targeted tests pass, including event-order and incremental-update cases.

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

- Comprehensive context generated for Story 6.1.5 (Phase A) with explicit no-regression guardrails for stories 6.1/6.3/6.4/6.5.
- Provider contract and file-level plan included to accelerate `dev-story` execution.

### Review Findings

- [x] [Review][Decision] D1: `showConversationLayout = hasMessages || isRunning` — accepted and kept as intentional UX behavior for immediate first-question rendering
- [x] [Review][Decision] D2: SVG icons added to ModelSelector/ThinkingEffortSelector — accepted and kept
- [x] [Review][Patch] P1: Filename typo triple-L `use-auto-scrolll.ts` → `use-auto-scroll.ts` [src/hooks/use-auto-scroll.ts]
- [x] [Review][Patch] P2: `optimisticUserMessages` never pruned — linear memory leak across session [src/context/ChatUIContext.tsx]
- [x] [Review][Patch] P3: Context `value` object + callbacks (`sendMessage`, `clearError`) recreated every render — memoized with useMemo/useCallback [src/context/ChatUIContext.tsx]
- [x] [Review][Patch] P4: `max-h-[360px]` + `overflow-hidden` clips tool content > 360px with no scroll affordance [src/components/ChatView.tsx]
- [x] [Review][Patch] P5: `aria-hidden` without `inert` — focusable button inside hidden tool-call wrapper (WCAG 4.1.2) [src/components/ChatView.tsx]
- [x] [Review][Patch] P6: `sendMessage("")` creates permanent ghost optimistic message (normalizeMessages drops blank but optimistic array never clears it) [src/context/ChatUIContext.tsx]
- [x] [Review][Patch] P7: Missing provider-level integration test for out-of-order tool-result arrival per DoD [src/__tests__/chat-ui-context.test.tsx]
- [x] [Review][Defer] W1: Race condition isRunning / double-send in same frame [src/context/ChatUIContext.tsx] — deferred, pre-existing pattern
- [x] [Review][Defer] W2: `runAgent` .catch swallows non-Error rejections without logging [src/context/ChatUIContext.tsx] — deferred, pre-existing
- [x] [Review][Defer] W3: `formatJson` no truncation for very large payloads [src/components/ToolCallItem.tsx] — deferred, pre-existing

### File List

- \_bmad-output/implementation-artifacts/6-1-5-ui-context-facade-copilotkit-presentation.md
