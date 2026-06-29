# Story 5.2: Sélection du thinking effort

Status: ready-for-dev

## Story

As an end user,
I want to control the thinking/reasoning effort when the model supports it,
so that I can decide between faster responses or deeper reasoning.

## Acceptance Criteria (BDD)

1. **Given** the selected model supports thinking (`haiku-4.5`, `sonnet-4.6`, `opus-4.6`, `o4-mini`) **When** the input area renders **Then** a thinking effort selector is visible with options: `off`, `low`, `medium`, `high` **And** the default is `off`

2. **Given** the selected model does NOT support thinking (`gpt-5.4`, `mistral-small`, `agent`) **When** the input area renders **Then** the thinking effort selector is hidden

3. **Given** a thinking effort is selected **When** the user sends a message **Then** `forwardedProps.thinkingEffort` is set to the selected value

4. **Given** the user switches to a non-thinking model **When** the model changes **Then** the thinking selector disappears **And** `forwardedProps.thinkingEffort` is omitted from the next request

5. **Given** the thinking effort is `off` **When** the user sends a message **Then** `forwardedProps.thinkingEffort` is omitted (not sent as "off")

## Tasks / Subtasks

- [ ] Task 1: Extend model catalog with thinking metadata (AC: #1, #2)
  - [ ] 1.1 Add `THINKING_MODELS` set or `supportsThinking` mapping to `src/config/models.ts`
  - [ ] 1.2 Add `THINKING_EFFORTS` const array and `ThinkingEffort` type with Zod schema
  - [ ] 1.3 Add `DEFAULT_THINKING_EFFORT` constant (`"off"`)
  - [ ] 1.4 Export `supportsThinking(model: ModelAlias): boolean` helper
  - [ ] 1.5 Add unit tests in `src/__tests__/models.test.ts`

- [ ] Task 2: Create ThinkingEffortSelector component (AC: #1)
  - [ ] 2.1 Create `src/components/ThinkingEffortSelector.tsx` — same custom dropdown pattern as ModelSelector
  - [ ] 2.2 Props: `value: ThinkingEffort`, `onChange: (effort: ThinkingEffort) => void`, `disabled?: boolean`
  - [ ] 2.3 Keyboard navigation (ArrowUp/Down/Enter/Escape), click-outside close, dropUp detection
  - [ ] 2.4 Aria label `"Effort de réflexion"`, `role="listbox"` with `role="option"` items
  - [ ] 2.5 Same styling conventions as ModelSelector (border-white/15, bg-white/5, text-[11px], etc.)

- [ ] Task 3: Integrate into ChatView (AC: #1, #2, #3, #4, #5)
  - [ ] 3.1 Add `thinkingEffort` state (default: `DEFAULT_THINKING_EFFORT`)
  - [ ] 3.2 Conditionally render ThinkingEffortSelector next to ModelSelector when `supportsThinking(selectedModel)`
  - [ ] 3.3 Reset `thinkingEffort` to `"off"` in `handleModelChange` when new model doesn't support thinking
  - [ ] 3.4 Update `handleSend`: include `thinkingEffort` in `forwardedProps` only when value ≠ `"off"` AND model supports thinking
  - [ ] 3.5 Pass `disabled={agent.isRunning}` to ThinkingEffortSelector

- [ ] Task 4: Write integration tests (AC: all)
  - [ ] 4.1 Update `src/__tests__/chat-view.test.tsx` — test thinking selector visibility based on model
  - [ ] 4.2 Test thinking effort forwarded in forwardedProps when effort ≠ off
  - [ ] 4.3 Test thinkingEffort omitted when effort is "off"
  - [ ] 4.4 Test thinkingEffort omitted when model doesn't support thinking
  - [ ] 4.5 Test selector reset to "off" on model switch to non-thinking model
  - [ ] 4.6 Test selector disabled during agent.isRunning

## Dev Notes

### Architecture Compliance

- **State ownership pattern**: ChatView owns ALL state (model + thinkingEffort). Components are controlled via props.
- **Forwarding contract (Backend FR-16)**: `forwardedProps.thinkingEffort` set to `"low"`, `"medium"`, or `"high"` → reasoning activated. Absent/empty/"off" → thinking not activated. Invalid value → backend ignores.
- **Conditional forwarding**: Do NOT send `thinkingEffort: "off"` — simply omit the key entirely. Use object spread conditionally:
  ```ts
  const forwardedProps: Record<string, string> = { model: selectedModel };
  if (thinkingEffort !== "off" && supportsThinking(selectedModel)) {
    forwardedProps.thinkingEffort = thinkingEffort;
  }
  ```
- **Zod v4**: Import from `"zod/v4"` — NOT `"zod"`.
- **No `any` types** anywhere in implementation (NFR-1).

### Component Pattern (from Story 5.1)

The ThinkingEffortSelector MUST follow the exact same dropdown pattern established in ModelSelector:
- Custom button + `<ul role="listbox">` + `<li role="option">`
- `useState` for `open`, `dropUp`, `focusedIndex`
- `useRef` for `containerRef`, `listRef`
- Click-outside listener via `document.addEventListener("mousedown", ...)`
- `handleOpen` calculates `dropUp` via `getBoundingClientRect()` (threshold 200px)
- `handleKeyDown` on `<ul>`: ArrowDown, ArrowUp, Enter, Space, Escape
- `useEffect` focuses `listRef` on open
- Custom scrollbar: `[&::-webkit-scrollbar]:w-1.5` (same as ModelSelector)

### UI Layout in ChatView

Current layout inside the `chatBox` div:
```
┌─────────────────────────────────────┐
│ [textarea]                 [send▶]  │  ← ChatInput row
│                [ThinkingSelector] [ModelSelector]  │  ← controls row (justify-end)
└─────────────────────────────────────┘
```

The ThinkingEffortSelector sits LEFT of ModelSelector in the same `flex justify-end pt-2.5` row. Add a small gap (`gap-2`) between them.

### Thinking Model Mapping (from PRD FR-5)

| Model | Thinking Support | PRD Type |
|-------|-----------------|----------|
| haiku-4.5 | ✅ | budget |
| sonnet-4.6 | ✅ | budget |
| opus-4.6 | ✅ | adaptive |
| o4-mini | ✅ | effort |
| gpt-5.4 | ❌ | — |
| mistral-small | ❌ | — |
| agent | ❌ | — |

For this story, the thinking "type" distinction (budget/adaptive/effort) is NOT relevant to the UI. All thinking-capable models get the same selector with the same options. The backend handles type-specific behavior.

### Project Structure Notes

- All source in `talk-ui/src/`
- Config/types: `src/config/models.ts` (extend here)
- Components: `src/components/ThinkingEffortSelector.tsx` (NEW file)
- Tests: `src/__tests/models.test.ts` (extend), `src/__tests__/chat-view.test.tsx` (extend)
- Labels/aria in French (e.g., `"Effort de réflexion"`)
- No i18n library — hardcoded French strings

### Previous Story (5.1) Lessons

- **Custom dropdown reuse**: ModelSelector was refactored out of ChatInput into its own component. ThinkingEffortSelector follows the same approach.
- **Review finding applied**: Use typed callbacks (`onChange: (effort: ThinkingEffort) => void`), no `any` leaks.
- **Review finding applied**: Integration tests should cover disabled state + default forwarding (omission when "off").
- **Lint trap**: Don't set state inside `useEffect` that depends on that state. `setFocusedIndex` goes in `handleOpen`, not in the effect.
- **Width**: Use `w-max whitespace-nowrap` on the listbox to avoid text wrapping to 2 lines.
- **Testing pattern**: Use `screen.getByLabelText("...")` for the trigger button, `screen.getByRole("option", { name: "..." })` for options.

### Testing Standards

- Vitest 4.1.9 + @testing-library/react 16 + @testing-library/user-event 14
- Test file location: `src/__tests__/`
- Assertions: `expect(...)` with vitest matchers
- Mock pattern for CopilotKit: already established in `chat-view.test.tsx` (vi.mock + vi.fn())
- To test `forwardedProps`, spy on `copilotkit.runAgent` mock and assert the argument object

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 5, Story 5.2]
- [Source: PRD FR-5, FR-6, FR-7, FR-16 — Model catalog, thinking selector, forwarding contract]
- [Source: PRD NFR-1 — Type safety, Zod validation]
- [Source: PRD NFR-11 — Accessibility, keyboard navigation]
- [Source: _bmad-output/implementation-artifacts/5-1-selection-du-modele-llm.md — Previous story patterns]
- [Source: src/config/models.ts — Current model catalog]
- [Source: src/components/ModelSelector.tsx — Dropdown pattern reference]
- [Source: src/components/ChatView.tsx — Integration target, state ownership]

## Dev Agent Record

### Agent Model Used

(to be filled by dev agent)

### Completion Notes List

(to be filled by dev agent)

### Change Log

| Date | Change | Reason |
|------|--------|--------|

### File List

**NEW:**
- `src/components/ThinkingEffortSelector.tsx`

**UPDATE:**
- `src/config/models.ts` — Add thinking metadata, ThinkingEffort type, supportsThinking helper
- `src/components/ChatView.tsx` — Add thinkingEffort state, conditional rendering, forwarding logic
- `src/__tests__/models.test.ts` — Tests for new exports
- `src/__tests__/chat-view.test.tsx` — Integration tests for thinking selector behavior
